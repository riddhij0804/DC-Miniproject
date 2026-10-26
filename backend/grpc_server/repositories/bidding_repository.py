"""
Bidding and Auction Management Repository (Member 2 Responsibility).
Handles atomic bid placement, auction creation, closure, and bid history retrieval.
Implements ACID transactions, concurrency synchronization, and strict state validation.
"""
import time
import uuid
import threading
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
import sqlite3

from database.db import get_connection

class BiddingRepository:
    # Process-level re-entrant lock to serialize write transactions across threads
    _global_write_lock = threading.RLock()
    # Fine-grained per-auction locks for higher throughput
    _auction_locks: Dict[str, threading.Lock] = {}
    _locks_mutex = threading.Lock()

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    @classmethod
    def _get_auction_lock(cls, auction_id: str) -> threading.Lock:
        with cls._locks_mutex:
            if auction_id not in cls._auction_locks:
                cls._auction_locks[auction_id] = threading.Lock()
            return cls._auction_locks[auction_id]

    @staticmethod
    def _parse_iso_datetime(dt_str: str) -> Optional[datetime]:
        """Safely parses ISO 8601 strings into timezone-aware datetime objects."""
        if not dt_str:
            return None
        dt_str = dt_str.strip()
        # Handle trailing Z
        if dt_str.endswith("Z"):
            dt_str = dt_str[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(dt_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return None

    @staticmethod
    def _format_iso(dt: datetime) -> str:
        """Formats datetime to ISO 8601 UTC string."""
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def create_auction(
        self,
        title: str,
        description: str,
        category: str,
        artist_name: str,
        image_path: str,
        seller_id: str,
        starting_price: float,
        min_increment: float = 50.0,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        duration_hours: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Creates a new auction after validating seller authorization, lot details, and dates.
        Saves directly to the database and returns the created auction_id.
        """
        # 1. Validate inputs
        if not title or not title.strip():
            return {"success": False, "auction_id": "", "error_message": "Item title cannot be empty."}
        if not description or not description.strip():
            return {"success": False, "auction_id": "", "error_message": "Item description cannot be empty."}
        if not seller_id or not seller_id.strip():
            return {"success": False, "auction_id": "", "error_message": "Seller ID is required."}

        title = title.strip()
        description = description.strip()
        seller_id = seller_id.strip()

        # Validate category against schema constraint
        valid_categories = {'Paintings', 'Sculptures', 'Vintage', 'Collectibles', 'Art'}
        matched_category = None
        for c in valid_categories:
            if c.lower() == (category or "").strip().lower():
                matched_category = c
                break
        category = matched_category or "Art"

        artist_name = (artist_name or "").strip() or "Masterwork Studio"
        image_path = (image_path or "").strip() or "/assets/images/artwork_001.svg"

        try:
            starting_price = float(starting_price)
            if starting_price < 0:
                return {"success": False, "auction_id": "", "error_message": "Starting price must be non-negative."}
        except (ValueError, TypeError):
            return {"success": False, "auction_id": "", "error_message": "Invalid starting price format."}

        try:
            min_increment = float(min_increment) if min_increment is not None else 50.0
            if min_increment <= 0:
                min_increment = max(10.0, round(starting_price * 0.05, 2))
        except (ValueError, TypeError):
            min_increment = 50.0

        # Validate timing
        now = datetime.now(timezone.utc)
        if start_time and end_time:
            parsed_start = self._parse_iso_datetime(start_time)
            parsed_end = self._parse_iso_datetime(end_time)
            if not parsed_start or not parsed_end:
                return {"success": False, "auction_id": "", "error_message": "Invalid ISO 8601 date format for start_time or end_time."}
            if parsed_end <= parsed_start:
                return {"success": False, "auction_id": "", "error_message": "Auction end time must be after start time."}
            start_iso = self._format_iso(parsed_start)
            end_iso = self._format_iso(parsed_end)
        else:
            hours = float(duration_hours) if duration_hours and float(duration_hours) > 0 else 24.0
            parsed_start = now
            parsed_end = now + timedelta(hours=hours)
            start_iso = self._format_iso(parsed_start)
            end_iso = self._format_iso(parsed_end)

        # Determine initial status
        if now < parsed_start:
            status = "UPCOMING"
        elif now >= parsed_end:
            status = "CLOSED"
        else:
            status = "ACTIVE"

        auction_id = f"auc_{int(time.time())}_{uuid.uuid4().hex[:4]}"

        # 2. Database transaction
        with self._global_write_lock:
            conn = get_connection(self.db_path)
            try:
                cur = conn.cursor()
                cur.execute("BEGIN IMMEDIATE;")

                # Verify seller exists and has SELLER or ADMIN role
                cur.execute("SELECT user_id, display_name, role FROM users WHERE user_id = ? OR username = ?;", (seller_id, seller_id))
                user_row = cur.fetchone()
                if not user_row:
                    conn.rollback()
                    return {
                        "success": False,
                        "auction_id": "",
                        "error_message": f"Seller user '{seller_id}' does not exist in the system."
                    }

                actual_seller_id = user_row["user_id"]
                user_role = user_row["role"]
                if user_role not in ('SELLER', 'ADMIN'):
                    conn.rollback()
                    return {
                        "success": False,
                        "auction_id": "",
                        "error_message": f"User '{user_row['display_name']}' has role '{user_role}'. Only authorized SELLERS or ADMINS may create auction lots."
                    }

                # Insert auction lot
                insert_sql = """
                    INSERT INTO auctions (
                        auction_id, title, description, category, artist_name, image_path,
                        seller_id, starting_price, min_increment, highest_bid, highest_bidder_id,
                        start_time, end_time, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0.0, NULL, ?, ?, ?);
                """
                cur.execute(
                    insert_sql,
                    (
                        auction_id, title, description, category, artist_name, image_path,
                        actual_seller_id, starting_price, min_increment,
                        start_iso, end_iso, status
                    )
                )
                conn.commit()
                return {
                    "success": True,
                    "auction_id": auction_id,
                    "error_message": ""
                }
            except Exception as e:
                conn.rollback()
                return {
                    "success": False,
                    "auction_id": "",
                    "error_message": f"Failed to persist auction: {str(e)}"
                }
            finally:
                conn.close()

    def place_bid(
        self,
        auction_id: str,
        bidder_id: str,
        bid_amount: float
    ) -> Dict[str, Any]:
        """
        Executes an atomic bid placement with synchronization and ACID validation.
        Prevents race conditions, out-of-order bids, and concurrent lost updates.
        """
        auction_id = (auction_id or "").strip()
        bidder_id = (bidder_id or "").strip()

        if not auction_id:
            return {"success": False, "message": "Auction ID cannot be empty.", "current_highest_bid": 0.0, "timestamp": ""}
        if not bidder_id:
            return {"success": False, "message": "Bidder ID cannot be empty.", "current_highest_bid": 0.0, "timestamp": ""}

        try:
            bid_amount = float(bid_amount)
            if bid_amount <= 0:
                return {"success": False, "message": "Bid amount must be greater than zero.", "current_highest_bid": 0.0, "timestamp": ""}
        except (ValueError, TypeError):
            return {"success": False, "message": "Invalid bid amount number.", "current_highest_bid": 0.0, "timestamp": ""}

        auction_lock = self._get_auction_lock(auction_id)

        # Synchronize bid operations for this auction
        with auction_lock:
            # Retry loop for SQLite busy/locked conditions under heavy multi-process load
            max_retries = 5
            for attempt in range(max_retries):
                conn = get_connection(self.db_path)
                try:
                    cur = conn.cursor()
                    cur.execute("BEGIN IMMEDIATE;")

                    # 1. Verify bidder exists
                    cur.execute("SELECT user_id, username, display_name, role FROM users WHERE user_id = ? OR username = ?;", (bidder_id, bidder_id))
                    bidder_row = cur.fetchone()
                    if not bidder_row:
                        conn.rollback()
                        return {
                            "success": False,
                            "message": f"Bidder '{bidder_id}' is not recognized in the system.",
                            "current_highest_bid": 0.0,
                            "timestamp": ""
                        }
                    actual_bidder_id = bidder_row["user_id"]
                    bidder_display_name = bidder_row["display_name"]

                    # 2. Retrieve latest committed auction state
                    cur.execute("""
                        SELECT auction_id, seller_id, starting_price, min_increment,
                               highest_bid, highest_bidder_id, start_time, end_time, status
                        FROM auctions
                        WHERE auction_id = ?;
                    """, (auction_id,))
                    auction_row = cur.fetchone()

                    if not auction_row:
                        conn.rollback()
                        return {
                            "success": False,
                            "message": f"Auction lot '{auction_id}' was not found.",
                            "current_highest_bid": 0.0,
                            "timestamp": ""
                        }

                    seller_id = auction_row["seller_id"]
                    if actual_bidder_id == seller_id:
                        conn.rollback()
                        return {
                            "success": False,
                            "message": "Sellers are prohibited from bidding on their own lots.",
                            "current_highest_bid": float(auction_row["highest_bid"] or 0.0),
                            "timestamp": ""
                        }

                    current_status = auction_row["status"]
                    now = datetime.now(timezone.utc)
                    start_dt = self._parse_iso_datetime(auction_row["start_time"])
                    end_dt = self._parse_iso_datetime(auction_row["end_time"])

                    # 3. Validate status & deadline
                    if current_status == "CLOSED":
                        conn.rollback()
                        return {
                            "success": False,
                            "message": "Auction is closed. No further bids can be accepted.",
                            "current_highest_bid": float(auction_row["highest_bid"] or 0.0),
                            "timestamp": ""
                        }

                    if current_status == "UPCOMING":
                        if start_dt and now < start_dt:
                            conn.rollback()
                            return {
                                "success": False,
                                "message": f"Auction has not opened yet. Starts at {auction_row['start_time']}.",
                                "current_highest_bid": 0.0,
                                "timestamp": ""
                            }
                        else:
                            # Start time reached, update status to ACTIVE
                            cur.execute("UPDATE auctions SET status = 'ACTIVE' WHERE auction_id = ?;", (auction_id,))
                            current_status = "ACTIVE"

                    # Check deadline
                    if end_dt and now >= end_dt:
                        # Automatically close expired auction
                        cur.execute("UPDATE auctions SET status = 'CLOSED' WHERE auction_id = ?;", (auction_id,))
                        conn.commit()
                        return {
                            "success": False,
                            "message": f"Auction deadline reached ({auction_row['end_time']}). The lot is now closed.",
                            "current_highest_bid": float(auction_row["highest_bid"] or 0.0),
                            "timestamp": self._format_iso(now)
                        }

                    # 4. Validate bid amount against freshest committed state
                    current_highest = float(auction_row["highest_bid"] or 0.0)
                    min_increment = float(auction_row["min_increment"] or 50.0)
                    starting_price = float(auction_row["starting_price"] or 0.0)

                    if current_highest > 0:
                        min_acceptable = round(current_highest + min_increment, 2)
                    else:
                        min_acceptable = round(starting_price, 2)

                    if round(bid_amount, 2) < min_acceptable:
                        conn.rollback()
                        return {
                            "success": False,
                            "message": (
                                f"Bid of ${bid_amount:,.2f} is insufficient. "
                                f"Minimum required bid is ${min_acceptable:,.2f} "
                                f"(Current highest: ${current_highest:,.2f}, increment: ${min_increment:,.2f})."
                            ),
                            "current_highest_bid": current_highest,
                            "timestamp": self._format_iso(now)
                        }

                    # Check if already highest bidder with same or lower amount
                    if auction_row["highest_bidder_id"] == actual_bidder_id and round(bid_amount, 2) <= current_highest:
                        conn.rollback()
                        return {
                            "success": False,
                            "message": f"You are already the highest bidder at ${current_highest:,.2f}.",
                            "current_highest_bid": current_highest,
                            "timestamp": self._format_iso(now)
                        }

                    # 5. Persist accepted bid and update auction state
                    bid_id = f"bid_{int(time.time())}_{uuid.uuid4().hex[:6]}"
                    timestamp_iso = self._format_iso(now)

                    cur.execute(
                        "INSERT INTO bids (bid_id, auction_id, bidder_id, bid_amount, timestamp) VALUES (?, ?, ?, ?, ?);",
                        (bid_id, auction_id, actual_bidder_id, round(bid_amount, 2), timestamp_iso)
                    )

                    cur.execute(
                        "UPDATE auctions SET highest_bid = ?, highest_bidder_id = ? WHERE auction_id = ?;",
                        (round(bid_amount, 2), actual_bidder_id, auction_id)
                    )

                    conn.commit()

                    return {
                        "success": True,
                        "message": f"Bid of ${bid_amount:,.2f} placed successfully by {bidder_display_name}.",
                        "current_highest_bid": round(bid_amount, 2),
                        "timestamp": timestamp_iso,
                        "bid_id": bid_id,
                        "auction_id": auction_id
                    }

                except sqlite3.OperationalError as oe:
                    conn.rollback()
                    if "locked" in str(oe).lower() and attempt < max_retries - 1:
                        time.sleep(0.01 * (attempt + 1))
                        continue
                    return {
                        "success": False,
                        "message": f"Database contention error: {str(oe)}",
                        "current_highest_bid": 0.0,
                        "timestamp": ""
                    }
                except Exception as ex:
                    conn.rollback()
                    return {
                        "success": False,
                        "message": f"Bid placement error: {str(ex)}",
                        "current_highest_bid": 0.0,
                        "timestamp": ""
                    }
                finally:
                    conn.close()

    def close_auction(
        self,
        auction_id: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Closes an auction, prevents further bids, and identifies the final winning bidder and price.
        Idempotent: repeating on already-closed auctions returns consistent final state.
        """
        auction_id = (auction_id or "").strip()
        user_id = (user_id or "").strip() if user_id else None

        if not auction_id:
            return {
                "success": False,
                "message": "Auction ID cannot be empty.",
                "auction_id": "",
                "status": "UNKNOWN",
                "winner_id": "",
                "winner_name": "",
                "final_price": 0.0,
                "total_bids": 0
            }

        auction_lock = self._get_auction_lock(auction_id)
        with auction_lock:
            conn = get_connection(self.db_path)
            try:
                cur = conn.cursor()
                cur.execute("BEGIN IMMEDIATE;")

                # Retrieve auction details
                cur.execute("""
                    SELECT a.auction_id, a.seller_id, a.highest_bid, a.highest_bidder_id,
                           a.status, u.display_name AS winner_name
                    FROM auctions a
                    LEFT JOIN users u ON a.highest_bidder_id = u.user_id
                    WHERE a.auction_id = ?;
                """, (auction_id,))
                row = cur.fetchone()

                if not row:
                    conn.rollback()
                    return {
                        "success": False,
                        "message": f"Auction lot '{auction_id}' was not found.",
                        "auction_id": auction_id,
                        "status": "NOT_FOUND",
                        "winner_id": "",
                        "winner_name": "",
                        "final_price": 0.0,
                        "total_bids": 0
                    }

                # If user_id is provided, verify they are the seller or an ADMIN
                if user_id:
                    cur.execute("SELECT user_id, role FROM users WHERE user_id = ? OR username = ?;", (user_id, user_id))
                    user_row = cur.fetchone()
                    if not user_row or (user_row["role"] != "ADMIN" and user_row["user_id"] != row["seller_id"]):
                        conn.rollback()
                        return {
                            "success": False,
                            "message": "Permission denied: Only the lot seller or an administrator can close this auction.",
                            "auction_id": auction_id,
                            "status": row["status"],
                            "winner_id": row["highest_bidder_id"] or "",
                            "winner_name": row["winner_name"] or "",
                            "final_price": float(row["highest_bid"] or 0.0),
                            "total_bids": 0
                        }

                # Count total bids
                cur.execute("SELECT COUNT(*) AS cnt FROM bids WHERE auction_id = ?;", (auction_id,))
                total_bids = cur.fetchone()["cnt"]

                # If already closed, return consistent result
                if row["status"] == "CLOSED":
                    conn.rollback()
                    return {
                        "success": True,
                        "message": "Auction was already closed.",
                        "auction_id": auction_id,
                        "status": "CLOSED",
                        "winner_id": row["highest_bidder_id"] or "",
                        "winner_name": row["winner_name"] or ("No Winner (No Bids)" if not row["highest_bidder_id"] else ""),
                        "final_price": float(row["highest_bid"] or 0.0),
                        "total_bids": total_bids
                    }

                # Update auction to CLOSED
                cur.execute("UPDATE auctions SET status = 'CLOSED' WHERE auction_id = ?;", (auction_id,))
                conn.commit()

                winner_id = row["highest_bidder_id"] or ""
                winner_name = row["winner_name"] or ("No Bids Placed" if not winner_id else "")
                final_price = float(row["highest_bid"] or 0.0)

                return {
                    "success": True,
                    "message": f"Auction closed successfully. Final price: ${final_price:,.2f}.",
                    "auction_id": auction_id,
                    "status": "CLOSED",
                    "winner_id": winner_id,
                    "winner_name": winner_name,
                    "final_price": final_price,
                    "total_bids": total_bids
                }

            except Exception as e:
                conn.rollback()
                return {
                    "success": False,
                    "message": f"Failed to close auction: {str(e)}",
                    "auction_id": auction_id,
                    "status": "ERROR",
                    "winner_id": "",
                    "winner_name": "",
                    "final_price": 0.0,
                    "total_bids": 0
                }
            finally:
                conn.close()

    def get_bids(self, auction_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieves bid history for an auction, ordered by amount and timestamp descending.
        """
        conn = get_connection(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT b.bid_id, b.auction_id, b.bidder_id, b.bid_amount, b.timestamp,
                       u.display_name AS bidder_name, u.username AS bidder_username
                FROM bids b
                LEFT JOIN users u ON b.bidder_id = u.user_id
                WHERE b.auction_id = ?
                ORDER BY b.bid_amount DESC, b.timestamp DESC
                LIMIT ?;
            """, (auction_id, max(1, min(100, limit))))
            rows = cur.fetchall()
            return [
                {
                    "bid_id": r["bid_id"],
                    "auction_id": r["auction_id"],
                    "bidder_id": r["bidder_id"],
                    "bid_amount": float(r["bid_amount"]),
                    "timestamp": r["timestamp"],
                    "bidder_name": r["bidder_name"] or "Anonymous Collector",
                    "bidder_username": r["bidder_username"] or ""
                }
                for r in rows
            ]
        finally:
            conn.close()

