from datetime import date
from typing import List
from pydantic import BaseModel, Field, field_validator

class EurojackpotDraw(BaseModel):
    draw_date: date
    mains: List[int] = Field(..., min_length=5, max_length=5)
    euros: List[int] = Field(..., min_length=2, max_length=2)
    source: str = "multipasko"

    @field_validator("mains")
    def check_mains(cls, v):
        if any(not (1 <= n <= 50) for n in v) or len(set(v)) != 5:
            raise ValueError("Mains non validi")
        return sorted(v)

    @field_validator("euros")
    def check_euros(cls, v):
        if any(not (1 <= n <= 12) for n in v) or len(set(v)) != 2:
            raise ValueError("Euros non validi")
        return sorted(v)

class SuperenalottoDraw(BaseModel):
    draw_date: date
    mains: List[int] = Field(..., min_length=6, max_length=6)
    source: str = "lottologia"

    @field_validator("mains")
    def check_mains(cls, v):
        if any(not (1 <= n <= 90) for n in v) or len(set(v)) != 6:
            raise ValueError("Mains non validi")
        return sorted(v)

class VinciDraw(BaseModel):
    draw_date: date
    mains: List[int] = Field(..., min_length=8, max_length=8)
    source: str = "agimeg"

    @field_validator("mains")
    def check_mains(cls, v):
        if any(not (1 <= n <= 90) for n in v) or len(set(v)) != 8:
            raise ValueError("Mains non validi")
        return sorted(v)
