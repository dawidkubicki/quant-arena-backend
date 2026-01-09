# Market Data Integration Guide

This document describes the real historical market data integration using Twelve Data API for the Quant Arena platform.

## Overview

The platform now supports **real historical market data** from Twelve Data API instead of synthetic GBM-generated data. This enables educationally accurate **CAPM-based alpha/beta calculations** using:

- **AAPL** - Trading asset (Apple Inc. stock)
- **SPY** - Benchmark (S&P 500 ETF for market factor)

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Twelve Data    │────▶│  PostgreSQL      │────▶│  Simulation     │
│  API            │     │  market_data     │     │  Engine         │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                         │
                                                         ▼
                                                 ┌─────────────────┐
                                                 │  Alpha/Beta     │
                                                 │  Calculations   │
                                                 └─────────────────┘
```

## Data Flow

1. **Admin fetches data** via `POST /api/market-data/fetch`
2. **Data stored** in PostgreSQL (`market_datasets`, `market_data` tables)
3. **Simulation uses real data** when available (falls back to synthetic if not)
4. **Alpha/Beta calculated** using CAPM methodology with SPY as benchmark

---

## API Endpoints

### Market Data Management

#### Check Data Status
```http
GET /api/market-data/status
```

**Response:**
```json
{
  "is_ready": true,
  "has_aapl": true,
  "has_spy": true,
  "aapl_bars": 49234,
  "spy_bars": 48976,
  "aapl_date_range": {
    "start": "2025-07-09T09:30:00",
    "end": "2026-01-08T16:00:00"
  },
  "spy_date_range": {
    "start": "2025-07-09T09:30:00",
    "end": "2026-01-08T16:00:00"
  },
  "message": "Market data is ready. Simulations will use real AAPL/SPY data with alpha/beta calculations.",
  "api_configured": true
}
```

**Use this endpoint to:**
- Check if data is available before starting rounds
- Display data status on admin dashboard
- Determine if alpha/beta metrics will be available

---

#### Fetch Market Data (Admin Only)
```http
POST /api/market-data/fetch
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "symbols": ["AAPL", "SPY"],
  "months": 6
}
```

**Response:**
```json
{
  "status": "completed",
  "message": "Successfully fetched data for AAPL, SPY",
  "datasets": [
    {
      "id": "uuid",
      "symbol": "AAPL",
      "interval": "1min",
      "start_date": "2025-07-09T09:30:00",
      "end_date": "2026-01-08T16:00:00",
      "total_bars": 49234,
      "fetched_at": "2026-01-09T10:00:00"
    }
  ]
}
```

**Important Notes:**
- This endpoint **takes several minutes** due to API rate limits (8 req/min)
- Fetches 6 months of 1-minute data by default
- Deletes existing data for the symbols before fetching
- Requires **TWELVEDATA_API_KEY** in environment variables

---

#### List Datasets
```http
GET /api/market-data/datasets
GET /api/market-data/datasets?symbol=AAPL
```

**Response:**
```json
[
  {
    "id": "uuid",
    "symbol": "AAPL",
    "interval": "1min",
    "start_date": "2025-07-09T09:30:00",
    "end_date": "2026-01-08T16:00:00",
    "total_bars": 49234,
    "fetched_at": "2026-01-09T10:00:00"
  }
]
```

---

#### Get Statistics
```http
GET /api/market-data/stats
```

**Response:**
```json
[
  {
    "symbol": "AAPL",
    "total_bars": 49234,
    "earliest_date": "2025-07-09T09:30:00",
    "latest_date": "2026-01-08T16:00:00",
    "datasets_count": 1
  },
  {
    "symbol": "SPY",
    "total_bars": 48976,
    "earliest_date": "2025-07-09T09:30:00",
    "latest_date": "2026-01-08T16:00:00",
    "datasets_count": 1
  }
]
```

---

#### Check API Status (Admin Only)
```http
GET /api/market-data/check-api
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
  "status": "ok",
  "daily_usage": 5,
  "daily_limit": 800,
  "credits_remaining": 795
}
```

---

#### Delete Market Data (Admin Only)
```http
DELETE /api/market-data/{symbol}
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
  "message": "Deleted 49234 bars for AAPL",
  "datasets_deleted": 1
}
```

---

## Round Configuration

### Updated MarketConfig Schema

```json
{
  "market": {
    "trading_interval": "5min",
    "num_ticks": null,
    "initial_equity": 100000.0,
    "base_slippage": 0.001,
    "fee_rate": 0.001
  }
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `trading_interval` | string | "5min" | Timeframe for simulation ("1min", "5min", "15min", "30min", "1h") |
| `num_ticks` | int \| null | null | Max ticks to simulate. `null` = use all available data |
| `initial_equity` | float | 100000.0 | Starting capital |
| `base_slippage` | float | 0.001 | Base slippage rate (0.1%) |
| `fee_rate` | float | 0.001 | Transaction fee rate (0.1%) |

**Note:** Synthetic data parameters (`initial_price`, `base_volatility`, etc.) are still supported as fallback when real data is not available.

---

## Round Response

After simulation, rounds include SPY returns:

```json
{
  "id": "uuid",
  "name": "Round 1",
  "status": "COMPLETED",
  "price_data": [150.23, 150.45, ...],
  "spy_returns": [0.0001, -0.0002, ...],
  ...
}
```

- `price_data`: AAPL close prices at each tick
- `spy_returns`: SPY log returns for each tick (used for alpha/beta)

---

## Agent Results

Results now include CAPM metrics:

```json
{
  "id": "uuid",
  "agent_id": "uuid",
  "final_equity": 105234.56,
  "total_return": 5.23,
  "sharpe_ratio": 1.45,
  "max_drawdown": 8.2,
  
  "alpha": 0.0234,
  "beta": 1.15,
  "cumulative_alpha": [0.0, 0.001, 0.002, ...],
  
  "equity_curve": [...],
  "trades": [...]
}
```

### CAPM Metrics Explained

| Metric | Description | Interpretation |
|--------|-------------|----------------|
| **alpha** | Annualized excess return over market | Positive = outperforming market on risk-adjusted basis |
| **beta** | Strategy's exposure to market risk | β≈1: moves with market, β>1: more volatile, β<1: less volatile, β≈0: market neutral |
| **cumulative_alpha** | Running sum of period alphas | Shows alpha generation over time |

### Strategy Behavior Expectations

| Strategy Type | Expected Beta | Why |
|--------------|---------------|-----|
| Buy & Hold AAPL | β ≈ 1.0 | Direct market exposure |
| Momentum | β > 1.0 | Amplifies market moves |
| Mean Reversion | β < 1.0 | Fades market moves |
| "Market Neutral" | β ≈ 0 | (Often not actually zero!) |

**Key Insight:** Positive PnL ≠ Alpha. A strategy can make money while having negative alpha if it simply has high beta exposure during a bull market.

---

## Leaderboard

Leaderboard now supports sorting by alpha/beta:

```http
GET /api/rounds/{round_id}/leaderboard?sort_by=alpha
GET /api/rounds/{round_id}/leaderboard?sort_by=beta
```

**Supported sort fields:**
- `sharpe_ratio` (default)
- `total_return`
- `max_drawdown`
- `calmar_ratio`
- `win_rate`
- `survival_time`
- `alpha` (NEW)
- `beta` (NEW)

---

## Frontend Integration Guide

### 1. Check Data Status on Load

```typescript
// On admin dashboard load
const checkDataStatus = async () => {
  const response = await fetch('/api/market-data/status');
  const status = await response.json();
  
  if (!status.is_ready) {
    // Show warning/prompt to fetch data
    showDataFetchPrompt(status.message);
  }
};
```

### 2. Fetch Data Button (Admin)

```typescript
const fetchMarketData = async () => {
  setLoading(true);
  setMessage('Fetching data... This may take several minutes.');
  
  try {
    const response = await fetch('/api/market-data/fetch', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        symbols: ['AAPL', 'SPY'],
        months: 6
      })
    });
    
    const result = await response.json();
    setMessage(result.message);
  } catch (error) {
    setError('Failed to fetch data');
  } finally {
    setLoading(false);
  }
};
```

### 3. Display Alpha/Beta in Results

```typescript
interface AgentResult {
  // ... existing fields
  alpha: number | null;
  beta: number | null;
  cumulative_alpha: number[];
}

// Format alpha as percentage
const formatAlpha = (alpha: number | null) => {
  if (alpha === null) return 'N/A';
  return `${(alpha * 100).toFixed(2)}%`;
};

// Format beta with context
const formatBeta = (beta: number | null) => {
  if (beta === null) return 'N/A';
  const label = beta > 1.2 ? '(Aggressive)' 
              : beta < 0.8 ? '(Defensive)' 
              : '(Market-like)';
  return `${beta.toFixed(2)} ${label}`;
};
```

### 4. Alpha Chart Component

```typescript
// Plot cumulative alpha over time
const AlphaChart = ({ cumulativeAlpha }: { cumulativeAlpha: number[] }) => {
  const data = cumulativeAlpha.map((value, index) => ({
    tick: index,
    alpha: value * 100  // Convert to percentage
  }));
  
  return (
    <LineChart data={data}>
      <XAxis dataKey="tick" />
      <YAxis label="Cumulative Alpha (%)" />
      <Line dataKey="alpha" stroke="#10B981" />
      <ReferenceLine y={0} stroke="#888" strokeDasharray="3 3" />
    </LineChart>
  );
};
```

### 5. Beta Scatter Plot (Strategy vs Market)

For the dashboard, you can show strategy returns vs SPY returns scatter plot:

```typescript
// Combine strategy equity curve with spy_returns from round
const ScatterPlot = ({ 
  equityCurve, 
  spyReturns 
}: { 
  equityCurve: number[], 
  spyReturns: number[] 
}) => {
  // Calculate strategy returns
  const strategyReturns = equityCurve.slice(1).map((eq, i) => 
    Math.log(eq / equityCurve[i])
  );
  
  // Create scatter data
  const data = strategyReturns.map((sr, i) => ({
    spy: spyReturns[i + 1] * 100,
    strategy: sr * 100
  }));
  
  // Beta is the slope of this relationship
  return (
    <ScatterChart data={data}>
      <XAxis dataKey="spy" label="SPY Return (%)" />
      <YAxis dataKey="strategy" label="Strategy Return (%)" />
      <Scatter fill="#3B82F6" />
    </ScatterChart>
  );
};
```

---

## Environment Variables

Add to `.env`:

```env
# Twelve Data API
TWELVEDATA_API_KEY=your_api_key_here
```

---

## Database Migration

Run the migration to add new tables and columns:

```bash
alembic upgrade head
```

This creates:
- `market_datasets` table
- `market_data` table
- `alpha`, `beta`, `cumulative_alpha` columns in `agent_results`
- `spy_returns` column in `rounds`

---

## API Rate Limits

Twelve Data free tier:
- **8 requests/minute**
- **800 requests/day**
- **1 credit per symbol**

The client automatically handles rate limiting with 8-second delays between requests.

---

## Fallback Behavior

If market data is **not available**, the simulation:
1. Uses synthetic GBM-generated prices
2. Sets `alpha`, `beta`, `cumulative_alpha` to `null`
3. Works exactly as before

This ensures backward compatibility while encouraging use of real data.

---

## Summary

| Feature | Before | After |
|---------|--------|-------|
| Price Data | Synthetic GBM | Real AAPL historical |
| Benchmark | None | SPY (S&P 500) |
| Alpha | Not calculated | CAPM alpha vs SPY |
| Beta | Not calculated | Rolling Cov/Var |
| Educational Value | Limited | Full factor investing concepts |
