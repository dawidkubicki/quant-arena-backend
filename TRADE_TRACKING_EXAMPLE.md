# Trade Tracking System - Complete Example

This document shows a complete end-to-end example of how the trade tracking system works.

## Workflow Overview

1. **User creates an agent** for a round
2. **Simulation runs** and automatically records all trades
3. **Frontend fetches trades** via API endpoints
4. **Charts display trade markers** on price graphs

---

## Step 1: Create an Agent and Run Simulation

```bash
# 1. Create a round (admin only)
curl -X POST "http://localhost:8000/api/rounds" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Winter 2026 Championship",
    "config": {
      "market": {
        "num_ticks": 500,
        "initial_equity": 100000,
        "trading_interval": "5min"
      }
    }
  }'

# Response: { "id": "round-uuid-123", ... }

# 2. Create an agent (any authenticated user)
curl -X POST "http://localhost:8000/api/rounds/round-uuid-123/agents" \
  -H "Authorization: Bearer ${USER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_type": "MEAN_REVERSION",
    "config": {
      "strategy_params": {
        "lookback_window": 20,
        "entry_threshold": 2.0,
        "exit_threshold": 0.5
      },
      "risk_params": {
        "position_size_pct": 10.0,
        "stop_loss_pct": 5.0,
        "take_profit_pct": 10.0
      }
    }
  }'

# Response: { "id": "agent-uuid-456", ... }

# 3. Start the round (admin only)
curl -X POST "http://localhost:8000/api/rounds/round-uuid-123/start" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}"

# The simulation runs automatically and records all trades to the database
```

---

## Step 2: Fetch Trades After Simulation

Once the simulation completes, trades are available via the API:

```bash
# Get all trades for your agent
curl -X GET "http://localhost:8000/api/trades/agent/agent-uuid-456" \
  -H "Authorization: Bearer ${USER_TOKEN}"
```

**Example Response:**

```json
{
  "trades": [
    {
      "id": "trade-uuid-1",
      "agent_id": "agent-uuid-456",
      "tick": 23,
      "action": "OPEN_LONG",
      "price": 150.25,
      "executed_price": 150.40,
      "size": 66.5,
      "cost": 10.00,
      "pnl": 0.0,
      "equity_after": 99990.00,
      "reason": "Mean reversion signal: z-score = -2.15 (oversold)",
      "created_at": "2026-01-10T15:30:00Z"
    },
    {
      "id": "trade-uuid-2",
      "agent_id": "agent-uuid-456",
      "tick": 67,
      "action": "CLOSE_LONG",
      "price": 152.80,
      "executed_price": 152.65,
      "size": 66.5,
      "cost": 10.15,
      "pnl": 129.50,
      "equity_after": 100109.35,
      "reason": "Mean reversion exit: z-score = 0.45 (return to mean)",
      "created_at": "2026-01-10T15:30:00Z"
    },
    {
      "id": "trade-uuid-3",
      "agent_id": "agent-uuid-456",
      "tick": 102,
      "action": "OPEN_SHORT",
      "price": 154.20,
      "executed_price": 154.05,
      "size": 65.0,
      "cost": 10.01,
      "pnl": 0.0,
      "equity_after": 100099.34,
      "reason": "Mean reversion signal: z-score = 2.31 (overbought)",
      "created_at": "2026-01-10T15:30:00Z"
    },
    {
      "id": "trade-uuid-4",
      "agent_id": "agent-uuid-456",
      "tick": 145,
      "action": "CLOSE_SHORT",
      "price": 151.90,
      "executed_price": 152.05,
      "size": 65.0,
      "cost": 9.88,
      "pnl": 120.12,
      "equity_after": 100209.58,
      "reason": "Mean reversion exit: z-score = -0.23 (return to mean)",
      "created_at": "2026-01-10T15:30:00Z"
    }
  ],
  "total_trades": 4,
  "total_pnl": 249.62,
  "winning_trades": 2,
  "losing_trades": 0,
  "win_rate": 100.0
}
```

---

## Step 3: Display Trades on a Chart (Frontend)

### React/TypeScript Example

```typescript
import React, { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, Scatter } from 'recharts';

interface Trade {
  id: string;
  tick: number;
  action: string;
  price: number;
  executed_price: number;
  pnl: number;
  reason: string;
}

interface TradeData {
  trades: Trade[];
  total_pnl: number;
  win_rate: number;
}

function AgentTradingChart({ agentId, roundId }: { agentId: string; roundId: string }) {
  const [trades, setTrades] = useState<TradeData | null>(null);
  const [priceData, setPriceData] = useState<number[]>([]);

  useEffect(() => {
    // Fetch trades
    fetch(`/api/trades/agent/${agentId}`)
      .then(res => res.json())
      .then(data => setTrades(data));

    // Fetch price data from round
    fetch(`/api/rounds/${roundId}`)
      .then(res => res.json())
      .then(data => setPriceData(data.price_data));
  }, [agentId, roundId]);

  if (!trades || !priceData.length) return <div>Loading...</div>;

  // Prepare chart data
  const chartData = priceData.map((price, tick) => ({ tick, price }));

  // Separate trades by type for different markers
  const buyMarkers = trades.trades
    .filter(t => t.action === 'OPEN_LONG' || t.action === 'CLOSE_SHORT')
    .map(t => ({
      tick: t.tick,
      price: t.executed_price,
      pnl: t.pnl,
      reason: t.reason
    }));

  const sellMarkers = trades.trades
    .filter(t => t.action === 'CLOSE_LONG' || t.action === 'OPEN_SHORT')
    .map(t => ({
      tick: t.tick,
      price: t.executed_price,
      pnl: t.pnl,
      reason: t.reason
    }));

  return (
    <div>
      <div className="stats">
        <h3>Trading Performance</h3>
        <p>Total P&L: <span className={trades.total_pnl >= 0 ? 'positive' : 'negative'}>
          ${trades.total_pnl.toFixed(2)}
        </span></p>
        <p>Win Rate: {trades.win_rate.toFixed(1)}%</p>
      </div>

      <LineChart width={1000} height={500} data={chartData}>
        {/* Price line */}
        <Line 
          type="monotone" 
          dataKey="price" 
          stroke="#8884d8" 
          dot={false}
          isAnimationActive={false}
        />

        {/* Buy markers (green triangles pointing up) */}
        <Scatter 
          data={buyMarkers} 
          fill="green" 
          shape="triangle"
          isAnimationActive={false}
        />

        {/* Sell markers (red triangles pointing down) */}
        <Scatter 
          data={sellMarkers} 
          fill="red" 
          shape="triangleDown"
          isAnimationActive={false}
        />

        <XAxis dataKey="tick" label={{ value: 'Time (ticks)', position: 'insideBottom', offset: -5 }} />
        <YAxis label={{ value: 'Price ($)', angle: -90, position: 'insideLeft' }} />
        <Tooltip content={<CustomTooltip />} />
      </LineChart>
    </div>
  );
}

// Custom tooltip to show trade details on hover
function CustomTooltip({ active, payload }: any) {
  if (!active || !payload || !payload.length) return null;

  const data = payload[0].payload;

  return (
    <div className="custom-tooltip" style={{ 
      background: 'white', 
      border: '1px solid #ccc', 
      padding: '10px',
      borderRadius: '4px'
    }}>
      <p><strong>Tick {data.tick}</strong></p>
      <p>Price: ${data.price?.toFixed(2) || data.executed_price?.toFixed(2)}</p>
      {data.pnl !== undefined && (
        <p className={data.pnl >= 0 ? 'positive' : 'negative'}>
          P&L: ${data.pnl.toFixed(2)}
        </p>
      )}
      {data.reason && <p style={{ fontSize: '0.9em', color: '#666' }}>{data.reason}</p>}
    </div>
  );
}

export default AgentTradingChart;
```

### CSS Styling

```css
.stats {
  margin-bottom: 20px;
  padding: 15px;
  background: #f5f5f5;
  border-radius: 8px;
}

.stats h3 {
  margin-top: 0;
}

.positive {
  color: #22c55e;
  font-weight: bold;
}

.negative {
  color: #ef4444;
  font-weight: bold;
}

.custom-tooltip {
  background: white;
  border: 1px solid #ccc;
  padding: 10px;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
```

---

## Step 4: Trade List Table

Display a detailed table of all trades:

```typescript
function TradeTable({ agentId }: { agentId: string }) {
  const [tradeData, setTradeData] = useState<TradeData | null>(null);

  useEffect(() => {
    fetch(`/api/trades/agent/${agentId}`)
      .then(res => res.json())
      .then(data => setTradeData(data));
  }, [agentId]);

  if (!tradeData) return <div>Loading trades...</div>;

  return (
    <div>
      <h2>Trade History ({tradeData.total_trades} trades)</h2>
      
      <table className="trade-table">
        <thead>
          <tr>
            <th>Tick</th>
            <th>Action</th>
            <th>Entry Price</th>
            <th>Executed</th>
            <th>Slippage</th>
            <th>Size</th>
            <th>Fees</th>
            <th>P&L</th>
            <th>Equity</th>
            <th>Reason</th>
          </tr>
        </thead>
        <tbody>
          {tradeData.trades.map(trade => {
            const slippage = Math.abs(trade.executed_price - trade.price);
            const isLong = trade.action.includes('LONG');
            const isOpen = trade.action.includes('OPEN');
            
            return (
              <tr key={trade.id}>
                <td>{trade.tick}</td>
                <td className={isLong ? 'long-trade' : 'short-trade'}>
                  {trade.action}
                </td>
                <td>${trade.price.toFixed(2)}</td>
                <td>${trade.executed_price.toFixed(2)}</td>
                <td>${slippage.toFixed(4)}</td>
                <td>{trade.size.toFixed(2)}</td>
                <td>${trade.cost.toFixed(2)}</td>
                <td className={trade.pnl >= 0 ? 'positive' : 'negative'}>
                  {isOpen ? '-' : `$${trade.pnl.toFixed(2)}`}
                </td>
                <td>${trade.equity_after.toFixed(2)}</td>
                <td className="reason">{trade.reason}</td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <div className="summary">
        <p>Total P&L: <span className={tradeData.total_pnl >= 0 ? 'positive' : 'negative'}>
          ${tradeData.total_pnl.toFixed(2)}
        </span></p>
        <p>Win Rate: {tradeData.win_rate.toFixed(1)}%</p>
        <p>Winning Trades: {tradeData.winning_trades} | Losing Trades: {tradeData.losing_trades}</p>
      </div>
    </div>
  );
}
```

```css
.trade-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 20px;
}

.trade-table th,
.trade-table td {
  padding: 10px;
  text-align: left;
  border-bottom: 1px solid #ddd;
}

.trade-table th {
  background: #f5f5f5;
  font-weight: 600;
}

.long-trade {
  color: #22c55e;
  font-weight: 600;
}

.short-trade {
  color: #ef4444;
  font-weight: 600;
}

.reason {
  font-size: 0.9em;
  color: #666;
  max-width: 300px;
}

.summary {
  margin-top: 20px;
  padding: 15px;
  background: #f5f5f5;
  border-radius: 8px;
}
```

---

## What Happens Behind the Scenes

### During Simulation

1. **ExecutionEngine** executes each trade and records details in memory
2. **Simulation engine** runs the agent through all ticks
3. **After simulation completes**, `_save_agent_results()` is called:
   - Deletes old trades for this agent (if re-simulating)
   - Creates a new `Trade` record for each trade
   - Saves all trades to the database in a single transaction

### When Fetching Trades

1. Frontend calls `/api/trades/agent/{agent_id}`
2. API queries `trades` table with index on `agent_id`
3. Returns trades ordered by `tick` (chronological)
4. Includes summary statistics (total P&L, win rate, etc.)

---

## Advanced Use Cases

### Comparing Multiple Agents

```typescript
async function compareAgentTrades(roundId: string) {
  // Fetch all trades for the round
  const response = await fetch(`/api/trades/round/${roundId}/all-trades`);
  const data = await response.json();

  // Extract all agents
  const agents = Object.values(data.trades_by_agent);

  // Compare trading frequency
  agents.forEach(agent => {
    console.log(`${agent.strategy_type}: ${agent.trade_count} trades`);
  });

  // Find most active trader
  const mostActive = agents.reduce((max, agent) => 
    agent.trade_count > max.trade_count ? agent : max
  );

  console.log(`Most active: ${mostActive.strategy_type} with ${mostActive.trade_count} trades`);
}
```

### Analyzing Trade Timing

```typescript
function analyzeTradeTimings(trades: Trade[]) {
  const openTrades = trades.filter(t => t.action.includes('OPEN'));
  const closeTrades = trades.filter(t => t.action.includes('CLOSE'));

  // Calculate average holding period
  let totalHoldingPeriod = 0;
  let tradeCount = 0;

  for (let i = 0; i < closeTrades.length; i++) {
    const close = closeTrades[i];
    // Find corresponding open trade (previous trade before this close)
    const open = openTrades.reverse().find(o => o.tick < close.tick);
    
    if (open) {
      totalHoldingPeriod += close.tick - open.tick;
      tradeCount++;
    }
  }

  const avgHoldingPeriod = totalHoldingPeriod / tradeCount;
  console.log(`Average holding period: ${avgHoldingPeriod.toFixed(1)} ticks`);
}
```

---

## Summary

The trade tracking system provides:

✅ **Automatic recording** - No manual work required  
✅ **Complete trade details** - Price, slippage, fees, P&L, reason  
✅ **Easy API access** - Simple REST endpoints  
✅ **Rich metadata** - Summary statistics included  
✅ **Frontend ready** - Perfect for charts and tables  

All trades are stored in the database and persist across sessions, making it easy to build powerful trading analytics and visualizations!
