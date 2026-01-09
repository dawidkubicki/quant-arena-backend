import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, BigInteger, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class MarketDataset(Base):
    """
    Metadata about a fetched market data dataset.
    Tracks when data was fetched and what date range it covers.
    """
    __tablename__ = "market_datasets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(20), nullable=False, index=True)  # AAPL, SPY
    interval = Column(String(10), nullable=False)  # 1min, 5min, etc.
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    total_bars = Column(Integer, nullable=False, default=0)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    bars = relationship("MarketData", back_populates="dataset", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<MarketDataset {self.symbol} {self.interval} ({self.total_bars} bars)>"


class MarketData(Base):
    """
    Individual OHLCV bar data for a symbol.
    Stores 1-minute data that can be resampled to higher timeframes.
    """
    __tablename__ = "market_data"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("market_datasets.id", ondelete="CASCADE"), nullable=False)
    symbol = Column(String(20), nullable=False)
    datetime = Column(DateTime, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(BigInteger, nullable=False)
    
    # Relationships
    dataset = relationship("MarketDataset", back_populates="bars")
    
    # Composite index for efficient querying by symbol and datetime
    __table_args__ = (
        Index('ix_market_data_symbol_datetime', 'symbol', 'datetime'),
    )
    
    def __repr__(self):
        return f"<MarketData {self.symbol} {self.datetime} close={self.close}>"
