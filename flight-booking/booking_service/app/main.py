import grpc
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import FastAPI, Depends, HTTPException, status, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy import select

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

    return HTTPException(status_code=mapping.get(code, 500), detail=detail)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/flights")
def search_flights(
    origin: str = Query(...),
    destination: str = Query(...),
    date: str | None = Query(None)
):
    flight_client = get_flight_client()

    try:
        response = flight_client.search_flights(origin, destination, date)
        return [
            {
                "id": f.id,
                "airline": f.airline,
                "flight_number": f.flight_number,
                "departure_airport": f.departure_airport,
                "arrival_airport": f.arrival_airport,
                "departure_time": f.departure_time.ToJsonString(),
                "arrival_time": f.arrival_time.ToJsonString(),
                "total_seats": f.total_seats,
                "available_seats": f.available_seats,
                "price": f.price,
                "status": f.status,
            }
            for f in response.flights
        ]
    except grpc.RpcError as e:
        raise grpc_to_http(e)


@app.get("/flights/{flight_id}")
def get_flight(flight_id: UUID):
    flight_client = get_flight_client()

    try:
        response = flight_client.get_flight(str(flight_id))
        f = response.flight
        return {
            "id": f.id,
            "airline": f.airline,
            "flight_number": f.flight_number,
            "departure_airport": f.departure_airport,
            "arrival_airport": f.arrival_airport,
            "departure_time": f.departure_time.ToJsonString(),
            "arrival_time": f.arrival_time.ToJsonString(),
            "total_seats": f.total_seats,
            "available_seats": f.available_seats,
            "price": f.price,
            "status": f.status,
        }
    except grpc.RpcError as e:
        raise grpc_to_http(e)


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
            user_id=payload.user_id,
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


@app.get("/bookings/{booking_id}", response_model=BookingResponse)
def get_booking(booking_id: UUID, db: Session = Depends(get_db)):
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@app.get("/bookings", response_model=list[BookingResponse])
def list_bookings(user_id: UUID, db: Session = Depends(get_db)):
    stmt = select(Booking).where(Booking.user_id == user_id)
    bookings = db.execute(stmt).scalars().all()
    return bookings


@app.post("/bookings/{booking_id}/cancel", response_model=BookingResponse)
def cancel_booking(booking_id: UUID, db: Session = Depends(get_db)):
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.status != BookingStatus.CONFIRMED:
        raise HTTPException(status_code=409, detail="Booking is not in CONFIRMED status")

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
    



