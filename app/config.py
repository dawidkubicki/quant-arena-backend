from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://localhost:5432/quant_arena"
    
    # Supabase Authentication
    # JWT verification uses JWKS (public keys) fetched from {supabase_url}/auth/v1/.well-known/jwks.json
    # No JWT secret needed - the backend fetches the public key automatically
    supabase_url: str = ""  # e.g. https://your-project.supabase.co
    supabase_publishable_key: str = ""  # New: sb_publishable_... (safe for browser)
    
    # Admin email (Supabase user email that has admin privileges)
    admin_emails: list[str] = []
    
    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]
    
    # Simulation defaults
    default_initial_equity: float = 100000.0
    default_num_ticks: int = 1000
    default_initial_price: float = 100.0
    
    # Twelve Data API
    twelvedata_api_key: str = ""
    twelvedata_base_url: str = "https://api.twelvedata.com"
    
    # Market Data Settings
    market_data_symbols: list[str] = ["AAPL", "SPY"]
    market_data_interval: str = "1min"
    market_data_trading_interval: str = "5min"
    
    class Config:
        env_file = ".env"
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
