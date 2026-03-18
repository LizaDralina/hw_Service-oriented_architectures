import os
import grpc

import flight_service_pb2 as pb2
import flight_service_pb2_grpc as pb2_grpc


class FlightGrpcClient:
    def __init__(self):
        target = os.getenv("FLIGHT_GRPC_TARGET", "flight_service:50051")
        self.channel = grpc.insecure_channel(target)
        self.stub = pb2_grpc.FlightServiceStub(self.channel)

    def get_flight(self, flight_id: str):
        return self.stub.GetFlight(pb2.GetFlightRequest(flight_id=flight_id))

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


_client = None


def get_flight_client() -> FlightGrpcClient:
    global _client
    if _client is None:
        _client = FlightGrpcClient()
    return _client