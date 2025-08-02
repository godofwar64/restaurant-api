from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date, time

class ReservationBase(BaseModel):
    table_number: int
    date: date
    time: time
    party_size: int
    special_requests: Optional[str] = None

class ReservationCreate(ReservationBase):
    pass

class ReservationUpdate(BaseModel):
    table_number: Optional[int] = None
    date: Optional[date] = None
    time: Optional[time] = None
    party_size: Optional[int] = None
    status: Optional[str] = None
    special_requests: Optional[str] = None

class Reservation(ReservationBase):
    id: str
    user_id: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ReservationStatus(BaseModel):
    status: str

class TableAvailability(BaseModel):
    table_number: int
    is_available: bool
    reservation_time: Optional[datetime] = None
