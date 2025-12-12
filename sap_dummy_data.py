# sap_dummy_data.py
import sqlite3
from datetime import datetime, timedelta
import random
from pathlib import Path

DB_PATH = Path(__file__).parent / "sap_dummy.db"

def init_dummy_sap_database():
    """Initialize a SQLite database with dummy SAP-like data."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create tables similar to SAP structure

    # Materials Master (MARA-like table)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS materials (
            material_id TEXT PRIMARY KEY,
            material_name TEXT,
            material_type TEXT,
            base_unit TEXT,
            material_group TEXT,
            created_date TEXT
        )
    """)

    # Sales Orders (VBAK-like table)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales_orders (
            order_id TEXT PRIMARY KEY,
            customer_id TEXT,
            order_date TEXT,
            total_amount REAL,
            currency TEXT,
            status TEXT,
            sales_org TEXT
        )
    """)

    # Sales Order Items (VBAP-like table)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales_order_items (
            order_id TEXT,
            item_number INTEGER,
            material_id TEXT,
            quantity REAL,
            unit_price REAL,
            net_value REAL,
            delivery_date TEXT,
            PRIMARY KEY (order_id, item_number)
        )
    """)

    # Customers (KNA1-like table)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id TEXT PRIMARY KEY,
            customer_name TEXT,
            country TEXT,
            city TEXT,
            credit_limit REAL,
            customer_group TEXT
        )
    """)

    # Inventory (MARD-like table)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            material_id TEXT,
            plant TEXT,
            storage_location TEXT,
            quantity REAL,
            unit TEXT,
            last_updated TEXT,
            PRIMARY KEY (material_id, plant, storage_location)
        )
    """)

    # Purchase Orders (EKKO-like table)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS purchase_orders (
            po_number TEXT PRIMARY KEY,
            vendor_id TEXT,
            po_date TEXT,
            total_amount REAL,
            currency TEXT,
            status TEXT
        )
    """)

    # Insert dummy data
    materials = [
        ("MAT001", "Steel Pipe 10cm", "RAW", "PC", "STEEL", "2024-01-15"),
        ("MAT002", "Aluminum Sheet", "RAW", "KG", "METAL", "2024-02-20"),
        ("MAT003", "Finished Product A", "FERT", "PC", "FINISHED", "2024-03-10"),
        ("MAT004", "Component B", "HALB", "PC", "SEMI", "2024-01-25"),
        ("MAT005", "Packaging Material", "VERP", "PC", "PACK", "2024-04-05"),
    ]
    cursor.executemany("INSERT OR IGNORE INTO materials VALUES (?, ?, ?, ?, ?, ?)", materials)

    customers = [
        ("CUST001", "Tech Corp Inc", "USA", "New York", 100000.0, "KEY"),
        ("CUST002", "Global Industries", "Germany", "Berlin", 150000.0, "KEY"),
        ("CUST003", "Local Supplies Ltd", "UK", "London", 50000.0, "STD"),
        ("CUST004", "Asian Traders", "Singapore", "Singapore", 80000.0, "STD"),
        ("CUST005", "Euro Manufacturing", "France", "Paris", 120000.0, "KEY"),
    ]
    cursor.executemany("INSERT OR IGNORE INTO customers VALUES (?, ?, ?, ?, ?, ?)", customers)

    sales_orders = [
        ("SO001", "CUST001", "2024-10-01", 25000.0, "USD", "COMPLETED", "US01"),
        ("SO002", "CUST002", "2024-10-15", 45000.0, "EUR", "IN_PROGRESS", "EU01"),
        ("SO003", "CUST003", "2024-10-20", 15000.0, "GBP", "COMPLETED", "UK01"),
        ("SO004", "CUST001", "2024-11-01", 35000.0, "USD", "IN_PROGRESS", "US01"),
        ("SO005", "CUST004", "2024-11-05", 20000.0, "SGD", "PENDING", "AP01"),
    ]
    cursor.executemany("INSERT OR IGNORE INTO sales_orders VALUES (?, ?, ?, ?, ?, ?, ?)", sales_orders)

    order_items = [
        ("SO001", 10, "MAT001", 100, 150.0, 15000.0, "2024-10-15"),
        ("SO001", 20, "MAT003", 50, 200.0, 10000.0, "2024-10-15"),
        ("SO002", 10, "MAT002", 200, 100.0, 20000.0, "2024-11-01"),
        ("SO002", 20, "MAT004", 250, 100.0, 25000.0, "2024-11-01"),
        ("SO003", 10, "MAT005", 300, 50.0, 15000.0, "2024-10-25"),
        ("SO004", 10, "MAT003", 100, 250.0, 25000.0, "2024-11-15"),
        ("SO004", 20, "MAT001", 50, 200.0, 10000.0, "2024-11-15"),
        ("SO005", 10, "MAT002", 150, 133.33, 20000.0, "2024-11-20"),
    ]
    cursor.executemany("INSERT OR IGNORE INTO sales_order_items VALUES (?, ?, ?, ?, ?, ?, ?)", order_items)

    inventory = [
        ("MAT001", "P001", "SL01", 500, "PC", "2024-11-08"),
        ("MAT002", "P001", "SL01", 1000, "KG", "2024-11-08"),
        ("MAT003", "P002", "SL01", 200, "PC", "2024-11-09"),
        ("MAT004", "P001", "SL02", 750, "PC", "2024-11-07"),
        ("MAT005", "P003", "SL01", 2000, "PC", "2024-11-09"),
    ]
    cursor.executemany("INSERT OR IGNORE INTO inventory VALUES (?, ?, ?, ?, ?, ?)", inventory)

    purchase_orders = [
        ("PO001", "VEND001", "2024-09-15", 50000.0, "USD", "COMPLETED"),
        ("PO002", "VEND002", "2024-10-01", 75000.0, "EUR", "IN_PROGRESS"),
        ("PO003", "VEND003", "2024-10-20", 30000.0, "USD", "PENDING"),
    ]
    cursor.executemany("INSERT OR IGNORE INTO purchase_orders VALUES (?, ?, ?, ?, ?, ?)", purchase_orders)

    conn.commit()
    conn.close()
    print(f"✓ Dummy SAP database initialized at {DB_PATH}")

def get_db_connection():
    """Get a connection to the dummy SAP database."""
    return sqlite3.connect(DB_PATH)

def execute_query(query: str, params: tuple = ()):
    """Execute a SQL query and return results."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    results = cursor.fetchall()
    columns = [description[0] for description in cursor.description]
    conn.close()
    return columns, results

if __name__ == "__main__":
    init_dummy_sap_database()
