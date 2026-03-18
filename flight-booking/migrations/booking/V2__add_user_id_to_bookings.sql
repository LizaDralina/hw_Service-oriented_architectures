ALTER TABLE bookings
ADD COLUMN user_id UUID NOT NULL;

CREATE INDEX idx_bookings_user_id ON bookings(user_id); 