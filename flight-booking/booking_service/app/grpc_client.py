import os
from datetime import datetime, timedelta, timezone

import grpc
from google.protobuf.timestamp_pb2 import Timestamp

import flight_service_pb2 as pb2
import flight_service_pb2_grpc as pb2_grpc


class FlightGrpcClient:
    def __init__(self):
        target = os.getenv("FLIGHT_GRPC_TARGET", "flight_service:50051")
        self.channel = grpc.insecure_channel(target)
        self.stub = pb2_grpc.FlightServiceStub(self.channel)

    def get_flight(self, flight_id: str):
        return self.stub.GetFlight(
            pb2.GetFlightRequest(flight_id=flight_id)
        )

    def reserve_seats(self, flight_id: str, booking_id: str, seat_count: int):
        return self.stub.ReserveSeats(
            pb2.ReserveSeatsRequest(
                flight_id=flight_id,
                booking_id=booking_id,
                seat_count=seat_count,
            )
        )

    def release_reservation(self, booking_id: str):
        return self.stub.ReleaseReservation(
            pb2.ReleaseReservationRequest(booking_id=booking_id)
        )

    def search_flights(self, origin: str, destination: str, date: str | None = None):
        if date:
            start = datetime.fromisoformat(date).replace(tzinfo=timezone.utc)
            end = start + timedelta(days=1)
        else:
            start = datetime(1970, 1, 1, tzinfo=timezone.utc)
            end = datetime(2100, 1, 1, tzinfo=timezone.utc)

        ts_from = Timestamp()
        ts_from.FromDatetime(start)

        ts_to = Timestamp()
        ts_to.FromDatetime(end)

        return self.stub.SearchFlights(
            pb2.SearchFlightsRequest(
                departure_airport=origin.upper(),
                arrival_airport=destination.upper(),
                departure_date_from=ts_from,
                departure_date_to=ts_to,
            )
        )


_client = None


def get_flight_client() -> FlightGrpcClient:
    global _client
    if _client is None:
        _client = FlightGrpcClient()
    return _client