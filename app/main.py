from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.api import auth, users, rounds, agents, leaderboard, market_data

settings = get_settings()

app = FastAPI(
    title="Quant Arena API",
    description="Educational trading simulation platform",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(rounds.router, prefix="/api/rounds", tags=["Rounds"])
app.include_router(agents.router, prefix="/api/rounds", tags=["Agents"])
app.include_router(leaderboard.router, prefix="/api/rounds", tags=["Leaderboard"])
app.include_router(market_data.router, prefix="/api/market-data", tags=["Market Data"])


@app.get("/")
def root():
    return {"message": "Welcome to Quant Arena API"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
