# Quant Arena API Documentation

## Overview

Quant Arena is an educational trading simulation platform where students compete using different algorithmic trading strategies. Students configure trading agents that compete in simulated market rounds, and results are displayed on a leaderboard.

## Base URL

- **Local**: `http://localhost:8000`
- **Production**: `https://your-backend.onrender.com`

## Authentication

The API uses **Supabase JWT tokens** for authentication.

### How It Works

1. Frontend authenticates users via Supabase Auth (email/password, OAuth, etc.)
2. Frontend gets the Supabase access token from the session
3. Frontend sends the token in the `Authorization` header for protected endpoints

### Header Format

```
Authorization: Bearer <supabase_access_token>
```

### User Creation

Users are **automatically created** in the backend database when they first authenticate. The backend extracts user info from the Supabase JWT token:

- `sub` → Supabase user ID (stored as `supabase_id`)
- `email` → User's email
- `user_metadata.nickname` → Display name (falls back to email prefix)
- `user_metadata.color` → Hex color for UI (default: `#3B82F6`)
- `user_metadata.icon` → Icon identifier (default: `user`)

### Admin Access

Admin users are determined by their email. Emails listed in the `ADMIN_EMAILS` environment variable have admin privileges.

---

## Data Models

### User

```typescript
{
  id: string;              // UUID
  supabase_id: string;     // Supabase user ID
  email: string | null;
  nickname: string;
  color: string;           // Hex color, e.g. "#3B82F6"
  icon: string;            // Icon identifier
  is_admin: boolean;
  created_at: string;      // ISO datetime
}
```

### Round

```typescript
{
  id: string;              // UUID
  name: string;
  status: "PENDING" | "RUNNING" | "COMPLETED";
  market_seed: number;     // Seed for reproducible simulation
  config: RoundConfig;
  price_data: number[] | null;  // Populated after simulation
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  agent_count: number;
}
```

### Round Config

```typescript
{
  market: {
    initial_price: number;      // Default: 100.0
    num_ticks: number;          // Default: 1000
    initial_equity: number;     // Default: 100000.0
    base_volatility: number;    // Default: 0.02
    base_drift: number;         // Default: 0.0001
    trend_probability: number;  // Default: 0.3
    volatile_probability: number; // Default: 0.2
    regime_persistence: number; // Default: 0.95
    base_slippage: number;      // Default: 0.001
    fee_rate: number;           // Default: 0.001
  }
}
```

### Agent

```typescript
{
  id: string;
  user_id: string;
  round_id: string;
  strategy_type: "MEAN_REVERSION" | "TREND_FOLLOWING" | "MOMENTUM" | "GHOST";
  config: AgentConfig;
  created_at: string;
  result: AgentResult | null;
  user_nickname: string | null;
  user_color: string | null;
}
```

### Agent Config

```typescript
{
  strategy_params: {
    // Mean Reversion
    lookback_window: number;    // Default: 20
    entry_threshold: number;    // Default: 2.0
    exit_threshold: number;     // Default: 0.5
    
    // Trend Following
    fast_window: number;        // Default: 10
    slow_window: number;        // Default: 30
    atr_multiplier: number;     // Default: 2.0
    
    // Momentum
    momentum_window: number;    // Default: 14
    rsi_window: number;         // Default: 14
    rsi_overbought: number;     // Default: 70
    rsi_oversold: number;       // Default: 30
  },
  signal_stack: {
    use_sma: boolean;
    sma_window: number;
    use_rsi: boolean;
    rsi_window: number;
    rsi_overbought: number;
    rsi_oversold: number;
    use_volatility_filter: boolean;
    volatility_window: number;
    volatility_threshold: number;
  },
  risk_params: {
    position_size_pct: number;  // Default: 10 (%)
    max_leverage: number;       // Default: 1.0
    stop_loss_pct: number;      // Default: 5 (%)
    take_profit_pct: number;    // Default: 10 (%)
    max_drawdown_kill: number;  // Default: 20 (%)
  }
}
```

### Agent Result

```typescript
{
  id: string;
  agent_id: string;
  final_equity: number;
  total_return: number;        // Percentage
  sharpe_ratio: number | null;
  max_drawdown: number;        // Percentage (positive value)
  calmar_ratio: number | null;
  total_trades: number;
  win_rate: number | null;     // Percentage
  survival_time: number;       // Ticks survived
  equity_curve: number[];      // Array of equity values per tick
  trades: Trade[];
  created_at: string;
}
```

### Trade

```typescript
{
  tick: number;
  action: string;              // "OPEN_LONG", "CLOSE_LONG", "OPEN_SHORT", "CLOSE_SHORT"
  price: number;
  executed_price: number;      // After slippage
  size: number;
  cost: number;                // Transaction fees
  pnl: number;                 // Realized P&L
  equity_after: number;
  reason: string;
}
```

### Leaderboard Entry

```typescript
{
  rank: number;
  agent_id: string;
  user_id: string;
  nickname: string;
  color: string;
  icon: string;
  strategy_type: string;
  final_equity: number;
  total_return: number;
  sharpe_ratio: number | null;
  max_drawdown: number;
  calmar_ratio: number | null;
  win_rate: number | null;
  total_trades: number;
  survival_time: number;
  is_ghost: boolean;           // True for benchmark agent
}
```

---

## API Endpoints

### Health & Info

#### GET /
Root endpoint.

**Response:**
```json
{"message": "Welcome to Quant Arena API"}
```

#### GET /health
Health check.

**Response:**
```json
{"status": "healthy"}
```

---

### Authentication

#### GET /api/auth/me
Get current authenticated user. Creates user in database if first login.

**Auth Required:** Yes

**Response:** `User` object

**Example:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "supabase_id": "auth0|123456",
  "email": "student@example.com",
  "nickname": "TraderJoe",
  "color": "#3B82F6",
  "icon": "user",
  "is_admin": false,
  "created_at": "2024-01-08T12:00:00"
}
```

#### PUT /api/auth/me
Update current user's profile.

**Auth Required:** Yes

**Request Body:**
```json
{
  "nickname": "NewName",
  "color": "#EF4444",
  "icon": "chart"
}
```

**Response:** Updated `User` object

#### GET /api/auth/verify
Verify token validity.

**Auth Required:** Yes

**Response:**
```json
{
  "valid": true,
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "is_admin": false,
  "nickname": "TraderJoe"
}
```

---

### Users

#### GET /api/users/me
Get current user profile.

**Auth Required:** Yes

**Response:** `User` object

#### GET /api/users/
List all users (admin only).

**Auth Required:** Yes (Admin)

**Response:** Array of `UserPublic` objects

#### GET /api/users/{user_id}
Get public info for a specific user.

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "nickname": "TraderJoe",
  "color": "#3B82F6",
  "icon": "user"
}
```

---

### Rounds

#### POST /api/rounds/
Create a new round.

**Auth Required:** Yes (Admin)

**Request Body:**
```json
{
  "name": "Battle Round 1",
  "market_seed": 42,
  "config": {
    "market": {
      "initial_price": 100.0,
      "num_ticks": 1000,
      "initial_equity": 100000.0,
      "base_volatility": 0.02,
      "fee_rate": 0.001
    }
  }
}
```

**Response:** `Round` object

#### GET /api/rounds/
List all rounds.

**Query Parameters:**
- `status_filter` (optional): `PENDING`, `RUNNING`, or `COMPLETED`
- `skip` (optional): Pagination offset (default: 0)
- `limit` (optional): Max results (default: 50)

**Response:** Array of `RoundList` objects
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Battle Round 1",
    "status": "PENDING",
    "market_seed": 42,
    "agent_count": 5,
    "created_at": "2024-01-08T12:00:00"
  }
]
```

#### GET /api/rounds/{round_id}
Get round details including price data if completed.

**Response:** `Round` object (includes `price_data` array if `status == COMPLETED`)

#### GET /api/rounds/{round_id}/status
Get round status (for polling).

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "COMPLETED",
  "started_at": "2024-01-08T12:00:00",
  "completed_at": "2024-01-08T12:00:05"
}
```

#### POST /api/rounds/{round_id}/start
Start the simulation for a round. Runs all ticks at once (batch mode).

**Auth Required:** Yes (Admin)

**Response:** `RoundStatus` object

**Notes:**
- Automatically adds a "Ghost" benchmark agent
- Simulation runs synchronously (may take a few seconds)
- All agents compete simultaneously

#### POST /api/rounds/{round_id}/stop
Force stop a running round.

**Auth Required:** Yes (Admin)

**Response:** `RoundStatus` object

**Example Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "COMPLETED",
  "started_at": "2024-01-08T12:00:00",
  "completed_at": "2024-01-08T12:00:05"
}
```

**Notes:**
- Can only force stop rounds that are currently `RUNNING`
- Round status will be set to `COMPLETED` with current timestamp
- Useful for stopping simulations that are taking too long or encountering issues

#### DELETE /api/rounds/{round_id}
Delete a round.

**Auth Required:** Yes (Admin)

**Response:**
```json
{"message": "Round deleted successfully"}
```

---

### Agents

#### POST /api/rounds/{round_id}/agents
Create or update agent configuration for a round.

**Auth Required:** Yes

**Request Body:**
```json
{
  "strategy_type": "MEAN_REVERSION",
  "config": {
    "strategy_params": {
      "lookback_window": 20,
      "entry_threshold": 2.0,
      "exit_threshold": 0.5
    },
    "signal_stack": {
      "use_sma": true,
      "sma_window": 20,
      "use_rsi": true,
      "rsi_window": 14,
      "rsi_overbought": 70,
      "rsi_oversold": 30
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

**Response:** `Agent` object

**Notes:**
- Each user can only have ONE agent per round
- Calling again updates the existing agent
- Can only create/update while round is `PENDING`

#### GET /api/rounds/{round_id}/agents/me
Get current user's agent in a round.

**Auth Required:** Yes

**Response:** `Agent` object (includes `result` if round completed)

#### GET /api/rounds/{round_id}/agents
List all agents in a round.

**Response:** Array of `Agent` objects

#### GET /api/rounds/{round_id}/agents/{agent_id}
Get specific agent details.

**Response:** `Agent` object

#### GET /api/rounds/{round_id}/agents/{agent_id}/results
Get detailed results for an agent.

**Response:** `AgentResult` object

#### DELETE /api/rounds/{round_id}/agents/me
Delete current user's agent from a round.

**Auth Required:** Yes

**Response:**
```json
{"message": "Agent deleted successfully"}
```

**Notes:** Can only delete while round is `PENDING`

---

### Leaderboard

#### GET /api/rounds/{round_id}/leaderboard
Get rankings for a completed round.

**Query Parameters:**
- `sort_by` (optional): `sharpe_ratio` (default), `total_return`, `max_drawdown`, `calmar_ratio`, `win_rate`, `survival_time`
- `ascending` (optional): `true` or `false` (default: false, except for max_drawdown)

**Response:**
```json
{
  "round_id": "550e8400-e29b-41d4-a716-446655440000",
  "round_name": "Battle Round 1",
  "entries": [
    {
      "rank": 1,
      "agent_id": "...",
      "user_id": "...",
      "nickname": "TraderJoe",
      "color": "#3B82F6",
      "icon": "chart",
      "strategy_type": "TREND_FOLLOWING",
      "final_equity": 115000.0,
      "total_return": 15.0,
      "sharpe_ratio": 1.5,
      "max_drawdown": 8.5,
      "calmar_ratio": 1.76,
      "win_rate": 55.0,
      "total_trades": 42,
      "survival_time": 1000,
      "is_ghost": false
    }
  ],
  "total_participants": 10,
  "best_sharpe": 1.5,
  "best_return": 15.0,
  "lowest_drawdown": 5.2,
  "average_survival": 850.0
}
```

#### GET /api/rounds/{round_id}/leaderboard/me?user_id={user_id}
Get current user's ranking in a round.

**Response:**
```json
{
  "rank": 3,
  "total_participants": 10,
  "final_equity": 108000.0,
  "total_return": 8.0,
  "sharpe_ratio": 1.2,
  "max_drawdown": 12.0,
  "percentile": 70.0
}
```

---

## Trading Strategies

### Mean Reversion
**Logic:** When price deviates significantly from its moving average, bet on price returning to the mean.

- **Entry:** Go LONG when z-score < -entry_threshold, SHORT when z-score > entry_threshold
- **Exit:** Close position when z-score returns to within exit_threshold
- **Best in:** Range-bound, mean-reverting markets
- **Risk:** Trend markets can cause large losses

### Trend Following
**Logic:** Follow market trends using moving average crossovers.

- **Entry:** Go LONG when fast MA crosses above slow MA, SHORT when below
- **Exit:** Reverse when opposite crossover occurs
- **Best in:** Trending markets
- **Risk:** Whipsaws in choppy markets

### Momentum
**Logic:** Buy strength, sell weakness based on price momentum and RSI.

- **Entry:** Go LONG when momentum is positive and RSI not overbought
- **Exit:** Close when momentum reverses or RSI hits extremes
- **Best in:** Strong trending markets
- **Risk:** Can buy tops and sell bottoms in reversals

---

## Simulation Flow

```
1. Admin creates round (status: PENDING)
2. Students join and configure agents
3. Admin starts simulation (status: RUNNING)
   ├── Ghost benchmark agent added automatically
   ├── Price series generated (deterministic from seed)
   ├── For each tick:
   │   ├── Calculate indicators for all agents
   │   ├── Generate signals from each strategy
   │   ├── Execute trades (with slippage & fees)
   │   ├── Update positions and equity
   │   └── Check risk limits (stop-loss, max DD kill)
   └── Calculate final metrics for all agents
4. Results saved (status: COMPLETED)
5. Leaderboard available
```

---

## Frontend Integration Example

### Supabase Auth Setup

```typescript
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

// Sign up with custom metadata
await supabase.auth.signUp({
  email: 'student@example.com',
  password: 'password123',
  options: {
    data: {
      nickname: 'TraderJoe',
      color: '#3B82F6',
      icon: 'chart'
    }
  }
})

// Get session token
const { data: { session } } = await supabase.auth.getSession()
const token = session?.access_token
```

### API Client

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL

async function apiCall(endpoint: string, options: RequestInit = {}) {
  const { data: { session } } = await supabase.auth.getSession()
  
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${session?.access_token}`,
      ...options.headers,
    },
  })
  
  if (!response.ok) {
    throw new Error(await response.text())
  }
  
  return response.json()
}

// Examples
const user = await apiCall('/api/auth/me')
const rounds = await apiCall('/api/rounds/')
const leaderboard = await apiCall(`/api/rounds/${roundId}/leaderboard`)
```

### Polling for Round Status

```typescript
async function pollRoundStatus(roundId: string) {
  while (true) {
    const status = await apiCall(`/api/rounds/${roundId}/status`)
    
    if (status.status === 'COMPLETED') {
      return status
    }
    
    if (status.status === 'PENDING') {
      // Round hasn't started yet
      await new Promise(r => setTimeout(r, 2000))
      continue
    }
    
    // RUNNING - poll more frequently
    await new Promise(r => setTimeout(r, 500))
  }
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message here"
}
```

### Common Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad Request (validation error, invalid state) |
| 401 | Unauthorized (missing/invalid token) |
| 403 | Forbidden (not admin for admin-only endpoints) |
| 404 | Not Found |
| 500 | Internal Server Error |

---

## Environment Variables (Backend)

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_PUBLISHABLE_KEY` | Supabase publishable key |
| `SUPABASE_JWT_SECRET` | Supabase JWT secret for token verification |
| `ADMIN_EMAILS` | JSON array of admin email addresses |
| `CORS_ORIGINS` | JSON array of allowed frontend origins |
