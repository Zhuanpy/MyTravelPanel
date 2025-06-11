-- Rename price fields in flight_orders table
ALTER TABLE flight_orders 
    CHANGE COLUMN total_price selling_price DECIMAL(10,2),
    CHANGE COLUMN tax_fee cost_price DECIMAL(10,2);

-- Rename price fields in passengers table
ALTER TABLE passengers
    CHANGE COLUMN ticket_price selling_price DECIMAL(10,2),
    CHANGE COLUMN tax cost_price DECIMAL(10,2); 