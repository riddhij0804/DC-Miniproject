# Online Auction System — Shared Project Context & Team Handover

**Version:** 1.0.0  
**Last Updated:** October 2026  
**Module Owner:** Member 1 (User Access & Auction Marketplace)  
**Cooperating Members:** Member 2 (Bidding Engine & Auction Management), Member 3 (Real-Time Bid Streaming & Notifications)

---

## 1. System Architecture Overview

The **Online Auction System** is an asynchronous, distributed computing platform designed to demonstrate native **gRPC unary and bidirectional streaming communication**, Protocol Buffers interface contracts, and reactive frontend integration without external proprietary dependencies.

```text
┌────────────────────────────────────────────────────────┐
│               Browser Client (HTML5 / CSS3 / JS)       │
│  - Marketplace UI      - Details & Bid View  - Login   │
└───────────────────▲────────────────────┬───────────────┘
                    │ WebSocket          │ HTTP (REST)
                    │ (Live Updates)     │ (Queries & Auth)
┌───────────────────┴────────────────────▼───────────────┐
│               Web Gateway (FastAPI / Uvicorn)          │
│  - Static Asset Server  - JSON / gRPC Marshalling      │
│  - Live WebSocket Hub   - Health & Session Handling    │
└─────────────────────────┬──────────────────────────────┘
                          │ gRPC Unary & Bidirectional Streams
                          │ (Port 50051, protobuf contract)
┌─────────────────────────▼──────────────────────────────┐
│               Native Python gRPC Server                │
│  - UserService (Login, Profile, Role Enforcement)       │
│  - AuctionService (List, Filter, GetLot Details)       │
│  - [Member 2] Bidding Engine (PlaceBid, CreateAuction) │
│  - [Member 3] Event Streaming (StreamAuctionEvents)    │
└─────────────────────────┬──────────────────────────────┘
                          │ Parameterized SQL Queries (WAL mode)
┌─────────────────────────▼──────────────────────────────┐
│           Shared SQLite Database (auction.db)          │
│  - users               - auctions           - bids     │
└────────────────────────────────────────────────────────┘
```

---

## 2. Team Member Responsibilities & Boundaries

| Member | Domain & Ownership | Key Deliverables & Boundary | Status |
| :--- | :--- | :--- | :--- |
| **Member 1** (Current) | **User Access & Auction Marketplace** | - Login & Role Verification (`UserService.Login`)<br>- Auction Catalog & Lot Retrieval (`AuctionService.ListAuctions`, `GetAuction`)<br>- SQLite Database Initializer & Seed Data<br>- Responsive Editorial Frontend (`login.html`, `marketplace.html`, `auction-details.html`)<br>- Web Gateway HTTP REST Endpoints & Proto Compiler script | **Implemented & Tested (30/30 tests passing)** |
| **Member 2** | **Bidding Engine & Auction Creation** | - `AuctionService.PlaceBid` RPC & bid validation<br>- Concurrency control, minimum increment enforcement, outbid logic<br>- `AuctionService.CreateAuction` RPC for sellers/admins<br>- Bidding UI mount point inside `#member2-bidding-container` | **Contract Defined; Integration Hooks Ready** |
| **Member 3** | **Live Streaming & Event Distribution** | - Bidirectional streaming (`StreamAuctionEvents`, `StreamBids`)<br>- Real-time event propagation to browser clients via `/ws/live` gateway hub<br>- Outbid push notifications & auction timer extension broadcasts | **Contract Defined; WebSocket Hub Ready** |

---

## 3. Shared Protocol Buffers Contract (`proto/auction_service.proto`)

### Implemented Services (Member 1)
```protobuf
service UserService {
  rpc Login (LoginRequest) returns (LoginResponse);
  rpc GetUserProfile (UserProfileRequest) returns (UserProfileResponse);
}

service AuctionService {
  rpc ListAuctions (ListAuctionsRequest) returns (ListAuctionsResponse);
  rpc GetAuction (GetAuctionRequest) returns (GetAuctionResponse);
  rpc GetCategories (GetCategoriesRequest) returns (GetCategoriesResponse);
  rpc AuctionStream (stream AuctionStreamRequest) returns (stream AuctionStreamEvent);
}
```

### Auction Management RPCs (Member 2)
```protobuf
rpc PlaceBid (PlaceBidRequest) returns (PlaceBidResponse);
rpc CreateAuction (CreateAuctionRequest) returns (CreateAuctionResponse);
```

---

## 4. Shared Database Schema (`database/schema.sql`)

### Tables
1. **`users`**
   - `user_id` (TEXT PRIMARY KEY)
   - `username` (TEXT UNIQUE NOT NULL)
   - `display_name` (TEXT NOT NULL)
   - `role` (TEXT CHECK IN ('BUYER', 'ADMIN', 'SELLER'))
   - `created_at` (DATETIME)

2. **`auctions`**
   - `auction_id` (TEXT PRIMARY KEY)
   - `title`, `description`, `category`, `artist_name`, `image_path`
   - `seller_id` (FK -> users)
   - `starting_price` (REAL), `min_increment` (REAL), `highest_bid` (REAL)
   - `highest_bidder_id` (FK -> users, NULLABLE)
   - `start_time` (ISO 8601), `end_time` (ISO 8601)
   - `status` (TEXT CHECK IN ('UPCOMING', 'ACTIVE', 'CLOSED'))

3. **`bids`** (Shared for Member 2)
   - `bid_id` (TEXT PRIMARY KEY)
   - `auction_id` (FK -> auctions)
   - `bidder_id` (FK -> users)
   - `bid_amount` (REAL)
   - `timestamp` (ISO 8601)

---

## 5. Frontend Integration Points

### For Member 2 (Bidding Engine UI Mount Point)
On `frontend/pages/auction-details.html`, a dedicated container is established:
```html
<div id="member2-bidding-container" class="member2-integration-container">
  <!-- Member 2 mounts live bid submission form here -->
</div>
```
Whenever an auction lot is loaded, the page exposes the full lot state on the global window object:
```javascript
window.AuctionDetailsContext = {
  auctionId: "auc_001",
  startingPrice: 4500.0,
  currentHighestBid: 6750.0,
  minIncrement: 250.0,
  minNextBid: 7000.0,
  status: "ACTIVE",
  currentUser: { user_id: "...", username: "...", role: "BUYER" },
  onBidSubmit: function(bidData) { ... }
};
```
Member 2 can attach their bid submission handler or bidirectional streaming client directly to this object or dispatch `auction:lot-loaded` events.

### For Member 3 (WebSocket Live Updates)
The Web Gateway exposes:
```
ws://127.0.0.1:8000/ws/live
```
When Member 3 pushes new bid events, the client updates the highest bid and live ticker without page reloads.

---

## 6. Pre-configured Demo Accounts

| Username | Display Name | Role | Focus / Description |
| :--- | :--- | :--- | :--- |
| `buyer_eleanor` | Eleanor Vance | `BUYER` | 19th Century French painting collector |
| `buyer_marcus` | Marcus Sterling | `BUYER` | Classical bronze & antiquity investor |
| `collector_sophia`| Sophia Loren | `BUYER` | Fine horology & avant-garde art collector |
| `art_lover` | Julian Croft | `BUYER` | Contemporary ceramics enthusiast |
| `admin_arthur` | Arthur Pendelton | `ADMIN` | Chief Auctioneer & Gallery Curator |

---

## 7. Setup & Run Instructions

```bash
# 1. Activate Virtual Environment
source .venv/bin/activate

# 2. Initialize Database & Generate Visual Assets
python3 scripts/init_db.py

# 3. Compile Protocol Buffers (if proto was updated)
python3 scripts/generate_proto.py

# 4. Start native gRPC Server (Terminal 1)
python3 scripts/run_server.py

# 5. Start Web Gateway (Terminal 2)
python3 scripts/run_gateway.py

# 6. Access Application
# Open browser at: http://127.0.0.1:8000/marketplace
```

---

## 8. Test Status

Previously recorded test status (`pytest -v`):
- **30 / 30 tests passing (100% pass rate) before Member 3 integration changes**
- `test_user_service.py`: Authentication, empty inputs, role matching.
- `test_auction_query_service.py`: Lot queries, category/status filters, NOT_FOUND responses.
- `test_repositories.py`: Parameterized SQL queries, count aggregations.
- `test_grpc_and_gateway.py`: Full end-to-end distributed HTTP -> FastAPI -> gRPC -> SQLite roundtrip.
- `test_concurrent_queries.py`: Multi-threaded query and login concurrency.
- New streaming and lifecycle tests have been added; their results require a test run.

## Member 3 Implementation Update

The current Python implementation now includes the bidirectional
`AuctionService.AuctionStream` RPC, auction-specific events bridged through the
FastAPI `/ws/live` endpoint, and a server-side lifecycle sweep for scheduled
activation, deadline closure, and startup recovery. The existing auction and bid
records remain the persistent source for final status, highest bid, and winner.
This implementation update supersedes the earlier Member 3 “integration hooks”
status above; it does not add a Java or Maven module.
