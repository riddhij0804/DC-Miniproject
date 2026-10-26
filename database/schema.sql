-- Online Auction System - Shared SQLite Schema
-- Coordinated between Member 1 (Marketplace & Auth), Member 2 (Bidding Engine), and Member 3 (Live Streaming)

PRAGMA foreign_keys = ON;

-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('BUYER', 'ADMIN', 'SELLER')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 2. Auctions Table
CREATE TABLE IF NOT EXISTS auctions (
    auction_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('Paintings', 'Sculptures', 'Vintage', 'Collectibles', 'Art')),
    artist_name TEXT NOT NULL,
    image_path TEXT NOT NULL,
    seller_id TEXT NOT NULL,
    starting_price REAL NOT NULL CHECK (starting_price >= 0),
    min_increment REAL NOT NULL DEFAULT 50.0 CHECK (min_increment > 0),
    highest_bid REAL NOT NULL DEFAULT 0.0,
    highest_bidder_id TEXT,
    start_time TEXT NOT NULL, -- ISO 8601 string: YYYY-MM-DDTHH:MM:SSZ
    end_time TEXT NOT NULL,   -- ISO 8601 string: YYYY-MM-DDTHH:MM:SSZ
    status TEXT NOT NULL CHECK (status IN ('UPCOMING', 'ACTIVE', 'CLOSED')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (seller_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (highest_bidder_id) REFERENCES users(user_id) ON DELETE SET NULL
);

-- 3. Bids Table (Shared integration table for Member 2 bidding engine)
CREATE TABLE IF NOT EXISTS bids (
    bid_id TEXT PRIMARY KEY,
    auction_id TEXT NOT NULL,
    bidder_id TEXT NOT NULL,
    bid_amount REAL NOT NULL CHECK (bid_amount > 0),
    timestamp TEXT NOT NULL, -- ISO 8601 string
    FOREIGN KEY (auction_id) REFERENCES auctions(auction_id) ON DELETE CASCADE,
    FOREIGN KEY (bidder_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Indexes for efficient queries and filtering
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_auctions_category ON auctions(category);
CREATE INDEX IF NOT EXISTS idx_auctions_status ON auctions(status);
CREATE INDEX IF NOT EXISTS idx_auctions_end_time ON auctions(end_time);
CREATE INDEX IF NOT EXISTS idx_bids_auction_id ON bids(auction_id);
