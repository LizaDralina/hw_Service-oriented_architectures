CREATE TYPE booking_status AS ENUM (
    'CONFIRMED',
    'CANCELLED'
);
CREATE TABLE bookings (
    id UUID PRIMARY KEY,
    passenger_name VARCHAR(255) NOT NULL,
    passenger_email VARCHAR(255) NOT NULL,
    flight_id UUID NOT NULL,
    seat_count INT NOT NULL CHECK (seat_count > 0),
    total_price NUMERIC(10,2) NOT NULL CHECK (total_price >= 0),
    status booking_status NOT NULL DEFAULT 'CONFIRMED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_bookings_flight_id ON bookings(flight_id);CREATE INDEX idx_bookings_passenger_email ON bookings(passenger_email);
