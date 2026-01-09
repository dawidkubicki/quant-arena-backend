"""
Market Data API endpoints for fetching and managing historical market data.
"""

import uuid
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.user import User
from app.models.market_data import MarketDataset, MarketData
from app.services.twelvedata import TwelveDataClient, TwelveDataError
from app.utils.auth import get_current_admin
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()

settings = get_settings()


class FetchRequest(BaseModel):
    """Request body for fetching market data."""
    symbols: List[str] = Field(
        default=["AAPL", "SPY"],
        description="List of symbols to fetch"
    )
    months: int = Field(
        default=6,
        ge=1,
        le=12,
        description="Number of months of history to fetch"
    )


class DatasetResponse(BaseModel):
    """Response for a market dataset."""
    id: uuid.UUID
    symbol: str
    interval: str
    start_date: datetime
    end_date: datetime
    total_bars: int
    fetched_at: datetime

    class Config:
        from_attributes = True


class FetchStatusResponse(BaseModel):
    """Response for fetch status."""
    status: str
    message: str
    datasets: Optional[List[DatasetResponse]] = None


class MarketDataStatsResponse(BaseModel):
    """Statistics about stored market data."""
    symbol: str
    total_bars: int
    earliest_date: Optional[datetime]
    latest_date: Optional[datetime]
    datasets_count: int


class MarketDataStatusResponse(BaseModel):
    """Overall status of market data availability."""
    is_ready: bool
    has_aapl: bool
    has_spy: bool
    aapl_bars: int
    spy_bars: int
    aapl_date_range: Optional[dict] = None
    spy_date_range: Optional[dict] = None
    message: str
    api_configured: bool


async def _fetch_and_store_data(
    db: Session,
    symbols: List[str],
    months: int
):
    """
    Background task to fetch and store market data.
    This can take several minutes due to rate limiting.
    
    Note: Free tier has limitations on historical data.
    The function will fetch as much data as available.
    """
    client = TwelveDataClient()
    fetched_count = 0
    
    for symbol in symbols:
        try:
            logger.info(f"Starting fetch for {symbol}...")
            
            # Fetch data from Twelve Data
            bars = await client.fetch_full_history(
                symbol=symbol,
                months=months,
                interval="1min"
            )
            
            if not bars:
                logger.warning(f"No data returned for {symbol} - API may have limitations")
                continue
            
            # Create dataset record
            dataset = MarketDataset(
                id=uuid.uuid4(),
                symbol=symbol,
                interval="1min",
                start_date=bars[0].datetime,
                end_date=bars[-1].datetime,
                total_bars=len(bars),
                fetched_at=datetime.utcnow()
            )
            db.add(dataset)
            db.flush()  # Get the ID
            
            # Batch insert bars
            batch_size = 1000
            for i in range(0, len(bars), batch_size):
                batch = bars[i:i + batch_size]
                db.bulk_insert_mappings(
                    MarketData,
                    [
                        {
                            "dataset_id": dataset.id,
                            "symbol": symbol,
                            "datetime": bar.datetime,
                            "open": bar.open,
                            "high": bar.high,
                            "low": bar.low,
                            "close": bar.close,
                            "volume": bar.volume
                        }
                        for bar in batch
                    ]
                )
                db.flush()
                logger.info(f"Inserted batch {i//batch_size + 1} for {symbol}")
            
            db.commit()
            fetched_count += 1
            logger.info(f"Completed storing {len(bars)} bars for {symbol}")
            
        except TwelveDataError as e:
            logger.error(f"Twelve Data API error for {symbol}: {e}")
            db.rollback()
            # Continue with next symbol instead of failing completely
            continue
        except Exception as e:
            logger.error(f"Error storing data for {symbol}: {e}")
            db.rollback()
            raise
    
    if fetched_count == 0:
        logger.warning("No data was fetched for any symbol")


@router.post("/fetch", response_model=FetchStatusResponse)
async def fetch_market_data(
    request: FetchRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Fetch historical market data from Twelve Data API (admin only).
    
    This endpoint triggers a background task to fetch data for the specified
    symbols. Due to API rate limits, this can take several minutes.
    
    Default symbols: AAPL (trading asset) and SPY (benchmark)
    """
    # Check if API key is configured
    if not settings.twelvedata_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Twelve Data API key not configured. Set TWELVEDATA_API_KEY in .env"
        )
    
    # Validate symbols
    valid_symbols = {"AAPL", "SPY", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA"}
    for symbol in request.symbols:
        if symbol not in valid_symbols:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid symbol: {symbol}. Supported: {valid_symbols}"
            )
    
    # Delete existing data for these symbols (fresh fetch)
    for symbol in request.symbols:
        existing = db.query(MarketDataset).filter(MarketDataset.symbol == symbol).all()
        for dataset in existing:
            db.delete(dataset)
    db.commit()
    
    # Run fetch (this blocks due to rate limits, but keeps connection alive)
    # Note: For production, use Celery or similar for true background processing
    try:
        await _fetch_and_store_data(db, request.symbols, request.months)
        
        # Get created datasets
        datasets = db.query(MarketDataset).filter(
            MarketDataset.symbol.in_(request.symbols)
        ).all()
        
        if not datasets:
            return FetchStatusResponse(
                status="warning",
                message="No data was fetched. Free tier may have limited historical data access. Try with fewer months.",
                datasets=[]
            )
        
        # Build detailed message
        details = []
        for d in datasets:
            details.append(f"{d.symbol}: {d.total_bars} bars ({d.start_date.date()} to {d.end_date.date()})")
        
        return FetchStatusResponse(
            status="completed",
            message=f"Successfully fetched data. {'; '.join(details)}",
            datasets=[DatasetResponse.model_validate(d) for d in datasets]
        )
        
    except TwelveDataError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Twelve Data API error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Fetch failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch market data: {str(e)}"
        )


@router.get("/status", response_model=MarketDataStatusResponse)
def get_market_data_status(
    db: Session = Depends(get_db)
):
    """
    Check if market data is ready for simulations.
    
    Returns the status of AAPL and SPY data availability.
    Both are required for proper alpha/beta calculations.
    """
    # Check AAPL data
    aapl_stats = db.query(
        func.count(MarketData.id).label("total_bars"),
        func.min(MarketData.datetime).label("earliest"),
        func.max(MarketData.datetime).label("latest")
    ).filter(MarketData.symbol == "AAPL").first()
    
    # Check SPY data
    spy_stats = db.query(
        func.count(MarketData.id).label("total_bars"),
        func.min(MarketData.datetime).label("earliest"),
        func.max(MarketData.datetime).label("latest")
    ).filter(MarketData.symbol == "SPY").first()
    
    has_aapl = aapl_stats.total_bars > 0 if aapl_stats else False
    has_spy = spy_stats.total_bars > 0 if spy_stats else False
    is_ready = has_aapl and has_spy
    
    # Build message
    if is_ready:
        message = "Market data is ready. Simulations will use real AAPL/SPY data with alpha/beta calculations."
    elif has_aapl and not has_spy:
        message = "Missing SPY data. Please fetch SPY for benchmark calculations."
    elif has_spy and not has_aapl:
        message = "Missing AAPL data. Please fetch AAPL for trading simulations."
    else:
        message = "No market data available. Please fetch AAPL and SPY data using POST /api/market-data/fetch"
    
    return MarketDataStatusResponse(
        is_ready=is_ready,
        has_aapl=has_aapl,
        has_spy=has_spy,
        aapl_bars=aapl_stats.total_bars if aapl_stats else 0,
        spy_bars=spy_stats.total_bars if spy_stats else 0,
        aapl_date_range={
            "start": aapl_stats.earliest.isoformat() if aapl_stats and aapl_stats.earliest else None,
            "end": aapl_stats.latest.isoformat() if aapl_stats and aapl_stats.latest else None
        } if has_aapl else None,
        spy_date_range={
            "start": spy_stats.earliest.isoformat() if spy_stats and spy_stats.earliest else None,
            "end": spy_stats.latest.isoformat() if spy_stats and spy_stats.latest else None
        } if has_spy else None,
        message=message,
        api_configured=bool(settings.twelvedata_api_key)
    )


@router.get("/datasets", response_model=List[DatasetResponse])
def list_datasets(
    symbol: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all available market data datasets."""
    query = db.query(MarketDataset)
    
    if symbol:
        query = query.filter(MarketDataset.symbol == symbol)
    
    datasets = query.order_by(MarketDataset.fetched_at.desc()).all()
    
    return [DatasetResponse.model_validate(d) for d in datasets]


@router.get("/stats", response_model=List[MarketDataStatsResponse])
def get_market_data_stats(
    db: Session = Depends(get_db)
):
    """Get statistics about stored market data."""
    stats = db.query(
        MarketData.symbol,
        func.count(MarketData.id).label("total_bars"),
        func.min(MarketData.datetime).label("earliest_date"),
        func.max(MarketData.datetime).label("latest_date"),
        func.count(func.distinct(MarketData.dataset_id)).label("datasets_count")
    ).group_by(MarketData.symbol).all()
    
    return [
        MarketDataStatsResponse(
            symbol=s.symbol,
            total_bars=s.total_bars,
            earliest_date=s.earliest_date,
            latest_date=s.latest_date,
            datasets_count=s.datasets_count
        )
        for s in stats
    ]


@router.get("/check-api")
async def check_api_status(
    current_user: User = Depends(get_current_admin)
):
    """Check Twelve Data API status and remaining credits (admin only)."""
    if not settings.twelvedata_api_key:
        return {
            "status": "error",
            "message": "API key not configured"
        }
    
    client = TwelveDataClient()
    return await client.check_api_status()


@router.delete("/{symbol}")
def delete_market_data(
    symbol: str,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Delete all market data for a symbol (admin only)."""
    datasets = db.query(MarketDataset).filter(MarketDataset.symbol == symbol).all()
    
    if not datasets:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No data found for symbol: {symbol}"
        )
    
    count = 0
    for dataset in datasets:
        count += dataset.total_bars
        db.delete(dataset)
    
    db.commit()
    
    return {
        "message": f"Deleted {count} bars for {symbol}",
        "datasets_deleted": len(datasets)
    }
