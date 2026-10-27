"""
Auction query repository for Member 1 marketplace queries.
Retrieves auction records, supports parameterized search, filtering, and pagination.
"""
from typing import Optional, List, Dict, Any, Tuple
from database.db import get_connection

class AuctionQueryRepository:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def _row_to_dict(self, row: Any) -> Dict[str, Any]:
        """Maps an SQLite row to a standard auction dictionary with computed fields."""
        d = dict(row)
        highest_bid = float(d.get("highest_bid") or 0.0)
        starting_price = float(d.get("starting_price") or 0.0)
        min_increment = float(d.get("min_increment") or 50.0)

        # Computed next minimum bid
        if highest_bid > 0:
            d["min_next_bid"] = round(highest_bid + min_increment, 2)
        else:
            d["min_next_bid"] = round(starting_price, 2)

        d["total_bids"] = int(d.get("total_bids") or 0)
        d["seller_name"] = d.get("seller_name") or "Curated House Lot"
        d["highest_bidder_name"] = d.get("highest_bidder_name") or ""
        d["highest_bidder_id"] = d.get("highest_bidder_id") or ""
        return d

    def find_auctions(
        self,
        search: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 12
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Retrieves auctions matching search text, category, and status.
        Returns a tuple of (items, total_count).
        """
        page = max(1, page)
        page_size = max(1, min(100, page_size))
        offset = (page - 1) * page_size

        where_clauses = []
        params = []

        if search and search.strip():
            term = f"%{search.strip()}%"
            where_clauses.append(
                "(a.title LIKE ? OR a.description LIKE ? OR a.artist_name LIKE ?)"
            )
            params.extend([term, term, term])

        if category and category.strip() and category.strip().lower() != "all":
            where_clauses.append("LOWER(a.category) = LOWER(?)")
            params.append(category.strip())

        if status and status.strip() and status.strip().upper() != "ALL":
            where_clauses.append("UPPER(a.status) = UPPER(?)")
            params.append(status.strip())

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        conn = get_connection(self.db_path)
        try:
            cur = conn.cursor()

            # 1. Count query
            count_sql = f"SELECT COUNT(*) AS cnt FROM auctions a {where_sql};"
            cur.execute(count_sql, params)
            total_count = cur.fetchone()["cnt"]

            # 2. Main data query
            data_sql = f"""
                SELECT
                    a.auction_id,
                    a.title,
                    a.description,
                    a.category,
                    a.artist_name,
                    a.image_path,
                    a.seller_id,
                    u_seller.display_name AS seller_name,
                    a.starting_price,
                    a.min_increment,
                    a.highest_bid,
                    a.highest_bidder_id,
                    u_bidder.display_name AS highest_bidder_name,
                    a.start_time,
                    a.end_time,
                    a.status,
                    (SELECT COUNT(*) FROM bids b WHERE b.auction_id = a.auction_id) AS total_bids
                FROM auctions a
                LEFT JOIN users u_seller ON a.seller_id = u_seller.user_id
                LEFT JOIN users u_bidder ON a.highest_bidder_id = u_bidder.user_id
                {where_sql}
                ORDER BY
                    CASE a.status
                        WHEN 'ACTIVE' THEN 1
                        WHEN 'UPCOMING' THEN 2
                        WHEN 'CLOSED' THEN 3
                        ELSE 4
                    END,
                    a.end_time ASC
                LIMIT ? OFFSET ?;
            """
            cur.execute(data_sql, params + [page_size, offset])
            rows = cur.fetchall()
            items = [self._row_to_dict(r) for r in rows]

            return items, total_count
        finally:
            conn.close()

    def find_auction_by_id(self, auction_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves full auction record by auction_id.
        """
        if not auction_id:
            return None

        conn = get_connection(self.db_path)
        try:
            cur = conn.cursor()
            sql = """
                SELECT
                    a.auction_id,
                    a.title,
                    a.description,
                    a.category,
                    a.artist_name,
                    a.image_path,
                    a.seller_id,
                    u_seller.display_name AS seller_name,
                    a.starting_price,
                    a.min_increment,
                    a.highest_bid,
                    a.highest_bidder_id,
                    u_bidder.display_name AS highest_bidder_name,
                    a.start_time,
                    a.end_time,
                    a.status,
                    (SELECT COUNT(*) FROM bids b WHERE b.auction_id = a.auction_id) AS total_bids
                FROM auctions a
                LEFT JOIN users u_seller ON a.seller_id = u_seller.user_id
                LEFT JOIN users u_bidder ON a.highest_bidder_id = u_bidder.user_id
                WHERE a.auction_id = ?
                LIMIT 1;
            """
            cur.execute(sql, (auction_id,))
            row = cur.fetchone()
            if row:
                return self._row_to_dict(row)
            return None
        finally:
            conn.close()

    def find_auctions_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Convenience method to query by category."""
        items, _ = self.find_auctions(category=category, page=1, page_size=100)
        return items

    def find_auctions_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Convenience method to query by status."""
        items, _ = self.find_auctions(status=status, page=1, page_size=100)
        return items

    def get_distinct_categories(self) -> List[str]:
        """Returns sorted list of distinct categories currently in database."""
        conn = get_connection(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT category FROM auctions ORDER BY category ASC;")
            rows = cur.fetchall()
            return [r["category"] for r in rows if r["category"]]
        finally:
            conn.close()

    def find_auctions_for_lifecycle(self) -> List[Dict[str, Any]]:
        """Returns non-final auctions for server-side lifecycle processing."""
        conn = get_connection(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT auction_id, status, start_time, end_time
                FROM auctions
                WHERE status IN ('UPCOMING', 'ACTIVE')
                ORDER BY end_time ASC;
            """)
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()
