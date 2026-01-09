"""
Twelve Data API client for fetching historical market data.

Features:
- Pagination for large date ranges (5000 bars max per request)
- Rate limiting (8 requests/minute for free tier)
- Retry logic with exponential backoff
- Fully adjusted prices (splits + dividends)
"""

import asyncio
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Optional
import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class OHLCVBar:
    """Single OHLCV bar from Twelve Data."""
    datetime: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class TwelveDataError(Exception):
    """Custom exception for Twelve Data API errors."""
    pass


class TwelveDataClient:
    """
    Client for fetching historical market data from Twelve Data API.
    
    API Constraints:
    - 1 credit per symbol for time_series endpoint
    - Max outputsize: 5000 bars per request
    - Free tier: 8 requests/minute, 800 requests/day
    """
    
    MAX_OUTPUT_SIZE = 5000
    RATE_LIMIT_DELAY = 8.0  # seconds between requests (free tier: 8 req/min)
    MAX_RETRIES = 3
    RETRY_DELAY = 2.0
    
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.twelvedata_api_key
        self.base_url = settings.twelvedata_base_url
        self._last_request_time: Optional[float] = None
        
    async def _wait_for_rate_limit(self):
        """Enforce rate limiting between requests."""
        if self._last_request_time is not None:
            elapsed = asyncio.get_event_loop().time() - self._last_request_time
            if elapsed < self.RATE_LIMIT_DELAY:
                wait_time = self.RATE_LIMIT_DELAY - elapsed
                logger.debug(f"Rate limiting: waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
        self._last_request_time = asyncio.get_event_loop().time()
    
    async def _make_request(
        self,
        endpoint: str,
        params: dict,
        retries: int = 0
    ) -> dict:
        """Make a rate-limited request with retry logic."""
        await self._wait_for_rate_limit()
        
        url = f"{self.base_url}/{endpoint}"
        params["apikey"] = self.api_key
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                # Check for API errors in response
                if data.get("status") == "error":
                    error_msg = data.get("message", "Unknown API error")
                    raise TwelveDataError(f"API Error: {error_msg}")
                
                return data
                
        except httpx.HTTPStatusError as e:
            if retries < self.MAX_RETRIES and e.response.status_code in [429, 500, 502, 503]:
                wait_time = self.RETRY_DELAY * (2 ** retries)
                logger.warning(f"Request failed ({e.response.status_code}), retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                return await self._make_request(endpoint, params, retries + 1)
            raise TwelveDataError(f"HTTP Error: {e}")
        except httpx.RequestError as e:
            if retries < self.MAX_RETRIES:
                wait_time = self.RETRY_DELAY * (2 ** retries)
                logger.warning(f"Request error, retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                return await self._make_request(endpoint, params, retries + 1)
            raise TwelveDataError(f"Request Error: {e}")
    
    def _parse_bar(self, raw: dict) -> OHLCVBar:
        """Parse raw API response into OHLCVBar."""
        return OHLCVBar(
            datetime=datetime.strptime(raw["datetime"], "%Y-%m-%d %H:%M:%S"),
            open=float(raw["open"]),
            high=float(raw["high"]),
            low=float(raw["low"]),
            close=float(raw["close"]),
            volume=int(raw.get("volume", 0))
        )
    
    async def fetch_time_series(
        self,
        symbol: str,
        interval: str = "1min",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        adjust: str = "all",
        outputsize: Optional[int] = None
    ) -> List[OHLCVBar]:
        """
        Fetch time series data for a symbol.
        
        Args:
            symbol: Ticker symbol (e.g., "AAPL", "SPY")
            interval: Bar interval (1min, 5min, 15min, etc.)
            start_date: Start of date range
            end_date: End of date range
            adjust: Price adjustment mode ("all" for splits + dividends)
            outputsize: Number of bars to fetch (max 5000)
        
        Returns:
            List of OHLCVBar sorted by datetime ascending
        """
        params = {
            "symbol": symbol,
            "interval": interval,
            "adjust": adjust,
            "outputsize": outputsize or self.MAX_OUTPUT_SIZE,
            "order": "asc",
            "timezone": "America/New_York"
        }
        
        if start_date:
            params["start_date"] = start_date.strftime("%Y-%m-%d")
        if end_date:
            params["end_date"] = end_date.strftime("%Y-%m-%d")
        
        logger.info(f"Fetching {symbol} {interval} from {start_date} to {end_date}")
        
        try:
            data = await self._make_request("time_series", params)
        except TwelveDataError as e:
            # Handle "no data available" gracefully
            if "No data is available" in str(e):
                logger.warning(f"No data available for {symbol} in date range {start_date} to {end_date}")
                return []
            raise
        
        if "values" not in data:
            logger.warning(f"No data returned for {symbol}")
            return []
        
        bars = [self._parse_bar(v) for v in data["values"]]
        logger.info(f"Fetched {len(bars)} bars for {symbol}")
        
        return bars
    
    async def fetch_full_history(
        self,
        symbol: str,
        months: int = 6,
        interval: str = "1min"
    ) -> List[OHLCVBar]:
        """
        Fetch full history with automatic pagination.
        
        Note: Free tier may have limited historical data access.
        This method will fetch as much data as available.
        
        Args:
            symbol: Ticker symbol
            months: Number of months of history to fetch
            interval: Bar interval
        
        Returns:
            Complete list of OHLCVBar sorted by datetime ascending
        """
        all_bars: List[OHLCVBar] = []
        
        # Strategy: First try to get recent data without date range
        # This works better with free tier limitations
        logger.info(f"Fetching recent {symbol} data (no date range)...")
        
        try:
            # First request: get most recent 5000 bars
            bars = await self.fetch_time_series(
                symbol=symbol,
                interval=interval,
                adjust="all",
                outputsize=self.MAX_OUTPUT_SIZE
            )
            
            if bars:
                all_bars.extend(bars)
                logger.info(f"Got {len(bars)} recent bars for {symbol}")
                
                # If we got data, try to get more historical data
                # by going backwards from the earliest bar
                earliest_bar = min(bars, key=lambda x: x.datetime)
                target_start = datetime.now() - timedelta(days=months * 30)
                
                # Only try to get more if we need more history
                if earliest_bar.datetime > target_start:
                    logger.info(f"Trying to fetch more historical data for {symbol}...")
                    
                    # Calculate chunk size based on interval
                    if interval == "1min":
                        chunk_days = 10  # ~3900 bars, leaving room for safety
                    elif interval == "5min":
                        chunk_days = 50
                    else:
                        chunk_days = 100
                    
                    current_end = earliest_bar.datetime - timedelta(minutes=1)
                    request_count = 1
                    consecutive_empty = 0
                    
                    while current_end > target_start and consecutive_empty < 3:
                        current_start = current_end - timedelta(days=chunk_days)
                        
                        try:
                            more_bars = await self.fetch_time_series(
                                symbol=symbol,
                                interval=interval,
                                start_date=current_start,
                                end_date=current_end,
                                adjust="all"
                            )
                            
                            if more_bars:
                                all_bars.extend(more_bars)
                                request_count += 1
                                consecutive_empty = 0
                                
                                logger.info(
                                    f"Progress: {symbol} chunk {request_count}, "
                                    f"total bars: {len(all_bars)}, "
                                    f"date range: {current_start.date()} to {current_end.date()}"
                                )
                                
                                # Move end to before the earliest bar we just got
                                earliest_new = min(more_bars, key=lambda x: x.datetime)
                                current_end = earliest_new.datetime - timedelta(minutes=1)
                            else:
                                consecutive_empty += 1
                                current_end = current_start - timedelta(days=1)
                                logger.info(f"No data in chunk, moving back ({consecutive_empty}/3 empty)")
                                
                        except TwelveDataError as e:
                            if "No data is available" in str(e):
                                consecutive_empty += 1
                                current_end = current_start - timedelta(days=1)
                                logger.info(f"No data available in chunk, moving back ({consecutive_empty}/3)")
                            else:
                                raise
                    
                    if consecutive_empty >= 3:
                        logger.info(f"Reached end of available historical data for {symbol}")
            else:
                logger.warning(f"No data returned for {symbol} - API may have limitations")
                
        except TwelveDataError as e:
            logger.error(f"Error fetching {symbol}: {e}")
            raise
        
        # Remove duplicates and sort
        seen_times = set()
        unique_bars = []
        for bar in all_bars:
            if bar.datetime not in seen_times:
                seen_times.add(bar.datetime)
                unique_bars.append(bar)
        
        unique_bars.sort(key=lambda x: x.datetime)
        
        if unique_bars:
            logger.info(
                f"Completed fetching {symbol}: {len(unique_bars)} unique bars, "
                f"date range: {unique_bars[0].datetime} to {unique_bars[-1].datetime}"
            )
        else:
            logger.warning(f"No data fetched for {symbol}")
        
        return unique_bars
    
    async def check_api_status(self) -> dict:
        """Check API status and remaining credits."""
        try:
            data = await self._make_request("api_usage", {})
            return {
                "status": "ok",
                "daily_usage": data.get("current_usage", 0),
                "daily_limit": data.get("plan_limit", 0),
                "credits_remaining": data.get("plan_limit", 0) - data.get("current_usage", 0)
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
