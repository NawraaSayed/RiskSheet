-- Create positions table
CREATE TABLE positions (
  ticker TEXT PRIMARY KEY,
  shares REAL NOT NULL,
  price_bought REAL NOT NULL,
  date_bought TEXT
);

-- Create cash table
CREATE TABLE cash (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  amount REAL NOT NULL
);

-- Create sector_allocations table
CREATE TABLE sector_allocations (
  sector TEXT PRIMARY KEY,
  allocation REAL NOT NULL
);

-- Initialize cash with default value
INSERT INTO cash (id, amount) VALUES (1, 0.0) ON CONFLICT (id) DO NOTHING;
