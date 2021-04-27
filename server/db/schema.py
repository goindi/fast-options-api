from typing import List, Optional

from pydantic import BaseModel

class UserRatingBase(BaseModel):
    user_email: str
    symbol:str
    ratings: int

class UserRating(UserRatingBase):
    id: int
    owner_id: int

    class Config:
        orm_mode = True
