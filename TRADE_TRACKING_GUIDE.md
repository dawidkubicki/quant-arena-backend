# Trade Tracking System - API Guide

This guide explains how to use the trade tracking endpoints to retrieve and display buy/sell transactions on charts in the frontend.

## Overview

The trade tracking system stores every individual buy and sell transaction executed by agents during simulations. Each trade record includes:
- **Tick**: When the trade occurred (timestep in simulation)
- **Action**: Type of trade (OPEN_LONG, CLOSE_LONG, OPEN_SHORT, CLOSE_SHORT)
- **Price**: Market price at execution
- **Executed Price**: Actual price after slippage
- **Size**: Position size
- **Cost**: Transaction fees paid
- **P&L**: Realized profit/loss (0 for opening trades, calculated for closing trades)
- **Equity After**: Total equity after the trade
- **Reason**: Why the trade was executed (signal description)

## API Endpoints

### 1. Get All Trades for an Agent

Retrieves the complete trade history for a specific agent, ordered chronologically by tick.

**Endpoint:** `GET /api/trades/agent/{agent_id}`

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/trades/agent/123e4567-e89b-12d3-a456-426614174000"
```

**Example Response:**
```json
{
  "trades": [
    {
      "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "agent_id": "123e4567-e89b-12d3-a456-426614174000",
      "tick": 45,
      "action": "OPEN_LONG",
      "price": 152.34,
      "executed_price": 152.49,
      "size": 65.0,
      "cost": 9.91,
      "pnl": 0.0,
      "equity_after": 99990.09,
      "reason": "Mean reversion signal: z-score = -2.15",
      "created_at": "2026-01-10T10:30:45.123456"
    },
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "agent_id": "123e4567-e89b-12d3-a456-426614174000",
      "tick": 78,
      "action": "CLOSE_LONG",
      "price": 154.82,
      "executed_price": 154.67,
      "size": 65.0,
      "cost": 10.05,
      "pnl": 121.65,
      "equity_after": 100101.69,
      "reason": "Mean reversion exit: z-score = 0.45",
      "created_at": "2026-01-10T10:30:45.234567"
    },
    {
      "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "agent_id": "123e4567-e89b-12d3-a456-426614174000",
      "tick": 142,
      "action": "OPEN_SHORT",
      "price": 156.20,
      "executed_price": 156.04,
      "size": 64.0,
      "cost": 9.99,
      "pnl": 0.0,
      "equity_after": 100091.70,
      "reason": "Mean reversion signal: z-score = 2.31",
      "created_at": "2026-01-10T10:30:45.345678"
    },
    {
      "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
      "agent_id": "123e4567-e89b-12d3-a456-426614174000",
      "tick": 189,
      "action": "CLOSE_SHORT",
      "price": 153.45,
      "executed_price": 153.61,
      "size": 64.0,
      "cost": 9.83,
      "pnl": 145.33,
      "equity_after": 100227.20,
      "reason": "Mean reversion exit: z-score = -0.23",
      "created_at": "2026-01-10T10:30:45.456789"
    }
  ],
  "total_trades": 4,
  "total_pnl": 266.98,
  "winning_trades": 2,
  "losing_trades": 0,
  "win_rate": 100.0
}
```

**Frontend Use Case:**
Display trade markers on a price chart:
- **OPEN_LONG**: Green upward arrow at `executed_price` on tick `tick`
- **CLOSE_LONG**: Red downward arrow at `executed_price` on tick `tick`
- **OPEN_SHORT**: Red downward arrow at `executed_price` on tick `tick`
- **CLOSE_SHORT**: Green upward arrow at `executed_price` on tick `tick`

You can also show tooltips with trade details (P&L, fees, reason) when hovering over markers.

---

### 2. Get Trade Summary for an Agent

Retrieves aggregated statistics without the full trade list (faster for dashboards).

**Endpoint:** `GET /api/trades/agent/{agent_id}/summary`

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/trades/agent/123e4567-e89b-12d3-a456-426614174000/summary"
```

**Example Response:**
```json
{
  "agent_id": "123e4567-e89b-12d3-a456-426614174000",
  "total_trades": 24,
  "total_closing_trades": 12,
  "total_pnl": 2456.78,
  "win_rate": 58.33,
  "avg_winning_trade": 485.23,
  "avg_losing_trade": -234.56,
  "largest_win": 892.45,
  "largest_loss": -456.78,
  "winning_trades": 7,
  "losing_trades": 5
}
```

**Frontend Use Case:**
Display key metrics in a dashboard card:
- Win rate badge
- Total P&L with color (green if positive, red if negative)
- Average win vs average loss comparison
- Best and worst trade highlights

---

### 3. Get Trades for All Agents in a Round

Retrieves trades for all participants in a specific round (useful for comparison).

**Endpoint:** `GET /api/trades/round/{round_id}/all-trades`

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/trades/round/987fcdeb-51a2-43f8-b456-123456789abc/all-trades"
```

**Example Response:**
```json
{
  "round_id": "987fcdeb-51a2-43f8-b456-123456789abc",
  "total_agents": 3,
  "total_trades": 72,
  "trades_by_agent": {
    "123e4567-e89b-12d3-a456-426614174000": {
      "agent_id": "123e4567-e89b-12d3-a456-426614174000",
      "user_id": "user-uuid-1",
      "strategy_type": "MEAN_REVERSION",
      "trade_count": 24,
      "trades": [
        {
          "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
          "agent_id": "123e4567-e89b-12d3-a456-426614174000",
          "tick": 45,
          "action": "OPEN_LONG",
          "price": 152.34,
          "executed_price": 152.49,
          "size": 65.0,
          "cost": 9.91,
          "pnl": 0.0,
          "equity_after": 99990.09,
          "reason": "Mean reversion signal: z-score = -2.15",
          "created_at": "2026-01-10T10:30:45.123456"
        }
        // ... more trades
      ]
    },
    "234b5678-f90c-23e4-b567-537625285111": {
      "agent_id": "234b5678-f90c-23e4-b567-537625285111",
      "user_id": "user-uuid-2",
      "strategy_type": "TREND_FOLLOWING",
      "trade_count": 18,
      "trades": [
        // ... trades
      ]
    },
    "345c6789-a01d-34f5-c678-648736396222": {
      "agent_id": "345c6789-a01d-34f5-c678-648736396222",
      "user_id": "user-uuid-3",
      "strategy_type": "MOMENTUM",
      "trade_count": 30,
      "trades": [
        // ... trades
      ]
    }
  }
}
```

**Frontend Use Case:**
Display a multi-agent comparison chart:
- Overlay trade markers from different agents on the same price chart
- Use different colors per agent
- Show side-by-side trade statistics
- Compare trading frequency and timing across strategies

---

## Trade Action Types Explained

| Action Type | Description | P&L Impact |
|------------|-------------|-----------|
| `OPEN_LONG` | Enter a long (buy) position | P&L = 0 (position opened, not closed yet) |
| `CLOSE_LONG` | Exit a long position (sell) | P&L = calculated (positive if price went up) |
| `OPEN_SHORT` | Enter a short (sell) position | P&L = 0 (position opened, not closed yet) |
| `CLOSE_SHORT` | Exit a short position (buy to cover) | P&L = calculated (positive if price went down) |

**Note:** Only closing trades (`CLOSE_LONG` and `CLOSE_SHORT`) have non-zero P&L values because they realize the profit or loss.

---

## Frontend Visualization Examples

### Example 1: Price Chart with Trade Markers

```typescript
import { LineChart, Line, XAxis, YAxis, Scatter } from 'recharts';

function TradingChart({ agentId }: { agentId: string }) {
  const [trades, setTrades] = useState([]);
  const [priceData, setPriceData] = useState([]);

  useEffect(() => {
    // Fetch trades
    fetch(`/api/trades/agent/${agentId}`)
      .then(res => res.json())
      .then(data => setTrades(data.trades));
    
    // Fetch price data from agent results
    fetch(`/api/rounds/{roundId}/agents`)
      .then(res => res.json())
      .then(data => {
        const agent = data.agents.find(a => a.id === agentId);
        setPriceData(agent.result.equity_curve);
      });
  }, [agentId]);

  // Map trades to chart markers
  const buyMarkers = trades
    .filter(t => t.action === 'OPEN_LONG' || t.action === 'CLOSE_SHORT')
    .map(t => ({ tick: t.tick, price: t.executed_price, pnl: t.pnl }));
  
  const sellMarkers = trades
    .filter(t => t.action === 'CLOSE_LONG' || t.action === 'OPEN_SHORT')
    .map(t => ({ tick: t.tick, price: t.executed_price, pnl: t.pnl }));

  return (
    <LineChart width={800} height={400}>
      {/* Price line */}
      <Line data={priceData} stroke="#8884d8" />
      
      {/* Buy markers (green) */}
      <Scatter data={buyMarkers} fill="green" shape="triangle" />
      
      {/* Sell markers (red) */}
      <Scatter data={sellMarkers} fill="red" shape="triangleDown" />
      
      <XAxis dataKey="tick" />
      <YAxis />
    </LineChart>
  );
}
```

### Example 2: Trade List Table

```typescript
function TradeListTable({ agentId }: { agentId: string }) {
  const [tradeData, setTradeData] = useState(null);

  useEffect(() => {
    fetch(`/api/trades/agent/${agentId}`)
      .then(res => res.json())
      .then(data => setTradeData(data));
  }, [agentId]);

  if (!tradeData) return <div>Loading...</div>;

  return (
    <div>
      <h2>Trade History</h2>
      <p>Win Rate: {tradeData.win_rate.toFixed(2)}%</p>
      <p>Total P&L: ${tradeData.total_pnl.toFixed(2)}</p>
      
      <table>
        <thead>
          <tr>
            <th>Tick</th>
            <th>Action</th>
            <th>Price</th>
            <th>Size</th>
            <th>P&L</th>
            <th>Reason</th>
          </tr>
        </thead>
        <tbody>
          {tradeData.trades.map(trade => (
            <tr key={trade.id}>
              <td>{trade.tick}</td>
              <td className={trade.action.includes('LONG') ? 'text-green' : 'text-red'}>
                {trade.action}
              </td>
              <td>${trade.executed_price.toFixed(2)}</td>
              <td>{trade.size.toFixed(2)}</td>
              <td className={trade.pnl >= 0 ? 'text-green' : 'text-red'}>
                ${trade.pnl.toFixed(2)}
              </td>
              <td>{trade.reason}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

### Example 3: Trade Statistics Dashboard

```typescript
function TradeStatsDashboard({ agentId }: { agentId: string }) {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    fetch(`/api/trades/agent/${agentId}/summary`)
      .then(res => res.json())
      .then(data => setStats(data));
  }, [agentId]);

  if (!stats) return <div>Loading...</div>;

  return (
    <div className="grid grid-cols-3 gap-4">
      <div className="stat-card">
        <h3>Win Rate</h3>
        <p className="text-2xl font-bold">{stats.win_rate.toFixed(1)}%</p>
        <p className="text-sm text-gray-500">
          {stats.winning_trades}W / {stats.losing_trades}L
        </p>
      </div>
      
      <div className="stat-card">
        <h3>Total P&L</h3>
        <p className={`text-2xl font-bold ${stats.total_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
          ${stats.total_pnl.toFixed(2)}
        </p>
        <p className="text-sm text-gray-500">
          Across {stats.total_closing_trades} trades
        </p>
      </div>
      
      <div className="stat-card">
        <h3>Best Trade</h3>
        <p className="text-2xl font-bold text-green-600">
          ${stats.largest_win.toFixed(2)}
        </p>
        <p className="text-sm text-gray-500">
          Worst: ${stats.largest_loss.toFixed(2)}
        </p>
      </div>
    </div>
  );
}
```

---

## Database Schema

The trades are stored in the `trades` table with the following structure:

```sql
CREATE TABLE trades (
    id UUID PRIMARY KEY,
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    tick INTEGER NOT NULL,
    action VARCHAR(20) NOT NULL,
    price FLOAT NOT NULL,
    executed_price FLOAT NOT NULL,
    size FLOAT NOT NULL,
    cost FLOAT NOT NULL,
    pnl FLOAT NOT NULL DEFAULT 0.0,
    equity_after FLOAT NOT NULL,
    reason VARCHAR(200),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX idx_trades_agent_id ON trades(agent_id);
CREATE INDEX idx_trades_agent_tick ON trades(agent_id, tick);
```

---

## Migration

The trade tracking system has been integrated via Alembic migration `003_add_trades_table.py`.

To apply the migration:

```bash
alembic upgrade head
```

To rollback (remove trades table):

```bash
alembic downgrade -1
```

---

## Automatic Trade Recording

Trades are automatically saved to the database during simulation. The simulation engine:

1. Executes trades through the `ExecutionEngine`
2. Records each trade with full details
3. Saves all trades to the database when simulation completes
4. Deletes old trades if re-simulating an existing agent

**No manual intervention needed** - just run your simulation and trades will be tracked automatically!

---

## Performance Considerations

- **Indexes**: The trades table has indexes on `agent_id` and `(agent_id, tick)` for fast queries
- **Cascade Deletes**: When an agent is deleted, all associated trades are automatically removed
- **Re-simulation**: Old trades are deleted before saving new ones to avoid duplicates
- **Batch Queries**: When fetching trades for multiple agents, use the `/round/{round_id}/all-trades` endpoint for better performance

---

## Testing the Endpoints

### Using cURL

```bash
# Get trades for a specific agent
curl -X GET "http://localhost:8000/api/trades/agent/{agent_id}"

# Get trade summary
curl -X GET "http://localhost:8000/api/trades/agent/{agent_id}/summary"

# Get all trades in a round
curl -X GET "http://localhost:8000/api/trades/round/{round_id}/all-trades"
```

### Using Python

```python
import requests

# Get trades
response = requests.get(f"http://localhost:8000/api/trades/agent/{agent_id}")
trade_data = response.json()

print(f"Total Trades: {trade_data['total_trades']}")
print(f"Win Rate: {trade_data['win_rate']:.2f}%")
print(f"Total P&L: ${trade_data['total_pnl']:.2f}")

for trade in trade_data['trades']:
    print(f"Tick {trade['tick']}: {trade['action']} @ ${trade['executed_price']:.2f} - P&L: ${trade['pnl']:.2f}")
```

### Using JavaScript/TypeScript

```typescript
// Fetch trades
async function getAgentTrades(agentId: string) {
  const response = await fetch(`/api/trades/agent/${agentId}`);
  const data = await response.json();
  
  console.log(`Total Trades: ${data.total_trades}`);
  console.log(`Win Rate: ${data.win_rate.toFixed(2)}%`);
  console.log(`Total P&L: $${data.total_pnl.toFixed(2)}`);
  
  return data;
}

// Fetch summary
async function getAgentSummary(agentId: string) {
  const response = await fetch(`/api/trades/agent/${agentId}/summary`);
  const summary = await response.json();
  
  console.log(`Avg Winning Trade: $${summary.avg_winning_trade.toFixed(2)}`);
  console.log(`Avg Losing Trade: $${summary.avg_losing_trade.toFixed(2)}`);
  
  return summary;
}
```

---

## Common Use Cases

### 1. Display Trade Markers on Equity Curve
Overlay buy/sell markers on the agent's equity curve to show when trades were executed and their impact.

### 2. Trade-by-Trade Analysis Table
Show a detailed table of all trades with columns for tick, action, price, P&L, and reason.

### 3. Win/Loss Statistics
Display win rate, average win, average loss, and profit factor in a dashboard.

### 4. Multi-Agent Comparison
Compare trading patterns across different agents in the same round (frequency, timing, profitability).

### 5. Trade Reason Analysis
Group trades by reason to understand which signals are most profitable.

### 6. Slippage Impact Analysis
Compare `price` vs `executed_price` to visualize slippage costs across trades.

---

## Troubleshooting

### No trades returned
- Ensure the simulation has been run for the agent
- Check that the agent_id is correct
- Verify the database connection

### Missing P&L values
- Only closing trades (`CLOSE_LONG` and `CLOSE_SHORT`) have P&L
- Opening trades (`OPEN_LONG` and `OPEN_SHORT`) always have P&L = 0

### Trades not appearing after simulation
- Check that the migration was applied: `alembic current`
- Verify the simulation completed successfully
- Look for errors in the application logs

---

## Summary

The trade tracking system provides comprehensive buy/sell transaction data for frontend visualization:

✅ **Automatic recording** of all trades during simulation  
✅ **Detailed trade information** (price, slippage, fees, P&L, reason)  
✅ **Multiple endpoints** for different use cases  
✅ **Aggregated statistics** for quick insights  
✅ **Efficient querying** with proper indexes  
✅ **Easy integration** with charting libraries  

Use the provided endpoints to build rich, interactive trading charts and dashboards that help users understand their agent's trading behavior!
