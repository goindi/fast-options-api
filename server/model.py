from typing import Optional
from pydantic import BaseModel

class RangeSchema(BaseModel):
  ivol: float
  price: float
  desc: Optional[str]
  low_range: float
  high_range:float
  symbol: str

  class Config:
    schema_extra = {
        "example": {
            "symbol": "IBM",
            "desc": "Internation Business Machine",
            "ivol":0.24,
            "price": 123,
            "low_range":103,
            "high_range":144
        }
    }
