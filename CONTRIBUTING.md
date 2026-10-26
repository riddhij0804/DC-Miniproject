# Contributing & Team Integration Guidelines

Welcome to the **Online Auction System** distributed computing project repository. To ensure smooth collaboration between Member 1, Member 2, and Member 3, please adhere to the following standards.

---

## 1. Team Division of Responsibilities

- **Member 1 (Current Module):** User Access (`UserService`), Auction Catalog & Details Retrieval (`AuctionService.ListAuctions`, `GetAuction`), Database initialization, Web Gateway foundation, Editorial Marketplace frontend.
- **Member 2:** Bid submission and validation engine (`AuctionService.PlaceBid`), Auction lot creation workflow (`CreateAuction`), Concurrency control.
- **Member 3:** Live event streaming (`StreamAuctionEvents`), Bidirectional streaming, Push notifications via WebSocket bridge.

---

## 2. Shared Contract Rules

1. **Protocol Buffers (`proto/auction_service.proto`):**
   - Any modifications to messages or RPC definitions must be agreed upon with the team.
   - Run `python3 scripts/generate_proto.py` after editing `.proto` files to rebuild Python stubs in `backend/grpc_server/generated/`.
2. **Database Schema (`database/schema.sql`):**
   - The SQLite schema is shared across all modules.
   - Always use parameterized queries (e.g. `cursor.execute("... WHERE id = ?", (val,))`). Never use string concatenation.
   - If tables require schema updates, document migrations in `PROJECT_CONTEXT.md`.
3. **No Standalone Forking:**
   - Do not create a separate or duplicate database.
   - Do not replace gRPC with direct database connections from the web gateway.

---

## 3. Git Workflow

- Pull the latest changes before starting work: `git pull origin main`.
- Work on descriptive feature branches (e.g., `feature/member2-bidding-engine`, `feature/member3-live-events`).
- Never commit virtual environment directories (`.venv`), `.env` files with credentials, or compiled SQLite databases (`*.db`). These are excluded by `.gitignore`.
- Run the test suite before committing:
  ```bash
  pytest -v
  ```

---

## 4. Code Style & Standards

- **Python:** PEP 8 compliance, descriptive variable names, clear docstrings, type annotations where practical.
- **Frontend:** Clean separation into HTML, CSS (`theme.css`, `marketplace.css`), and JavaScript modules (`api.js`, `auth.js`, etc.).
- **Error Handling:** Avoid leaking raw stack traces to the browser client; return clean gRPC status codes (`NOT_FOUND`, `INVALID_ARGUMENT`, etc.) which the gateway translates to appropriate HTTP status codes.
