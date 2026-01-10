# Trade Tracking API - Endpoint Output Examples

This document shows **actual example outputs** from each trade tracking endpoint to help you understand the data structure and build your frontend.

---

## Endpoint 1: Get All Trades for an Agent

**Request:**
```http
GET /api/trades/agent/f47ac10b-58cc-4372-a567-0e02b2c3d479
```

**Response (200 OK):**
```json
{
  "trades": [
    {
      "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
      "agent_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "tick": 23,
      "action": "OPEN_LONG",
      "price": 150.25,
      "executed_price": 150.40,
      "size": 66.5,
      "cost": 10.00,
      "pnl": 0.0,
      "equity_after": 99990.00,
      "reason": "Mean reversion signal: z-score = -2.15 (oversold)",
      "created_at": "2026-01-10T15:30:00.123456Z"
    },
    {
      "id": "d4e5f6a7-b8c9-0123-def0-234567890123",
      "agent_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "tick": 67,
      "action": "CLOSE_LONG",
      "price": 152.80,
      "executed_price": 152.65,
      "size": 66.5,
      "cost": 10.15,
      "pnl": 129.50,
      "equity_after": 100109.35,
      "reason": "Mean reversion exit: z-score = 0.45 (return to mean)",
      "created_at": "2026-01-10T15:30:00.234567Z"
    },
    {
      "id": "e5f6a7b8-c9d0-1234-ef01-345678901234",
      "agent_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "tick": 102,
      "action": "OPEN_SHORT",
      "price": 154.20,
      "executed_price": 154.05,
      "size": 65.0,
      "cost": 10.01,
      "pnl": 0.0,
      "equity_after": 100099.34,
      "reason": "Mean reversion signal: z-score = 2.31 (overbought)",
      "created_at": "2026-01-10T15:30:00.345678Z"
    },
    {
      "id": "f6a7b8c9-d0e1-2345-f012-456789012345",
      "agent_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "tick": 145,
      "action": "CLOSE_SHORT",
      "price": 151.90,
      "executed_price": 152.05,
      "size": 65.0,
      "cost": 9.88,
      "pnl": 120.12,
      "equity_after": 100209.58,
      "reason": "Mean reversion exit: z-score = -0.23 (return to mean)",
      "created_at": "2026-01-10T15:30:00.456789Z"
    },
    {
      "id": "a7b8c9d0-e1f2-3456-0123-567890123456",
      "agent_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "tick": 189,
      "action": "OPEN_LONG",
      "price": 149.50,
      "executed_price": 149.65,
      "size": 67.0,
      "cost": 10.03,
      "pnl": 0.0,
      "equity_after": 100199.55,
      "reason": "Mean reversion signal: z-score = -2.05 (oversold)",
      "created_at": "2026-01-10T15:30:00.567890Z"
    },
    {
      "id": "b8c9d0e1-f2a3-4567-1234-678901234567",
      "agent_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "tick": 245,
      "action": "CLOSE_LONG",
      "price": 151.20,
      "executed_price": 151.05,
      "size": 67.0,
      "cost": 10.12,
      "pnl": 73.68,
      "equity_after": 100263.11,
      "reason": "Mean reversion exit: z-score = 0.38 (return to mean)",
      "created_at": "2026-01-10T15:30:00.678901Z"
    },
    {
      "id": "c9d0e1f2-a3b4-5678-2345-789012345678",
      "agent_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "tick": 298,
      "action": "OPEN_LONG",
      "price": 147.80,
      "executed_price": 147.95,
      "size": 67.5,
      "cost": 9.99,
      "pnl": 0.0,
      "equity_after": 100253.12,
      "reason": "Mean reversion signal: z-score = -2.42 (oversold)",
      "created_at": "2026-01-10T15:30:00.789012Z"
    },
    {
      "id": "d0e1f2a3-b4c5-6789-3456-890123456789",
      "agent_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "tick": 356,
      "action": "CLOSE_LONG",
      "price": 146.90,
      "executed_price": 146.75,
      "size": 67.5,
      "cost": 9.91,
      "pnl": -91.41,
      "equity_after": 100151.80,
      "reason": "Stop loss hit (-5.12%)",
      "created_at": "2026-01-10T15:30:00.890123Z"
    }
  ],
  "total_trades": 8,
  "total_pnl": 231.89,
  "winning_trades": 3,
  "losing_trades": 1,
  "win_rate": 75.0
}
```

**Key Points:**
- Trades are ordered by `tick` (chronological)
- Opening trades have `pnl = 0`
- Closing trades show realized P&L
- `executed_price` includes slippage (differs from `price`)
- `reason` shows why the trade was made
- Statistics include win rate and total P&L

---

## Endpoint 2: Get Trade Summary

**Request:**
```http
GET /api/trades/agent/f47ac10b-58cc-4372-a567-0e02b2c3d479/summary
```

**Response (200 OK):**
```json
{
  "agent_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "total_trades": 8,
  "total_closing_trades": 4,
  "total_pnl": 231.89,
  "win_rate": 75.0,
  "avg_winning_trade": 107.77,
  "avg_losing_trade": -91.41,
  "largest_win": 129.50,
  "largest_loss": -91.41,
  "winning_trades": 3,
  "losing_trades": 1
}
```

**Key Points:**
- No trade list (faster query)
- `total_closing_trades` used for win rate calculation
- Average win/loss helps evaluate strategy performance
- Largest win/loss shows best/worst trades

---

## Endpoint 3: Get All Trades for a Round

**Request:**
```http
GET /api/trades/round/987fcdeb-51a2-43f8-b456-123456789abc/all-trades
```

**Response (200 OK):**
```json
{
  "round_id": "987fcdeb-51a2-43f8-b456-123456789abc",
  "total_agents": 3,
  "total_trades": 24,
  "trades_by_agent": {
    "f47ac10b-58cc-4372-a567-0e02b2c3d479": {
      "agent_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "user_id": "user-123e4567-e89b-12d3-a456-426614174000",
      "strategy_type": "MEAN_REVERSION",
      "trade_count": 8,
      "trades": [
        {
          "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
          "agent_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
          "tick": 23,
          "action": "OPEN_LONG",
          "price": 150.25,
          "executed_price": 150.40,
          "size": 66.5,
          "cost": 10.00,
          "pnl": 0.0,
          "equity_after": 99990.00,
          "reason": "Mean reversion signal: z-score = -2.15 (oversold)",
          "created_at": "2026-01-10T15:30:00.123456Z"
        }
        // ... more trades for this agent
      ]
    },
    "234b5678-f90c-23e4-b567-537625285111": {
      "agent_id": "234b5678-f90c-23e4-b567-537625285111",
      "user_id": "user-234b5678-f90c-23e4-b567-537625285111",
      "strategy_type": "TREND_FOLLOWING",
      "trade_count": 6,
      "trades": [
        {
          "id": "e1f2a3b4-c5d6-7890-1234-567890123456",
          "agent_id": "234b5678-f90c-23e4-b567-537625285111",
          "tick": 45,
          "action": "OPEN_LONG",
          "price": 150.75,
          "executed_price": 150.90,
          "size": 66.0,
          "cost": 9.96,
          "pnl": 0.0,
          "equity_after": 99990.04,
          "reason": "Trend following: EMA crossover (bullish)",
          "created_at": "2026-01-10T15:30:00.234567Z"
        },
        {
          "id": "f2a3b4c5-d6e7-8901-2345-678901234567",
          "agent_id": "234b5678-f90c-23e4-b567-537625285111",
          "tick": 123,
          "action": "CLOSE_LONG",
          "price": 153.40,
          "executed_price": 153.25,
          "size": 66.0,
          "cost": 10.11,
          "pnl": 144.94,
          "equity_after": 100124.87,
          "reason": "Trend following: EMA crossover (bearish)",
          "created_at": "2026-01-10T15:30:00.345678Z"
        }
        // ... more trades
      ]
    },
    "345c6789-a01d-34f5-c678-648736396222": {
      "agent_id": "345c6789-a01d-34f5-c678-648736396222",
      "user_id": "user-345c6789-a01d-34f5-c678-648736396222",
      "strategy_type": "MOMENTUM",
      "trade_count": 10,
      "trades": [
        {
          "id": "a3b4c5d6-e7f8-9012-3456-789012345678",
          "agent_id": "345c6789-a01d-34f5-c678-648736396222",
          "tick": 34,
          "action": "OPEN_LONG",
          "price": 150.50,
          "executed_price": 150.65,
          "size": 66.3,
          "cost": 9.99,
          "pnl": 0.0,
          "equity_after": 99990.01,
          "reason": "Momentum: RSI oversold + strong momentum",
          "created_at": "2026-01-10T15:30:00.456789Z"
        },
        {
          "id": "b4c5d6e7-f8a9-0123-4567-890123456789",
          "agent_id": "345c6789-a01d-34f5-c678-648736396222",
          "tick": 89,
          "action": "CLOSE_LONG",
          "price": 154.20,
          "executed_price": 154.05,
          "size": 66.3,
          "cost": 10.21,
          "pnl": 205.23,
          "equity_after": 100185.03,
          "reason": "Momentum: RSI overbought",
          "created_at": "2026-01-10T15:30:00.567890Z"
        }
        // ... more trades
      ]
    }
  }
}
```

**Key Points:**
- Groups trades by agent_id
- Includes agent metadata (user_id, strategy_type)
- Shows trade count per agent
- Useful for comparing trading patterns across agents

---

## Error Responses

### Agent Not Found

**Request:**
```http
GET /api/trades/agent/00000000-0000-0000-0000-000000000000
```

**Response (404 Not Found):**
```json
{
  "detail": "Agent not found"
}
```

### Round Not Found or No Agents

**Request:**
```http
GET /api/trades/round/00000000-0000-0000-0000-000000000000/all-trades
```

**Response (404 Not Found):**
```json
{
  "detail": "Round not found or no agents in round"
}
```

### No Trades Yet (Empty Response)

**Request:**
```http
GET /api/trades/agent/f47ac10b-58cc-4372-a567-0e02b2c3d479
```

**Response (200 OK):**
```json
{
  "trades": [],
  "total_trades": 0,
  "total_pnl": 0.0,
  "winning_trades": 0,
  "losing_trades": 0,
  "win_rate": 0.0
}
```

---

## Trade Action Breakdown

### OPEN_LONG Example
```json
{
  "tick": 23,
  "action": "OPEN_LONG",
  "price": 150.25,          // Market price
  "executed_price": 150.40,  // Price after slippage (+0.15)
  "size": 66.5,
  "cost": 10.00,            // Transaction fees
  "pnl": 0.0,               // Always 0 for opening trades
  "equity_after": 99990.00, // Equity decreased by fees
  "reason": "Mean reversion signal: z-score = -2.15"
}
```

### CLOSE_LONG Example
```json
{
  "tick": 67,
  "action": "CLOSE_LONG",
  "price": 152.80,
  "executed_price": 152.65,  // Price after slippage (-0.15)
  "size": 66.5,
  "cost": 10.15,
  "pnl": 129.50,            // Profit from this trade
  "equity_after": 100109.35, // Equity increased by profit
  "reason": "Mean reversion exit: z-score = 0.45"
}
```

### OPEN_SHORT Example
```json
{
  "tick": 102,
  "action": "OPEN_SHORT",
  "price": 154.20,
  "executed_price": 154.05,  // Worse price when shorting
  "size": 65.0,
  "cost": 10.01,
  "pnl": 0.0,
  "equity_after": 100099.34,
  "reason": "Mean reversion signal: z-score = 2.31"
}
```

### CLOSE_SHORT Example
```json
{
  "tick": 145,
  "action": "CLOSE_SHORT",
  "price": 151.90,
  "executed_price": 152.05,  // Worse price when buying to cover
  "size": 65.0,
  "cost": 9.88,
  "pnl": 120.12,            // Profit from short (price went down)
  "equity_after": 100209.58,
  "reason": "Mean reversion exit: z-score = -0.23"
}
```

---

## Statistics Calculation Examples

### Win Rate Calculation
```
Closing Trades: [CLOSE_LONG, CLOSE_SHORT, CLOSE_LONG, CLOSE_LONG]
P&L Values: [129.50, 120.12, 73.68, -91.41]

Winning Trades: 3 (P&L > 0)
Losing Trades: 1 (P&L < 0)
Win Rate: 3 / 4 × 100 = 75.0%
```

### Average Win/Loss Calculation
```
Winning Trades P&L: [129.50, 120.12, 73.68]
Average Win: (129.50 + 120.12 + 73.68) / 3 = 107.77

Losing Trades P&L: [-91.41]
Average Loss: -91.41
```

### Total P&L
```
All Closing Trades: 129.50 + 120.12 + 73.68 - 91.41 = 231.89
```

---

## Frontend Usage Examples

### Fetch and Display

```typescript
// Fetch trades
const response = await fetch('/api/trades/agent/f47ac10b-58cc-4372-a567-0e02b2c3d479');
const data = await response.json();

// Display summary
console.log(`Total P&L: $${data.total_pnl.toFixed(2)}`);
console.log(`Win Rate: ${data.win_rate.toFixed(1)}%`);
console.log(`Total Trades: ${data.total_trades}`);

// Map trades for chart markers
const buyMarkers = data.trades
  .filter(t => t.action === 'OPEN_LONG' || t.action === 'CLOSE_SHORT')
  .map(t => ({ x: t.tick, y: t.executed_price, pnl: t.pnl }));

const sellMarkers = data.trades
  .filter(t => t.action === 'CLOSE_LONG' || t.action === 'OPEN_SHORT')
  .map(t => ({ x: t.tick, y: t.executed_price, pnl: t.pnl }));
```

### Color Coding by P&L

```typescript
function getTradeColor(trade: Trade): string {
  if (trade.action.includes('OPEN')) {
    return '#808080'; // Gray for opening trades
  }
  return trade.pnl >= 0 ? '#22c55e' : '#ef4444'; // Green/Red
}
```

### Tooltip Content

```typescript
function TradeTooltip({ trade }: { trade: Trade }) {
  return (
    <div className="tooltip">
      <p><strong>Tick {trade.tick}</strong></p>
      <p>{trade.action}</p>
      <p>Price: ${trade.executed_price.toFixed(2)}</p>
      <p>Size: {trade.size.toFixed(2)}</p>
      {trade.pnl !== 0 && (
        <p className={trade.pnl >= 0 ? 'profit' : 'loss'}>
          P&L: ${trade.pnl.toFixed(2)}
        </p>
      )}
      <p className="reason">{trade.reason}</p>
    </div>
  );
}
```

---

## Summary

This document provides complete examples of:

✅ **All endpoint responses** with realistic data  
✅ **Trade action types** with detailed examples  
✅ **Statistics calculations** showing formulas  
✅ **Error responses** for edge cases  
✅ **Frontend integration** patterns  

Use these examples to build your frontend integration with confidence!
