import grpc
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Booking, BookingStatus
from app.schemas import CreateBookingRequest, BookingResponse
from app.grpc_client import get_flight_client

app = FastAPI(title="Booking Service")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def grpc_to_http(exc: grpc.RpcError) -> HTTPException:
    code = exc.code()
    detail = exc.details() or "gRPC error"

    mapping = {
        grpc.StatusCode.NOT_FOUND: 404,
        grpc.StatusCode.INVALID_ARGUMENT: 400,
        grpc.StatusCode.RESOURCE_EXHAUSTED: 409,
        grpc.StatusCode.FAILED_PRECONDITION: 409,
        grpc.StatusCode.ALREADY_EXISTS: 409,
        grpc.StatusCode.UNAVAILABLE: 503,
        grpc.StatusCode.INTERNAL: 500,
    }

    return HTTPException(
        status_code=mapping.get(code, 500),
        detail=detail
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/bookings", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(payload: CreateBookingRequest, db: Session = Depends(get_db)):
    flight_client = get_flight_client()
    booking_id = uuid4()
    reservation_done = False

    try:
        flight_response = flight_client.get_flight(str(payload.flight_id))
        flight = flight_response.flight

        flight_client.reserve_seats(
            flight_id=str(payload.flight_id),
            booking_id=str(booking_id),
            seat_count=payload.seat_count
        )
        reservation_done = True

        total_price = Decimal(str(flight.price)) * payload.seat_count

        booking = Booking(
            id=booking_id,
            passenger_name=payload.passenger_name,
            passenger_email=payload.passenger_email,
            flight_id=payload.flight_id,
            seat_count=payload.seat_count,
            total_price=total_price,
            status=BookingStatus.CONFIRMED,
        )

        db.add(booking)
        db.commit()
        db.refresh(booking)

        return booking

    except grpc.RpcError as e:
        db.rollback()
        raise grpc_to_http(e)

    except SQLAlchemyError:
        db.rollback()

        if reservation_done:
            try:
                flight_client.release_reservation(str(booking_id))
            except Exception:
                pass

        raise HTTPException(status_code=500, detail="Failed to save booking")

    except Exception:
        db.rollback()

        if reservation_done:
            try:
                flight_client.release_reservation(str(booking_id))
            except Exception:
                pass

        raise HTTPException(status_code=500, detail="Unexpected error")


@app.get("/bookings/{booking_id}", response_model=BookingResponse)
def get_booking(booking_id: UUID, db: Session = Depends(get_db)):
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@app.post("/bookings/{booking_id}/cancel", response_model=BookingResponse)
def cancel_booking(booking_id: UUID, db: Session = Depends(get_db)):
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.status == BookingStatus.CANCELLED:
        return booking

    flight_client = get_flight_client()

    try:
        flight_client.release_reservation(str(booking_id))
    except grpc.RpcError as e:
        raise grpc_to_http(e)

    try:
        booking.status = BookingStatus.CANCELLED
        db.commit()
        db.refresh(booking)
        return booking
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to cancel booking")