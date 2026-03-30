from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime


class Stock(BaseModel):
    symbol: str = Field(..., description="Stock symbol, e.g., TCS")
    name: Optional[str] = Field(None, description="Full company name")
    sector: Optional[str] = Field(None, description="Industry sector")
    market_cap: Optional[float] = Field(None, description="Market capitalization")
    price: Optional[float] = Field(None, description="Current stock price")
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    metadata: Dict = Field(default_factory=dict, description="Additional scraped attributes")

    class Config:
        orm_mode = True
