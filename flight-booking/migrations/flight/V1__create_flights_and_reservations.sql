CREATE TYPE flight_status AS ENUM (
    'SCHEDULED',
    'DEPARTED',
    'CANCELLED',
    'COMPLETED'
);
CREATE TYPE reservation_status AS ENUM (
    'ACTIVE',
    'RELEASED',
    'EXPIRED'
);
CREATE TABLE flights (
    id UUID PRIMARY KEY,
    airline VARCHAR(100) NOT NULL,
    flight_number VARCHAR(20) NOT NULL,
    departure_airport CHAR(3) NOT NULL,
    arrival_airport CHAR(3) NOT NULL,
    departure_time TIMESTAMPTZ NOT NULL,
    arrival_time TIMESTAMPTZ NOT NULL,
    departure_date DATE GENERATED ALWAYS AS ((departure_time AT TIME ZONE 'UTC')::date) STORED,
    total_seats INT NOT NULL CHECK (total_seats > 0),
    available_seats INT NOT NULL CHECK (available_seats >= 0),
    price NUMERIC(10,2) NOT NULL CHECK (price > 0),
    status flight_status NOT NULL DEFAULT 'SCHEDULED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT ck_flight_airports_different CHECK (departure_airport <> arrival_airport),
    CONSTRAINT ck_available_le_total CHECK (available_seats <= total_seats),
    CONSTRAINT ck_arrival_after_departure CHECK (arrival_time > departure_time),
    CONSTRAINT uq_flight_number_departure_date UNIQUE (flight_number, departure_date)
);
CREATE TABLE seat_reservations (
    id UUID PRIMARY KEY,
    flight_id UUID NOT NULL REFERENCES flights(id) ON DELETE CASCADE,
    booking_id UUID NOT NULL UNIQUE,
    seat_count INT NOT NULL CHECK (seat_count > 0),
    status reservation_status NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_flights_route_time
    ON flights(departure_airport, arrival_airport, departure_time);
CREATE INDEX idx_seat_reservations_flight_id
    ON seat_reservations(flight_id);
