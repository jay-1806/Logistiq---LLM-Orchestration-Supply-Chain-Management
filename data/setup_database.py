
import os
import sqlite3


def create_schema(cursor: sqlite3.Cursor):
    """Create all core tables used by the assistant."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            customer TEXT NOT NULL,
            product TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            status TEXT NOT NULL CHECK(status IN (
                'pending', 'processing', 'shipped', 'delivered', 'cancelled'
            )),
            priority TEXT NOT NULL DEFAULT 'standard' CHECK(priority IN (
                'standard', 'expedited', 'critical'
            )),
            created_at TEXT NOT NULL,
            ship_by TEXT NOT NULL,
            notes TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory (
            product TEXT NOT NULL,
            warehouse TEXT NOT NULL,
            quantity_on_hand INTEGER NOT NULL,
            reorder_point INTEGER NOT NULL,
            last_updated TEXT NOT NULL,
            PRIMARY KEY (product, warehouse)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS shipments (
            shipment_id TEXT PRIMARY KEY,
            order_id TEXT NOT NULL,
            carrier TEXT NOT NULL,
            tracking_number TEXT,
            status TEXT NOT NULL CHECK(status IN (
                'label_created', 'picked_up', 'in_transit', 'out_for_delivery', 'delivered'
            )),
            shipped_at TEXT,
            estimated_delivery TEXT,
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS quality_holds (
            hold_id TEXT PRIMARY KEY,
            unit_serial_number TEXT NOT NULL,
            product TEXT NOT NULL,
            reason TEXT NOT NULL,
            severity TEXT NOT NULL CHECK(severity IN ('minor', 'major', 'critical')),
            status TEXT NOT NULL CHECK(status IN ('open', 'under_review', 'resolved', 'scrapped')),
            created_at TEXT NOT NULL,
            resolved_at TEXT,
            resolution_notes TEXT
        )
        """
    )


def create_indexes(cursor: sqlite3.Cursor):
    """Add indexes for higher-volume query performance."""
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_priority ON orders(priority)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_shipments_order_id ON shipments(order_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_shipments_status ON shipments(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_quality_product ON quality_holds(product)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_quality_status ON quality_holds(status)")


def seed_sample_data(cursor: sqlite3.Cursor):
    """Insert the small demo dataset used by default."""
    orders = [
        ("ORD-001", "Acme Corp", "SSD-4TB-Enterprise", 500, 89.99,
         "processing", "standard", "2026-03-15", "2026-03-25", None),
        ("ORD-002", "GlobalTech", "HDD-12TB-NAS", 1000, 199.99,
         "shipped", "expedited", "2026-03-10", "2026-03-18",
         "Customer requested expedited shipping"),
        ("ORD-003", "DataVault Inc", "SSD-8TB-Enterprise", 200, 159.99,
         "pending", "critical", "2026-03-20", "2026-03-23",
         "Critical priority - customer SLA at risk"),
        ("ORD-004", "CloudNine Systems", "HDD-18TB-Enterprise", 750, 279.99,
         "processing", "standard", "2026-03-12", "2026-03-28", None),
        ("ORD-005", "Acme Corp", "SSD-2TB-Consumer", 2000, 49.99,
         "delivered", "standard", "2026-03-01", "2026-03-10", None),
        ("ORD-006", "MegaStore", "Flash-256GB-Industrial", 5000, 12.99,
         "processing", "standard", "2026-03-18", "2026-04-01", None),
        ("ORD-007", "DataVault Inc", "SSD-4TB-Enterprise", 300, 89.99,
         "pending", "expedited", "2026-03-21", "2026-03-26",
         "Repeat customer - priority handling"),
        ("ORD-008", "TechFlow Ltd", "HDD-8TB-Surveillance", 1500, 129.99,
         "cancelled", "standard", "2026-03-05", "2026-03-15",
         "Customer cancelled - budget constraints"),
    ]
    cursor.executemany("INSERT OR REPLACE INTO orders VALUES (?,?,?,?,?,?,?,?,?,?)", orders)

    inventory = [
        ("SSD-4TB-Enterprise", "Santa Clara", 1200, 300, "2026-03-22"),
        ("SSD-4TB-Enterprise", "Singapore", 800, 200, "2026-03-22"),
        ("HDD-12TB-NAS", "Santa Clara", 450, 500, "2026-03-22"),
        ("HDD-12TB-NAS", "Singapore", 2000, 400, "2026-03-22"),
        ("SSD-8TB-Enterprise", "Santa Clara", 150, 100, "2026-03-22"),
        ("SSD-8TB-Enterprise", "Singapore", 300, 100, "2026-03-22"),
        ("HDD-18TB-Enterprise", "Santa Clara", 600, 200, "2026-03-22"),
        ("SSD-2TB-Consumer", "Santa Clara", 5000, 1000, "2026-03-22"),
        ("Flash-256GB-Industrial", "Santa Clara", 8000, 2000, "2026-03-22"),
        ("Flash-256GB-Industrial", "Singapore", 12000, 3000, "2026-03-22"),
        ("HDD-8TB-Surveillance", "Santa Clara", 3000, 500, "2026-03-22"),
    ]
    cursor.executemany("INSERT OR REPLACE INTO inventory VALUES (?,?,?,?,?)", inventory)

    shipments = [
        ("SHP-001", "ORD-002", "FedEx", "FX-9876543210", "in_transit", "2026-03-14", "2026-03-18"),
        ("SHP-002", "ORD-005", "UPS", "1Z-999-AA1-012345", "delivered", "2026-03-05", "2026-03-09"),
        ("SHP-003", "ORD-004", "DHL", None, "label_created", None, "2026-03-27"),
    ]
    cursor.executemany("INSERT OR REPLACE INTO shipments VALUES (?,?,?,?,?,?,?)", shipments)

    quality_holds = [
        ("QH-001", "SN-445721", "SSD-8TB-Enterprise", "Failed burn-in test", "critical", "open", "2026-03-19", None, None),
        ("QH-002", "SN-331892", "SSD-4TB-Enterprise", "Cosmetic scratch on casing", "minor", "resolved", "2026-03-15", "2026-03-16", "Re-inspected - scratch within tolerance, cleared for ship"),
        ("QH-003", "SN-772001", "HDD-12TB-NAS", "Firmware version mismatch", "major", "under_review", "2026-03-20", None, None),
        ("QH-004", "SN-558834", "Flash-256GB-Industrial", "ESD damage detected", "critical", "scrapped", "2026-03-18", "2026-03-19", "Unit scrapped - irreparable ESD damage"),
        ("QH-005", "SN-990112", "SSD-4TB-Enterprise", "Labeling error", "minor", "open", "2026-03-21", None, None),
    ]
    cursor.executemany("INSERT OR REPLACE INTO quality_holds VALUES (?,?,?,?,?,?,?,?,?)", quality_holds)


def create_database(db_path: str = "./data/supply_chain.db"):
    """Create the supply chain database with schema, indexes, and sample data."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    create_schema(cursor)
    seed_sample_data(cursor)
    create_indexes(cursor)

    conn.commit()
    conn.close()

    print(f"Database created at {db_path}")
    print("  - 8 orders")
    print("  - 11 inventory records")
    print("  - 3 shipments")
    print("  - 5 quality holds")


if __name__ == "__main__":
    create_database()

