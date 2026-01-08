# Quant Arena Backend

Educational trading simulation platform where students compete using different trading strategies.

## Features

- **Supabase Authentication**: Secure JWT-based authentication via Supabase
- **Multiple Trading Strategies**: Mean Reversion, Trend Following, Momentum
- **Realistic Market Simulation**: GBM with regime switching (trending, range-bound, high volatility)
- **Batch Simulation**: Admin starts round, simulation runs all at once
- **Multi-metric Leaderboard**: Sharpe, Calmar, Max DD, Win Rate, Survival Time
- **Ghost Benchmark**: Automatic benchmark agent for comparison

## Architecture

```
Frontend (Next.js)
    ↓ Supabase Auth
    ↓ HTTP/Polling
FastAPI Backend
    ↓
PostgreSQL (Render)
```

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL
- Supabase project (for authentication)

### Supabase Setup

1. Create a new Supabase project at https://supabase.com
2. Go to **Project Settings > API**
3. Copy the following values:
   - **Project URL** → `SUPABASE_URL`
   - **Publishable key** (new format: `sb_publishable_...`) → `SUPABASE_PUBLISHABLE_KEY`
4. For JWT Secret:
   - Go to **Project Settings > API > JWT Settings**
   - Copy **JWT Secret** → `SUPABASE_JWT_SECRET`

### Installation

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
# Database
export DATABASE_URL="postgresql://user:password@localhost:5432/quant_arena"

# Supabase
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_PUBLISHABLE_KEY="sb_publishable_xxxxx"
export SUPABASE_JWT_SECRET="your-jwt-secret-from-jwt-settings"

# Admin emails (JSON array of emails that have admin access)
export ADMIN_EMAILS='["admin@example.com"]'

# CORS (frontend URL)
export CORS_ORIGINS='["http://localhost:3000"]'
```

4. Run database migrations:
```bash
alembic upgrade head
```

5. Start the server:
```bash
uvicorn app.main:app --reload
```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Authentication Flow

1. **Frontend**: User signs up/logs in via Supabase Auth
2. **Frontend**: Gets Supabase access token
3. **Frontend**: Sends token in `Authorization: Bearer <token>` header
4. **Backend**: Validates JWT using Supabase JWT secret
5. **Backend**: Creates/updates user in local database
6. **Backend**: Returns user data and processes requests

### User Metadata

When users sign up in Supabase, you can set custom metadata:
```javascript
await supabase.auth.signUp({
  email: 'user@example.com',
  password: 'password',
  options: {
    data: {
      nickname: 'TraderJoe',
      color: '#3B82F6',
      icon: 'chart'
    }
  }
})
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `SUPABASE_URL` | Supabase project URL (e.g. `https://xxx.supabase.co`) | Yes |
| `SUPABASE_PUBLISHABLE_KEY` | Supabase publishable key (`sb_publishable_...`) | Yes |
| `SUPABASE_JWT_SECRET` | Supabase JWT secret (from JWT Settings) | Yes |
| `ADMIN_EMAILS` | JSON array of admin email addresses | No |
| `CORS_ORIGINS` | JSON array of allowed CORS origins | No |

## Deployment on Render

### Web Service

1. Create a new Web Service
2. Connect your GitHub repository
3. Settings:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables in Render dashboard

### PostgreSQL

1. Create a PostgreSQL database in Render
2. Copy the Internal Database URL
3. Add as `DATABASE_URL` environment variable to the web service

### Environment Variables on Render

```
DATABASE_URL=<from Render PostgreSQL>
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_xxxxx
SUPABASE_JWT_SECRET=your-jwt-secret-from-jwt-settings
ADMIN_EMAILS=["admin@example.com"]
CORS_ORIGINS=["https://your-frontend.onrender.com"]
```

## API Endpoints

### Authentication
- `GET /api/auth/me` - Get current user (validates token, creates user if needed)
- `PUT /api/auth/me` - Update user profile (nickname, color, icon)
- `GET /api/auth/verify` - Verify token validity

### Users
- `GET /api/users/me` - Get current user profile
- `GET /api/users/` - List all users (admin only)
- `GET /api/users/{id}` - Get user by ID

### Rounds
- `POST /api/rounds/` - Create round (admin only)
- `GET /api/rounds/` - List all rounds
- `GET /api/rounds/{id}` - Get round details
- `GET /api/rounds/{id}/status` - Get round status (for polling)
- `POST /api/rounds/{id}/start` - Start simulation (admin only)
- `DELETE /api/rounds/{id}` - Delete round (admin only)

### Agents
- `POST /api/rounds/{round_id}/agents` - Create/update agent
- `GET /api/rounds/{round_id}/agents/me` - Get my agent
- `GET /api/rounds/{round_id}/agents` - List all agents in round
- `GET /api/rounds/{round_id}/agents/{id}` - Get agent details
- `GET /api/rounds/{round_id}/agents/{id}/results` - Get agent results
- `DELETE /api/rounds/{round_id}/agents/me` - Delete my agent

### Leaderboard
- `GET /api/rounds/{round_id}/leaderboard` - Get rankings
- `GET /api/rounds/{round_id}/leaderboard/me` - Get my ranking

## Trading Strategies

### Mean Reversion
Bets on price returning to the moving average when it deviates significantly.
- Parameters: `lookback_window`, `entry_threshold`, `exit_threshold`

### Trend Following
Follows market trends using moving average crossovers.
- Parameters: `fast_window`, `slow_window`, `atr_multiplier`

### Momentum
Buys strength and sells weakness based on price momentum and RSI.
- Parameters: `momentum_window`, `rsi_window`, `rsi_overbought`, `rsi_oversold`

## License

MIT
