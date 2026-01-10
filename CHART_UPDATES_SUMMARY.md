# Chart Data Updates - Summary

## Problem

The frontend was receiving chart data (prices, equity curves, etc.) with **only Y-axis values** (the actual data) but **no X-axis data** (timestamps or tick numbers). This made it difficult to create properly aligned time-series charts.

**Example of the problem:**
- Market Price chart showed Apple prices on Y-axis
- But nothing on X-axis to indicate when those prices occurred
- Same issue for equity curves, alpha accumulation, and other time-series data

---

## Solution

All time-series data now includes both **X-axis** (time) and **Y-axis** (values) information in a standardized format:

```typescript
interface ChartDataPoint {
  tick: number;              // X-axis: Sequential tick number
  timestamp: string | null;  // X-axis: ISO datetime (null for synthetic data)
  value: number;             // Y-axis: The actual value
}
```

---

## Changes Made

### 1. Database Schema Updates

**Migration:** `alembic/versions/005_add_chart_timestamps.py`

- Added `timestamps` column to `rounds` table (stores ISO timestamps for each tick)
- Added `timestamp` column to `trades` table (market timestamp for each trade)
- Updated JSONB columns to store `{tick, timestamp, value}` objects instead of just values

### 2. Model Updates

**Files Modified:**
- `app/models/round.py` - Added timestamps field
- `app/models/trade.py` - Added timestamp field to individual trades
- `app/models/agent_result.py` - Updated comments for equity_curve and cumulative_alpha

### 3. Schema Updates

**Files Modified:**
- `app/schemas/round.py` - Added `ChartDataPoint` type and updated response models
- `app/schemas/agent.py` - Added `ChartDataPoint` type for equity/alpha curves
- `app/schemas/trade.py` - Added timestamp field with documentation

### 4. Simulation Engine Updates

**File:** `app/engine/simulation.py`

- Modified to store timestamps alongside price data
- Updated equity curve and cumulative alpha to include tick/timestamp
- Passes timestamps through the execution pipeline

**Changes:**
- Real market data: Includes actual timestamps from market data
- Synthetic data: Includes tick numbers only (timestamp = null)

### 5. Execution Engine Updates

**File:** `app/engine/execution.py`

- Added timestamp parameter to `Trade` dataclass
- Updated `execute_trade()` to accept and propagate timestamps
- Updated `_open_position()` and `_close_position()` to include timestamps
- Modified `check_risk_limits()` to pass timestamps for stop-loss/take-profit trades

---

## Data Format Examples

### Price Data (Round)

**Before:**
```json
{
  "price_data": [145.50, 145.75, 146.00, 146.25]
}
```

**After:**
```json
{
  "price_data": [
    {"tick": 0, "timestamp": "2024-01-15T09:30:00Z", "value": 145.50},
    {"tick": 1, "timestamp": "2024-01-15T09:35:00Z", "value": 145.75},
    {"tick": 2, "timestamp": "2024-01-15T09:40:00Z", "value": 146.00},
    {"tick": 3, "timestamp": "2024-01-15T09:45:00Z", "value": 146.25}
  ]
}
```

### Equity Curve (Agent Result)

**Before:**
```json
{
  "equity_curve": [100000, 100125, 100250, 100180]
}
```

**After:**
```json
{
  "equity_curve": [
    {"tick": 0, "timestamp": "2024-01-15T09:30:00Z", "value": 100000},
    {"tick": 1, "timestamp": "2024-01-15T09:35:00Z", "value": 100125},
    {"tick": 2, "timestamp": "2024-01-15T09:40:00Z", "value": 100250},
    {"tick": 3, "timestamp": "2024-01-15T09:45:00Z", "value": 100180}
  ]
}
```

### Trades

**Before:**
```json
{
  "tick": 23,
  "action": "OPEN_LONG",
  "price": 150.25
}
```

**After:**
```json
{
  "tick": 23,
  "timestamp": "2024-01-15T10:55:00Z",
  "action": "OPEN_LONG",
  "price": 150.25
}
```

---

## Backward Compatibility

To ensure existing frontends continue working during migration, **legacy fields** are still available:

- `price_data_values: number[]` - Array of just the values (deprecated)
- `equity_curve_values: number[]` - Array of just the values (deprecated)
- `cumulative_alpha_values: number[]` - Array of just the values (deprecated)

**⚠️ These will be removed in a future version. Please migrate to the new format.**

---

## Benefits for Frontend

1. **Proper Time Alignment**: Charts can show exact timestamps on X-axis
2. **No Guesswork**: Backend provides complete data, frontend doesn't need to infer
3. **Easy Overlays**: Multiple data series can be overlaid using matching timestamps
4. **Trade Visualization**: Trades can be plotted at exact market times
5. **Flexible Display**: Use timestamps for real data, tick numbers for synthetic

---

## Frontend Migration Steps

### Step 1: Update TypeScript Types

```typescript
// Add the new ChartDataPoint interface
interface ChartDataPoint {
  tick: number;
  timestamp: string | null;
  value: number;
}

// Update your response types
interface RoundResponse {
  price_data: ChartDataPoint[] | null;
  spy_returns: ChartDataPoint[] | null;
  // ... other fields
}
```

### Step 2: Update Chart Components

**Before:**
```typescript
// Old: Manual index as x-axis
const data = prices.map((price, index) => ({
  x: index,
  y: price
}));
```

**After:**
```typescript
// New: Use provided tick/timestamp
const data = priceData.map(point => ({
  x: point.timestamp || point.tick,
  y: point.value
}));
```

### Step 3: Handle Synthetic vs Real Data

```typescript
function formatXAxis(point: ChartDataPoint): string {
  if (point.timestamp) {
    return new Date(point.timestamp).toLocaleTimeString();
  }
  return `Tick ${point.tick}`;
}
```

---

## Testing Checklist

- [x] Database migration runs successfully
- [x] Real market data includes actual timestamps
- [x] Synthetic data uses null timestamps
- [x] Trades include both tick and timestamp
- [x] Equity curves have complete x/y data
- [x] Price data has complete x/y data
- [x] Cumulative alpha has complete x/y data
- [ ] Frontend charts display correctly with new format
- [ ] Trade markers align with price chart
- [ ] Timestamp formatting works in UI

---

## Documentation Files

1. **CHART_DATA_FORMAT.md** - Complete guide for frontend developers
2. **CHART_UPDATES_SUMMARY.md** - This file (overview of changes)
3. **API_DOCUMENTATION.md** - Updated with new response formats
4. **FRONTEND_API_CHANGES.md** - Breaking changes documentation

---

## Database Migration

**Run this to apply the changes:**

```bash
alembic upgrade head
```

**Status:** ✅ Migration `005` completed successfully

---

## Files Changed

### Backend Core
- `app/models/round.py`
- `app/models/trade.py`
- `app/models/agent_result.py`
- `app/schemas/round.py`
- `app/schemas/agent.py`
- `app/schemas/trade.py`

### Engine
- `app/engine/simulation.py`
- `app/engine/execution.py`

### Database
- `alembic/versions/005_add_chart_timestamps.py` (new)

### Documentation
- `CHART_DATA_FORMAT.md` (new)
- `CHART_UPDATES_SUMMARY.md` (new)

---

## Next Steps

1. **Frontend Team**: Review `CHART_DATA_FORMAT.md` for integration examples
2. **Testing**: Verify charts display correctly with real and synthetic data
3. **Migration**: Update existing chart components to use new format
4. **Deprecation**: Plan removal of legacy fields in next major version

---

## Questions?

Contact the backend team or refer to the documentation files listed above.
