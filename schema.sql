-- AgentNet Database Schema
-- Run this in your Supabase SQL Editor

-- 1. Parking Slots Table (The Inventory)
CREATE TABLE IF NOT EXISTS parking_slots (
    id SERIAL PRIMARY KEY,
    slot_number VARCHAR(10) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'FREE', -- FREE, OCCUPIED, RESERVED, MAINTENANCE
    size_type VARCHAR(10) DEFAULT 'Medium', -- Small, Medium, Large
    zone VARCHAR(10) DEFAULT 'P-NORTH',
    current_vehicle VARCHAR(20), -- License Plate
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- 2. Active Sessions (Real-time tracking)
CREATE TABLE IF NOT EXISTS active_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    license_plate VARCHAR(20) NOT NULL,
    slot_id INT REFERENCES parking_slots(id),
    vehicle_type VARCHAR(10),
    entry_time TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    is_active BOOLEAN DEFAULT TRUE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- 3. Transactions (Historical Logs)
CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    license_plate VARCHAR(20) NOT NULL,
    slot_id INT,
    action_type VARCHAR(10), -- ENTRY, EXIT
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    metadata JSONB -- SRE and Vision confidence data
);

-- 4. Initial Seed Data (Optional - Change to your layout)
INSERT INTO parking_slots (slot_number, size_type, zone) VALUES
('P1-01', 'Small', 'P-NORTH'),
('P1-02', 'Medium', 'P-NORTH'),
('P1-03', 'Large', 'P-NORTH'),
('P1-04', 'Medium', 'P-NORTH'),
('P1-05', 'Medium', 'P-SOUTH'),
('P1-06', 'Large', 'P-SOUTH');
