# Online Auction System — Distributed Computing Mini-Project

An editorial-grade **Online Auction System** built with **Python gRPC, Protocol Buffers, SQLite3, FastAPI, and Vanilla JavaScript**.

This repository implements user access and the auction marketplace (Member 1),
the bidding and auction-management engine (Member 2), and auction event streaming
and lifecycle processing (Member 3).

---

## 1. Architecture Overview

The system strictly decouples the browser frontend from the native gRPC backend using a lightweight Python Web Gateway:

```text
Browser Client (HTML5 / CSS3 / Vanilla JS)
       │                        ▲
       │ HTTP Requests          │ Live WebSockets
       ▼                        │
FastAPI Web Gateway (Port 8000)
       │
       │ Native gRPC Unary Calls (Port 50051)
       ▼
Python gRPC Server
 ├── UserService (Demo login, Role retrieval)
 └── AuctionService (Catalog, Bids, Auction Lifecycle, Bidirectional Events)
       │
       │ Parameterized SQLite Queries (WAL Mode)
       ▼
Shared SQLite Database (database/auction.db)
 ├── users (Eleanor, Marcus, Sophia, Julian, Arthur)
 ├── auctions (Curated museum-grade artworks & antiques)
 └── bids (Shared integration table for Member 2)
```

---

## 2. Technology Stack

- **Frontend:** HTML5, CSS3, and vanilla JavaScript (zero frontend build steps or heavy node frameworks required).
- **Backend:** Python 3 (3.10+ / 3.14 compatible) with `grpcio` and `grpcio-tools`.
- **API Contract:** Protocol Buffers (`proto/auction_service.proto`).
- **Database:** SQLite using Python's built-in `sqlite3` module with Write-Ahead Logging (`WAL`) enabled.
- **Web Gateway:** FastAPI & Uvicorn acting as an HTTP and WebSocket proxy to native gRPC stubs.
- **Testing:** `pytest`, `fastapi.testclient`, and `httpx`.
- **Dependencies:** Managed via Python virtual environment (`.venv`) and `requirements.txt`.

All technologies are free, open-source, and runnable without paid licenses or external cloud services.

---

## 3. Repository Structure

```text
dc-miniproject/
├── backend/
│   ├── grpc_server/
│   │   ├── generated/                 # Compiled gRPC stubs (_pb2.py, _pb2_grpc.py)
│   │   ├── repositories/              # Parameterized SQL queries
│   │   │   ├── user_repository.py
│   │   │   └── auction_query_repository.py
│   │   ├── services/                  # gRPC Service implementations
│   │   │   ├── user_service.py
│   │   │   └── auction_query_service.py
│   │   └── server.py                  # Native gRPC server entry point (:50051)
│   └── web_gateway/
│       ├── routers/
│       │   ├── auth.py                # HTTP auth endpoints -> gRPC client
│       │   └── auctions.py            # HTTP auction endpoints -> gRPC client
│       ├── grpc_client.py             # Reusable gRPC channel & stub wrapper
│       └── app.py                     # FastAPI application & WebSocket hub (:8000)
├── frontend/
│   ├── pages/
│   │   ├── login.html                 # Page A: Login & Role Selection
│   │   ├── marketplace.html           # Page B: Curated Auction Marketplace
│   │   └── auction-details.html       # Page C: Lot Details & Bidding Integration
│   ├── css/
│   │   ├── theme.css                  # Design tokens, typography & resets
│   │   └── marketplace.css            # Responsive layout & editorial styling
│   ├── js/
│   │   ├── api.js                     # Gateway API client & utility helpers
│   │   ├── auth.js                    # User session manager & role-aware nav
│   │   ├── marketplace.js             # Catalog loader, search, & countdown ticker
│   │   └── auction-details.js         # Lot viewer & Member 2 integration hooks
│   └── assets/
│       └── images/                    # Local SVG artwork catalog assets
├── proto/
│   └── auction_service.proto          # Shared Protocol Buffers interface contract
├── database/
│   ├── schema.sql                     # Shared SQLite schema (users, auctions, bids)
│   ├── db.py                          # Connection manager & SQLite pragma setup
│   └── seed_data.py                   # Demo accounts & realistic lot catalog
├── tests/
│   ├── unit/                          # Service & repository unit tests
│   ├── integration/                   # Full HTTP -> Gateway -> gRPC -> DB tests
│   └── concurrency/                   # Multi-threaded concurrent query tests
├── scripts/
│   ├── generate_proto.py              # Protobuf compilation script
│   ├── init_db.py                     # Database initialization & asset generation
│   ├── run_server.py                  # Launches native gRPC server
│   └── run_gateway.py                 # Launches FastAPI web gateway
├── docs/                              # Architecture documentation & diagrams
├── .gitignore                         # Comprehensive ignore rules
├── .env.example                       # Example configuration variables
├── pytest.ini                         # Test runner configuration
├── requirements.txt                   # Pinned dependency definitions
├── PROJECT_CONTEXT.md                 # Living team handover & status document
├── CONTRIBUTING.md                    # Git & collaboration guidelines
└── README.md                          # Main project guide
```

---

## 4. Quick Start Guide

### Prerequisites
- Python 3.10, 3.11, 3.12, 3.13, or 3.14 installed on your machine.
- Git.

### Step 1: Clone Repository & Create Virtual Environment
```bash
cd dc-miniproject
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 2: Initialize Database and Artwork Assets
Run the initialization utility to generate the local artwork vectors and seed the SQLite database with authentic lots and demo accounts:
```bash
python3 scripts/init_db.py
```
*(This creates `database/auction.db` and generates 8 vector artworks in `frontend/assets/images/`)*

### Step 3: Compile Protocol Buffers (Optional / Verified)
The compiled Python stubs are checked into `backend/grpc_server/generated/`. To re-generate them at any time:
```bash
python3 scripts/generate_proto.py
```

### Step 4: Start the Services

Open two terminal windows (or tabs) with the virtual environment activated:

**Terminal 1 — Native gRPC Server:**
```bash
source .venv/bin/activate
python3 scripts/run_server.py
```
*Output: Listening on `0.0.0.0:50051`, hosting `UserService` and `AuctionService`.*

**Terminal 2 — FastAPI Web Gateway:**
```bash
source .venv/bin/activate
python3 scripts/run_gateway.py
```
*Output: Gateway listening at `http://127.0.0.1:8000`.*

---

## 5. Accessing the Application

Open your browser to:
```
http://127.0.0.1:8000/marketplace
```
or to sign in:
```
http://127.0.0.1:8000/login
```

### Pre-configured Demo Accounts

Click any one-click demo button on the login screen or enter the username manually:

| Username | Role | Display Name | Profile Bio |
| :--- | :--- | :--- | :--- |
| `buyer_eleanor` | `BUYER` | Eleanor Vance | Barbizon & 19th Century French painting collector |
| `buyer_marcus` | `BUYER` | Marcus Sterling | Classical bronze & antiquity investor |
| `collector_sophia` | `BUYER` | Sophia Loren | Vintage horology & avant-garde art collector |
| `art_lover` | `BUYER` | Julian Croft | Contemporary ceramics enthusiast |
| `admin_arthur` | `ADMIN` | Arthur Pendelton (Curator) | Chief Auctioneer & Gallery Administrator |

---

## 6. Testing

The automated test suite covers unit logic, repositories, gRPC services, distributed integration, concurrency, live-stream routing, and auction lifecycle recovery:

```bash
source .venv/bin/activate
pytest -v
```

### Test Coverage Highlights
1. **Known Demo User Login:** Verifies exact user profile and role retrieval from database.
2. **Unknown Account Rejection:** Validates `NOT_FOUND` / invalid credentials handling.
3. **Role Enforcement:** Confirms `ADMIN` vs `BUYER` roles returned accurately.
4. **Catalog Retrieval via gRPC:** Validates `ListAuctions` RPC payload mapping.
5. **Category & Status Filtering:** Tests filtering by `Paintings`, `Sculptures`, `ACTIVE`, `UPCOMING`, `CLOSED`.
6. **Lot Lookup by ID:** Validates `GetAuction` RPC details and next minimum bid formula.
7. **Unknown Lot Lookup:** Validates gRPC `NOT_FOUND` error code propagation.
8. **Empty Search Handling:** Gracefully handles queries with no matching artworks.
9. **Concurrency & Thread Safety:** Validates 30+ concurrent reader threads against SQLite in WAL mode.
10. **Full Distributed Integration:** Uses `fastapi.testclient` to execute HTTP -> Gateway -> gRPC Server -> SQLite Database round-trips.

---

## 7. Team Integration Guide (Members 2 & 3)

### Member 2: Bidding Engine & Auction Creation
- **Proto RPCs:** Implement `PlaceBid` and `CreateAuction` in `backend/grpc_server/services/`.
- **Database:** Write to the `bids` table in `database/schema.sql` and update `auctions.highest_bid` and `auctions.highest_bidder_id`.
- **Frontend Mount Point:** Mount your interactive bidding form in `frontend/pages/auction-details.html` inside `#member2-bidding-container`.
- **Context API:** Listen for `auction:lot-loaded` or inspect `window.AuctionDetailsContext`.

### Member 3: Live Bid Streaming & Push Notifications
- **Proto RPC:** `AuctionService.AuctionStream` is a bidirectional gRPC subscription stream.
- **WebSocket Gateway:** `/ws/live` bridges each browser's auction subscription to the gRPC stream.
- **Frontend Live Hub:** Auction details refresh from the REST API after bid, status, or closure events and on reconnect.
- **Lifecycle:** The gRPC server activates scheduled auctions, closes expired auctions, and recovers due auctions at startup.

---

## 8. Troubleshooting

- **gRPC Connection Refused:** Ensure `scripts/run_server.py` is started before browsing `http://127.0.0.1:8000`. The gateway will display a clear error message with a "Retry Connection" button if the server is offline.
- **Port Conflict:** Set `GRPC_SERVER_PORT=50052` or `WEB_GATEWAY_PORT=8080` in your environment or `.env` file.
- **Database Reset:** To wipe and re-seed the catalog at any time, run `python3 scripts/init_db.py`.

## Member 2 Features Added

- **Auction Creation**: Sellers can create auctions with item details, starting price, and duration via the `CreateAuction` RPC.
- **Bidding Engine**: Buyers place bids; the system validates amount, bidder permissions, auction state, and deadline, updating the highest bid atomically.
- **Concurrent Bidding Safety**: Uses database transactions and per‑auction locks to prevent race conditions.
- **Auction Closure & Winner Selection**: Auctions close automatically or via authorized request, recording the winner and final price; idempotent handling of repeated closures.
- **UI Integration**: New auction creation modal, bid submission UI, and an activity panel showing request processing, validation results, and database outcomes.

These features integrate with the existing authentication, gRPC services, FastAPI gateway, and frontend UI without affecting other modules.

## Member 2 Features Added

- **Auction Creation**: Sellers can create auctions with item details, starting price, and duration via the `CreateAuction` RPC.
- **Bidding Engine**: Buyers place bids; the system validates amount, bidder permissions, auction state, and deadline, updating the highest bid atomically.
- **Concurrent Bidding Safety**: Uses database transactions and per‑auction locks to prevent race conditions.
- **Auction Closure & Winner Selection**: Auctions close automatically or via authorized request, recording the winner and final price; idempotent handling of repeated closures.
- **UI Integration**: New auction creation modal, bid submission UI, and an activity panel showing request processing, validation results, and database outcomes.

These features integrate with the existing authentication, gRPC services, FastAPI gateway, and frontend UI without affecting other modules.

## Member 3: Live Events and Auction Lifecycle

The native gRPC `AuctionService.AuctionStream` RPC is bidirectional. Browser
auction-detail pages subscribe to an auction through the FastAPI `/ws/live` gateway;
accepted bids and status/closure changes are routed only to clients subscribed to
that auction. The browser refreshes the REST auction query after events and when
reconnecting, so SQLite-backed server state remains authoritative.

The gRPC server also activates scheduled auctions and closes expired auctions from
their stored deadlines, including a recovery sweep on startup. Final status, highest
accepted bid, and winner remain persisted on the existing auction and bid records.
The countdown is a display only and does not close auctions.
