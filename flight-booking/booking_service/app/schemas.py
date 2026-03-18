from uuid import UUID
from decimal import Decimal
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class CreateBookingRequest(BaseModel):
    passenger_name: str = Field(..., min_length=1, max_length=255)
    passenger_email: EmailStr
    flight_id: UUID
    seat_count: int = Field(..., gt=0)


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: UUID
    passenger_name: str
    passenger_email: EmailStr
    flight_id: UUID
    seat_count: int
    total_price: Decimal
    status: str