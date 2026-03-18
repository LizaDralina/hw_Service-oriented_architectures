INSERT INTO flights (
    id,
    airline,
    flight_number,
    departure_airport,
    arrival_airport,
    departure_time,
    arrival_time,
    total_seats,
    available_seats,
    price,
    status
)VALUES
(
    '11111111-1111-1111-1111-111111111111',
    'Aeroflot',
    'SU100',
    'SVO',
    'LED',
    '2026-04-01 07:00:00+00',
    '2026-04-01 08:30:00+00',
    100,
    100,
    5500.00,
    'SCHEDULED'
),
(
    '22222222-2222-2222-2222-222222222222',
    'Pobeda',
    'DP200',
    'VKO',
    'KZN',
    '2026-04-01 12:00:00+00',
    '2026-04-01 13:40:00+00',
    80,
    80,
    4200.00,
    'SCHEDULED'
);
