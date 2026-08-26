"""
db.py - Local SQLite Database Manager for Transaction Scanner
Stores and queries all financial transactions, categories, items, and settings.
"""

import sqlite3
import json
import csv
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transactions.db")


def get_connection(db_path: str = DB_FILE) -> sqlite3.Connection:
    """Create a database connection with dictionary-like row access."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DB_FILE) -> None:
    """Initialize SQLite database tables."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            merchant TEXT NOT NULL,
            category TEXT NOT NULL,
            total_amount REAL NOT NULL,
            currency TEXT DEFAULT '$',
            tax_amount REAL DEFAULT 0.0,
            items_json TEXT DEFAULT '[]',
            payment_method TEXT DEFAULT 'Unknown',
            image_path TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            tx_type TEXT DEFAULT 'Expense',
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'Marker',
            phone TEXT DEFAULT '',
            salary_type TEXT DEFAULT 'Monthly',
            base_salary REAL NOT NULL DEFAULT 0.0,
            hire_date TEXT DEFAULT '',
            leave_date TEXT DEFAULT '',
            status TEXT DEFAULT 'Active',
            settlement_amount REAL DEFAULT 0.0,
            security_refunded REAL DEFAULT 0.0,
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            phone TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
    """)

    # Ensure resignation columns exist if table was created previously
    for col in ["leave_date TEXT DEFAULT ''", "settlement_amount REAL DEFAULT 0.0", "security_refunded REAL DEFAULT 0.0"]:
        try:
            cursor.execute(f"ALTER TABLE staff ADD COLUMN {col}")
        except Exception:
            pass

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def add_transaction(
    date: str,
    merchant: str,
    category: str,
    total_amount: float,
    currency: str = "$",
    tax_amount: float = 0.0,
    items: Optional[List[Dict[str, Any]]] = None,
    payment_method: str = "Unknown",
    image_path: str = "",
    notes: str = "",
    tx_type: str = "Expense",
    db_path: str = DB_FILE
) -> int:
    """Add a new transaction to the database."""
    init_db(db_path)
    conn = get_connection(db_path)
    cursor = conn.cursor()

    items_str = json.dumps(items or [])
    created_at = datetime.now().isoformat()

    cursor.execute("""
        INSERT INTO transactions (
            date, merchant, category, total_amount, currency,
            tax_amount, items_json, payment_method, image_path, notes, tx_type, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        date or datetime.now().strftime("%Y-%m-%d"),
        merchant or "Unknown Merchant",
        category or "General",
        float(total_amount),
        currency or "$",
        float(tax_amount or 0.0),
        items_str,
        payment_method or "Unknown",
        image_path or "",
        notes or "",
        tx_type or "Expense",
        created_at
    ))

    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id


def add_manual_cash_entry(
    date: str,
    title: str,
    amount: float,
    category: str = "Cash",
    currency: str = "Rs.",
    payment_method: str = "Cash",
    notes: str = "",
    tx_type: str = "Expense",
    db_path: str = DB_FILE
) -> int:
    """Add a manual cash transaction entry with Expense or Credit type."""
    default_title = f"Cash {tx_type}" if not title else title
    return add_transaction(
        date=date or datetime.now().strftime("%Y-%m-%d"),
        merchant=default_title,
        category=category or "Cash",
        total_amount=float(amount),
        currency=currency or "$",
        tax_amount=0.0,
        items=[{"name": default_title, "qty": 1, "price": float(amount)}],
        payment_method=payment_method or "Cash",
        image_path="",
        notes=notes or f"Manual {tx_type}",
        tx_type=tx_type or "Expense",
        db_path=db_path
    )


def update_transaction(
    tx_id: int,
    date: str,
    merchant: str,
    category: str,
    total_amount: float,
    currency: str = "$",
    tax_amount: float = 0.0,
    payment_method: str = "Unknown",
    notes: str = "",
    tx_type: str = "Expense",
    db_path: str = DB_FILE
) -> bool:
    """Update existing transaction details."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE transactions
        SET date = ?, merchant = ?, category = ?, total_amount = ?,
            currency = ?, tax_amount = ?, payment_method = ?, notes = ?, tx_type = ?
        WHERE id = ?
    """, (
        date, merchant, category, float(total_amount),
        currency, float(tax_amount), payment_method, notes, tx_type or "Expense", tx_id
    ))

    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


def delete_transaction(tx_id: int, db_path: str = DB_FILE) -> bool:
    """Delete a transaction by ID."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


def clear_all_transactions(db_path: str = DB_FILE) -> None:
    """Clear all records from the database."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM transactions")
    conn.commit()
    conn.close()


def get_transaction(tx_id: int, db_path: str = DB_FILE) -> Optional[Dict[str, Any]]:
    """Retrieve a single transaction by ID."""
    init_db(db_path)
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transactions WHERE id = ?", (tx_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        d = dict(row)
        try:
            d["items"] = json.loads(d.get("items_json", "[]"))
        except Exception:
            d["items"] = []
        return d
    return None


def get_all_transactions(
    category: Optional[str] = None,
    search_query: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    tx_type: Optional[str] = None,
    sort_by: str = "date_desc",
    db_path: str = DB_FILE
) -> List[Dict[str, Any]]:
    """Retrieve all transactions with optional filtering and sorting."""
    init_db(db_path)
    conn = get_connection(db_path)
    cursor = conn.cursor()

    query = "SELECT * FROM transactions WHERE 1=1"
    params = []

    if category and category != "All":
        query += " AND category = ?"
        params.append(category)

    if tx_type and tx_type != "All":
        query += " AND tx_type = ?"
        params.append(tx_type)

    if search_query:
        query += " AND (merchant LIKE ? OR notes LIKE ? OR items_json LIKE ?)"
        term = f"%{search_query}%"
        params.extend([term, term, term])

    if date_from:
        query += " AND date >= ?"
        params.append(date_from)

    if date_to:
        query += " AND date <= ?"
        params.append(date_to)

    sort_map = {
        "date_desc": " ORDER BY date DESC, id DESC",
        "date_asc": " ORDER BY date ASC, id ASC",
        "amount_desc": " ORDER BY total_amount DESC",
        "amount_asc": " ORDER BY total_amount ASC",
        "merchant_asc": " ORDER BY merchant ASC"
    }
    query += sort_map.get(sort_by, " ORDER BY date DESC, id DESC")

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    results = []
    for r in rows:
        item = dict(r)
        try:
            item["items"] = json.loads(item.get("items_json", "[]"))
        except Exception:
            item["items"] = []
        results.append(item)
    return results


def get_stats(db_path: str = DB_FILE) -> Dict[str, Any]:
    """Calculate summary statistics, category breakdowns, and expense vs credit totals."""
    init_db(db_path)
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            COUNT(*) as count,
            COALESCE(SUM(total_amount), 0.0) as total_amount,
            COALESCE(SUM(CASE WHEN tx_type = 'Expense' THEN total_amount ELSE 0.0 END), 0.0) as total_expense,
            COALESCE(SUM(CASE WHEN tx_type = 'Credit' THEN total_amount ELSE 0.0 END), 0.0) as total_credit,
            COALESCE(SUM(CASE WHEN tx_type IN ('Slip', 'Receipt Slip') THEN total_amount ELSE 0.0 END), 0.0) as total_slips,
            COUNT(CASE WHEN tx_type IN ('Slip', 'Receipt Slip') THEN 1 END) as slips_count,
            COUNT(CASE WHEN tx_type = 'Credit' THEN 1 END) as credit_count,
            COUNT(CASE WHEN tx_type = 'Expense' THEN 1 END) as expense_count,
            COALESCE(SUM(CASE WHEN tx_type = 'Udhaar' THEN total_amount ELSE 0.0 END), 0.0) as total_udhaar,
            COUNT(CASE WHEN tx_type = 'Udhaar' THEN 1 END) as udhaar_count,
            COALESCE(AVG(total_amount), 0.0) as avg_spent,
            COALESCE(MAX(total_amount), 0.0) as max_spent,
            COALESCE(MIN(total_amount), 0.0) as min_spent
        FROM transactions
    """)
    overview = dict(cursor.fetchone())

    # Spending by category
    cursor.execute("""
        SELECT 
            category,
            COUNT(*) as count,
            COALESCE(SUM(total_amount), 0.0) as total
        FROM transactions
        GROUP BY category
        ORDER BY total DESC
    """)
    by_category = [dict(r) for r in cursor.fetchall()]

    # Spending by month (YYYY-MM)
    cursor.execute("""
        SELECT 
            SUBSTR(date, 1, 7) as month,
            COUNT(*) as count,
            COALESCE(SUM(total_amount), 0.0) as total
        FROM transactions
        GROUP BY month
        ORDER BY month DESC
        LIMIT 12
    """)
    by_month = [dict(r) for r in cursor.fetchall()]

    # Spending by payment method
    cursor.execute("""
        SELECT 
            payment_method,
            COUNT(*) as count,
            COALESCE(SUM(total_amount), 0.0) as total
        FROM transactions
        GROUP BY payment_method
        ORDER BY total DESC
    """)
    by_payment = [dict(r) for r in cursor.fetchall()]

    conn.close()

    total_exp = round(overview.get("total_expense", 0.0), 2)
    total_crd = round(overview.get("total_credit", 0.0), 2)
    total_slps = round(overview.get("total_slips", 0.0), 2)
    total_udh = round(overview.get("total_udhaar", 0.0), 2)
    net_bal = round(total_crd - total_exp, 2)

    return {
        "count": overview["count"],
        "total_spent": round(overview["total_amount"], 2),
        "total_expense": total_exp,
        "total_credit": total_crd,
        "total_slips": total_slps,
        "total_udhaar": total_udh,
        "slips_count": overview.get("slips_count", 0),
        "credit_count": overview.get("credit_count", 0),
        "expense_count": overview.get("expense_count", 0),
        "udhaar_count": overview.get("udhaar_count", 0),
        "net_balance": net_bal,
        "avg_spent": round(overview["avg_spent"], 2),
        "max_spent": round(overview["max_spent"], 2),
        "min_spent": round(overview["min_spent"], 2),
        "by_category": by_category,
        "by_month": by_month,
        "by_payment": by_payment
    }


def settle_udhaar_transaction(tx_id: int, settle_into: str = "Cash", settle_date: Optional[str] = None, db_path: str = DB_FILE) -> bool:
    """Settle an Udhaar transaction by converting/recording it as a settled Cash / Bank Credit."""
    init_db(db_path)
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transactions WHERE id = ?", (tx_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False

    t = dict(row)
    cust_name = t.get("merchant", "Customer")
    amt = t.get("total_amount", 0.0)
    curr = t.get("currency", "PKR")
    new_date = settle_date or datetime.now().strftime("%Y-%m-%d")

    cursor.execute("""
        INSERT INTO transactions (
            date, merchant, category, total_amount, currency, tax_amount, items_json, payment_method, image_path, notes, tx_type, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        new_date,
        cust_name,
        "Udhaar Recovery",
        amt,
        curr,
        0.0,
        "[]",
        settle_into,
        "",
        f"Udhaar Returned by {cust_name}",
        "Udhaar Recovery",
        datetime.now().isoformat()
    ))

    cursor.execute("""
        UPDATE transactions 
        SET notes = notes || ' [PAID on ' || ? || ']'
        WHERE id = ?
    """, (new_date, tx_id))

    conn.commit()
    conn.close()
    return True


def get_setting(key: str, default: str = "", db_path: str = DB_FILE) -> str:
    """Get a configuration setting."""
    init_db(db_path)
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key: str, value: str, db_path: str = DB_FILE) -> None:
    """Save a configuration setting."""
    init_db(db_path)
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO settings (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
    """, (key, str(value)))
    conn.commit()
    conn.close()


def get_admin_pin(db_path: str = DB_FILE) -> str:
    """Get the current security PIN (default: 6861)."""
    return get_setting("admin_pin", "6861", db_path=db_path)


def set_admin_pin(new_pin: str, db_path: str = DB_FILE) -> None:
    """Update the security PIN."""
    set_setting("admin_pin", str(new_pin).strip(), db_path=db_path)


def verify_admin_pin(input_pin: str, db_path: str = DB_FILE) -> bool:
    """Verify if the provided PIN matches the configured admin PIN."""
    current_pin = get_admin_pin(db_path=db_path)
    return str(input_pin).strip() == current_pin.strip()


def get_daily_closings(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sort_by: str = "date_desc",
    db_path: str = DB_FILE
) -> List[Dict[str, Any]]:
    """
    Retrieve aggregated financial closings grouped by Date.
    Returns daily manual credits, manual expenses, net balance, and scanned slips breakdown.
    """
    init_db(db_path)
    conn = get_connection(db_path)
    cursor = conn.cursor()

    query = """
        SELECT 
            date,
            COUNT(*) as count,
            COALESCE(SUM(CASE WHEN tx_type IN ('Credit', 'Udhaar Recovery') THEN total_amount ELSE 0.0 END), 0.0) as total_credit,
            COALESCE(SUM(CASE WHEN tx_type = 'Expense' THEN total_amount ELSE 0.0 END), 0.0) as total_expense,
            COALESCE(SUM(CASE WHEN tx_type = 'Udhaar' THEN total_amount ELSE 0.0 END), 0.0) as total_udhaar,
            COALESCE(SUM(CASE WHEN tx_type = 'Udhaar Recovery' OR category = 'Udhaar Recovery' THEN total_amount ELSE 0.0 END), 0.0) as total_udhaar_returned,
            COALESCE(SUM(CASE WHEN tx_type IN ('Slip', 'Receipt Slip') THEN total_amount ELSE 0.0 END), 0.0) as total_slips,
            COUNT(CASE WHEN tx_type IN ('Slip', 'Receipt Slip') THEN 1 END) as slips_count,
            COUNT(CASE WHEN tx_type = 'Credit' THEN 1 END) as credit_count,
            COUNT(CASE WHEN tx_type = 'Expense' THEN 1 END) as expense_count,
            COUNT(CASE WHEN tx_type = 'Udhaar' THEN 1 END) as udhaar_count,
            COUNT(CASE WHEN tx_type = 'Udhaar Recovery' OR category = 'Udhaar Recovery' THEN 1 END) as udhaar_returned_count,
            COALESCE(SUM(total_amount), 0.0) as total_amount,
            MAX(currency) as currency
        FROM transactions
        WHERE 1=1
    """
    params = []

    if date_from:
        query += " AND date >= ?"
        params.append(date_from)

    if date_to:
        query += " AND date <= ?"
        params.append(date_to)

    query += " GROUP BY date"

    if sort_by == "date_asc":
        query += " ORDER BY date ASC"
    elif sort_by == "amount_desc":
        query += " ORDER BY total_credit DESC, total_expense DESC"
    elif sort_by == "amount_asc":
        query += " ORDER BY total_credit ASC"
    elif sort_by == "count_desc":
        query += " ORDER BY count DESC"
    else:
        query += " ORDER BY date DESC"

    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]

    # Enrich each date with payment method and category breakdown
    for day in rows:
        d_val = day["date"]
        day["net_balance"] = round(day["total_credit"] - day["total_expense"], 2)

        # Payment method breakdown for this day
        cursor.execute("""
            SELECT payment_method, COUNT(*) as count, SUM(total_amount) as total
            FROM transactions
            WHERE date = ?
            GROUP BY payment_method
        """, (d_val,))
        day["payment_methods"] = [dict(p) for p in cursor.fetchall()]

        # Category breakdown for this day
        cursor.execute("""
            SELECT category, COUNT(*) as count, SUM(total_amount) as total
            FROM transactions
            WHERE date = ?
            GROUP BY category
            ORDER BY total DESC
        """, (d_val,))
        day["categories"] = [dict(c) for c in cursor.fetchall()]

    conn.close()
    return rows


def get_closing_summary_for_date(target_date: str, db_path: str = DB_FILE) -> Dict[str, Any]:
    """Retrieve full closing summary and transaction list for a specific date."""
    init_db(db_path)
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            COUNT(*) as count,
            COALESCE(SUM(CASE WHEN tx_type IN ('Credit', 'Udhaar Recovery') THEN total_amount ELSE 0.0 END), 0.0) as total_credit,
            COALESCE(SUM(CASE WHEN tx_type = 'Expense' THEN total_amount ELSE 0.0 END), 0.0) as total_expense,
            COALESCE(SUM(CASE WHEN tx_type = 'Udhaar' THEN total_amount ELSE 0.0 END), 0.0) as total_udhaar,
            COALESCE(SUM(CASE WHEN tx_type = 'Udhaar Recovery' OR category = 'Udhaar Recovery' THEN total_amount ELSE 0.0 END), 0.0) as total_udhaar_returned,
            COALESCE(SUM(CASE WHEN (tx_type IN ('Credit', 'Udhaar Recovery')) AND (payment_method LIKE '%Cash%' OR category LIKE '%Cash%') THEN total_amount ELSE 0.0 END), 0.0) as cash_credit,
            COALESCE(SUM(CASE WHEN (tx_type IN ('Credit', 'Udhaar Recovery')) AND (payment_method NOT LIKE '%Cash%' AND category NOT LIKE '%Cash%') THEN total_amount ELSE 0.0 END), 0.0) as bank_credit,
            COALESCE(SUM(CASE WHEN tx_type = 'Expense' AND (payment_method LIKE '%Cash%' OR payment_method NOT LIKE '%Bank%') THEN total_amount ELSE 0.0 END), 0.0) as expense_cash,
            COALESCE(SUM(CASE WHEN tx_type = 'Expense' AND (payment_method LIKE '%Bank%' OR payment_method LIKE '%Card%') THEN total_amount ELSE 0.0 END), 0.0) as expense_bank,
            COALESCE(SUM(CASE WHEN tx_type = 'Expense' AND (category IN ('Daily Expense', 'Petty Cash') OR notes LIKE '%daily%') THEN total_amount ELSE 0.0 END), 0.0) as daily_expense,
            COALESCE(SUM(CASE WHEN tx_type IN ('Slip', 'Receipt Slip') THEN total_amount ELSE 0.0 END), 0.0) as total_slips,
            COUNT(CASE WHEN tx_type IN ('Slip', 'Receipt Slip') THEN 1 END) as slips_count,
            COUNT(CASE WHEN tx_type = 'Credit' THEN 1 END) as credit_count,
            COUNT(CASE WHEN tx_type = 'Expense' THEN 1 END) as expense_count,
            COUNT(CASE WHEN tx_type = 'Udhaar' THEN 1 END) as udhaar_count,
            COUNT(CASE WHEN tx_type = 'Udhaar Recovery' OR category = 'Udhaar Recovery' THEN 1 END) as udhaar_returned_count,
            COALESCE(SUM(total_amount), 0.0) as total_amount
        FROM transactions
        WHERE date = ?
    """, (target_date,))
    summary = dict(cursor.fetchone())

    # Get transactions on this day
    cursor.execute("SELECT * FROM transactions WHERE date = ? ORDER BY id ASC", (target_date,))
    raw_txs = cursor.fetchall()
    txs = []
    for r in raw_txs:
        t = dict(r)
        try:
            t["items"] = json.loads(t.get("items_json", "[]"))
        except Exception:
            t["items"] = []
        txs.append(t)

    # Category breakdown
    cursor.execute("""
        SELECT category, COUNT(*) as count, SUM(total_amount) as total
        FROM transactions
        WHERE date = ?
        GROUP BY category
        ORDER BY total DESC
    """, (target_date,))
    categories = [dict(c) for c in cursor.fetchall()]

    # Payment methods
    cursor.execute("""
        SELECT payment_method, COUNT(*) as count, SUM(total_amount) as total
        FROM transactions
        WHERE date = ?
        GROUP BY payment_method
        ORDER BY total DESC
    """, (target_date,))
    payment_methods = [dict(p) for p in cursor.fetchall()]

    conn.close()

    return {
        "date": target_date,
        "count": summary["count"],
        "total_amount": round(summary["total_amount"], 2),
        "total_expense": round(summary.get("total_expense", 0.0), 2),
        "total_credit": round(summary.get("total_credit", 0.0), 2),
        "total_udhaar": round(summary.get("total_udhaar", 0.0), 2),
        "total_udhaar_returned": round(summary.get("total_udhaar_returned", 0.0), 2),
        "cash_credit": round(summary.get("cash_credit", 0.0), 2),
        "bank_credit": round(summary.get("bank_credit", 0.0), 2),
        "expense_cash": round(summary.get("expense_cash", 0.0), 2),
        "expense_bank": round(summary.get("expense_bank", 0.0), 2),
        "daily_expense": round(summary.get("daily_expense", 0.0), 2),
        "total_slips": round(summary.get("total_slips", 0.0), 2),
        "slips_count": summary.get("slips_count", 0),
        "credit_count": summary.get("credit_count", 0),
        "expense_count": summary.get("expense_count", 0),
        "udhaar_count": summary.get("udhaar_count", 0),
        "udhaar_returned_count": summary.get("udhaar_returned_count", 0),
        "transactions": txs,
        "categories": categories,
        "payment_methods": payment_methods
    }


def export_daily_closing_csv(target_date: str, filepath: str, db_path: str = DB_FILE) -> int:
    """Export daily closing report for a specific date to CSV."""
    day_data = get_closing_summary_for_date(target_date, db_path=db_path)
    txs = day_data.get("transactions", [])
    if not txs:
        return 0

    fieldnames = [
        "date", "tx_type", "merchant_reason", "category", "cash_amount", "bank_amount",
        "total_amount", "currency", "payment_method", "notes"
    ]

    with open(filepath, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for t in txs:
            amt = t.get("total_amount", 0.0)
            pm = t.get("payment_method", "Cash")
            is_cash = "Cash" in pm or "Cash" in t.get("category", "")
            writer.writerow({
                "date": t["date"],
                "tx_type": t.get("tx_type", "Expense"),
                "merchant_reason": t["merchant"],
                "category": t["category"],
                "cash_amount": amt if is_cash else "",
                "bank_amount": amt if not is_cash else "",
                "total_amount": amt,
                "currency": t.get("currency", "$"),
                "payment_method": pm,
                "notes": t.get("notes", "")
            })

    return len(txs)


def export_to_csv(filepath: str, db_path: str = DB_FILE) -> int:
    """Export all transactions to a CSV file sorted chronologically."""
    txs = get_all_transactions(sort_by="date_asc", db_path=db_path)
    if not txs:
        return 0

    fieldnames = [
        "id", "date", "tx_type", "merchant_reason", "category", "cash_amount", "bank_amount",
        "total_amount", "currency", "payment_method", "notes"
    ]

    with open(filepath, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for t in txs:
            amt = t.get("total_amount", 0.0)
            pm = t.get("payment_method", "Cash")
            is_cash = "Cash" in pm or "Cash" in t.get("category", "")
            writer.writerow({
                "id": t["id"],
                "date": t["date"],
                "tx_type": t.get("tx_type", "Expense"),
                "merchant_reason": t["merchant"],
                "category": t["category"],
                "cash_amount": amt if is_cash else "",
                "bank_amount": amt if not is_cash else "",
                "total_amount": amt,
                "currency": t.get("currency", "$"),
                "payment_method": pm,
                "notes": t.get("notes", "")
            })

    return len(txs)


def export_rion_template_csv(filepath: str, month_year: Optional[str] = None, db_path: str = DB_FILE) -> int:
    """
    Export closing data formatted exactly according to the Rion data.xlsx May sheet template:
    Row 1: Expense Detail Month of <Month-Year>
    Row 2: (empty)
    Row 3: DATE, CASH, BANK, TOTAL, EXPENSE BANK, REASON, EXPENSE CASH, DAILY EXPENSE, NET BALANCE
    ... data rows sorted chronologically by DATE ...
    Bottom row: Totals / Summary
    """
    init_db(db_path)
    conn = get_connection(db_path)
    cursor = conn.cursor()

    query = """
        SELECT DISTINCT date 
        FROM transactions 
        WHERE 1=1
    """
    params = []
    if month_year:
        query += " AND date LIKE ?"
        params.append(f"{month_year}%")

    query += " ORDER BY date ASC"
    cursor.execute(query, params)
    dates = [r[0] for r in cursor.fetchall()]

    if not dates:
        conn.close()
        return 0

    try:
        title_month = month_year if month_year else (datetime.strptime(dates[0], "%Y-%m-%d").strftime("%B-%Y") if dates else "ALL")
    except Exception:
        title_month = month_year or "CLOSING"

    rows_to_write = []
    tot_cash = 0.0
    tot_bank = 0.0
    tot_total = 0.0
    tot_exp_cash = 0.0
    tot_net = 0.0

    for d_val in dates:
        # 1. Cash Credit (Manual Cash In)
        cursor.execute("""
            SELECT COALESCE(SUM(total_amount), 0.0) 
            FROM transactions 
            WHERE date = ? AND tx_type = 'Credit' AND (payment_method LIKE '%Cash%' OR category LIKE '%Cash%')
        """, (d_val,))
        cash_crd = cursor.fetchone()[0] or 0.0

        # 2. Bank Credit (Bank Receipts In)
        cursor.execute("""
            SELECT COALESCE(SUM(total_amount), 0.0) 
            FROM transactions 
            WHERE date = ? AND tx_type = 'Credit' AND (payment_method NOT LIKE '%Cash%' AND category NOT LIKE '%Cash%')
        """, (d_val,))
        bank_crd = cursor.fetchone()[0] or 0.0

        day_total_crd = cash_crd + bank_crd

        # 3. Expense Cash (Manual Expenses)
        cursor.execute("""
            SELECT COALESCE(SUM(total_amount), 0.0) 
            FROM transactions 
            WHERE date = ? AND tx_type = 'Expense'
        """, (d_val,))
        exp_cash = cursor.fetchone()[0] or 0.0

        day_net = day_total_crd - exp_cash

        tot_cash += cash_crd
        tot_bank += bank_crd
        tot_total += day_total_crd
        tot_exp_cash += exp_cash
        tot_net += day_net

        rows_to_write.append([
            d_val,
            round(cash_crd, 2) if cash_crd else "",
            round(bank_crd, 2) if bank_crd else "",
            round(day_total_crd, 2) if day_total_crd else "",
            round(exp_cash, 2) if exp_cash else "",
            round(day_net, 2)
        ])

    conn.close()

    with open(filepath, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        # Row 1: Header title
        writer.writerow([f"Expense Detail Month of {title_month.upper()}"])
        # Row 2: Empty
        writer.writerow([])
        # Row 3: Column headers (Removed Reason, Daily Expense, Expense Bank)
        writer.writerow([
            "DATE", "CASH", "BANK", "TOTAL", "EXPENSE CASH", "NET BALANCE"
        ])
        # Data rows
        for r in rows_to_write:
            writer.writerow(r)
        # Summary Row
        writer.writerow([
            "TOTAL",
            round(tot_cash, 2),
            round(tot_bank, 2),
            round(tot_total, 2),
            round(tot_exp_cash, 2),
            round(tot_net, 2)
        ])

    return len(rows_to_write)


def get_khata_customers_summary(db_path: str = DB_FILE) -> Dict[str, Any]:
    """Retrieve aggregated customer credit (Khata) records grouped by client name."""
    init_db(db_path)
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Get customer info from customers table
    cursor.execute("SELECT name, phone, notes, created_at FROM customers")
    cust_info_map = {row["name"]: dict(row) for row in cursor.fetchall()}

    cursor.execute("""
        SELECT 
            merchant as customer_name,
            COUNT(*) as total_entries,
            COALESCE(SUM(CASE WHEN tx_type = 'Udhaar' THEN total_amount ELSE 0.0 END), 0.0) as total_given,
            COALESCE(SUM(CASE WHEN tx_type = 'Udhaar Recovery' OR category = 'Udhaar Recovery' THEN total_amount ELSE 0.0 END), 0.0) as total_returned,
            MAX(date) as last_date,
            MIN(date) as first_date
        FROM transactions
        WHERE tx_type IN ('Udhaar', 'Udhaar Recovery') OR category IN ('Customer Credit', 'Udhaar Recovery')
        GROUP BY merchant
        ORDER BY (SUM(CASE WHEN tx_type = 'Udhaar' THEN total_amount ELSE 0.0 END) - SUM(CASE WHEN tx_type = 'Udhaar Recovery' OR category = 'Udhaar Recovery' THEN total_amount ELSE 0.0 END)) DESC, merchant ASC
    """)
    rows = cursor.fetchall()
    clients = []
    overall_given = 0.0
    overall_returned = 0.0
    seen_names = set()

    for r in rows:
        c_name = r["customer_name"]
        seen_names.add(c_name)
        given = round(r["total_given"], 2)
        returned = round(r["total_returned"], 2)
        pending = round(given - returned, 2)
        overall_given += given
        overall_returned += returned

        info = cust_info_map.get(c_name, {})

        clients.append({
            "customer_name": c_name,
            "phone": info.get("phone", ""),
            "notes": info.get("notes", ""),
            "total_entries": r["total_entries"],
            "total_given": given,
            "total_returned": returned,
            "pending_balance": pending,
            "last_date": r["last_date"],
            "first_date": r["first_date"],
            "status": "Cleared" if pending <= 0 else "Pending"
        })

    # Include customers created in customers table who haven't had transactions yet
    for name, info in cust_info_map.items():
        if name not in seen_names:
            clients.append({
                "customer_name": name,
                "phone": info.get("phone", ""),
                "notes": info.get("notes", ""),
                "total_entries": 0,
                "total_given": 0.0,
                "total_returned": 0.0,
                "pending_balance": 0.0,
                "last_date": info.get("created_at", "")[:10],
                "first_date": info.get("created_at", "")[:10],
                "status": "Cleared"
            })

    conn.close()

    return {
        "total_clients": len(clients),
        "total_given": round(overall_given, 2),
        "total_returned": round(overall_returned, 2),
        "total_outstanding": round(overall_given - overall_returned, 2),
        "clients": clients
    }


def add_khata_customer(name: str, phone: str = "", initial_balance: float = 0.0, notes: str = "", date: str = "", db_path: str = DB_FILE) -> Dict[str, Any]:
    """Add a new customer to Khata directory, optionally with an initial Udhaar balance."""
    init_db(db_path)
    name = name.strip()
    if not name:
        raise ValueError("Customer name cannot be empty")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    target_date = date.strip() or datetime.now().strftime("%Y-%m-%d")

    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO customers (name, phone, notes, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            phone = CASE WHEN excluded.phone != '' THEN excluded.phone ELSE customers.phone END,
            notes = CASE WHEN excluded.notes != '' THEN excluded.notes ELSE customers.notes END
    """, (name, phone.strip(), notes.strip(), now))
    conn.commit()
    conn.close()

    if initial_balance > 0:
        add_transaction(
            date=target_date,
            merchant=name,
            category="Customer Credit",
            total_amount=initial_balance,
            currency="PKR",
            tax_amount=0.0,
            items=[],
            payment_method="Credit / Udhaar",
            notes=notes or "Opening Udhaar Balance",
            tx_type="Udhaar",
            db_path=db_path
        )

    return {"name": name, "phone": phone, "initial_balance": initial_balance, "notes": notes}


def update_khata_customer(old_name: str, new_name: str, phone: str = "", notes: str = "", db_path: str = DB_FILE) -> Dict[str, Any]:
    """Edit customer details and update all corresponding transactions in Khata."""
    init_db(db_path)
    old_name = old_name.strip()
    new_name = new_name.strip() or old_name
    if not old_name:
        raise ValueError("Original customer name is required")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Upsert or update customers table
    cursor.execute("SELECT id FROM customers WHERE name = ?", (old_name,))
    existing = cursor.fetchone()
    if existing:
        cursor.execute("UPDATE customers SET name = ?, phone = ?, notes = ? WHERE name = ?",
                       (new_name, phone.strip(), notes.strip(), old_name))
    else:
        cursor.execute("INSERT OR REPLACE INTO customers (name, phone, notes, created_at) VALUES (?, ?, ?, ?)",
                       (new_name, phone.strip(), notes.strip(), now))

    # Rename merchant in all transactions if name changed
    if old_name != new_name:
        cursor.execute("""
            UPDATE transactions
            SET merchant = ?
            WHERE merchant = ? AND (tx_type IN ('Udhaar', 'Udhaar Recovery') OR category IN ('Customer Credit', 'Udhaar Recovery'))
        """, (new_name, old_name))

    conn.commit()
    conn.close()
    return {"old_name": old_name, "new_name": new_name, "phone": phone, "notes": notes}


def delete_khata_customer(customer_name: str, delete_transactions: bool = False, db_path: str = DB_FILE) -> bool:
    """Delete customer from Khata table."""
    init_db(db_path)
    customer_name = customer_name.strip()
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM customers WHERE name = ?", (customer_name,))
    if delete_transactions:
        cursor.execute("DELETE FROM transactions WHERE merchant = ? AND (tx_type IN ('Udhaar', 'Udhaar Recovery') OR category IN ('Customer Credit', 'Udhaar Recovery'))", (customer_name,))
    conn.commit()
    conn.close()
    return True


def add_manual_udhaar_entry(customer_name: str, amount: float, date: str = "", notes: str = "", db_path: str = DB_FILE) -> int:
    """Add a direct Udhaar debit entry to a customer's Khata."""
    if amount <= 0:
        raise ValueError("Udhaar amount must be positive")
    target_date = date.strip() or datetime.now().strftime("%Y-%m-%d")
    return add_transaction(
        date=target_date,
        merchant=customer_name.strip(),
        category="Customer Credit",
        total_amount=amount,
        currency="PKR",
        tax_amount=0.0,
        items=[],
        payment_method="Credit / Udhaar",
        notes=notes or "Customer Udhaar",
        tx_type="Udhaar",
        db_path=db_path
    )


def get_customer_khata_history(customer_name: str, db_path: str = DB_FILE) -> List[Dict[str, Any]]:
    """Retrieve detailed ledger history for a specific customer."""
    init_db(db_path)
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM transactions
        WHERE merchant = ? AND (tx_type IN ('Udhaar', 'Udhaar Recovery') OR category IN ('Customer Credit', 'Udhaar Recovery'))
        ORDER BY date ASC, id ASC
    """, (customer_name,))
    raw_txs = cursor.fetchall()
    conn.close()

    history = []
    running_balance = 0.0
    for r in raw_txs:
        t = dict(r)
        amt = t["total_amount"]
        if t["tx_type"] == "Udhaar":
            running_balance += amt
        else:
            running_balance -= amt
        
        t["running_balance"] = round(running_balance, 2)
        history.append(t)

    return history


def get_monthly_closing_summary(target_month: Optional[str] = None, db_path: str = DB_FILE) -> Dict[str, Any]:
    """Retrieve full aggregated monthly closing statement, daily register, and expense breakdowns."""
    init_db(db_path)
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Find all distinct months available in DB
    cursor.execute("SELECT DISTINCT SUBSTR(date, 1, 7) as m FROM transactions ORDER BY m DESC")
    months = [r[0] for r in cursor.fetchall() if r[0] and len(r[0]) == 7 and r[0].startswith("20")]

    if not target_month or target_month not in months:
        target_month = months[0] if months else datetime.now().strftime("%Y-%m")

    # Days in this month
    cursor.execute("""
        SELECT DISTINCT date 
        FROM transactions 
        WHERE date LIKE ? 
        ORDER BY date ASC
    """, (f"{target_month}%",))
    dates = [r[0] for r in cursor.fetchall()]

    days_breakdown = []
    tot_cash_sales = 0.0
    tot_bank_slips = 0.0
    tot_udhaar_returned = 0.0
    tot_udhaar_given = 0.0
    tot_expense = 0.0

    for d_val in dates:
        # 1. Cash Credit
        cursor.execute("""
            SELECT COALESCE(SUM(total_amount), 0.0) 
            FROM transactions 
            WHERE date = ? AND tx_type = 'Credit' AND (payment_method LIKE '%Cash%' OR category LIKE '%Cash%')
        """, (d_val,))
        cash_sales = cursor.fetchone()[0] or 0.0

        # 2. Bank Credit
        cursor.execute("""
            SELECT COALESCE(SUM(total_amount), 0.0)
            FROM transactions 
            WHERE date = ? AND (tx_type = 'Credit' OR tx_type IN ('Slip', 'Receipt Slip')) AND (payment_method NOT LIKE '%Cash%' AND category NOT LIKE '%Cash%')
        """, (d_val,))
        bank_in = cursor.fetchone()[0] or 0.0

        # 3. Udhaar Returned (Recovery)
        cursor.execute("""
            SELECT COALESCE(SUM(total_amount), 0.0)
            FROM transactions 
            WHERE date = ? AND (tx_type = 'Udhaar Recovery' OR category = 'Udhaar Recovery')
        """, (d_val,))
        udh_ret = cursor.fetchone()[0] or 0.0

        # 4. Udhaar Given
        cursor.execute("""
            SELECT COALESCE(SUM(total_amount), 0.0)
            FROM transactions 
            WHERE date = ? AND tx_type = 'Udhaar'
        """, (d_val,))
        udh_given = cursor.fetchone()[0] or 0.0

        # 5. Expenses
        cursor.execute("""
            SELECT COALESCE(SUM(total_amount), 0.0)
            FROM transactions 
            WHERE date = ? AND tx_type = 'Expense'
        """, (d_val,))
        exp_val = cursor.fetchone()[0] or 0.0

        day_total_in = cash_sales + bank_in + udh_ret
        day_net = day_total_in - exp_val

        tot_cash_sales += cash_sales
        tot_bank_slips += bank_in
        tot_udhaar_returned += udh_ret
        tot_udhaar_given += udh_given
        tot_expense += exp_val

        days_breakdown.append({
            "date": d_val,
            "cash_sales": round(cash_sales, 2),
            "bank_slips": round(bank_in, 2),
            "udhaar_returned": round(udh_ret, 2),
            "udhaar_given": round(udh_given, 2),
            "total_in": round(day_total_in, 2),
            "expense": round(exp_val, 2),
            "net_balance": round(day_net, 2)
        })

    # Expense category breakdown for this month
    cursor.execute("""
        SELECT category, COUNT(*) as count, COALESCE(SUM(total_amount), 0.0) as total
        FROM transactions
        WHERE date LIKE ? AND tx_type = 'Expense'
        GROUP BY category
        ORDER BY total DESC
    """, (f"{target_month}%",))
    expense_categories = [dict(c) for c in cursor.fetchall()]

    conn.close()

    gross_rev = tot_cash_sales + tot_bank_slips + tot_udhaar_returned
    net_profit = gross_rev - tot_expense

    return {
        "month": target_month,
        "available_months": months,
        "total_days_recorded": len(dates),
        "tot_cash_sales": round(tot_cash_sales, 2),
        "tot_bank_slips": round(tot_bank_slips, 2),
        "tot_udhaar_returned": round(tot_udhaar_returned, 2),
        "tot_udhaar_given": round(tot_udhaar_given, 2),
        "gross_revenue": round(gross_rev, 2),
        "tot_expense": round(tot_expense, 2),
        "net_profit": round(net_profit, 2),
        "days": days_breakdown,
        "expense_categories": expense_categories
    }


# =============================================================================
# STAFF & SALARY MANAGEMENT
# =============================================================================
def add_staff(
    name: str,
    role: str = "Marker",
    phone: str = "",
    salary_type: str = "Monthly",
    base_salary: float = 0.0,
    hire_date: str = "",
    notes: str = "",
    db_path: str = DB_FILE
) -> int:
    """Add a new staff member (marker, manager, canteen staff). If hire_date is omitted, standard full salary applies."""
    init_db(db_path)
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO staff (name, role, phone, salary_type, base_salary, hire_date, status, notes, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'Active', ?, ?)
    """, (name.strip(), role.strip(), phone.strip(), salary_type, float(base_salary), (hire_date or "").strip(), notes.strip(), datetime.now().isoformat()))

    staff_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return staff_id


def update_staff(
    staff_id: int,
    name: str,
    role: str,
    phone: str,
    salary_type: str,
    base_salary: float,
    hire_date: str = "",
    status: str = "Active",
    notes: str = "",
    db_path: str = DB_FILE
) -> bool:
    """Update existing staff member details."""
    init_db(db_path)
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE staff
        SET name = ?, role = ?, phone = ?, salary_type = ?, base_salary = ?, hire_date = ?, status = ?, notes = ?
        WHERE id = ?
    """, (name.strip(), role.strip(), phone.strip(), salary_type, float(base_salary), (hire_date or "").strip(), status, notes.strip(), staff_id))

    affected = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return affected


def delete_staff(staff_id: int, db_path: str = DB_FILE) -> bool:
    """Delete a staff member."""
    init_db(db_path)
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM staff WHERE id = ?", (staff_id,))
    affected = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return affected


def get_all_staff(status: Optional[str] = None, db_path: str = DB_FILE) -> List[Dict[str, Any]]:
    """Retrieve list of staff members."""
    init_db(db_path)
    conn = get_connection(db_path)
    cursor = conn.cursor()

    if status:
        cursor.execute("SELECT * FROM staff WHERE status = ? ORDER BY id ASC", (status,))
    else:
        cursor.execute("SELECT * FROM staff ORDER BY id ASC")

    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def pay_staff_salary(
    staff_id: int,
    amount: float,
    pay_date: Optional[str] = None,
    payment_method: str = "Cash",
    notes: str = "",
    db_path: str = DB_FILE
) -> int:
    """Record a salary/wage/advance payout for a staff member and log as Expense in transactions."""
    init_db(db_path)
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM staff WHERE id = ?", (staff_id,))
    staff_row = cursor.fetchone()
    if not staff_row:
        conn.close()
        raise ValueError(f"Staff member #{staff_id} not found.")

    staff_name = staff_row["name"]
    role = staff_row["role"]
    curr = get_setting("currency", "PKR ", db_path=db_path)

    if not pay_date:
        pay_date = datetime.now().strftime("%Y-%m-%d")

    payout_note = f"Salary/Advance Paid to {staff_name} ({role})"
    if notes:
        payout_note += f" - {notes}"

    # Log into transactions table as Expense
    items_json = json.dumps([{"name": f"Salary payout ({staff_name})", "qty": 1, "price": amount}])
    cursor.execute("""
        INSERT INTO transactions (
            date, merchant, category, total_amount, currency, tax_amount, items_json, payment_method, image_path, notes, tx_type, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        pay_date,
        staff_name,
        "Staff & Marker Salary",
        amount,
        curr,
        0.0,
        items_json,
        payment_method,
        "",
        payout_note,
        "Expense",
        datetime.now().isoformat()
    ))

    tx_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return tx_id


def get_staff_salary_summary(target_month: Optional[str] = None, as_of_date: Optional[str] = None, db_path: str = DB_FILE) -> Dict[str, Any]:
    """Retrieve full staff directory with fresh earned salary as of today, projected month salary, amount paid this month, and pending balance."""
    init_db(db_path)
    conn = get_connection(db_path)
    cursor = conn.cursor()

    now = datetime.now()
    if not target_month:
        target_month = now.strftime("%Y-%m")
    if not as_of_date:
        as_of_date = now.strftime("%Y-%m-%d")

    import calendar
    try:
        y, m = map(int, target_month.split("-"))
        days_in_m = calendar.monthrange(y, m)[1]
    except Exception:
        y, m = now.year, now.month
        days_in_m = 30

    current_month_str = now.strftime("%Y-%m")
    if target_month == current_month_str:
        current_day = now.day
    elif target_month < current_month_str:
        current_day = days_in_m  # Past month: full month completed
    else:
        current_day = 0          # Future month: 0 days elapsed

    cursor.execute("SELECT * FROM staff ORDER BY status ASC, role ASC, name ASC")
    staff_rows = [dict(r) for r in cursor.fetchall()]

    staff_summary = []
    tot_projected_payroll = 0.0
    tot_earned_to_date = 0.0
    tot_paid_month = 0.0

    for s in staff_rows:
        s_name = s["name"]
        base = s["base_salary"] or 0.0
        
        # Calculate all salary payouts in this month for this staff member
        cursor.execute("""
            SELECT COALESCE(SUM(total_amount), 0.0), COUNT(*)
            FROM transactions
            WHERE date LIKE ? 
              AND tx_type = 'Expense' 
              AND (category LIKE '%Salary%' OR category LIKE '%Staff%' OR category LIKE '%Marker%')
              AND merchant = ?
        """, (f"{target_month}%", s_name))
        
        p_row = cursor.fetchone()
        paid_month = p_row[0] or 0.0
        payout_count = p_row[1] or 0

        daily_rate = round(base / 30.0, 2)
        target_security = round((base / 30.0) * 10.0, 2)  # 10 days target security

        hire_date = s.get("hire_date", "") or ""
        effective_salary = base
        is_prorated = False
        projected_days_worked = 30
        days_worked_to_date = min(30, current_day)

        # If staff has optional joining date and joined during this target month
        if hire_date and hire_date.startswith(target_month) and s["salary_type"] == "Monthly":
            try:
                h_day = int(hire_date.split("-")[2])
                if h_day > 1:
                    projected_days_worked = max(1, days_in_m - h_day + 1)
                    effective_salary = round(projected_days_worked * daily_rate, 2)
                    is_prorated = True

                # Calculate fresh days worked up to today
                if h_day <= current_day:
                    days_worked_to_date = max(1, current_day - h_day + 1)
                else:
                    days_worked_to_date = 0
            except Exception:
                pass
        elif s["salary_type"] != "Monthly":
            effective_salary = round(current_day * daily_rate, 2)
            days_worked_to_date = current_day

        # Earned fresh salary as of today
        earned_to_date = round(days_worked_to_date * daily_rate, 2)

        # Security is automatically withheld as the person works their first 10 days
        security_days_today = min(days_worked_to_date, 10)
        security_held_today = round(security_days_today * daily_rate, 2)

        security_days_projected = min(projected_days_worked, 10)
        security_held_projected = round(security_days_projected * daily_rate, 2)

        fresh_due_as_of_today = max(0.0, earned_to_date - paid_month)

        # Net cash payable on 10th (after retaining security hold)
        net_payable_10th = round(max(0.0, effective_salary - security_held_projected), 2)
        pending_due = max(0.0, effective_salary - paid_month) if s["salary_type"] == "Monthly" else 0.0

        if s["status"] == "Active":
            tot_projected_payroll += effective_salary
            tot_earned_to_date += earned_to_date
            tot_paid_month += paid_month

        staff_summary.append({
            "id": s["id"],
            "name": s_name,
            "role": s["role"],
            "phone": s["phone"],
            "salary_type": s["salary_type"],
            "base_salary": round(base, 2),
            "effective_salary": round(effective_salary, 2),
            "earned_to_date": round(earned_to_date, 2),
            "fresh_due_today": round(fresh_due_as_of_today, 2),
            "days_worked_to_date": days_worked_to_date,
            "projected_days_worked": projected_days_worked,
            "is_prorated": is_prorated,
            "daily_wage": daily_rate,
            "target_security": target_security,
            "security_days_held": security_days_today,
            "security_held": security_held_today,
            "security_held_projected": security_held_projected,
            "net_payable_10th": net_payable_10th,
            "paid_this_month": round(paid_month, 2),
            "balance_due": round(pending_due, 2),
            "payout_count": payout_count,
            "status": s["status"],
            "hire_date": hire_date,
            "leave_date": s.get("leave_date", ""),
            "settlement_amount": s.get("settlement_amount", 0.0),
            "security_refunded": s.get("security_refunded", 0.0),
            "notes": s["notes"]
        })

    conn.close()

    tot_remaining = max(0.0, tot_projected_payroll - tot_paid_month)
    tot_security_held = sum(s["security_held"] for s in staff_summary if s["status"] == "Active")

    return {
        "month": target_month,
        "as_of_date": as_of_date,
        "current_day": current_day,
        "pay_cycle_day": "10th of every month",
        "security_policy": "Security is automatically withheld from first 10 days of work",
        "total_staff": len([s for s in staff_summary if s["status"] == "Active"]),
        "total_payroll": round(tot_projected_payroll, 2),
        "total_earned_to_date": round(tot_earned_to_date, 2),
        "total_security_held": round(tot_security_held, 2),
        "total_paid_month": round(tot_paid_month, 2),
        "total_remaining_due": round(tot_remaining, 2),
        "staff": staff_summary
    }


def get_staff_payout_history(staff_name: str, db_path: str = DB_FILE) -> List[Dict[str, Any]]:
    """Retrieve complete chronological salary and advance payout history for a staff member."""
    init_db(db_path)
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM transactions
        WHERE merchant = ?
          AND tx_type = 'Expense'
          AND (category LIKE '%Salary%' OR category LIKE '%Staff%' OR category LIKE '%Marker%' OR category LIKE '%Settlement%')
        ORDER BY date DESC, id DESC
    """, (staff_name,))

    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def calculate_staff_settlement(
    staff_id: int,
    leave_date: str,
    refund_security: bool = True,
    deductions: float = 0.0,
    db_path: str = DB_FILE
) -> Dict[str, Any]:
    """Calculate exact final settlement for a resigning/leaving staff member including 10 days security hold."""
    init_db(db_path)
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM staff WHERE id = ?", (staff_id,))
    staff = cursor.fetchone()
    if not staff:
        conn.close()
        raise ValueError(f"Staff member #{staff_id} not found.")

    base = staff["base_salary"] or 0.0
    daily_rate = round(base / 30.0, 2)
    security_deposit = round((base / 30.0) * 10.0, 2)

    # Parse leave date
    if not leave_date:
        leave_date = datetime.now().strftime("%Y-%m-%d")

    try:
        leave_parts = leave_date.split("-")
        leave_day = int(leave_parts[2])
        leave_month_str = f"{leave_parts[0]}-{leave_parts[1]}"
    except Exception:
        leave_day = datetime.now().day
        leave_month_str = datetime.now().strftime("%Y-%m")

    hire_date = staff["hire_date"] or ""
    days_worked = leave_day

    # If joined in the same month as leaving
    if hire_date and hire_date.startswith(leave_month_str):
        try:
            hire_day = int(hire_date.split("-")[2])
            days_worked = max(1, leave_day - hire_day + 1)
        except Exception:
            pass
        security_days_held = min(days_worked, 10)
    else:
        security_days_held = 10  # Full security held from previous months

    security_deposit = round(security_days_held * daily_rate, 2)
    earned_salary = round(days_worked * daily_rate, 2)

    # Already paid in final month
    cursor.execute("""
        SELECT COALESCE(SUM(total_amount), 0.0)
        FROM transactions
        WHERE date LIKE ? AND tx_type = 'Expense' AND merchant = ?
          AND (category LIKE '%Salary%' OR category LIKE '%Staff%' OR category LIKE '%Marker%')
    """, (f"{leave_month_str}%", staff["name"]))
    already_paid = cursor.fetchone()[0] or 0.0
    conn.close()

    sec_refund = max(0.0, security_deposit - float(deductions)) if refund_security else 0.0
    net_settlement = max(0.0, earned_salary + sec_refund - already_paid)

    return {
        "staff_id": staff_id,
        "name": staff["name"],
        "role": staff["role"],
        "hire_date": hire_date,
        "leave_date": leave_date,
        "base_salary": round(base, 2),
        "daily_rate": daily_rate,
        "days_worked_in_final_month": days_worked,
        "earned_salary": earned_salary,
        "security_deposit_held": security_deposit,
        "security_days_held": security_days_held,
        "refund_security": refund_security,
        "security_refund_amount": round(sec_refund, 2),
        "deductions": round(float(deductions), 2),
        "already_paid_in_month": round(already_paid, 2),
        "net_settlement_payable": round(net_settlement, 2)
    }


def settle_resigned_staff(
    staff_id: int,
    leave_date: str,
    final_amount: float,
    refund_security: bool = True,
    deductions: float = 0.0,
    payment_method: str = "Cash",
    notes: str = "",
    pay_now: bool = True,
    db_path: str = DB_FILE
) -> Dict[str, Any]:
    """Mark staff member as Resigned/Left, record leave date, and log final settlement payout expense."""
    init_db(db_path)
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM staff WHERE id = ?", (staff_id,))
    staff = cursor.fetchone()
    if not staff:
        conn.close()
        raise ValueError(f"Staff member #{staff_id} not found.")

    staff_name = staff["name"]
    role = staff["role"]
    base = staff["base_salary"] or 0.0
    security_held = round((base / 30.0) * 10.0, 2)
    sec_refunded = max(0.0, security_held - float(deductions)) if refund_security else 0.0

    if not leave_date:
        leave_date = datetime.now().strftime("%Y-%m-%d")

    # Update staff status to Resigned
    cursor.execute("""
        UPDATE staff
        SET status = 'Resigned',
            leave_date = ?,
            settlement_amount = ?,
            security_refunded = ?,
            notes = ?
        WHERE id = ?
    """, (
        leave_date,
        float(final_amount),
        float(sec_refunded),
        f"Resigned on {leave_date}. Final settlement: PKR {final_amount:,.2f}. {notes}".strip(),
        staff_id
    ))

    tx_id = None
    curr = get_setting("currency", "PKR ", db_path=db_path)

    # If paying settlement amount now, log Expense transaction
    if pay_now and final_amount > 0:
        payout_note = f"Final Resignation Settlement & Security Refund for {staff_name} ({role}) - Left on {leave_date}"
        if notes:
            payout_note += f" - {notes}"

        items_json = json.dumps([{
            "name": f"Final Settlement (Left on {leave_date})",
            "qty": 1,
            "price": float(final_amount)
        }])

        cursor.execute("""
            INSERT INTO transactions (
                date, merchant, category, total_amount, currency, tax_amount, items_json, payment_method, image_path, notes, tx_type, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            leave_date,
            staff_name,
            "Staff & Marker Salary",
            float(final_amount),
            curr,
            0.0,
            items_json,
            payment_method,
            "",
            payout_note,
            "Expense",
            datetime.now().isoformat()
        ))
        tx_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return {
        "success": True,
        "staff_id": staff_id,
        "name": staff_name,
        "leave_date": leave_date,
        "final_settlement_paid": float(final_amount),
        "security_refunded": float(sec_refunded),
        "transaction_id": tx_id,
        "message": f"Successfully processed resignation and settlement for {staff_name}."
    }


def reopen_resigned_staff(staff_id: int, db_path: str = DB_FILE) -> bool:
    """Reactivate a resigned staff member back to Active status."""
    init_db(db_path)
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE staff
        SET status = 'Active', leave_date = ''
        WHERE id = ?
    """, (staff_id,))
    affected = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return affected
