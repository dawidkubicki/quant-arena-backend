# Frontend API Changes - Strategy Parameters Refactor

## Summary

The backend has been refactored to **eliminate duplicate RSI parameters** between `StrategyParams` and `SignalStack`. Each strategy now has its own dedicated parameters, and `SignalStack` contains only **universal filters** that apply to all strategies.

---

## Breaking Changes

### 1. SignalStack - Removed Fields

The following fields have been **REMOVED** from `signal_stack`:

```diff
- use_sma: boolean
- sma_window: number
- use_rsi: boolean
- rsi_window: number
- rsi_overbought: number
- rsi_oversold: number
```

### 2. SignalStack - Renamed Fields

| Old Field | New Field | Notes |
|-----------|-----------|-------|
| `use_sma` | `use_sma_trend_filter` | Renamed for clarity |
| `sma_window` | `sma_filter_window` | Renamed, default changed from 20 → 50 |

### 3. RSI is Now Strategy-Specific

RSI parameters (`rsi_window`, `rsi_overbought`, `rsi_oversold`) are **only used by the Momentum strategy** and should only be shown when Momentum is selected.

---

## New Data Structures

### AgentConfig (Complete Structure)

```typescript
interface AgentConfig {
  strategy_params: StrategyParams;
  signal_stack: SignalStack;
  risk_params: RiskParams;
}
```

### StrategyParams

Each strategy uses **only its relevant parameters**. The frontend should show/hide fields based on the selected strategy type.

```typescript
interface StrategyParams {
  // === MEAN REVERSION ===
  // Show these when strategy_type === "MEAN_REVERSION"
  lookback_window: number;    // Default: 20, Range: 5-200
  entry_threshold: number;    // Default: 2.0, Range: 0.5-5.0
  exit_threshold: number;     // Default: 0.5, Range: 0.0-2.0

  // === TREND FOLLOWING ===
  // Show these when strategy_type === "TREND_FOLLOWING"
  fast_window: number;        // Default: 10, Range: 3-50
  slow_window: number;        // Default: 30, Range: 10-200
  atr_multiplier: number;     // Default: 2.0, Range: 0.5-5.0

  // === MOMENTUM ===
  // Show these when strategy_type === "MOMENTUM"
  momentum_window: number;    // Default: 14, Range: 5-100
  rsi_window: number;         // Default: 14, Range: 5-50
  rsi_overbought: number;     // Default: 70, Range: 50-95
  rsi_oversold: number;       // Default: 30, Range: 5-50
}
```

### SignalStack (Universal Filters)

These filters apply to **ALL strategies** equally. They are optional enhancements that reduce signal confidence based on market conditions.

```typescript
interface SignalStack {
  // === SMA TREND FILTER ===
  // When enabled: only allow LONG signals when price > SMA (uptrend)
  //               only allow SHORT signals when price < SMA (downtrend)
  use_sma_trend_filter: boolean;  // Default: false
  sma_filter_window: number;      // Default: 50, Range: 10-200

  // === VOLATILITY FILTER ===
  // When enabled: reduces signal confidence during high volatility periods
  use_volatility_filter: boolean; // Default: false
  volatility_window: number;      // Default: 20, Range: 5-100
  volatility_threshold: number;   // Default: 1.5, Range: 0.5-5.0
}
```

### RiskParams (Unchanged)

```typescript
interface RiskParams {
  position_size_pct: number;   // Default: 10, Range: 1-100
  max_leverage: number;        // Default: 1.0, Range: 1.0-5.0
  stop_loss_pct: number;       // Default: 5, Range: 0.5-50
  take_profit_pct: number;     // Default: 10, Range: 1-100
  max_drawdown_kill: number;   // Default: 20, Range: 5-100
}
```

---

## UI Recommendations

### Strategy Parameter Display

Show only relevant parameters based on selected strategy:

```tsx
// Pseudocode for conditional rendering
{strategyType === 'MEAN_REVERSION' && (
  <>
    <Input label="Lookback Window" field="lookback_window" />
    <Input label="Entry Threshold (Z-score)" field="entry_threshold" />
    <Input label="Exit Threshold (Z-score)" field="exit_threshold" />
  </>
)}

{strategyType === 'TREND_FOLLOWING' && (
  <>
    <Input label="Fast EMA Window" field="fast_window" />
    <Input label="Slow EMA Window" field="slow_window" />
    <Input label="ATR Multiplier" field="atr_multiplier" />
  </>
)}

{strategyType === 'MOMENTUM' && (
  <>
    <Input label="Momentum Window" field="momentum_window" />
    <Input label="RSI Window" field="rsi_window" />
    <Input label="RSI Overbought" field="rsi_overbought" />
    <Input label="RSI Oversold" field="rsi_oversold" />
  </>
)}
```

### Signal Stack Display

Always show these (they apply to all strategies):

```tsx
<Section title="Signal Filters (Optional)">
  <Toggle label="SMA Trend Filter" field="use_sma_trend_filter" />
  {useSMATrendFilter && (
    <Input label="SMA Period" field="sma_filter_window" />
  )}
  
  <Toggle label="Volatility Filter" field="use_volatility_filter" />
  {useVolatilityFilter && (
    <>
      <Input label="Volatility Window" field="volatility_window" />
      <Input label="Volatility Threshold" field="volatility_threshold" />
    </>
  )}
</Section>
```

---

## Strategy Descriptions (For UI Tooltips)

### Mean Reversion
- **Description**: Bets on price returning to average - buys dips, sells rallies
- **Best for**: Range-bound, choppy markets
- **Typical Beta**: Low (<1.0) - dampens market moves
- **Risk Profile**: Lower volatility but can struggle in strong trends

### Trend Following
- **Description**: Follows the trend using moving average crossovers
- **Best for**: Trending markets with clear directional moves
- **Typical Beta**: Medium (~1.0) - moves with the market
- **Risk Profile**: Can have whipsaws in choppy markets

### Momentum
- **Description**: Buys strength, sells weakness based on price momentum and RSI
- **Best for**: Markets with clear momentum and overbought/oversold conditions
- **Typical Beta**: High (>1.0) - amplifies market moves
- **Risk Profile**: Higher volatility, larger drawdowns possible

---

## Parameter Descriptions (For UI Tooltips)

### Strategy Parameters

| Parameter | Strategy | Description |
|-----------|----------|-------------|
| `lookback_window` | Mean Reversion | Window for calculating mean price (z-score baseline). Larger = smoother mean |
| `entry_threshold` | Mean Reversion | Z-score threshold to enter position. Higher = more extreme deviation required |
| `exit_threshold` | Mean Reversion | Z-score threshold to exit position. Lower = exit closer to mean |
| `fast_window` | Trend Following | Fast EMA period. Shorter = more responsive to recent prices |
| `slow_window` | Trend Following | Slow EMA period. Longer = smoother trend identification |
| `atr_multiplier` | Trend Following | ATR multiplier for volatility-adjusted signals |
| `momentum_window` | Momentum | Lookback period for momentum calculation |
| `rsi_window` | Momentum | RSI calculation period |
| `rsi_overbought` | Momentum | RSI level indicating overbought (avoid new longs above this) |
| `rsi_oversold` | Momentum | RSI level indicating oversold (avoid new shorts below this) |

### Signal Stack (Universal Filters)

| Parameter | Description |
|-----------|-------------|
| `use_sma_trend_filter` | When ON: only allows LONG when price > SMA, SHORT when price < SMA |
| `sma_filter_window` | SMA period for trend filter. Longer = stronger trend confirmation |
| `use_volatility_filter` | When ON: reduces signal confidence during high volatility |
| `volatility_window` | Window for volatility calculation |
| `volatility_threshold` | Volatility multiplier threshold. Higher = more permissive |

---

## Example API Request

### Creating an Agent with Momentum Strategy

```json
POST /api/rounds/{round_id}/agents

{
  "strategy_type": "MOMENTUM",
  "config": {
    "strategy_params": {
      "momentum_window": 14,
      "rsi_window": 14,
      "rsi_overbought": 70,
      "rsi_oversold": 30
    },
    "signal_stack": {
      "use_sma_trend_filter": true,
      "sma_filter_window": 50,
      "use_volatility_filter": false,
      "volatility_window": 20,
      "volatility_threshold": 1.5
    },
    "risk_params": {
      "position_size_pct": 10,
      "stop_loss_pct": 5,
      "take_profit_pct": 10,
      "max_drawdown_kill": 20
    }
  }
}
```

### Creating an Agent with Mean Reversion Strategy

```json
POST /api/rounds/{round_id}/agents

{
  "strategy_type": "MEAN_REVERSION",
  "config": {
    "strategy_params": {
      "lookback_window": 20,
      "entry_threshold": 2.0,
      "exit_threshold": 0.5
    },
    "signal_stack": {
      "use_sma_trend_filter": false,
      "sma_filter_window": 50,
      "use_volatility_filter": true,
      "volatility_window": 20,
      "volatility_threshold": 1.5
    },
    "risk_params": {
      "position_size_pct": 15,
      "stop_loss_pct": 3,
      "take_profit_pct": 8,
      "max_drawdown_kill": 15
    }
  }
}
```

---

## Migration Checklist

- [ ] Remove `use_sma` from signal_stack form (replaced by `use_sma_trend_filter`)
- [ ] Rename `sma_window` to `sma_filter_window` in signal_stack form
- [ ] Remove `use_rsi`, `rsi_window`, `rsi_overbought`, `rsi_oversold` from signal_stack form
- [ ] Implement conditional rendering of strategy_params based on strategy_type
- [ ] Update default value for `sma_filter_window` from 20 to 50
- [ ] Add tooltips/descriptions for each parameter
- [ ] Test with each strategy type (Mean Reversion, Trend Following, Momentum)

---

# Async Round Start - Scalability Update

## Summary

The round start endpoint has been changed to **async execution** to handle 100+ participants efficiently. The simulation now runs in the background and returns immediately with status `202 Accepted`.

---

## Breaking Changes

### 1. `POST /api/rounds/{round_id}/start` - Now Async

**Before (Blocking):**
```
POST /api/rounds/{round_id}/start
→ Waits for entire simulation to complete
→ Returns 200 OK with final status
→ Could timeout with many participants
```

**After (Async):**
```
POST /api/rounds/{round_id}/start
→ Returns immediately with 202 Accepted
→ Simulation runs in background
→ Frontend polls for progress
```

### 2. New Round Status: `FAILED`

A new status has been added for error handling:

```typescript
type RoundStatus = "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";
```

### 3. Enhanced Status Response

The status endpoint now returns progress information:

```typescript
interface RoundStatusResponse {
  id: string;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";
  progress: number;           // 0-100 percentage of simulation ticks completed
  agents_processed: number;   // Number of agents with saved results
  total_agents: number;       // Total agents in the round
  error_message: string | null; // Error details if status is FAILED
  started_at: string | null;
  completed_at: string | null;
}
```

---

## New Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Frontend Flow                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. Admin clicks "Start Round"                                      │
│     │                                                               │
│     ▼                                                               │
│  2. POST /api/rounds/{id}/start                                     │
│     │                                                               │
│     ▼                                                               │
│  3. Receive 202 Accepted immediately                                │
│     {status: "RUNNING", progress: 0, total_agents: 100}             │
│     │                                                               │
│     ▼                                                               │
│  4. Show progress UI (progress bar, status indicator)               │
│     │                                                               │
│     ▼                                                               │
│  5. Poll GET /api/rounds/{id}/status every 1-2 seconds              │
│     │                                                               │
│     ├─── status: "RUNNING", progress: 45%  → Update progress bar    │
│     │                                                               │
│     ├─── status: "RUNNING", progress: 80%  → Update progress bar    │
│     │                                                               │
│     ├─── status: "COMPLETED", progress: 100%  → Show results        │
│     │                                                               │
│     └─── status: "FAILED", error_message: "..."  → Show error       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Guide

### 1. Starting a Round

```typescript
async function startRound(roundId: string) {
  const response = await fetch(`/api/rounds/${roundId}/start`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` }
  });
  
  // Now returns 202 Accepted immediately
  if (response.status === 202) {
    const data = await response.json();
    // Start polling for progress
    startPolling(roundId);
    return data;
  }
  
  throw new Error('Failed to start round');
}
```

### 2. Polling for Progress

```typescript
interface RoundStatus {
  id: string;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';
  progress: number;
  agents_processed: number;
  total_agents: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
}

async function pollRoundStatus(roundId: string): Promise<RoundStatus> {
  const response = await fetch(`/api/rounds/${roundId}/status`);
  return response.json();
}

function startPolling(roundId: string) {
  const intervalId = setInterval(async () => {
    const status = await pollRoundStatus(roundId);
    
    // Update UI with progress
    updateProgressUI(status.progress, status.agents_processed, status.total_agents);
    
    if (status.status === 'COMPLETED') {
      clearInterval(intervalId);
      showResults(roundId);
    } else if (status.status === 'FAILED') {
      clearInterval(intervalId);
      showError(status.error_message);
    }
  }, 1500); // Poll every 1.5 seconds
}
```

### 3. Progress UI Component (React Example)

```tsx
interface SimulationProgressProps {
  roundId: string;
  onComplete: () => void;
  onError: (message: string) => void;
}

function SimulationProgress({ roundId, onComplete, onError }: SimulationProgressProps) {
  const [status, setStatus] = useState<RoundStatus | null>(null);
  
  useEffect(() => {
    const interval = setInterval(async () => {
      const data = await pollRoundStatus(roundId);
      setStatus(data);
      
      if (data.status === 'COMPLETED') {
        clearInterval(interval);
        onComplete();
      } else if (data.status === 'FAILED') {
        clearInterval(interval);
        onError(data.error_message || 'Simulation failed');
      }
    }, 1500);
    
    return () => clearInterval(interval);
  }, [roundId]);
  
  if (!status) return <Spinner />;
  
  return (
    <div className="simulation-progress">
      <h3>Simulation Running</h3>
      
      {/* Progress Bar */}
      <div className="progress-bar">
        <div 
          className="progress-fill" 
          style={{ width: `${status.progress}%` }}
        />
      </div>
      
      {/* Progress Text */}
      <p className="progress-text">
        {status.progress}% complete
      </p>
      
      {/* Agent Counter */}
      <p className="agent-count">
        Processing {status.total_agents} agents...
      </p>
      
      {/* Agents Saved (shows after tick processing) */}
      {status.agents_processed > 0 && (
        <p className="agents-saved">
          Saved results: {status.agents_processed} / {status.total_agents}
        </p>
      )}
    </div>
  );
}
```

### 4. Handling the FAILED Status

```tsx
function RoundStatusBadge({ status, errorMessage }: { 
  status: RoundStatus['status']; 
  errorMessage: string | null;
}) {
  const statusConfig = {
    PENDING: { color: 'gray', label: 'Pending' },
    RUNNING: { color: 'blue', label: 'Running' },
    COMPLETED: { color: 'green', label: 'Completed' },
    FAILED: { color: 'red', label: 'Failed' }
  };
  
  const config = statusConfig[status];
  
  return (
    <div className={`badge badge-${config.color}`}>
      {config.label}
      {status === 'FAILED' && errorMessage && (
        <Tooltip content={errorMessage}>
          <InfoIcon />
        </Tooltip>
      )}
    </div>
  );
}
```

---

## API Response Examples

### Starting a Round (202 Accepted)

```json
POST /api/rounds/abc-123/start

Response (202 Accepted):
{
  "id": "abc-123",
  "status": "RUNNING",
  "progress": 0,
  "agents_processed": 0,
  "total_agents": 100,
  "error_message": null,
  "started_at": "2026-01-10T12:00:00Z",
  "completed_at": null
}
```

### Polling Status - In Progress

```json
GET /api/rounds/abc-123/status

Response (200 OK):
{
  "id": "abc-123",
  "status": "RUNNING",
  "progress": 45,
  "agents_processed": 0,
  "total_agents": 100,
  "error_message": null,
  "started_at": "2026-01-10T12:00:00Z",
  "completed_at": null
}
```

### Polling Status - Completed

```json
GET /api/rounds/abc-123/status

Response (200 OK):
{
  "id": "abc-123",
  "status": "COMPLETED",
  "progress": 100,
  "agents_processed": 100,
  "total_agents": 100,
  "error_message": null,
  "started_at": "2026-01-10T12:00:00Z",
  "completed_at": "2026-01-10T12:02:30Z"
}
```

### Polling Status - Failed

```json
GET /api/rounds/abc-123/status

Response (200 OK):
{
  "id": "abc-123",
  "status": "FAILED",
  "progress": 23,
  "agents_processed": 0,
  "total_agents": 100,
  "error_message": "Database connection lost during simulation",
  "started_at": "2026-01-10T12:00:00Z",
  "completed_at": null
}
```

---

## Migration Checklist - Async Round Start

- [ ] Update `startRound()` function to handle 202 Accepted response
- [ ] Add polling mechanism for round status
- [ ] Create progress UI component (progress bar, percentage, agent count)
- [ ] Handle new `FAILED` status in round status displays
- [ ] Add `error_message` display for failed rounds
- [ ] Update TypeScript types for `RoundStatusResponse`
- [ ] Update any loading states that waited for round completion
- [ ] Test with large number of agents (10+, 50+, 100+)
- [ ] Add cleanup for polling intervals on component unmount
