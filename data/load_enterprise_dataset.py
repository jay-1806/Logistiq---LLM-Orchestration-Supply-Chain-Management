
from __future__ import annotations

import argparse
import csv
import os
import random
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from data.setup_database import create_indexes, create_schema

ORDER_STATUS_MAP = {
    "created": "pending",
    "approved": "processing",
    "invoiced": "processing",
    "processing": "processing",
    "shipped": "shipped",
    "delivered": "delivered",
    "unavailable": "cancelled",
    "canceled": "cancelled",
}

SHIPMENT_STATUS_MAP = {
    "created": "label_created",
    "approved": "label_created",
    "invoiced": "picked_up",
    "processing": "picked_up",
    "shipped": "in_transit",
    "delivered": "delivered",
    "unavailable": "out_for_delivery",
    "canceled": "out_for_delivery",
}

WAREHOUSES = ["Sao Paulo", "Campinas", "Curitiba", "Recife", "Manaus"]
CARRIERS = ["DHL", "FedEx", "UPS", "BlueDart", "Correios"]
HOLD_REASONS = [
    ("Packaging damage risk", "minor"),
    ("Label mismatch", "minor"),
    ("Firmware validation failure", "major"),
    ("QA electrical test failed", "critical"),
]


def _read_csv(path: Path):
    with path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            yield row


def _parse_date(value: str, fallback: datetime) -> datetime:
    if not value:
        return fallback
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    return fallback


def _safe_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def load_olist_to_supply_chain_schema(
    source_dir: str,
    db_path: str = "./data/supply_chain.db",
    max_orders: int | None = None,
    seed: int = 42,
):
    random.seed(seed)

    source = Path(source_dir)
    required = [
        source / "olist_orders_dataset.csv",
        source / "olist_order_items_dataset.csv",
        source / "olist_customers_dataset.csv",
    ]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing required CSV files: " + ", ".join(missing))

    products_path = source / "olist_products_dataset.csv"

    customer_id_to_name: dict[str, str] = {}
    for row in _read_csv(source / "olist_customers_dataset.csv"):
        customer_id_to_name[row.get("customer_id", "")] = row.get("customer_unique_id", "unknown_customer")

    product_id_to_category: dict[str, str] = {}
    if products_path.exists():
        for row in _read_csv(products_path):
            product_id_to_category[row.get("product_id", "")] = row.get("product_category_name", "unknown_product")

    order_items = defaultdict(lambda: {"qty": 0, "price_sum": 0.0, "product_votes": defaultdict(int)})
    for row in _read_csv(source / "olist_order_items_dataset.csv"):
        order_id = row.get("order_id", "")
        if not order_id:
            continue
        product_id = row.get("product_id", "")
        product_name = product_id_to_category.get(product_id, product_id or "unknown_product")
        order_items[order_id]["qty"] += 1
        order_items[order_id]["price_sum"] += _safe_float(row.get("price"), 0.0)
        order_items[order_id]["product_votes"][product_name] += 1

    orders_rows = []
    shipments_rows = []
    quality_rows = []
    now = datetime.utcnow()

    loaded = 0
    for row in _read_csv(source / "olist_orders_dataset.csv"):
        if max_orders is not None and loaded >= max_orders:
            break

        order_id = row.get("order_id", "")
        if not order_id or order_id not in order_items:
            continue

        item_info = order_items[order_id]
        customer_id = row.get("customer_id", "")
        customer = customer_id_to_name.get(customer_id, customer_id or "unknown_customer")

        purchase_dt = _parse_date(row.get("order_purchase_timestamp", ""), now)
        ship_by_dt = _parse_date(row.get("order_estimated_delivery_date", ""), purchase_dt + timedelta(days=7))
        carrier_dt = _parse_date(row.get("order_delivered_carrier_date", ""), purchase_dt + timedelta(days=1))

        raw_status = (row.get("order_status") or "processing").strip().lower()
        status = ORDER_STATUS_MAP.get(raw_status, "processing")
        ship_delta = (ship_by_dt - purchase_dt).days

        if raw_status in {"canceled", "unavailable"}:
            priority = "standard"
            notes = "Order cancelled or unavailable in source system"
        elif ship_delta <= 3:
            priority = "critical"
            notes = "Tight SLA window"
        elif ship_delta <= 6:
            priority = "expedited"
            notes = "Fast lane order"
        else:
            priority = "standard"
            notes = None

        product = max(item_info["product_votes"], key=item_info["product_votes"].get)
        quantity = int(item_info["qty"])
        unit_price = round(item_info["price_sum"] / max(quantity, 1), 2)

        mapped_order_id = f"ORD-{order_id[:12]}"
        orders_rows.append(
            (
                mapped_order_id,
                customer,
                product,
                quantity,
                unit_price,
                status,
                priority,
                purchase_dt.strftime("%Y-%m-%d"),
                ship_by_dt.strftime("%Y-%m-%d"),
                notes,
            )
        )

        shipments_rows.append(
            (
                f"SHP-{order_id[:12]}",
                mapped_order_id,
                random.choice(CARRIERS),
                f"TRK-{order_id[:10].upper()}",
                SHIPMENT_STATUS_MAP.get(raw_status, "label_created"),
                carrier_dt.strftime("%Y-%m-%d") if carrier_dt else None,
                ship_by_dt.strftime("%Y-%m-%d"),
            )
        )

        if random.random() < 0.02:
            reason, severity = random.choice(HOLD_REASONS)
            hold_status = random.choice(["open", "under_review", "resolved"])
            created_at = purchase_dt + timedelta(days=random.randint(0, 3))
            resolved_at = created_at + timedelta(days=2) if hold_status == "resolved" else None
            quality_rows.append(
                (
                    f"QH-{loaded+1:08d}",
                    f"SN-{random.randint(100000, 999999)}",
                    product,
                    reason,
                    severity,
                    hold_status,
                    created_at.strftime("%Y-%m-%d"),
                    resolved_at.strftime("%Y-%m-%d") if resolved_at else None,
                    "Resolved after QA recheck" if resolved_at else None,
                )
            )

        loaded += 1

    demand_by_product = defaultdict(int)
    for row in orders_rows:
        demand_by_product[row[2]] += row[3]

    inventory_rows = []
    for product, demand in demand_by_product.items():
        reorder_point = max(50, int(demand * 0.05))
        for wh in WAREHOUSES:
            qty = max(reorder_point + 10, int(reorder_point * random.uniform(0.8, 3.2)))
            inventory_rows.append((product, wh, qty, reorder_point, datetime.utcnow().strftime("%Y-%m-%d")))

    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    create_schema(cur)
    create_indexes(cur)

    cur.execute("DELETE FROM shipments")
    cur.execute("DELETE FROM quality_holds")
    cur.execute("DELETE FROM inventory")
    cur.execute("DELETE FROM orders")

    cur.executemany("INSERT OR REPLACE INTO orders VALUES (?,?,?,?,?,?,?,?,?,?)", orders_rows)
    cur.executemany("INSERT OR REPLACE INTO shipments VALUES (?,?,?,?,?,?,?)", shipments_rows)
    cur.executemany("INSERT OR REPLACE INTO inventory VALUES (?,?,?,?,?)", inventory_rows)
    if quality_rows:
        cur.executemany("INSERT OR REPLACE INTO quality_holds VALUES (?,?,?,?,?,?,?,?,?)", quality_rows)

    conn.commit()
    conn.close()

    print(f"Loaded enterprise dataset into {db_path}")
    print(f"  - orders: {len(orders_rows)}")
    print(f"  - shipments: {len(shipments_rows)}")
    print(f"  - inventory records: {len(inventory_rows)}")
    print(f"  - quality holds: {len(quality_rows)}")


def main():
    parser = argparse.ArgumentParser(description="Load Olist dataset into supply chain schema")
    parser.add_argument("--source-dir", required=True, help="Folder containing Olist CSV files")
    parser.add_argument("--db-path", default="./data/supply_chain.db", help="SQLite DB output path")
    parser.add_argument("--max-orders", type=int, default=None, help="Limit number of orders to import")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for deterministic synthetic fields")
    args = parser.parse_args()

    load_olist_to_supply_chain_schema(
        source_dir=args.source_dir,
        db_path=args.db_path,
        max_orders=args.max_orders,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()

