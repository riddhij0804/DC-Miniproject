"""
Seeds the SQLite database with realistic art auction data, demo accounts, and initial bids.
Dates are calculated relative to current execution time so live countdowns work reliably.
"""
import os
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Optional
from database.db import get_connection, init_db, get_db_path

def seed_database(db_path: Optional[str] = None):
    # Ensure tables exist
    init_db(db_path)
    conn = get_connection(db_path)
    cur = conn.cursor()

    now = datetime.now(timezone.utc)

    # 1. Seed Demo Users
    users = [
        ("usr_eleanor", "buyer_eleanor", "Eleanor Vance", "BUYER"),
        ("usr_marcus", "buyer_marcus", "Marcus Sterling", "BUYER"),
        ("usr_sophia", "collector_sophia", "Sophia Loren", "BUYER"),
        ("usr_julian", "art_lover", "Julian Croft", "BUYER"),
        ("usr_arthur", "admin_arthur", "Arthur Pendelton (Curator)", "ADMIN"),
        ("usr_galerie", "seller_galerie", "Galerie Belle Époque", "SELLER"),
    ]

    for uid, uname, dname, role in users:
        cur.execute(
            """
            INSERT INTO users (user_id, username, display_name, role)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                display_name = excluded.display_name,
                role = excluded.role;
            """,
            (uid, uname, dname, role)
        )

    # 2. Seed Auctions
    # Formatted ISO 8601 strings
    def iso(dt: datetime) -> str:
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    auctions = [
        (
            "auc_001",
            "The Whispering Pines at Dusk",
            "An evocative Barbizon school landscape capturing the atmospheric transition of twilight through silver birch and dark pine canopies. Provenance: Private collection, Lyon. Certificate of authenticity included.",
            "Paintings",
            "Jean-Baptiste Corot (School)",
            "/assets/images/artwork_001.svg",
            "usr_galerie",
            4500.0,
            250.0,
            6750.0,
            "usr_eleanor",
            iso(now - timedelta(hours=4)),
            iso(now + timedelta(hours=8, minutes=45)),
            "ACTIVE"
        ),
        (
            "auc_002",
            "Bronze Minotaur Study No. 4",
            "Lost-wax cast bronze sculpture with rich dark brown patina and subtle greenish highlights. Signed on base with foundry seal. Exceptional anatomical tension and fine muscular detail.",
            "Sculptures",
            "Antoine-Louis Barye",
            "/assets/images/artwork_002.svg",
            "usr_galerie",
            12000.0,
            500.0,
            15500.0,
            "usr_marcus",
            iso(now - timedelta(days=1)),
            iso(now + timedelta(hours=22, minutes=15)),
            "ACTIVE"
        ),
        (
            "auc_003",
            "Gilded Art Deco Chronometer, c. 1928",
            "18-karat yellow gold case with stepped geometric lugs, champagne dial, and blued steel Breguet hands. Fully documented provenance with original box and archival extract.",
            "Vintage",
            "Horlogerie Genevoise Atelier",
            "/assets/images/artwork_003.svg",
            "usr_galerie",
            8200.0,
            300.0,
            9400.0,
            "usr_sophia",
            iso(now - timedelta(hours=18)),
            iso(now + timedelta(days=2, hours=4)),
            "ACTIVE"
        ),
        (
            "auc_004",
            "Ceramic Vessel with Indigo & Ash Glaze",
            "Mingei folk-craft ceramic vase with spontaneous iron brushwork over tenmoku and wood-ash glaze. Fired in Mashiko ascending climbing kiln. Registered cultural collectible.",
            "Collectibles",
            "Master Shoji Hamada (Attr.)",
            "/assets/images/artwork_004.svg",
            "usr_galerie",
            3200.0,
            150.0,
            3650.0,
            "usr_julian",
            iso(now - timedelta(hours=12)),
            iso(now + timedelta(hours=14, minutes=30)),
            "ACTIVE"
        ),
        (
            "auc_005",
            "Geometric Abstraction in Ochre and Vermilion",
            "Oil on linen featuring intersecting dynamic planes of raw ochre, cadmium vermilion, and deep charcoal. Exhibited in Berlin Retrospective, 1974. Acquired directly from artist estate.",
            "Paintings",
            "Kazimir Malevich Circle (c. 1922)",
            "/assets/images/artwork_005.svg",
            "usr_galerie",
            28000.0,
            1000.0,
            34000.0,
            "usr_sophia",
            iso(now - timedelta(days=2)),
            iso(now + timedelta(days=1, hours=6)),
            "ACTIVE"
        ),
        (
            "auc_006",
            "Imperial Cloisonné Chrysanthemum Vase",
            "Meiji-era silver-wire cloisonné enamel depicting blooming white and gold chrysanthemums against a mirror-black midnight ground. Retains original carved wooden stand.",
            "Collectibles",
            "Hayashi Kodenji Studio",
            "/assets/images/artwork_006.svg",
            "usr_galerie",
            6500.0,
            250.0,
            0.0,
            None,
            iso(now + timedelta(days=1, hours=10)),
            iso(now + timedelta(days=5)),
            "UPCOMING"
        ),
        (
            "auc_007",
            "Study of Drapery in Charcoal & White Chalk",
            "Fine drawing on toned rag paper exploring light and shadow folds of Venetian satin. Bearing artist monogram lower right and collector stamp on verso.",
            "Art",
            "John Singer Sargent (Attr.)",
            "/assets/images/artwork_007.svg",
            "usr_galerie",
            5000.0,
            200.0,
            0.0,
            None,
            iso(now + timedelta(days=3)),
            iso(now + timedelta(days=7)),
            "UPCOMING"
        ),
        (
            "auc_008",
            "Torso of Aphrodite in Thassos Marble",
            "Carved from pure white crystalline Thassos marble, mounted on a honed Belgian black marble plinth. Exhibited widely in neoclassical retrospectives.",
            "Sculptures",
            "Hellenistic Revival Atelier (19th Century)",
            "/assets/images/artwork_008.svg",
            "usr_galerie",
            18000.0,
            1000.0,
            26000.0,
            "usr_eleanor",
            iso(now - timedelta(days=6)),
            iso(now - timedelta(hours=2)),
            "CLOSED"
        ),
    ]

    for auc in auctions:
        cur.execute(
            """
            INSERT INTO auctions (
                auction_id, title, description, category, artist_name, image_path,
                seller_id, starting_price, min_increment, highest_bid,
                highest_bidder_id, start_time, end_time, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(auction_id) DO UPDATE SET
                title = excluded.title,
                description = excluded.description,
                category = excluded.category,
                artist_name = excluded.artist_name,
                image_path = excluded.image_path,
                seller_id = excluded.seller_id,
                starting_price = excluded.starting_price,
                min_increment = excluded.min_increment,
                highest_bid = excluded.highest_bid,
                highest_bidder_id = excluded.highest_bidder_id,
                start_time = excluded.start_time,
                end_time = excluded.end_time,
                status = excluded.status;
            """,
            auc
        )

    # 3. Seed Demo Bids (Supporting Member 2 Integration)
    bids = [
        # auc_001
        ("bid_001", "auc_001", "usr_marcus", 4750.0, iso(now - timedelta(hours=3, minutes=30))),
        ("bid_002", "auc_001", "usr_julian", 5500.0, iso(now - timedelta(hours=2, minutes=45))),
        ("bid_003", "auc_001", "usr_eleanor", 6750.0, iso(now - timedelta(minutes=40))),
        # auc_002
        ("bid_004", "auc_002", "usr_sophia", 13000.0, iso(now - timedelta(hours=14))),
        ("bid_005", "auc_002", "usr_marcus", 15500.0, iso(now - timedelta(hours=4))),
        # auc_003
        ("bid_006", "auc_003", "usr_eleanor", 8500.0, iso(now - timedelta(hours=10))),
        ("bid_007", "auc_003", "usr_sophia", 9400.0, iso(now - timedelta(hours=1))),
        # auc_004
        ("bid_008", "auc_004", "usr_marcus", 3350.0, iso(now - timedelta(hours=8))),
        ("bid_009", "auc_004", "usr_julian", 3650.0, iso(now - timedelta(hours=2))),
        # auc_005
        ("bid_010", "auc_005", "usr_marcus", 30000.0, iso(now - timedelta(days=1))),
        ("bid_011", "auc_005", "usr_sophia", 34000.0, iso(now - timedelta(hours=6))),
        # auc_008 (closed)
        ("bid_012", "auc_008", "usr_marcus", 20000.0, iso(now - timedelta(days=4))),
        ("bid_013", "auc_008", "usr_eleanor", 26000.0, iso(now - timedelta(hours=3))),
    ]

    for bid in bids:
        cur.execute(
            """
            INSERT OR REPLACE INTO bids (bid_id, auction_id, bidder_id, bid_amount, timestamp)
            VALUES (?, ?, ?, ?, ?);
            """,
            bid
        )

    conn.commit()
    conn.close()
    print(f"Database successfully seeded at: {db_path or get_db_path()}")

if __name__ == "__main__":
    seed_database()
