# Chart Data Format - X-Axis and Y-Axis Support

## Summary

All chart data from the backend now includes **both X-axis (time) and Y-axis (values)** information. This ensures charts can properly display data with correct temporal alignment.

---

## Data Format

### ChartDataPoint Structure

All time-series data uses the following format:

```typescript
interface ChartDataPoint {
  tick: number;              // X-axis: Sequential tick number (0-indexed)
  timestamp: string | null;  // X-axis: ISO 8601 timestamp (null for synthetic data)
  value: number;             // Y-axis: The actual data value
}
```

**Example:**
```json
{
  "tick": 42,
  "timestamp": "2024-01-15T10:30:00Z",
  "value": 150.25
}
```

---

## API Response Changes

### 1. Round Data (GET `/api/rounds/{id}`)

**Price Data (AAPL prices):**

```json
{
  "price_data": [
    {"tick": 0, "timestamp": "2024-01-15T09:30:00Z", "value": 145.50},
    {"tick": 1, "timestamp": "2024-01-15T09:35:00Z", "value": 145.75},
    {"tick": 2, "timestamp": "2024-01-15T09:40:00Z", "value": 146.00}
  ]
}
```

**SPY Returns:**

```json
{
  "spy_returns": [
    {"tick": 0, "timestamp": "2024-01-15T09:30:00Z", "value": 0.0},
    {"tick": 1, "timestamp": "2024-01-15T09:35:00Z", "value": 0.0015},
    {"tick": 2, "timestamp": "2024-01-15T09:40:00Z", "value": -0.0008}
  ]
}
```

---

### 2. Agent Results

**Equity Curve:**

```json
{
  "equity_curve": [
    {"tick": 0, "timestamp": "2024-01-15T09:30:00Z", "value": 100000.0},
    {"tick": 1, "timestamp": "2024-01-15T09:35:00Z", "value": 100125.5},
    {"tick": 2, "timestamp": "2024-01-15T09:40:00Z", "value": 100250.0}
  ]
}
```

**Cumulative Alpha:**

```json
{
  "cumulative_alpha": [
    {"tick": 0, "timestamp": "2024-01-15T09:30:00Z", "value": 0.0},
    {"tick": 1, "timestamp": "2024-01-15T09:35:00Z", "value": 0.12},
    {"tick": 2, "timestamp": "2024-01-15T09:40:00Z", "value": 0.25}
  ]
}
```

---

### 3. Trades (GET `/api/trades/agent/{id}`)

Trades now include both `tick` and `timestamp` fields:

```json
{
  "trades": [
    {
      "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
      "agent_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "tick": 23,                                    // X-axis (tick number)
      "timestamp": "2024-01-15T10:55:00Z",           // X-axis (datetime)
      "action": "OPEN_LONG",
      "price": 150.25,                               // Y-axis (market price)
      "executed_price": 150.40,                      // Y-axis (actual price)
      "size": 66.5,
      "cost": 10.00,
      "pnl": 0.0,
      "equity_after": 99990.00,
      "reason": "Mean reversion signal: z-score = -2.15"
    }
  ]
}
```

---

## Frontend Integration

### Example 1: Charting Price Data with Chart.js

```typescript
import { ChartDataPoint } from './types';

// Fetch round data
const response = await fetch('/api/rounds/abc-123');
const round = await response.json();

// Extract price data
const priceData: ChartDataPoint[] = round.price_data;

// Format for Chart.js
const chartData = {
  labels: priceData.map(d => d.timestamp || `Tick ${d.tick}`),  // X-axis
  datasets: [{
    label: 'AAPL Price',
    data: priceData.map(d => d.value),  // Y-axis
  }]
};
```

### Example 2: Charting Equity Curve with Recharts

```typescript
import { LineChart, Line, XAxis, YAxis, Tooltip } from 'recharts';
import { ChartDataPoint } from './types';

function EquityCurveChart({ agentResult }: { agentResult: AgentResult }) {
  // Data is already in the correct format for Recharts
  const data = agentResult.equity_curve.map(point => ({
    time: point.timestamp || `Tick ${point.tick}`,
    equity: point.value
  }));

  return (
    <LineChart data={data}>
      <XAxis dataKey="time" />
      <YAxis />
      <Line type="monotone" dataKey="equity" stroke="#8884d8" />
      <Tooltip />
    </LineChart>
  );
}
```

### Example 3: Plotting Trade Signals on Price Chart

```typescript
// Combine price data with trade markers
function PriceWithTradesChart({ round, trades }) {
  const pricePoints = round.price_data;
  
  // Filter trades by type
  const buyTrades = trades.filter(t => 
    t.action === 'OPEN_LONG' || t.action === 'CLOSE_SHORT'
  );
  const sellTrades = trades.filter(t => 
    t.action === 'CLOSE_LONG' || t.action === 'OPEN_SHORT'
  );

  return (
    <Chart>
      {/* Price line */}
      <Line
        data={pricePoints.map(p => ({ x: p.tick, y: p.value }))}
        color="blue"
      />
      
      {/* Buy markers */}
      {buyTrades.map(trade => (
        <Marker
          key={trade.id}
          x={trade.tick}                    // X-axis from tick
          y={trade.executed_price}          // Y-axis from price
          color="green"
          label={`$${trade.pnl.toFixed(2)}`}
        />
      ))}
      
      {/* Sell markers */}
      {sellTrades.map(trade => (
        <Marker
          key={trade.id}
          x={trade.tick}                    // X-axis from tick
          y={trade.executed_price}          // Y-axis from price
          color="red"
          label={`$${trade.pnl.toFixed(2)}`}
        />
      ))}
    </Chart>
  );
}
```

---

## Handling Synthetic vs Real Data

The `timestamp` field will be `null` when using synthetic (simulated) data:

```typescript
function formatXAxis(point: ChartDataPoint): string {
  if (point.timestamp) {
    // Real market data - format timestamp
    return new Date(point.timestamp).toLocaleTimeString();
  } else {
    // Synthetic data - use tick number
    return `Tick ${point.tick}`;
  }
}
```

---

## Backward Compatibility

For backward compatibility, the following legacy fields are still available (deprecated):

- `price_data_values: number[]` - Array of prices (no x-axis data)
- `spy_returns_values: number[]` - Array of returns (no x-axis data)
- `equity_curve_values: number[]` - Array of equity values (no x-axis data)
- `cumulative_alpha_values: number[]` - Array of alpha values (no x-axis data)

**⚠️ These fields will be removed in a future version. Use the new `ChartDataPoint[]` format instead.**

---

## TypeScript Types

```typescript
// Chart data point with x and y axes
export interface ChartDataPoint {
  tick: number;              // Sequential tick number (0-indexed)
  timestamp: string | null;  // ISO 8601 timestamp (null for synthetic data)
  value: number;             // The actual data value
}

// Round response
export interface RoundResponse {
  id: string;
  name: string;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';
  
  // Chart data with x-axis and y-axis
  price_data: ChartDataPoint[] | null;      // AAPL prices
  spy_returns: ChartDataPoint[] | null;     // SPY returns
  
  // Legacy (deprecated)
  price_data_values?: number[];
  spy_returns_values?: number[];
  
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  agent_count: number;
}

// Agent result response
export interface AgentResultResponse {
  id: string;
  agent_id: string;
  final_equity: number;
  total_return: number;
  sharpe_ratio: number | null;
  max_drawdown: number;
  
  // Chart data with x-axis and y-axis
  equity_curve: ChartDataPoint[] | null;
  cumulative_alpha: ChartDataPoint[] | null;
  
  // Legacy (deprecated)
  equity_curve_values?: number[];
  cumulative_alpha_values?: number[];
  
  trades: Trade[];
  alpha: number | null;
  beta: number | null;
  created_at: string;
}

// Trade response
export interface Trade {
  id: string;
  agent_id: string;
  tick: number;              // X-axis: tick number
  timestamp: string | null;  // X-axis: market timestamp
  action: string;
  price: number;             // Y-axis: market price
  executed_price: number;    // Y-axis: execution price
  size: number;
  cost: number;
  pnl: number;
  equity_after: number;
  reason: string | null;
  created_at: string;
}
```

---

## Migration Guide

### Before (Missing X-Axis Data)

```typescript
// ❌ Old format - only values, no x-axis
const prices: number[] = [145.50, 145.75, 146.00];

// Had to manually create x-axis
const chartData = prices.map((price, index) => ({
  x: index,  // Manual tick number
  y: price
}));
```

### After (Complete Chart Data)

```typescript
// ✅ New format - includes both x and y axes
const priceData: ChartDataPoint[] = [
  {tick: 0, timestamp: "2024-01-15T09:30:00Z", value: 145.50},
  {tick: 1, timestamp: "2024-01-15T09:35:00Z", value: 145.75},
  {tick: 2, timestamp: "2024-01-15T09:40:00Z", value: 146.00}
];

// Ready to chart - no manual processing needed
const chartData = priceData.map(d => ({
  x: d.timestamp || d.tick,
  y: d.value
}));
```

---

## Benefits

1. **Proper Time Alignment**: Charts display data at the correct time points
2. **Flexible X-Axis**: Use timestamps (real data) or ticks (synthetic data)
3. **Easy Overlays**: Combine multiple data series with matching time axes
4. **Trade Visualization**: Plot trade signals at exact execution times
5. **Better UX**: No frontend guesswork about x-axis values

---

## Questions?

For issues or questions about the chart data format, see:
- API Documentation: `API_DOCUMENTATION.md`
- Frontend Changes: `FRONTEND_API_CHANGES.md`
- Trade Tracking: `TRADE_TRACKING_GUIDE.md`
