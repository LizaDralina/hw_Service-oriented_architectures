import os
import uuid
from concurrent import futures
from datetime import timezone

import grpc
from google.protobuf.timestamp_pb2 import Timestamp
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

import flight_service_pb2 as pb2
import flight_service_pb2_grpc as pb2_grpc

from app.db import SessionLocal
from app.models import Flight, SeatReservation, FlightStatus, ReservationStatus


def to_timestamp(dt):
    ts = Timestamp()
    ts.FromDatetime(dt.astimezone(timezone.utc))
    return ts


def parse_uuid_or_abort(value: str, field_name: str, context) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        context.abort(grpc.StatusCode.INVALID_ARGUMENT, f"{field_name} must be a valid UUID")


def flight_status_to_proto(status: FlightStatus):
    mapping = {
        FlightStatus.SCHEDULED: pb2.SCHEDULED,
        FlightStatus.DEPARTED: pb2.DEPARTED,
        FlightStatus.CANCELLED: pb2.CANCELLED,
        FlightStatus.COMPLETED: pb2.COMPLETED,
    }
    return mapping[status]


def reservation_status_to_proto(status: ReservationStatus):
    mapping = {
        ReservationStatus.ACTIVE: pb2.ACTIVE,
        ReservationStatus.RELEASED: pb2.RELEASED,
        ReservationStatus.EXPIRED: pb2.EXPIRED,
    }
    return mapping[status]


def serialize_flight(flight: Flight):
    return pb2.Flight(
        id=str(flight.id),
        airline=flight.airline,
        flight_number=flight.flight_number,
        departure_airport=flight.departure_airport.strip(),
        arrival_airport=flight.arrival_airport.strip(),
        departure_time=to_timestamp(flight.departure_time),
        arrival_time=to_timestamp(flight.arrival_time),
        total_seats=flight.total_seats,
        available_seats=flight.available_seats,
        price=float(flight.price),
        status=flight_status_to_proto(flight.status),
    )


def serialize_reservation(reservation: SeatReservation):
    return pb2.SeatReservation(
        id=str(reservation.id),
        flight_id=str(reservation.flight_id),
        booking_id=str(reservation.booking_id),
        seat_count=reservation.seat_count,
        status=reservation_status_to_proto(reservation.status),
        created_at=to_timestamp(reservation.created_at),
    )


class FlightService(pb2_grpc.FlightServiceServicer):
    def SearchFlights(self, request, context):
        departure_airport = request.departure_airport.upper()
        arrival_airport = request.arrival_airport.upper()
        date_from = request.departure_date_from.ToDatetime(tzinfo=timezone.utc)
        date_to = request.departure_date_to.ToDatetime(tzinfo=timezone.utc)

        with SessionLocal() as session:
            stmt = (
                select(Flight)
                .where(Flight.departure_airport == departure_airport)
                .where(Flight.arrival_airport == arrival_airport)
                .where(Flight.status == FlightStatus.SCHEDULED)
                .where(Flight.departure_time >= date_from)
                .where(Flight.departure_time <= date_to)
                .order_by(Flight.departure_time.asc())
            )
           
            flights = session.execute(stmt).scalars().all()

            return pb2.SearchFlightsResponse(
                flights=[serialize_flight(f) for f in flights]
            )

    def GetFlight(self, request, context):
        flight_id = parse_uuid_or_abort(request.flight_id, "flight_id", context)

        with SessionLocal() as session:
            flight = session.get(Flight, flight_id)
            if not flight:
                context.abort(grpc.StatusCode.NOT_FOUND, "Flight not found")

            return pb2.GetFlightResponse(flight=serialize_flight(flight))

    def ReserveSeats(self, request, context):
        if request.seat_count <= 0:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "seat_count must be positive")

        flight_id = parse_uuid_or_abort(request.flight_id, "flight_id", context)
        booking_id = parse_uuid_or_abort(request.booking_id, "booking_id", context)

        with SessionLocal() as session:
            try:
                with session.begin():
                    existing = session.execute(
                        select(SeatReservation).where(SeatReservation.booking_id == booking_id)
                    ).scalar_one_or_none()

                    if existing:
                        context.abort(grpc.StatusCode.ALREADY_EXISTS, "Reservation already exists")

                    flight = session.execute(
                        select(Flight)
                        .where(Flight.id == flight_id)
                        .with_for_update()
                    ).scalar_one_or_none()

                    if not flight:
                        context.abort(grpc.StatusCode.NOT_FOUND, "Flight not found")

                    if flight.status != FlightStatus.SCHEDULED:
                        context.abort(grpc.StatusCode.FAILED_PRECONDITION, "Flight is not available for reservation")

                    if flight.available_seats < request.seat_count:
                        context.abort(grpc.StatusCode.RESOURCE_EXHAUSTED, "Not enough seats")

                    flight.available_seats -= request.seat_count

                    reservation = SeatReservation(
                        id=uuid.uuid4(),
                        flight_id=flight.id,
                        booking_id=booking_id,
                        seat_count=request.seat_count,
                        status=ReservationStatus.ACTIVE,
                    )
                    session.add(reservation)
                    session.flush()

                    response = pb2.ReserveSeatsResponse(
                        reservation=serialize_reservation(reservation),
                        flight=serialize_flight(flight),
                    )

                return response

            except IntegrityError:
                session.rollback()
                context.abort(grpc.StatusCode.ALREADY_EXISTS, "Reservation already exists")

    def ReleaseReservation(self, request, context):
        booking_id = parse_uuid_or_abort(request.booking_id, "booking_id", context)

        with SessionLocal() as session:
            with session.begin():
                reservation = session.execute(
                    select(SeatReservation)
                    .where(SeatReservation.booking_id == booking_id)
                    .with_for_update()
                ).scalar_one_or_none()

                if not reservation:
                    context.abort(grpc.StatusCode.NOT_FOUND, "Reservation not found")

                if reservation.status != ReservationStatus.ACTIVE:
                    context.abort(grpc.StatusCode.FAILED_PRECONDITION, "Reservation is not active")

                flight = session.execute(
                    select(Flight)
                    .where(Flight.id == reservation.flight_id)
                    .with_for_update()
                ).scalar_one_or_none()

                if not flight:
                    context.abort(grpc.StatusCode.NOT_FOUND, "Flight not found")

                flight.available_seats += reservation.seat_count
                reservation.status = ReservationStatus.RELEASED
                session.flush()

                response = pb2.ReleaseReservationResponse(
                    reservation=serialize_reservation(reservation),
                    flight=serialize_flight(flight),
                )

            return response


def serve():
    port = os.getenv("GRPC_PORT", "50051")
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    pb2_grpc.add_FlightServiceServicer_to_server(FlightService(), server)
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    print(f"Flight Service started on port {port}")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()

