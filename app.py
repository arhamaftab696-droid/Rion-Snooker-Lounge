"""
app.py - Native macOS Desktop Application for Local Transaction Scanner & AI Analyzer
Built with CustomTkinter for a modern macOS native dark/light interface.
"""

import os
import sys
import time
import threading
import concurrent.futures
import json
import shutil
import subprocess
import calendar
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import customtkinter as ctk

import socket
import webbrowser

# Local modules
import db
import extractor

# Set CustomTkinter appearance
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

APP_DIR = os.path.dirname(os.path.abspath(__file__))
RECEIPTS_DIR = os.path.join(APP_DIR, "receipt_images")
os.makedirs(RECEIPTS_DIR, exist_ok=True)


def get_local_ip() -> str:
    """Get local Wi-Fi / LAN IP address for phone connection."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def is_port_in_use(port: int = 8000) -> bool:
    """Check if web server port is already listening."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def ensure_web_server_running():
    """Starts FastAPI web server in background thread if not already running."""
    if not is_port_in_use(8000):
        try:
            import uvicorn
            from server import app as web_app
            def run_srv():
                uvicorn.run(web_app, host="0.0.0.0", port=8000, log_level="warning")
            t = threading.Thread(target=run_srv, daemon=True)
            t.start()
        except Exception as e:
            print("Background web server launch error:", e)


class CalendarDialog(ctk.CTkToplevel):
    """Interactive visual calendar modal for choosing closing dates."""
    def __init__(self, parent, initial_date=None, on_select=None, title="Select Closing Date"):
        super().__init__(parent)
        self.title(title)
        self.geometry("360x420")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.on_select = on_select

        if initial_date:
            try:
                parts = initial_date.split("-")
                self.year = int(parts[0])
                self.month = int(parts[1])
                self.selected_day = int(parts[2])
            except Exception:
                now = datetime.now()
                self.year, self.month, self.selected_day = now.year, now.month, now.day
        else:
            now = datetime.now()
            self.year, self.month, self.selected_day = now.year, now.month, now.day

        self._build_ui()

    def _build_ui(self):
        top_f = ctk.CTkFrame(self, fg_color="transparent")
        top_f.pack(fill="x", padx=16, pady=(16, 8))
        top_f.grid_columnconfigure(1, weight=1)

        prev_btn = ctk.CTkButton(top_f, text="◀", width=36, height=32, command=self._prev_month, font=ctk.CTkFont(weight="bold"))
        prev_btn.grid(row=0, column=0, sticky="w")

        self.month_label = ctk.CTkLabel(top_f, text="", font=ctk.CTkFont(size=16, weight="bold"))
        self.month_label.grid(row=0, column=1, sticky="nsew")

        next_btn = ctk.CTkButton(top_f, text="▶", width=36, height=32, command=self._next_month, font=ctk.CTkFont(weight="bold"))
        next_btn.grid(row=0, column=2, sticky="e")

        days_f = ctk.CTkFrame(self, fg_color="transparent")
        days_f.pack(fill="x", padx=16, pady=(4, 4))
        for i, d in enumerate(["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]):
            days_f.grid_columnconfigure(i, weight=1)
            lbl = ctk.CTkLabel(days_f, text=d, font=ctk.CTkFont(size=12, weight="bold"), text_color="gray60")
            lbl.grid(row=0, column=i)

        self.grid_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.grid_frame.pack(fill="both", expand=True, padx=16, pady=4)
        for i in range(7):
            self.grid_frame.grid_columnconfigure(i, weight=1)

        bot_f = ctk.CTkFrame(self, fg_color="transparent")
        bot_f.pack(fill="x", padx=16, pady=(6, 16))

        today_btn = ctk.CTkButton(bot_f, text="Today", height=32, font=ctk.CTkFont(size=12, weight="bold"), command=self._select_today)
        today_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))

        close_btn = ctk.CTkButton(bot_f, text="Cancel", height=32, fg_color="gray40", hover_color="gray30", command=self.destroy)
        close_btn.pack(side="right", fill="x", expand=True, padx=(6, 0))

        self._render_calendar()

  
    def _render_calendar(self):
        month_name = calendar.month_name[self.month]
        self.month_label.configure(text=f"{month_name} {self.year}")

        for w in self.grid_frame.winfo_children():
            w.destroy()

        first_weekday, num_days = calendar.monthrange(self.year, self.month)
        today = datetime.now()

        row = 0
        col = first_weekday

        for day in range(1, num_days + 1):
            is_today = (today.year == self.year and today.month == self.month and today.day == day)
            is_selected = (self.selected_day == day)

            btn_color = "#3b82f6" if is_selected else (("gray80", "gray25") if not is_today else ("#10b981", "#059669"))

            btn = ctk.CTkButton(
                self.grid_frame,
                text=str(day),
                width=36,
                height=32,
                fg_color=btn_color,
                font=ctk.CTkFont(size=12),
                command=lambda d=day: self._on_day_clicked(d)
            )
            btn.grid(row=row, column=col, padx=2, pady=2, sticky="nsew")

            col += 1
            if col > 6:
                col = 0
                row += 1

    def _prev_month(self):
        self.month -= 1
        if self.month < 1:
            self.month = 12
            self.year -= 1
        self._render_calendar()

    def _next_month(self):
        self.month += 1
        if self.month > 12:
            self.month = 1
            self.year += 1
        self._render_calendar()

    def _select_today(self):
        now = datetime.now()
        formatted = now.strftime("%Y-%m-%d")
        if self.on_select:
            self.on_select(formatted)
        self.destroy()

    def _on_day_clicked(self, day: int):
        selected_date = f"{self.year:04d}-{self.month:02d}-{day:02d}"
        if self.on_select:
            self.on_select(selected_date)
        self.destroy()


class CashEntryDialog(ctk.CTkToplevel):
    """Modal dialog to manually enter cash transactions / drawer closing amounts."""
    def __init__(self, parent, initial_date=None, on_saved=None, title="Record Manual Cash Amount"):
        super().__init__(parent)
        self.title(title)
        self.geometry("450x540")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.parent_app = parent
        self.on_saved = on_saved
        self.initial_date = initial_date or datetime.now().strftime("%Y-%m-%d")
        self.currency = db.get_setting("currency", "PKR ")

        self._build_ui()

    def _build_ui(self):
        # Header
        top_f = ctk.CTkFrame(self, fg_color="transparent")
        top_f.pack(fill="x", padx=20, pady=(18, 12))
        
        ctk.CTkLabel(top_f, text="💵 Record Manual Cash Amount", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(top_f, text="Enter manual cash receipts, counter sales, or petty cash expenses.", font=ctk.CTkFont(size=12), text_color="gray60").pack(anchor="w", pady=(2, 0))

        form = ctk.CTkFrame(self, corner_radius=10)
        form.pack(fill="both", expand=True, padx=20, pady=(0, 14))

        # 1. Closing Date Row
        ctk.CTkLabel(form, text="Closing Date:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=16, pady=(10, 2))
        
        d_row = ctk.CTkFrame(form, fg_color="transparent")
        d_row.pack(fill="x", padx=16, pady=(0, 6))
        d_row.grid_columnconfigure(0, weight=1)

        self.date_entry = ctk.CTkEntry(d_row, height=34, font=ctk.CTkFont(size=13, weight="bold"))
        self.date_entry.insert(0, self.initial_date)
        self.date_entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        cal_btn = ctk.CTkButton(d_row, text="🗓️ Calendar", width=90, height=34, command=self._pick_date)
        cal_btn.grid(row=0, column=1, padx=(0, 4))

        today_btn = ctk.CTkButton(d_row, text="Today", width=55, height=34, fg_color=("gray75", "gray30"), text_color=("gray10", "gray90"), command=lambda: self._set_date(datetime.now().strftime("%Y-%m-%d")))
        today_btn.grid(row=0, column=2)

        # 2. Type Selector: Expense vs Credit vs Udhaar Given vs Udhaar Returned
        ctk.CTkLabel(form, text="Transaction Type: *", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=16, pady=(4, 2))
        self.type_segmented = ctk.CTkSegmentedButton(
            form,
            values=["🔴 Expense", "🟢 Cash In", "🔵 Udhaar Given", "🟣 Udhaar Returned"],
            selected_color=("#0284c7", "#0284c7"),
            command=self._on_type_changed,
            height=34
        )
        self.type_segmented.set("🔴 Expense")
        self.type_segmented.pack(fill="x", padx=16, pady=(0, 6))

        # Slide-Down Customer Selection Dropdown (For Udhaar)
        self.customer_frame = ctk.CTkFrame(form, fg_color=("gray85", "gray20"), corner_radius=8)
        
        c_lbl = ctk.CTkLabel(self.customer_frame, text="👤 Select Customer from List:", font=ctk.CTkFont(size=12, weight="bold"), text_color=("#4f46e5", "#818cf8"))
        c_lbl.pack(anchor="w", padx=12, pady=(8, 2))

        # Get customers from db
        cust_summary = db.get_khata_customers_summary()
        self.customer_names = [c["customer_name"] for c in cust_summary.get("clients", [])]
        combo_vals = ["-- Select Customer from List --"] + self.customer_names + ["➕ Enter New Customer..."]

        self.customer_combo = ctk.CTkComboBox(
            self.customer_frame,
            values=combo_vals,
            command=self._on_customer_selected,
            height=34,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.customer_combo.set("-- Select Customer from List --")
        self.customer_combo.pack(fill="x", padx=12, pady=(0, 8))

        # 3. Cash Amount (Prominent)
        ctk.CTkLabel(form, text=f"Amount ({self.currency}): *", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=16, pady=(4, 2))
        self.amount_entry = ctk.CTkEntry(form, height=38, font=ctk.CTkFont(size=17, weight="bold"), placeholder_text="0.00")
        self.amount_entry.pack(fill="x", padx=16, pady=(0, 6))
        self.amount_entry.focus_set()

        # 4. Description / Title / Customer Name
        self.desc_label = ctk.CTkLabel(form, text="Description / Reason:", font=ctk.CTkFont(size=12, weight="bold"))
        self.desc_label.pack(anchor="w", padx=16, pady=(4, 2))
        self.desc_entry = ctk.CTkEntry(form, height=32, placeholder_text="e.g. Marker Salary, Generator Diesel")
        self.desc_entry.pack(fill="x", padx=16, pady=(0, 6))

        # 5. Category & Payment Method Split
        split_row = ctk.CTkFrame(form, fg_color="transparent")
        split_row.pack(fill="x", padx=16, pady=(0, 6))
        split_row.grid_columnconfigure(0, weight=1)
        split_row.grid_columnconfigure(1, weight=1)

        # Category
        c_f = ctk.CTkFrame(split_row, fg_color="transparent")
        c_f.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkLabel(c_f, text="Category:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(0, 2))
        self.cat_menu = ctk.CTkOptionMenu(
            c_f,
            values=["Table Play", "Canteen & Cafe", "Snooker Accessories", "Counter Cash", "Marker & Staff Salary", "Electricity & AC Fuel", "Table Cloth & Repair", "Member Udhaar", "Udhaar Recovery", "Daily Expense", "Other"],
            height=32
        )
        self.cat_menu.set("Daily Expense")
        self.cat_menu.pack(fill="x")

        # Payment Method
        p_f = ctk.CTkFrame(split_row, fg_color="transparent")
        p_f.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        ctk.CTkLabel(p_f, text="Payment Type:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(0, 2))
        self.pay_menu = ctk.CTkOptionMenu(
            p_f,
            values=["Cash", "Bank", "Udhaar", "Cash in Hand", "Counter Cash", "Petty Cash", "Cash Deposit"],
            height=32
        )
        self.pay_menu.set("Cash")
        self.pay_menu.pack(fill="x")

        # 6. Notes
        ctk.CTkLabel(form, text="Notes (Optional):", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=16, pady=(2, 2))
        self.notes_entry = ctk.CTkEntry(form, height=30, placeholder_text="e.g. Will pay next Friday / Verified by cashier")
        self.notes_entry.pack(fill="x", padx=16, pady=(0, 10))

        # Bottom Action Buttons
        bot_f = ctk.CTkFrame(self, fg_color="transparent")
        bot_f.pack(fill="x", padx=20, pady=(0, 18))

        save_btn = ctk.CTkButton(
            bot_f,
            text="💾 Save Entry",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=38,
            fg_color="#10b981",
            hover_color="#059669",
            command=self._save_entry
        )
        save_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        cancel_btn = ctk.CTkButton(
            bot_f,
            text="Cancel",
            height=38,
            fg_color="gray40",
            hover_color="gray30",
            command=self.destroy
        )
        cancel_btn.pack(side="right", width=90)

        # Bind Return key to save
        self.amount_entry.bind("<Return>", lambda e: self._save_entry())
        self.desc_entry.bind("<Return>", lambda e: self._save_entry())

    def _on_type_changed(self, value):
        if "Udhaar" in value:
            self.customer_frame.pack(fill="x", padx=16, pady=(0, 6), before=self.desc_label)
            self.desc_label.configure(text="👤 Customer Name / Note:")
            if not self.desc_entry.get().strip() or self.desc_entry.get().strip() in ["Cash Collection", "Daily Expense", "Table Play"]:
                self.desc_entry.delete(0, "end")
            self.desc_entry.configure(placeholder_text="Customer Name (e.g. Chatta, Hamza, Moez)")
            if "Returned" in value:
                self.cat_menu.set("Udhaar Recovery")
                self.pay_menu.set("Cash")
            else:
                self.cat_menu.set("Member Udhaar")
                self.pay_menu.set("Udhaar")
        else:
            self.customer_frame.pack_forget()
            self.desc_label.configure(text="Description / Reason:")
            if "Expense" in value:
                self.cat_menu.set("Daily Expense")
                self.pay_menu.set("Cash")
                self.desc_entry.configure(placeholder_text="Reason (e.g. Marker Salary, Generator Diesel)")
            elif "Credit" in value or "Cash In" in value:
                self.cat_menu.set("Table Play")
                self.pay_menu.set("Cash")
                self.desc_entry.configure(placeholder_text="Counter Sales / Frame Collection")

    def _on_customer_selected(self, choice):
        if choice == "➕ Enter New Customer..." or choice == "-- Select Customer from List --":
            self.desc_entry.delete(0, "end")
            self.desc_entry.focus_set()
        elif choice:
            self.desc_entry.delete(0, "end")
            self.desc_entry.insert(0, choice)

    def _pick_date(self):
        cur = self.date_entry.get().strip() or datetime.now().strftime("%Y-%m-%d")
        CalendarDialog(self, initial_date=cur, on_select=self._set_date, title="Pick Date for Cash Entry")

    def _set_date(self, d_str: str):
        self.date_entry.delete(0, "end")
        self.date_entry.insert(0, d_str)

    def _save_entry(self):
        raw_amt = self.amount_entry.get().strip()
        if not raw_amt:
            messagebox.showwarning("Validation Error", "Please enter a valid amount.")
            return

        try:
            amt = float(raw_amt.replace(",", ""))
            if amt <= 0:
                raise ValueError("Amount must be positive.")
        except ValueError:
            messagebox.showwarning("Validation Error", "Amount must be a positive number.")
            return

        date_val = self.date_entry.get().strip() or datetime.now().strftime("%Y-%m-%d")
        desc_val = self.desc_entry.get().strip() or "Entry"
        cat_val = self.cat_menu.get()
        pay_val = self.pay_menu.get()
        notes_val = self.notes_entry.get().strip()
        
        sel_type = self.type_segmented.get()
        if "Returned" in sel_type:
            type_str = "Udhaar Recovery"
            cat_val = "Udhaar Recovery"
            desc_val = desc_val
            notes_val = f"Udhaar Returned by {desc_val}"
        elif "Udhaar" in sel_type:
            type_str = "Udhaar"
            pay_val = "Udhaar"
            cat_val = "Customer Credit"
        elif "Credit" in sel_type or "Cash In" in sel_type:
            type_str = "Credit"
        else:
            type_str = "Expense"

        db.add_manual_cash_entry(
            date=date_val,
            title=desc_val,
            amount=amt,
            category=cat_val,
            currency=self.currency,
            payment_method=pay_val,
            notes=notes_val,
            tx_type=type_str
        )

        if self.on_saved:
            self.on_saved(date_val)

        self.destroy()


class TransactionApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window configuration
        self.title("🎱 Rion Snooker Lounge - Management & Closing System")
        self.geometry("1100x720")
        self.minsize(950, 620)

        # Initialize local database
        db.init_db()

        # Load initial settings
        self.api_key = db.get_setting("gemini_api_key", "")
        self.currency = db.get_setting("currency", "PKR ")
        self.model_name = db.get_setting("model_name", extractor.DEFAULT_MODEL)
        theme_setting = db.get_setting("theme", "Dark")
        ctk.set_appearance_mode(theme_setting)

        # State variables
        self.current_tab = "dashboard"
        self.batch_queue: List[Dict[str, Any]] = []
        self.is_scanning = False

        # Ensure integrated Web Server is running for real-time web & mobile sync
        ensure_web_server_running()

        # Main Layout (Sidebar + Main Content Area)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_content_frames()

        # Default to Dashboard view
        self._show_tab("dashboard")

    # =========================================================================
    # SIDEBAR
    # =========================================================================
    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(9, weight=1)

        # App Brand / Title
        self.logo_label = ctk.CTkLabel(
            self.sidebar,
            text="🎱 Rion Snooker",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(24, 6), sticky="w")

        self.sub_label = ctk.CTkLabel(
            self.sidebar,
            text="Lounge Management System",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#10b981"
        )
        self.sub_label.grid(row=1, column=0, padx=20, pady=(0, 16), sticky="w")

        # Navigation Buttons
        self.nav_buttons = {}
        nav_items = [
            ("dashboard", "📊  Dashboard"),
            ("closing", "📅  Daily Closing"),
            ("monthly", "🗓️  Monthly Closing"),
            ("khata", "👥  Customer Khata"),
            ("staff", "👨‍💼  Staff & Salaries"),
            ("upload", "📸  Scan Receipts"),
            ("transactions", "📋  Transactions"),
            ("chat", "💬  Ask AI Assistant"),
            ("settings", "⚙️  Settings"),
        ]

        for idx, (tab_id, label) in enumerate(nav_items, start=2):
            btn = ctk.CTkButton(
                self.sidebar,
                text=label,
                anchor="w",
                font=ctk.CTkFont(size=14, weight="normal"),
                height=38,
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray75", "gray25"),
                command=lambda t=tab_id: self._show_tab(t)
            )
            btn.grid(row=idx, column=0, padx=14, pady=3, sticky="ew")
            self.nav_buttons[tab_id] = btn

        # Interlink Web & Phone Access Button
        web_btn = ctk.CTkButton(
            self.sidebar,
            text="🌐  Web & Phone Access",
            anchor="w",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=36,
            fg_color=("#10b981", "#059669"),
            hover_color=("#059669", "#047857"),
            text_color="white",
            command=self._open_web_connect_dialog
        )
        web_btn.grid(row=8, column=0, padx=14, pady=(8, 4), sticky="ew")

        # Cloud Sync button
        sync_btn = ctk.CTkButton(
            self.sidebar,
            text="☁️ Sync with Cloud",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#4f46e5",
            hover_color="#4338ca",
            height=34,
            command=self._open_cloud_sync_dialog
        )
        sync_btn.grid(row=9, column=0, padx=14, pady=(4, 4), sticky="ew")

        # Sidebar Bottom Info Card
        self.sidebar_stats_frame = ctk.CTkFrame(self.sidebar, fg_color=("gray85", "gray17"), corner_radius=8)
        self.sidebar_stats_frame.grid(row=10, column=0, padx=14, pady=(10, 10), sticky="sew")

        self.sidebar_total_label = ctk.CTkLabel(
            self.sidebar_stats_frame,
            text="Total Spending",
            font=ctk.CTkFont(size=11),
            text_color="gray60"
        )
        self.sidebar_total_label.pack(anchor="w", padx=10, pady=(8, 0))

        self.sidebar_total_val = ctk.CTkLabel(
            self.sidebar_stats_frame,
            text=f"{self.currency}0.00",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=("#1f6aa5", "#38bdf8")
        )
        self.sidebar_total_val.pack(anchor="w", padx=10, pady=(0, 8))

        # Appearance mode selector
        self.theme_menu = ctk.CTkOptionMenu(
            self.sidebar,
            values=["Dark", "Light", "System"],
            command=self._change_theme,
            width=190
        )
        self.theme_menu.set(db.get_setting("theme", "Dark"))
        self.theme_menu.grid(row=11, column=0, padx=14, pady=(0, 20), sticky="s")

    def _open_cloud_sync_dialog(self):
        """Instant modal dialog for Cloud Database Sync & Pull/Push."""
        dlg = ctk.CTkToplevel(self)
        dlg.title("☁️ Cloud Database Sync")
        dlg.geometry("500x380")
        dlg.transient(self)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text="☁️ Cloud Database Sync", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(18, 4))
        ctk.CTkLabel(dlg, text="Synchronize your Mac app with your 24/7 Render Cloud Server.", font=ctk.CTkFont(size=11), text_color="gray60").pack(pady=(0, 14))

        box = ctk.CTkFrame(dlg, fg_color=("gray85", "gray17"), corner_radius=10)
        box.pack(fill="x", padx=20, pady=(0, 14))

        ctk.CTkLabel(box, text="Cloud Server URL:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=14, pady=(12, 4))
        cloud_url_in = ctk.CTkEntry(box, height=34)
        cloud_url_in.insert(0, db.get_setting("cloud_url", "https://rion-snooker-lounge-rk51.onrender.com"))
        cloud_url_in.pack(fill="x", padx=14, pady=(0, 12))

        btn_f = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_f.pack(fill="x", padx=20)
        btn_f.grid_columnconfigure(0, weight=1)
        btn_f.grid_columnconfigure(1, weight=1)

        def do_pull():
            url = cloud_url_in.get().strip().rstrip("/")
            if not url:
                return
            db.set_setting("cloud_url", url)
            dlg.destroy()
            self._do_pull_from_cloud(url)

        def do_push():
            url = cloud_url_in.get().strip().rstrip("/")
            if not url:
                return
            db.set_setting("cloud_url", url)
            dlg.destroy()
            self._do_push_to_cloud(url)

        pull_b = ctk.CTkButton(
            btn_f,
            text="⬇️ Pull from Cloud\n(Update Mac)",
            height=44,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#4f46e5",
            hover_color="#4338ca",
            command=do_pull
        )
        pull_b.grid(row=0, column=0, padx=(0, 6), sticky="ew")

        push_b = ctk.CTkButton(
            btn_f,
            text="⬆️ Push to Cloud\n(Update Server)",
            height=44,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#059669",
            hover_color="#047857",
            command=do_push
        )
        push_b.grid(row=0, column=1, padx=(6, 0), sticky="ew")

    def _open_web_connect_dialog(self):
        """Show connection details and open web portal in browser."""
        dlg = ctk.CTkToplevel(self)
        dlg.title("🌐 Web & Mobile Connection")
        dlg.geometry("480x370")
        dlg.transient(self)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text="🌐 Live Synced Web Portal", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(18, 4))
        ctk.CTkLabel(dlg, text="The local desktop app and web browser share the exact same database in real-time.", font=ctk.CTkFont(size=11), text_color="gray60").pack(pady=(0, 14))

        box = ctk.CTkFrame(dlg, fg_color=("gray85", "gray17"), corner_radius=10)
        box.pack(fill="x", padx=20, pady=(0, 14))

        local_ip = get_local_ip()

        # Mac URL
        ctk.CTkLabel(box, text="💻 On this Mac / PC:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=14, pady=(12, 2))
        ctk.CTkLabel(box, text="http://localhost:8000", font=ctk.CTkFont(size=14, weight="bold"), text_color=("#0284c7", "#38bdf8")).pack(anchor="w", padx=14, pady=(0, 8))

        # Phone URL
        ctk.CTkLabel(box, text="📱 On Mobile / Tablet (Same Wi-Fi):", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=14, pady=(4, 2))
        ctk.CTkLabel(box, text=f"http://{local_ip}:8000", font=ctk.CTkFont(size=14, weight="bold"), text_color=("#10b981", "#34d399")).pack(anchor="w", padx=14, pady=(0, 14))

        btn_f = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_f.pack(fill="x", padx=20)

        open_b = ctk.CTkButton(
            btn_f,
            text="🚀 Open Web App in Browser",
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#10b981",
            hover_color="#059669",
            command=lambda: webbrowser.open("http://localhost:8000")
        )
        open_b.pack(fill="x", pady=(0, 8))

    # =========================================================================
    # CONTENT FRAMES
    # =========================================================================
    def _build_content_frames(self):
        self.frames = {
            "dashboard": ctk.CTkFrame(self, fg_color="transparent"),
            "closing": ctk.CTkFrame(self, fg_color="transparent"),
            "monthly": ctk.CTkFrame(self, fg_color="transparent"),
            "khata": ctk.CTkFrame(self, fg_color="transparent"),
            "staff": ctk.CTkFrame(self, fg_color="transparent"),
            "upload": ctk.CTkFrame(self, fg_color="transparent"),
            "transactions": ctk.CTkFrame(self, fg_color="transparent"),
            "chat": ctk.CTkFrame(self, fg_color="transparent"),
            "settings": ctk.CTkFrame(self, fg_color="transparent"),
        }

        self._build_dashboard_tab(self.frames["dashboard"])
        self._build_closing_tab(self.frames["closing"])
        self._build_monthly_tab(self.frames["monthly"])
        self._build_khata_tab(self.frames["khata"])
        self._build_staff_tab(self.frames["staff"])
        self._build_upload_tab(self.frames["upload"])
        self._build_transactions_tab(self.frames["transactions"])
        self._build_chat_tab(self.frames["chat"])
        self._build_settings_tab(self.frames["settings"])

    def _show_tab(self, tab_name: str):
        self.current_tab = tab_name

        # Update button highlights
        for name, btn in self.nav_buttons.items():
            if name == tab_name:
                btn.configure(fg_color=("gray75", "gray25"), font=ctk.CTkFont(size=14, weight="bold"))
            else:
                btn.configure(fg_color="transparent", font=ctk.CTkFont(size=14, weight="normal"))

        # Hide all frames and show selected
        for name, frame in self.frames.items():
            if name == tab_name:
                frame.grid(row=0, column=1, sticky="nsew", padx=24, pady=20)
            else:
                frame.grid_forget()

        # Refresh data when opening specific tabs
        if tab_name == "dashboard":
            self._refresh_dashboard()
        elif tab_name == "closing":
            self._refresh_closing_tab()
        elif tab_name == "monthly":
            self._refresh_monthly_tab()
        elif tab_name == "khata":
            self._refresh_khata_tab()
        elif tab_name == "staff":
            self._refresh_staff_tab()
        elif tab_name == "upload":
            self._refresh_upload_customer_list()
        elif tab_name == "transactions":
            self._refresh_transactions_table()
        self._update_sidebar_stats()

    def _update_sidebar_stats(self):
        stats = db.get_stats()
        self.currency = db.get_setting("currency", "PKR ")
        self.sidebar_total_val.configure(text=f"{self.currency}{stats['total_spent']:,.2f}")

    def _change_theme(self, new_theme: str):
        ctk.set_appearance_mode(new_theme)
        db.set_setting("theme", new_theme)



    # =========================================================================
    # MONTHLY CLOSING & STATEMENT TAB
    # =========================================================================
    def _build_monthly_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(2, weight=1)

        # Header Frame with Month Selector & Export
        top_f = ctk.CTkFrame(parent, fg_color="transparent")
        top_f.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        top_f.grid_columnconfigure(0, weight=1)

        left_h = ctk.CTkFrame(top_f, fg_color="transparent")
        left_h.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(left_h, text="🗓️ Monthly Closing Statement", font=ctk.CTkFont(size=22, weight="bold")).pack(anchor="w")
        self.monthly_subtitle_lbl = ctk.CTkLabel(left_h, text="Aggregated daily revenues, expenses, and net profit.", font=ctk.CTkFont(size=12), text_color="gray60")
        self.monthly_subtitle_lbl.pack(anchor="w", pady=(2, 0))

        # Controls right
        ctrl_f = ctk.CTkFrame(top_f, fg_color="transparent")
        ctrl_f.grid(row=0, column=1, sticky="e")

        ctk.CTkLabel(ctrl_f, text="Select Month:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 6))
        self.monthly_menu = ctk.CTkOptionMenu(ctrl_f, values=["2026-08"], width=130, height=34, command=self._on_monthly_menu_changed)
        self.monthly_menu.pack(side="left", padx=(0, 10))

        exp_btn = ctk.CTkButton(ctrl_f, text="📥 Export CSV", width=110, height=34, fg_color="#10b981", hover_color="#059669", font=ctk.CTkFont(weight="bold"), command=self._export_monthly_closing_csv)
        exp_btn.pack(side="left")

        # Top Summary Cards (6 Cards)
        cards_f = ctk.CTkFrame(parent, fg_color="transparent")
        cards_f.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        for c in range(6):
            cards_f.grid_columnconfigure(c, weight=1)

        self.monthly_cards = {}
        items = [
            ("cash", "💵 CASH IN", f"{self.currency}0.00", ("#059669", "#34d399")),
            ("bank", "🏦 BANK IN", f"{self.currency}0.00", ("#0284c7", "#38bdf8")),
            ("udhaar", "🟣 UDHAAR RET.", f"{self.currency}0.00", ("#9333ea", "#c084fc")),
            ("gross", "💰 GROSS IN", f"{self.currency}0.00", ("#d97706", "#fbbf24")),
            ("expense", "🔴 EXPENSES", f"{self.currency}0.00", ("#ef4444", "#f87171")),
            ("net", "💎 NET PROFIT", f"{self.currency}0.00", ("#10b981", "#34d399")),
        ]

        for idx, (cid, title, default_val, val_color) in enumerate(items):
            box = ctk.CTkFrame(cards_f, corner_radius=10, fg_color=("gray85", "gray17"))
            box.grid(row=0, column=idx, padx=4, sticky="ew")

            ctk.CTkLabel(box, text=title, font=ctk.CTkFont(size=10, weight="bold"), text_color="gray60").pack(anchor="w", padx=10, pady=(8, 2))
            v_lbl = ctk.CTkLabel(box, text=default_val, font=ctk.CTkFont(size=15, weight="bold"), text_color=val_color)
            v_lbl.pack(anchor="w", padx=10, pady=(0, 8))
            self.monthly_cards[cid] = v_lbl

        # Main Table Container
        main_box = ctk.CTkFrame(parent, corner_radius=10)
        main_box.grid(row=2, column=0, sticky="nsew")
        main_box.grid_columnconfigure(0, weight=1)
        main_box.grid_rowconfigure(1, weight=1)

        # Table Header
        h_bar = ctk.CTkFrame(main_box, fg_color="transparent")
        h_bar.grid(row=0, column=0, sticky="ew", padx=16, pady=10)
        ctk.CTkLabel(h_bar, text="📋 Daily Register Breakdown for Selected Month", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        self.monthly_days_cnt_lbl = ctk.CTkLabel(h_bar, text="0 days recorded", font=ctk.CTkFont(size=11), text_color="gray60")
        self.monthly_days_cnt_lbl.pack(side="right")

        # Scrollable Daily Breakdown List
        self.monthly_scroll = ctk.CTkScrollableFrame(main_box, corner_radius=8)
        self.monthly_scroll.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 10))
        self.monthly_scroll.grid_columnconfigure(0, weight=1)

        # Footer summary bar
        self.monthly_footer_frame = ctk.CTkFrame(main_box, fg_color=("gray85", "gray17"), corner_radius=8)
        self.monthly_footer_frame.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 12))
        self.monthly_footer_lbl = ctk.CTkLabel(self.monthly_footer_frame, text="MONTH TOTAL: -", font=ctk.CTkFont(size=13, weight="bold"))
        self.monthly_footer_lbl.pack(padx=14, pady=8, anchor="w")

    def _refresh_monthly_tab(self):
        curr = db.get_setting("currency", "PKR ")
        cur_sel = self.monthly_menu.get() if hasattr(self, "monthly_menu") else None
        data = db.get_monthly_closing_summary(target_month=cur_sel)

        # Update available months menu
        months = data.get("available_months", [])
        if months and hasattr(self, "monthly_menu"):
            self.monthly_menu.configure(values=months)
            if cur_sel not in months:
                self.monthly_menu.set(data["month"])

        m_str = data["month"]
        self.monthly_subtitle_lbl.configure(text=f"Statement for {m_str} ({data['total_days_recorded']} closing days recorded)")
        self.monthly_days_cnt_lbl.configure(text=f"{data['total_days_recorded']} days recorded")

        # Cards
        self.monthly_cards["cash"].configure(text=f"{curr}{data['tot_cash_sales']:,.2f}")
        self.monthly_cards["bank"].configure(text=f"{curr}{data['tot_bank_slips']:,.2f}")
        self.monthly_cards["udhaar"].configure(text=f"{curr}{data['tot_udhaar_returned']:,.2f}")
        self.monthly_cards["gross"].configure(text=f"{curr}{data['gross_revenue']:,.2f}")
        self.monthly_cards["expense"].configure(text=f"{curr}{data['tot_expense']:,.2f}")

        net_val = data["net_profit"]
        net_color = ("#059669", "#34d399") if net_val >= 0 else ("#ef4444", "#f87171")
        self.monthly_cards["net"].configure(text=f"{'+' if net_val >= 0 else ''}{curr}{net_val:,.2f}", text_color=net_color)

        self.monthly_footer_lbl.configure(
            text=f"MONTH TOTAL -> Cash: {curr}{data['tot_cash_sales']:,.2f}  |  Bank: {curr}{data['tot_bank_slips']:,.2f}  |  Udhaar Ret: {curr}{data['tot_udhaar_returned']:,.2f}  |  Gross: {curr}{data['gross_revenue']:,.2f}  |  Expenses: {curr}{data['tot_expense']:,.2f}  |  Net Profit: {'+' if net_val >= 0 else ''}{curr}{net_val:,.2f}"
        )

        # Render rows
        for w in self.monthly_scroll.winfo_children():
            w.destroy()

        days = data.get("days", [])
        if not days:
            ctk.CTkLabel(self.monthly_scroll, text=f"No transactions recorded for {m_str}.", text_color="gray50", font=ctk.CTkFont(size=13)).pack(pady=40)
            return

        for d in days:
            row = ctk.CTkFrame(self.monthly_scroll, fg_color=("gray90", "gray22"), corner_radius=6)
            row.pack(fill="x", pady=2)
            row.grid_columnconfigure(1, weight=1)

            # Date
            ctk.CTkLabel(row, text=f"📅 {d['date']}", font=ctk.CTkFont(size=12, weight="bold"), width=110, anchor="w").grid(row=0, column=0, padx=10, pady=8, sticky="w")

            # Metrics
            fin_text = f"💵 Cash: {curr}{d['cash_sales']:,.2f}  |  🏦 Bank: {curr}{d['bank_slips']:,.2f}  |  🟣 Udhaar: {curr}{d['udhaar_returned']:,.2f}  |  🔴 Exp: {curr}{d['expense']:,.2f}"
            ctk.CTkLabel(row, text=fin_text, font=ctk.CTkFont(size=11), text_color="gray70", anchor="w").grid(row=0, column=1, padx=6, pady=8, sticky="w")

            # Net
            d_net = d["net_balance"]
            d_color = ("#059669", "#34d399") if d_net >= 0 else ("#ef4444", "#f87171")
            ctk.CTkLabel(row, text=f"Net: {'+' if d_net >= 0 else ''}{curr}{d_net:,.2f}", font=ctk.CTkFont(size=12, weight="bold"), text_color=d_color, width=120, anchor="e").grid(row=0, column=2, padx=8, pady=8, sticky="e")

            # View Day button
            v_btn = ctk.CTkButton(row, text="View Day", width=75, height=28, command=lambda dt=d["date"]: self._view_date_from_monthly(dt))
            v_btn.grid(row=0, column=3, padx=10, pady=8, sticky="e")

    def _on_monthly_menu_changed(self, new_month: str):
        self._refresh_monthly_tab()

    def _view_date_from_monthly(self, dt: str):
        self.closing_date_entry.delete(0, "end")
        self.closing_date_entry.insert(0, dt)
        self._show_tab("closing")

    def _export_monthly_closing_csv(self):
        sel_m = self.monthly_menu.get() if hasattr(self, "monthly_menu") else None
        export_path = filedialog.asksaveasfilename(
            title="Export Monthly Closing CSV",
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
            initialfile=f"Rion_Monthly_Closing_{sel_m or 'Report'}.csv"
        )
        if not export_path:
            return

        cnt = db.export_rion_template_csv(export_path, month_year=sel_m)
        if cnt > 0:
            messagebox.showinfo("Export Successful", f"Successfully exported {cnt} closing days for {sel_m} to:\\n{export_path}")
        else:
            messagebox.showwarning("Export Empty", f"No closing records found for {sel_m}.")

    # =========================================================================
    # CUSTOMER KHATA / UDHAAR DIRECTORY TAB
    # =========================================================================
    def _build_khata_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(2, weight=1)

        # Header Frame
        top_f = ctk.CTkFrame(parent, fg_color="transparent")
        top_f.grid(row=0, column=0, sticky="ew", pady=(0, 14))

        ctk.CTkLabel(top_f, text="👥 Customer Khata & Credit Directory", font=ctk.CTkFont(size=22, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(top_f, text="Track customer credit given, payments returned, and outstanding balances.", font=ctk.CTkFont(size=12), text_color="gray60").pack(anchor="w", pady=(2, 0))

        # Top Summary Cards (4 Cards)
        cards_f = ctk.CTkFrame(parent, fg_color="transparent")
        cards_f.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        for c in range(4):
            cards_f.grid_columnconfigure(c, weight=1)

        self.khata_cards = {}
        items = [
            ("clients", "👥 TOTAL CLIENTS", "0", "gray50"),
            ("given", "🔵 TOTAL GIVEN", f"{self.currency}0.00", ("#6366f1", "#818cf8")),
            ("returned", "🟣 TOTAL RETURNED", f"{self.currency}0.00", ("#a855f7", "#c084fc")),
            ("outstanding", "💎 NET OUTSTANDING", f"{self.currency}0.00", ("#f59e0b", "#fbbf24"))
        ]

        for idx, (cid, title, default_val, val_color) in enumerate(items):
            box = ctk.CTkFrame(cards_f, corner_radius=10, fg_color=("gray85", "gray17"))
            box.grid(row=0, column=idx, padx=5, sticky="ew")

            ctk.CTkLabel(box, text=title, font=ctk.CTkFont(size=11, weight="bold"), text_color="gray60").pack(anchor="w", padx=12, pady=(10, 2))
            v_lbl = ctk.CTkLabel(box, text=default_val, font=ctk.CTkFont(size=17, weight="bold"), text_color=val_color)
            v_lbl.pack(anchor="w", padx=12, pady=(0, 10))
            self.khata_cards[cid] = v_lbl

        # Main Table Container
        main_box = ctk.CTkFrame(parent, corner_radius=10)
        main_box.grid(row=2, column=0, sticky="nsew")
        main_box.grid_columnconfigure(0, weight=1)
        main_box.grid_rowconfigure(1, weight=1)

        # Search Bar Row
        bar_f = ctk.CTkFrame(main_box, fg_color="transparent")
        bar_f.grid(row=0, column=0, sticky="ew", padx=16, pady=12)
        bar_f.grid_columnconfigure(0, weight=1)

        self.khata_search_entry = ctk.CTkEntry(bar_f, placeholder_text="🔍 Search client / customer name...", height=32)
        self.khata_search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.khata_search_entry.bind("<KeyRelease>", lambda e: self._filter_khata_desktop())

        add_c_btn = ctk.CTkButton(bar_f, text="+ Add Customer", fg_color="#4f46e5", hover_color="#4338ca", width=115, height=32, command=self._dialog_add_khata_customer)
        add_c_btn.grid(row=0, column=1, padx=(0, 6))

        add_u_btn = ctk.CTkButton(bar_f, text="+ Add Udhaar", fg_color="#d97706", hover_color="#b45309", width=105, height=32, command=self._dialog_add_direct_udhaar)
        add_u_btn.grid(row=0, column=2, padx=(0, 6))

        ref_btn = ctk.CTkButton(bar_f, text="🔄 Refresh", width=80, height=32, command=self._refresh_khata_tab)
        ref_btn.grid(row=0, column=3)

        # Scrollable Customer List
        self.khata_scroll = ctk.CTkScrollableFrame(main_box, corner_radius=8)
        self.khata_scroll.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 14))
        self.khata_scroll.grid_columnconfigure(0, weight=1)

        self.khata_clients_cache = []

    def _refresh_khata_tab(self):
        curr = db.get_setting("currency", "PKR ")
        data = db.get_khata_customers_summary()
        self.khata_clients_cache = data.get("clients", [])

        # Update cards
        self.khata_cards["clients"].configure(text=str(data.get("total_clients", 0)))
        self.khata_cards["given"].configure(text=f"{curr}{data.get('total_given', 0.0):,.2f}")
        self.khata_cards["returned"].configure(text=f"{curr}{data.get('total_returned', 0.0):,.2f}")
        self.khata_cards["outstanding"].configure(text=f"{curr}{data.get('total_outstanding', 0.0):,.2f}")

        self._filter_khata_desktop()
        self._refresh_upload_customer_list()

    def _refresh_upload_customer_list(self):
        try:
            data = db.get_khata_customers_summary()
            names = [c["customer_name"] for c in data.get("clients", [])]
            if not names:
                names = ["-- Select Customer from Khata --"]
            if hasattr(self, "upload_slip_customer_combo"):
                self.upload_slip_customer_combo.configure(values=names)
        except Exception:
            pass

    def _filter_khata_desktop(self):
        query = self.khata_search_entry.get().strip().lower()
        filtered = [c for c in self.khata_clients_cache if query in c["customer_name"].lower()] if query else self.khata_clients_cache
        self._render_khata_list(filtered)

    def _render_khata_list(self, clients):
        for w in self.khata_scroll.winfo_children():
            w.destroy()

        if not clients:
            ctk.CTkLabel(self.khata_scroll, text="No customer credit accounts found. Click '+ Add Customer' to register a customer!", text_color="gray50", font=ctk.CTkFont(size=13)).pack(pady=40)
            return

        curr = db.get_setting("currency", "PKR ")

        for c in clients:
            row = ctk.CTkFrame(self.khata_scroll, fg_color=("gray90", "gray22"), corner_radius=8)
            row.pack(fill="x", pady=4)
            row.grid_columnconfigure(0, weight=1)

            # Left: Customer info
            info_f = ctk.CTkFrame(row, fg_color="transparent")
            info_f.grid(row=0, column=0, padx=12, pady=10, sticky="w")

            ctk.CTkLabel(info_f, text=c["customer_name"], font=ctk.CTkFont(size=14, weight="bold"), anchor="w").pack(anchor="w")
            contact_str = f" • Phone: {c['phone']}" if c.get("phone") else ""
            ctk.CTkLabel(info_f, text=f"Last Activity: {c['last_date']} • {c['total_entries']} txs{contact_str}", font=ctk.CTkFont(size=11), text_color="gray60", anchor="w").pack(anchor="w")

            # Middle: Financials
            fin_f = ctk.CTkFrame(row, fg_color="transparent")
            fin_f.grid(row=0, column=1, padx=16, pady=10, sticky="e")

            due = c["pending_balance"]
            due_color = ("#d97706", "#fbbf24") if due > 0 else ("#059669", "#34d399")
            due_text = f"Due: {curr}{due:,.2f}" if due > 0 else "✓ Cleared"

            ctk.CTkLabel(fin_f, text=due_text, font=ctk.CTkFont(size=14, weight="bold"), text_color=due_color).pack(anchor="e")
            ctk.CTkLabel(fin_f, text=f"Given: {curr}{c['total_given']:,.2f} | Returned: {curr}{c['total_returned']:,.2f}", font=ctk.CTkFont(size=11), text_color="gray60").pack(anchor="e")

            # Right: Action Buttons
            btn_f = ctk.CTkFrame(row, fg_color="transparent")
            btn_f.grid(row=0, column=2, padx=12, pady=10, sticky="e")

            if due > 0:
                rec_btn = ctk.CTkButton(btn_f, text="💵 Receive", width=72, height=28, fg_color=("#10b981", "#059669"), hover_color=("#059669", "#047857"), font=ctk.CTkFont(size=11, weight="bold"), command=lambda cn=c["customer_name"], d=due: self._receive_khata_payment_action(cn, d))
                rec_btn.pack(side="left", padx=(0, 4))

            add_u_btn = ctk.CTkButton(btn_f, text="+ Udhaar", width=72, height=28, fg_color=("#d97706", "#b45309"), hover_color=("#b45309", "#92400e"), font=ctk.CTkFont(size=11, weight="bold"), command=lambda cn=c["customer_name"]: self._dialog_add_direct_udhaar(cn))
            add_u_btn.pack(side="left", padx=(0, 4))

            edit_btn = ctk.CTkButton(btn_f, text="✏️ Edit", width=62, height=28, fg_color=("gray70", "gray35"), hover_color=("gray60", "gray45"), font=ctk.CTkFont(size=11), command=lambda cust=c: self._dialog_edit_khata_customer(cust))
            edit_btn.pack(side="left", padx=(0, 4))

            hist_btn = ctk.CTkButton(btn_f, text="📖 History", width=72, height=28, font=ctk.CTkFont(size=11), command=lambda cn=c["customer_name"]: self._open_khata_history_modal(cn))
            hist_btn.pack(side="left")

    def _open_khata_history_modal(self, customer_name: str):
        history = db.get_customer_khata_history(customer_name)
        curr = db.get_setting("currency", "PKR ")

        dlg = ctk.CTkToplevel(self)
        dlg.title(f"📖 {customer_name}'s Khata Ledger")
        dlg.geometry("640x520")
        dlg.transient(self)
        dlg.grab_set()

        dlg.grid_columnconfigure(0, weight=1)
        dlg.grid_rowconfigure(1, weight=1)

        # Header
        h_box = ctk.CTkFrame(dlg, fg_color=("gray85", "gray17"), corner_radius=10)
        h_box.grid(row=0, column=0, sticky="ew", padx=16, pady=14)
        ctk.CTkLabel(h_box, text=f"👤 {customer_name}", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=12, pady=(10, 2))
        
        final_bal = history[-1]["running_balance"] if history else 0.0
        bal_color = ("#d97706", "#fbbf24") if final_bal > 0 else ("#059669", "#34d399")
        ctk.CTkLabel(h_box, text=f"Current Outstanding Balance: {curr}{final_bal:,.2f}", font=ctk.CTkFont(size=13, weight="bold"), text_color=bal_color).pack(anchor="w", padx=12, pady=(0, 10))

        # Table
        scroll = ctk.CTkScrollableFrame(dlg, corner_radius=8)
        scroll.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 14))
        scroll.grid_columnconfigure(2, weight=1)

        for t in history:
            row = ctk.CTkFrame(scroll, fg_color=("gray90", "gray22"), corner_radius=6)
            row.pack(fill="x", pady=3)
            row.grid_columnconfigure(2, weight=1)

            is_given = t["tx_type"] == "Udhaar"
            badge_text = "🔵 Udhaar Given" if is_given else "🟣 Returned"
            badge_color = ("#4f46e5", "#4338ca") if is_given else ("#9333ea", "#7e22ce")
            amt_prefix = "+" if is_given else "-"
            amt_color = ("#6366f1", "#818cf8") if is_given else ("#a855f7", "#c084fc")

            ctk.CTkLabel(row, text=t["date"], font=ctk.CTkFont(size=11, weight="bold"), width=85).grid(row=0, column=0, padx=8, pady=6, sticky="w")
            ctk.CTkLabel(row, text=f" {badge_text} ", font=ctk.CTkFont(size=10, weight="bold"), fg_color=badge_color, text_color="white", corner_radius=4).grid(row=0, column=1, padx=4, pady=6, sticky="w")
            ctk.CTkLabel(row, text=t.get("notes") or t.get("category"), font=ctk.CTkFont(size=11), text_color="gray60", anchor="w").grid(row=0, column=2, padx=8, pady=6, sticky="w")
            ctk.CTkLabel(row, text=f"{amt_prefix}{curr}{t['total_amount']:,.2f}", font=ctk.CTkFont(size=13, weight="bold"), text_color=amt_color).grid(row=0, column=3, padx=8, pady=6, sticky="e")
            ctk.CTkLabel(row, text=f"Bal: {curr}{t['running_balance']:,.2f}", font=ctk.CTkFont(size=11, weight="bold"), text_color="gray70").grid(row=0, column=4, padx=8, pady=6, sticky="e")

        # Footer
        bot_f = ctk.CTkFrame(dlg, fg_color="transparent")
        bot_f.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 14))
        ctk.CTkButton(bot_f, text="Close", command=dlg.destroy, width=90, fg_color="gray40", hover_color="gray30").pack(side="right")

    def _receive_khata_payment_action(self, customer_name: str, due_amt: float):
        curr = db.get_setting("currency", "PKR ")
        dlg = ctk.CTkToplevel(self)
        dlg.title("Receive Customer Payment")
        dlg.geometry("420x300")
        dlg.transient(self)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text=f"💵 Receive Payment: {customer_name}", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(16, 4))
        ctk.CTkLabel(dlg, text=f"Total Pending Due: {curr}{due_amt:,.2f}", font=ctk.CTkFont(size=12), text_color="gray60").pack(pady=(0, 12))

        box = ctk.CTkFrame(dlg, corner_radius=10)
        box.pack(fill="x", padx=20, pady=(0, 14))

        ctk.CTkLabel(box, text="Amount Received Today: *", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=14, pady=(10, 2))
        amt_in = ctk.CTkEntry(box, height=36, font=ctk.CTkFont(size=15, weight="bold"))
        amt_in.insert(0, str(due_amt))
        amt_in.pack(fill="x", padx=14, pady=(0, 10))

        def do_save():
            try:
                amt = float(amt_in.get().strip())
                if amt <= 0:
                    raise ValueError()
            except ValueError:
                messagebox.showwarning("Validation Error", "Please enter a valid positive amount.")
                return

            today_str = datetime.now().strftime("%Y-%m-%d")
            db.add_manual_cash_entry(
                date=today_str,
                title=customer_name,
                amount=amt,
                category="Udhaar Recovery",
                currency=curr,
                payment_method="Cash",
                notes=f"Udhaar Returned by {customer_name}",
                tx_type="Udhaar Recovery"
            )
            dlg.destroy()
            self._refresh_khata_tab()
            messagebox.showinfo("Payment Recorded", f"Successfully recorded payment of {curr}{amt:,.2f} from {customer_name} into today's closing!")

        btn_f = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_f.pack(fill="x", padx=20)

        s_btn = ctk.CTkButton(btn_f, text="💾 Confirm Payment", height=36, fg_color="#10b981", hover_color="#059669", font=ctk.CTkFont(weight="bold"), command=do_save)
        s_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))
        c_btn = ctk.CTkButton(btn_f, text="Cancel", width=80, height=36, fg_color="gray40", hover_color="gray30", command=dlg.destroy)
        c_btn.pack(side="right")

    def _dialog_add_khata_customer(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Add New Khata Customer")
        dlg.geometry("420x360")
        dlg.transient(self)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text="👤 Add New Khata Customer", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(16, 12))

        f = ctk.CTkFrame(dlg, fg_color="transparent")
        f.pack(fill="x", padx=20)

        ctk.CTkLabel(f, text="Customer Name *:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(0, 2))
        name_in = ctk.CTkEntry(f, placeholder_text="e.g. Bilal, Chaudhry Asif, Shakeel", height=32)
        name_in.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(f, text="Phone Number (Optional):", font=ctk.CTkFont(size=12)).pack(anchor="w", pady=(0, 2))
        phone_in = ctk.CTkEntry(f, placeholder_text="0300-1234567", height=32)
        phone_in.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(f, text="Initial Udhaar Balance (PKR):", font=ctk.CTkFont(size=12)).pack(anchor="w", pady=(0, 2))
        bal_in = ctk.CTkEntry(f, placeholder_text="0.00", height=32)
        bal_in.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(f, text="Notes / Description:", font=ctk.CTkFont(size=12)).pack(anchor="w", pady=(0, 2))
        notes_in = ctk.CTkEntry(f, placeholder_text="e.g. VIP player", height=32)
        notes_in.pack(fill="x", pady=(0, 12))

        def do_save():
            name = name_in.get().strip()
            if not name:
                messagebox.showwarning("Validation Error", "Customer name is required.")
                return
            phone = phone_in.get().strip()
            notes = notes_in.get().strip()
            try:
                bal = float(bal_in.get().strip().replace(",", "") or "0")
            except ValueError:
                bal = 0.0

            db.add_khata_customer(name=name, phone=phone, initial_balance=bal, notes=notes)
            dlg.destroy()
            self._refresh_khata_tab()
            messagebox.showinfo("Customer Added", f"✅ Customer '{name}' added to Khata directory!")

        btn_f = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_f.pack(fill="x", padx=20)

        s_btn = ctk.CTkButton(btn_f, text="💾 Save Customer", height=36, fg_color="#4f46e5", hover_color="#4338ca", font=ctk.CTkFont(weight="bold"), command=do_save)
        s_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))
        c_btn = ctk.CTkButton(btn_f, text="Cancel", width=80, height=36, fg_color="gray40", hover_color="gray30", command=dlg.destroy)
        c_btn.pack(side="right")

    def _dialog_edit_khata_customer(self, cust_dict: Dict[str, Any]):
        old_name = cust_dict["customer_name"]
        dlg = ctk.CTkToplevel(self)
        dlg.title(f"Edit Customer: {old_name}")
        dlg.geometry("420x330")
        dlg.transient(self)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text=f"✏️ Edit Customer Profile", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(16, 12))

        f = ctk.CTkFrame(dlg, fg_color="transparent")
        f.pack(fill="x", padx=20)

        ctk.CTkLabel(f, text="Customer Name *:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(0, 2))
        name_in = ctk.CTkEntry(f, height=32)
        name_in.insert(0, old_name)
        name_in.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(f, text="Phone Number:", font=ctk.CTkFont(size=12)).pack(anchor="w", pady=(0, 2))
        phone_in = ctk.CTkEntry(f, height=32)
        phone_in.insert(0, cust_dict.get("phone", ""))
        phone_in.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(f, text="Notes / Profile Details:", font=ctk.CTkFont(size=12)).pack(anchor="w", pady=(0, 2))
        notes_in = ctk.CTkEntry(f, height=32)
        notes_in.insert(0, cust_dict.get("notes", ""))
        notes_in.pack(fill="x", pady=(0, 12))

        def do_update():
            new_name = name_in.get().strip()
            if not new_name:
                messagebox.showwarning("Validation Error", "Customer name is required.")
                return
            phone = phone_in.get().strip()
            notes = notes_in.get().strip()

            db.update_khata_customer(old_name=old_name, new_name=new_name, phone=phone, notes=notes)
            dlg.destroy()
            self._refresh_khata_tab()
            messagebox.showinfo("Customer Updated", f"✅ Customer profile '{new_name}' updated successfully!")

        btn_f = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_f.pack(fill="x", padx=20)

        s_btn = ctk.CTkButton(btn_f, text="💾 Update Customer", height=36, fg_color="#4f46e5", hover_color="#4338ca", font=ctk.CTkFont(weight="bold"), command=do_update)
        s_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))
        c_btn = ctk.CTkButton(btn_f, text="Cancel", width=80, height=36, fg_color="gray40", hover_color="gray30", command=dlg.destroy)
        c_btn.pack(side="right")

    def _dialog_add_direct_udhaar(self, prefilled_customer: str = ""):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Add Customer Udhaar (Credit)")
        dlg.geometry("420x330")
        dlg.transient(self)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text="📒 Add Customer Udhaar (Credit)", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(16, 12))

        f = ctk.CTkFrame(dlg, fg_color="transparent")
        f.pack(fill="x", padx=20)

        ctk.CTkLabel(f, text="Customer Name *:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(0, 2))
        name_in = ctk.CTkEntry(f, placeholder_text="e.g. Chatta, Hamza", height=32)
        if prefilled_customer:
            name_in.insert(0, prefilled_customer)
        name_in.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(f, text="Udhaar Amount (PKR) *:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(0, 2))
        amt_in = ctk.CTkEntry(f, placeholder_text="0.00", height=32)
        amt_in.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(f, text="Description / Notes:", font=ctk.CTkFont(size=12)).pack(anchor="w", pady=(0, 2))
        notes_in = ctk.CTkEntry(f, placeholder_text="e.g. Table frames bill / Canteen", height=32)
        notes_in.pack(fill="x", pady=(0, 12))

        def do_save():
            name = name_in.get().strip()
            if not name:
                messagebox.showwarning("Validation Error", "Customer name is required.")
                return
            try:
                amt = float(amt_in.get().strip().replace(",", ""))
                if amt <= 0:
                    raise ValueError()
            except ValueError:
                messagebox.showwarning("Validation Error", "Please enter a valid positive Udhaar amount.")
                return

            notes = notes_in.get().strip() or "Customer Udhaar"
            today_str = datetime.now().strftime("%Y-%m-%d")
            db.add_manual_udhaar_entry(customer_name=name, amount=amt, date=today_str, notes=notes)
            dlg.destroy()
            self._refresh_khata_tab()
            messagebox.showinfo("Udhaar Logged", f"✅ Added PKR {amt:,.2f} Udhaar for customer '{name}'!")

        btn_f = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_f.pack(fill="x", padx=20)

        s_btn = ctk.CTkButton(btn_f, text="💾 Save Udhaar", height=36, fg_color="#d97706", hover_color="#b45309", font=ctk.CTkFont(weight="bold"), command=do_save)
        s_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))
        c_btn = ctk.CTkButton(btn_f, text="Cancel", width=80, height=36, fg_color="gray40", hover_color="gray30", command=dlg.destroy)
        c_btn.pack(side="right")

    # =========================================================================
    # STAFF & SALARY MANAGEMENT TAB
    # =========================================================================
    def _build_staff_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(3, weight=1)

        # Header
        head_f = ctk.CTkFrame(parent, fg_color="transparent")
        head_f.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        head_f.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(head_f, text="👨‍💼 Staff & Salary Management", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            head_f,
            text="Salary Pay Day: 10th of every month • Real-time accrued wages calculated as of today.",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#10b981"
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        add_btn = ctk.CTkButton(
            head_f,
            text="➕ Add Staff Member",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#10b981",
            hover_color="#059669",
            height=36,
            command=self._open_add_staff_dialog
        )
        add_btn.grid(row=0, column=1, rowspan=2, sticky="e", padx=(10, 0))

        # 5 Staff Metric Cards
        self.staff_cards_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.staff_cards_frame.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        for col_idx in range(5):
            self.staff_cards_frame.grid_columnconfigure(col_idx, weight=1)

        self.staff_card_widgets = {}
        card_configs = [
            ("count", "👨‍💼 ACTIVE STAFF", "0 staff", "#94a3b8"),
            ("earned", "⚡ EARNED TILL TODAY", f"{self.currency}0.00", "#34d399"),
            ("payroll", "💰 FULL MONTH DUE", f"{self.currency}0.00", "#38bdf8"),
            ("security", "🔒 SECURITY HELD", f"{self.currency}0.00", "#818cf8"),
            ("due", "⏳ REMAINING DUE", f"{self.currency}0.00", "#f87171"),
        ]

        for idx, (key, title, default_val, text_col) in enumerate(card_configs):
            card = ctk.CTkFrame(self.staff_cards_frame, corner_radius=10)
            card.grid(row=0, column=idx, padx=(0 if idx == 0 else 4, 0 if idx == 4 else 4), sticky="ew")

            t_lbl = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=10, weight="bold"), text_color="gray60")
            t_lbl.pack(anchor="w", padx=10, pady=(8, 2))

            v_lbl = ctk.CTkLabel(card, text=default_val, font=ctk.CTkFont(size=16, weight="bold"), text_color=text_col)
            v_lbl.pack(anchor="w", padx=10, pady=(0, 8))

            self.staff_card_widgets[key] = v_lbl

        # Staff List Container
        list_header_f = ctk.CTkFrame(parent, fg_color="transparent")
        list_header_f.grid(row=2, column=0, sticky="ew", pady=(0, 6))
        ctk.CTkLabel(list_header_f, text="Club Staff Directory & Fresh Salary Register (Pay: 10th)", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")

        self.staff_scroll = ctk.CTkScrollableFrame(parent, corner_radius=10)
        self.staff_scroll.grid(row=3, column=0, sticky="nsew")
        self.staff_scroll.grid_columnconfigure(0, weight=1)

    def _refresh_staff_tab(self):
        summary = db.get_staff_salary_summary()
        self.staff_card_widgets["count"].configure(text=f"{summary.get('total_staff', 0)} active")
        self.staff_card_widgets["earned"].configure(text=f"{self.currency}{summary.get('total_earned_to_date', 0):,.2f}")
        self.staff_card_widgets["payroll"].configure(text=f"{self.currency}{summary.get('total_payroll', 0):,.2f}")
        self.staff_card_widgets["security"].configure(text=f"{self.currency}{summary.get('total_security_held', 0):,.2f}")
        self.staff_card_widgets["due"].configure(text=f"{self.currency}{summary.get('total_remaining_due', 0):,.2f}")

        # Clear scrollable list
        for child in self.staff_scroll.winfo_children():
            child.destroy()

        staff_list = summary.get("staff", [])
        if not staff_list:
            ctk.CTkLabel(self.staff_scroll, text="No staff members registered. Click '+ Add Staff Member' to register markers and employees.", text_color="gray50").pack(pady=40)
            return

        for s in staff_list:
            s_id = s["id"]
            s_name = s["name"]
            s_role = s["role"]
            base = s["base_salary"]
            sec = s.get("security_held", 0)
            paid = s["paid_this_month"]
            due = s["balance_due"]
            earned_today = s.get("earned_to_date", 0)
            days_today = s.get("days_worked_to_date", 0)
            eff = s.get("effective_salary", base)
            is_pro = s.get("is_prorated", False)
            h_date = s.get("hire_date", "")

            card = ctk.CTkFrame(self.staff_scroll, fg_color=("gray90", "gray17"), corner_radius=8)
            card.pack(fill="x", pady=4, padx=4)
            card.grid_columnconfigure(0, weight=1)

            # Left Info
            info_f = ctk.CTkFrame(card, fg_color="transparent")
            info_f.grid(row=0, column=0, padx=12, pady=10, sticky="w")

            ctk.CTkLabel(info_f, text=s_name, font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w")
            join_str = f"Joined: {h_date}" if h_date else "Regular Staff"
            sub_txt = f"{s_role} • {join_str} • Base: {self.currency}{base:,.2f}"
            ctk.CTkLabel(info_f, text=sub_txt, font=ctk.CTkFont(size=11), text_color="gray60").pack(anchor="w")

            # Middle Stats: Fresh Earned Till Today
            stats_f = ctk.CTkFrame(card, fg_color="transparent")
            stats_f.grid(row=0, column=1, padx=12, pady=10, sticky="e")

            sec_days = s.get("security_days_held", 10)
            stat_line = f"⚡ Earned: {self.currency}{earned_today:,.2f} ({days_today}d)  |  📅 Month: {self.currency}{eff:,.2f}  |  🔒 Sec: {self.currency}{sec:,.2f} ({sec_days}/10d)"
            ctk.CTkLabel(stats_f, text=stat_line, font=ctk.CTkFont(size=12, weight="bold"), text_color="#10b981").pack(anchor="e")

            # Right Buttons
            btn_f = ctk.CTkFrame(card, fg_color="transparent")
            btn_f.grid(row=0, column=2, padx=12, pady=10, sticky="e")

            pay_b = ctk.CTkButton(
                btn_f,
                text="💵 Pay",
                width=65,
                height=28,
                fg_color="#10b981",
                hover_color="#059669",
                font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda sid=s_id, sname=s_name, sdue=due, seff=eff: self._open_pay_salary_dialog(sid, sname, sdue or seff)
            )
            pay_b.pack(side="left", padx=3)

            resign_b = ctk.CTkButton(
                btn_f,
                text="🚪 Resign",
                width=68,
                height=28,
                fg_color=("#d97706", "#b45309"),
                hover_color=("#b45309", "#92400e"),
                font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda sid=s_id, sname=s_name: self._open_resign_dialog(sid, sname)
            )
            resign_b.pack(side="left", padx=3)

            hist_b = ctk.CTkButton(
                btn_f,
                text="📖 History",
                width=75,
                height=28,
                fg_color=("gray75", "gray25"),
                font=ctk.CTkFont(size=11),
                command=lambda sname=s_name: self._open_staff_history_dialog(sname)
            )
            hist_b.pack(side="left", padx=3)

            del_b = ctk.CTkButton(
                btn_f,
                text="🗑️",
                width=32,
                height=28,
                fg_color="transparent",
                text_color="#ef4444",
                hover_color=("gray75", "gray30"),
                command=lambda sid=s_id, sname=s_name: self._delete_staff_member(sid, sname)
            )
            del_b.pack(side="left", padx=3)

    def _open_add_staff_dialog(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("➕ Add Staff Member")
        dlg.geometry("440x490")
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text="Register New Staff Member", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(16, 12))

        form = ctk.CTkFrame(dlg, fg_color="transparent")
        form.pack(fill="x", padx=20)

        ctk.CTkLabel(form, text="Staff Name:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(0, 2))
        name_entry = ctk.CTkEntry(form, height=32, placeholder_text="e.g. Usman Marker")
        name_entry.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(form, text="Role / Designation:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(0, 2))
        role_menu = ctk.CTkOptionMenu(form, values=["Marker", "Manager / Cashier", "Cafe / Canteen Staff", "Maintenance / Cleaner", "Security", "Other"], height=32)
        role_menu.set("Marker")
        role_menu.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(form, text="Monthly Base Salary (PKR):", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(0, 2))
        sal_entry = ctk.CTkEntry(form, height=32, placeholder_text="25000")
        sal_entry.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(form, text="Joining Date (Optional - e.g. 2026-08-25):", font=ctk.CTkFont(size=12)).pack(anchor="w", pady=(0, 2))
        hire_entry = ctk.CTkEntry(form, height=32, placeholder_text="Leave blank for full month")
        hire_entry.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(form, text="Phone Number (Optional):", font=ctk.CTkFont(size=12)).pack(anchor="w", pady=(0, 2))
        phone_entry = ctk.CTkEntry(form, height=32, placeholder_text="0300-1234567")
        phone_entry.pack(fill="x", pady=(0, 16))

        def save():
            n = name_entry.get().strip()
            if not n:
                messagebox.showwarning("Missing Name", "Please enter staff member name.")
                return
            try:
                s_val = float(sal_entry.get().strip() or "0")
            except ValueError:
                messagebox.showwarning("Invalid Salary", "Please enter a valid numeric salary amount.")
                return

            db.add_staff(
                name=n,
                role=role_menu.get(),
                phone=phone_entry.get().strip(),
                salary_type="Monthly",
                base_salary=s_val,
                hire_date=hire_entry.get().strip()
            )
            dlg.destroy()
            self._refresh_staff_tab()

        save_btn = ctk.CTkButton(dlg, text="Save Staff Member", height=38, font=ctk.CTkFont(weight="bold"), fg_color="#10b981", hover_color="#059669", command=save)
        save_btn.pack(fill="x", padx=20, pady=(0, 12))

    def _open_pay_salary_dialog(self, staff_id, staff_name, due_amt):
        dlg = ctk.CTkToplevel(self)
        dlg.title(f"💵 Pay Salary: {staff_name}")
        dlg.geometry("400x340")
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text=f"Pay Salary / Advance to {staff_name}", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(16, 4))
        ctk.CTkLabel(dlg, text="Will be recorded as today's closing expense (Pay: 10th)", font=ctk.CTkFont(size=11), text_color="gray60").pack(pady=(0, 12))

        form = ctk.CTkFrame(dlg, fg_color="transparent")
        form.pack(fill="x", padx=20)

        ctk.CTkLabel(form, text="Amount (PKR):", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(0, 2))
        amt_entry = ctk.CTkEntry(form, height=32)
        amt_entry.insert(0, str(int(due_amt)) if due_amt > 0 else "")
        amt_entry.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(form, text="Payment Method:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(0, 2))
        method_menu = ctk.CTkOptionMenu(form, values=["Cash", "Bank"], height=32)
        method_menu.set("Cash")
        method_menu.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(form, text="Notes (Optional):", font=ctk.CTkFont(size=12)).pack(anchor="w", pady=(0, 2))
        notes_entry = ctk.CTkEntry(form, height=32, placeholder_text="e.g. Weekly advance")
        notes_entry.pack(fill="x", pady=(0, 16))

        def confirm_pay():
            try:
                a = float(amt_entry.get().strip())
                if a <= 0: raise ValueError()
            except Exception:
                messagebox.showwarning("Invalid Amount", "Please enter a valid positive payment amount.")
                return

            db.pay_staff_salary(
                staff_id=staff_id,
                amount=a,
                pay_date=datetime.now().strftime("%Y-%m-%d"),
                payment_method=method_menu.get(),
                notes=notes_entry.get().strip()
            )
            dlg.destroy()
            messagebox.showinfo("Success", f"Recorded salary payment of {self.currency}{a:,.2f} for {staff_name}!")
            self._refresh_staff_tab()
            if hasattr(self, "_refresh_closing_tab"):
                self._refresh_closing_tab()

        ctk.CTkButton(dlg, text="Confirm & Pay", height=38, font=ctk.CTkFont(weight="bold"), fg_color="#10b981", hover_color="#059669", command=confirm_pay).pack(fill="x", padx=20)

    def _open_staff_history_dialog(self, staff_name):
        dlg = ctk.CTkToplevel(self)
        dlg.title(f"📖 Salary Statement: {staff_name}")
        dlg.geometry("520x400")
        dlg.transient(self)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text=f"Payout History: {staff_name}", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(14, 10))

        scroll = ctk.CTkScrollableFrame(dlg, corner_radius=8)
        scroll.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        history = db.get_staff_payout_history(staff_name)
        if not history:
            ctk.CTkLabel(scroll, text="No payouts recorded yet.", text_color="gray50").pack(pady=30)
        else:
            tot = 0
            for t in history:
                tot += t["total_amount"]
                row = ctk.CTkFrame(scroll, fg_color=("gray90", "gray20"), corner_radius=6)
                row.pack(fill="x", pady=2)
                row.grid_columnconfigure(1, weight=1)

                ctk.CTkLabel(row, text=t["date"], font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=0, padx=8, pady=6)
                ctk.CTkLabel(row, text=f"{t['payment_method']} • {t['notes'] or 'Salary'}", font=ctk.CTkFont(size=11), text_color="gray60").grid(row=0, column=1, sticky="w", padx=8)
                ctk.CTkLabel(row, text=f"-{self.currency}{t['total_amount']:,.2f}", font=ctk.CTkFont(size=12, weight="bold"), text_color="#ef4444").grid(row=0, column=2, padx=8)

            ctk.CTkLabel(dlg, text=f"Total Paid: {self.currency}{tot:,.2f}", font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(0, 12))

    def _delete_staff_member(self, staff_id, staff_name):
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to remove staff member '{staff_name}'?"):
            db.delete_staff(staff_id)
            self._refresh_staff_tab()

    # =========================================================================
    # 1. DASHBOARD TAB
    # =========================================================================
    def _build_dashboard_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(2, weight=1)

        # Header
        header_frame = ctk.CTkFrame(parent, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        header_frame.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            header_frame,
            text="Financial Dashboard",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, sticky="w")

        btn_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        btn_box.grid(row=0, column=1, sticky="e")

        cash_btn = ctk.CTkButton(
            btn_box,
            text="💵 + Add Cash",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=("#0284c7", "#0369a1"),
            hover_color=("#0369a1", "#075985"),
            command=self._open_cash_entry_dialog
        )
        cash_btn.pack(side="left", padx=(0, 8))

        scan_btn = ctk.CTkButton(
            btn_box,
            text="+ Scan Receipts",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self._show_tab("upload")
        )
        scan_btn.pack(side="left")

        # Metric Cards (Row 1)
        self.metric_cards_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.metric_cards_frame.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        for i in range(4):
            self.metric_cards_frame.grid_columnconfigure(i, weight=1)

        self.card_credits = self._create_metric_card(self.metric_cards_frame, 0, "🟢 TOTAL CREDITS (INCOME)", "$0.00", "Payments received & sales")
        self.card_expenses = self._create_metric_card(self.metric_cards_frame, 1, "🔴 TOTAL EXPENSES", "$0.00", "Money spent & bills paid")
        self.card_net = self._create_metric_card(self.metric_cards_frame, 2, "💎 NET BALANCE", "$0.00", "Credits minus Expenses")
        self.card_count = self._create_metric_card(self.metric_cards_frame, 3, "📋 TRANSACTIONS", "0", "Logged transactions")

        # Split Section: Categories & Recent Activity
        split_frame = ctk.CTkFrame(parent, fg_color="transparent")
        split_frame.grid(row=2, column=0, sticky="nsew")
        split_frame.grid_columnconfigure(0, weight=1)
        split_frame.grid_columnconfigure(1, weight=1)
        split_frame.grid_rowconfigure(0, weight=1)

        # Left Column: Category Breakdown
        cat_box = ctk.CTkFrame(split_frame, corner_radius=10)
        cat_box.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        cat_box.grid_rowconfigure(1, weight=1)
        cat_box.grid_columnconfigure(0, weight=1)

        cat_title = ctk.CTkLabel(cat_box, text="Spending by Category", font=ctk.CTkFont(size=16, weight="bold"))
        cat_title.grid(row=0, column=0, padx=16, pady=(14, 8), sticky="w")

        self.cat_scroll = ctk.CTkScrollableFrame(cat_box, fg_color="transparent")
        self.cat_scroll.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

        # Right Column: Recent Transactions
        rec_box = ctk.CTkFrame(split_frame, corner_radius=10)
        rec_box.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        rec_box.grid_rowconfigure(1, weight=1)
        rec_box.grid_columnconfigure(0, weight=1)

        rec_title = ctk.CTkLabel(rec_box, text="Recent Transactions", font=ctk.CTkFont(size=16, weight="bold"))
        rec_title.grid(row=0, column=0, padx=16, pady=(14, 8), sticky="w")

        self.rec_scroll = ctk.CTkScrollableFrame(rec_box, fg_color="transparent")
        self.rec_scroll.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

    def _create_metric_card(self, parent, col, title, value, subtext):
        card = ctk.CTkFrame(parent, corner_radius=10)
        card.grid(row=0, column=col, padx=6 if col > 0 and col < 3 else (0 if col == 0 else 6), sticky="ew")

        t_lbl = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=11, weight="bold"), text_color="gray60")
        t_lbl.pack(anchor="w", padx=14, pady=(12, 2))

        v_lbl = ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=22, weight="bold"))
        v_lbl.pack(anchor="w", padx=14, pady=(0, 2))

        s_lbl = ctk.CTkLabel(card, text=subtext, font=ctk.CTkFont(size=11), text_color="gray50")
        s_lbl.pack(anchor="w", padx=14, pady=(0, 12))

        return {"title": t_lbl, "val": v_lbl, "sub": s_lbl}

    def _refresh_dashboard(self):
        stats = db.get_stats()
        curr = db.get_setting("currency", "PKR ")

        self.card_credits["val"].configure(text=f"{curr}{stats.get('total_credit', 0):,.2f}", text_color=("#10b981", "#34d399"))
        self.card_expenses["val"].configure(text=f"{curr}{stats.get('total_expense', 0):,.2f}", text_color=("#ef4444", "#f87171"))

        net_val = stats.get("net_balance", 0.0)
        net_sign = "+" if net_val > 0 else ""
        net_col = ("#10b981", "#34d399") if net_val > 0 else (("#ef4444", "#f87171") if net_val < 0 else ("gray10", "gray90"))
        self.card_net["val"].configure(text=f"{net_sign}{curr}{net_val:,.2f}", text_color=net_col)
        self.card_count["val"].configure(text=str(stats['count']))

        # Clear and rebuild category rows
        for widget in self.cat_scroll.winfo_children():
            widget.destroy()

        if not stats["by_category"]:
            lbl = ctk.CTkLabel(self.cat_scroll, text="No transactions recorded yet.\nClick '+ Scan Receipts' to get started.", text_color="gray50")
            lbl.pack(pady=30)
        else:
            total = stats["total_spent"] or 1.0
            for item in stats["by_category"]:
                cat_row = ctk.CTkFrame(self.cat_scroll, fg_color="transparent")
                cat_row.pack(fill="x", pady=6)
                cat_row.grid_columnconfigure(1, weight=1)

                name_lbl = ctk.CTkLabel(cat_row, text=item["category"], font=ctk.CTkFont(weight="bold"), width=110, anchor="w")
                name_lbl.grid(row=0, column=0, sticky="w")

                pct = (item["total"] / total)
                pbar = ctk.CTkProgressBar(cat_row, height=8)
                pbar.set(pct)
                pbar.grid(row=0, column=1, padx=8, sticky="ew")

                amt_lbl = ctk.CTkLabel(cat_row, text=f"{curr}{item['total']:,.2f} ({int(pct*100)}%)", font=ctk.CTkFont(size=12), text_color="gray70")
                amt_lbl.grid(row=0, column=2, sticky="e")

        # Clear and rebuild recent transactions
        for widget in self.rec_scroll.winfo_children():
            widget.destroy()

        recent = db.get_all_transactions(sort_by="date_desc")[:6]
        if not recent:
            lbl = ctk.CTkLabel(self.rec_scroll, text="No recent transactions.", text_color="gray50")
            lbl.pack(pady=30)
        else:
            for t in recent:
                row = ctk.CTkFrame(self.rec_scroll, fg_color=("gray90", "gray20"), corner_radius=6)
                row.pack(fill="x", pady=4)
                row.grid_columnconfigure(2, weight=1)

                t_type = t.get("tx_type") or "Expense"
                t_badge_col = ("#10b981", "#059669") if t_type == "Credit" else ("#ef4444", "#dc2626")
                amt_col = ("#10b981", "#34d399") if t_type == "Credit" else ("#1f6aa5", "#38bdf8")
                amt_prefix = "+" if t_type == "Credit" else "-"

                d_lbl = ctk.CTkLabel(row, text=t["date"], font=ctk.CTkFont(size=11), text_color="gray60", width=75)
                d_lbl.grid(row=0, column=0, padx=(8, 2), pady=8, sticky="w")

                type_lbl = ctk.CTkLabel(row, text=f" {t_type} ", font=ctk.CTkFont(size=10, weight="bold"), fg_color=t_badge_col, text_color="white", corner_radius=4)
                type_lbl.grid(row=0, column=1, padx=(2, 6), sticky="w")

                m_lbl = ctk.CTkLabel(row, text=t["merchant"], font=ctk.CTkFont(weight="bold"), anchor="w")
                m_lbl.grid(row=0, column=2, padx=5, pady=8, sticky="w")

                amt_lbl = ctk.CTkLabel(row, text=f"{amt_prefix}{t['currency']}{t['total_amount']:,.2f}", font=ctk.CTkFont(weight="bold"), text_color=amt_col)
                amt_lbl.grid(row=0, column=3, padx=(5, 12), pady=8, sticky="e")

    # =========================================================================
    # 2. DATE-WISE FINANCIAL CLOSING TAB
    # =========================================================================
    def _build_closing_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(2, weight=1)

        # Header
        header_frame = ctk.CTkFrame(parent, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        header_frame.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            header_frame,
            text="📅 Date-Wise Financial Closing",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, sticky="w")

        btn_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        btn_box.grid(row=0, column=1, sticky="e")

        cash_day_btn = ctk.CTkButton(
            btn_box,
            text="💵 + Record Cash",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=("#0284c7", "#0369a1"),
            hover_color=("#0369a1", "#075985"),
            command=lambda: self._open_cash_entry_dialog()
        )
        cash_day_btn.pack(side="left", padx=(0, 8))

        upload_day_btn = ctk.CTkButton(
            btn_box,
            text="➕ Upload Receipts for Date...",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._start_day_closing_from_calendar
        )
        upload_day_btn.pack(side="left")

        sub = ctk.CTkLabel(
            parent,
            text="Daily settlement, transaction counts, and financial reconciliations grouped by date.",
            font=ctk.CTkFont(size=13),
            text_color="gray60"
        )
        sub.grid(row=1, column=0, sticky="w", pady=(0, 12))

        # Main Content Box
        closing_box = ctk.CTkFrame(parent, corner_radius=12)
        closing_box.grid(row=2, column=0, sticky="nsew")
        closing_box.grid_columnconfigure(0, weight=1)
        closing_box.grid_rowconfigure(2, weight=1)

        # Top KPI Summary Row for Closings (Row 0)
        self.closing_kpi_frame = ctk.CTkFrame(closing_box, fg_color="transparent")
        self.closing_kpi_frame.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 10))
        for i in range(3):
            self.closing_kpi_frame.grid_columnconfigure(i, weight=1)

        self.kpi_days_card = self._create_metric_card(self.closing_kpi_frame, 0, "TOTAL DAYS LOGGED", "0 Days", "Active transaction days")
        self.kpi_max_day_card = self._create_metric_card(self.closing_kpi_frame, 1, "HIGHEST DAY CLOSING", "$0.00", "Peak daily spending")
        self.kpi_avg_day_card = self._create_metric_card(self.closing_kpi_frame, 2, "AVERAGE DAILY CLOSING", "$0.00", "Per active day")

        # Toolbar (Row 1)
        tb_frame = ctk.CTkFrame(closing_box, fg_color=("gray85", "gray17"), corner_radius=8)
        tb_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 10))
        tb_frame.grid_columnconfigure(0, weight=1)

        self.closing_search = ctk.CTkEntry(tb_frame, placeholder_text="🔍 Filter by date (e.g. 2026-08)...", height=36)
        self.closing_search.grid(row=0, column=0, padx=10, pady=8, sticky="ew")
        self.closing_search.bind("<KeyRelease>", lambda e: self._refresh_closing_tab())

        self.closing_sort_menu = ctk.CTkOptionMenu(
            tb_frame,
            values=["Newest Date First", "Oldest Date First", "Highest Day Total", "Lowest Day Total", "Most Transactions"],
            command=lambda v: self._refresh_closing_tab(),
            width=170,
            height=36
        )
        self.closing_sort_menu.grid(row=0, column=1, padx=6, pady=8)

        export_all_btn = ctk.CTkButton(
            tb_frame,
            text="📥 Export Closings CSV",
            command=self._export_all_closings_action,
            width=160,
            height=36
        )
        export_all_btn.grid(row=0, column=2, padx=(6, 10), pady=8)

        # Scrollable Daily Closings List (Row 2)
        self.closing_scroll = ctk.CTkScrollableFrame(closing_box, fg_color="transparent")
        self.closing_scroll.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.closing_scroll.grid_columnconfigure(0, weight=1)

    def _refresh_closing_tab(self):
        curr = db.get_setting("currency", "PKR ")
        sort_choice = self.closing_sort_menu.get()

        sort_map = {
            "Newest Date First": "date_desc",
            "Oldest Date First": "date_asc",
            "Highest Day Total": "amount_desc",
            "Lowest Day Total": "amount_asc",
            "Most Transactions": "count_desc"
        }
        sort_by = sort_map.get(sort_choice, "date_desc")
        query = self.closing_search.get().strip()

        closings = db.get_daily_closings(sort_by=sort_by)

        if query:
            closings = [c for c in closings if query.lower() in str(c.get("date", "")).lower()]

        # Update KPI Cards
        num_days = len(closings)
        self.kpi_days_card["val"].configure(text=f"{num_days} Days")
        if closings:
            max_day = max(c["total_amount"] for c in closings)
            avg_day = sum(c["total_amount"] for c in closings) / num_days
            self.kpi_max_day_card["val"].configure(text=f"{curr}{max_day:,.2f}")
            self.kpi_avg_day_card["val"].configure(text=f"{curr}{avg_day:,.2f}")
        else:
            self.kpi_max_day_card["val"].configure(text=f"{curr}0.00")
            self.kpi_avg_day_card["val"].configure(text=f"{curr}0.00")

        # Clear and rebuild list
        for w in self.closing_scroll.winfo_children():
            w.destroy()

        if not closings:
            lbl = ctk.CTkLabel(
                self.closing_scroll,
                text="No daily closings recorded yet.\nScan transactions to automatically generate daily settlement sheets.",
                text_color="gray50"
            )
            lbl.pack(pady=40)
            return

        for day in closings:
            d_str = day.get("date") or "Unknown Date"
            c_card = ctk.CTkFrame(self.closing_scroll, fg_color=("gray90", "gray20"), corner_radius=10)
            c_card.pack(fill="x", pady=6)
            c_card.grid_columnconfigure(2, weight=1)

            # Date Badge
            badge_f = ctk.CTkFrame(c_card, fg_color=("gray80", "gray30"), corner_radius=8, width=130)
            badge_f.grid(row=0, column=0, padx=14, pady=12, sticky="w")
            ctk.CTkLabel(badge_f, text="📅 " + d_str, font=ctk.CTkFont(size=13, weight="bold")).pack(padx=10, pady=6)

            # Middle: Breakdown info
            info_f = ctk.CTkFrame(c_card, fg_color="transparent")
            info_f.grid(row=0, column=1, padx=12, pady=10, sticky="w")

            exp_d = day.get("total_expense", 0.0)
            crd_d = day.get("total_credit", 0.0)
            day_curr = day.get("currency") or curr

            m_title = ctk.CTkLabel(
                info_f,
                text=f"{day['count']} Transactions Logged",
                font=ctk.CTkFont(size=14, weight="bold"),
                anchor="w"
            )
            m_title.pack(anchor="w")

            sub_txt = f"🔴 Expenses: {day_curr} {exp_d:,.2f}  |  🟢 Credits: {day_curr} {crd_d:,.2f}"
            s_lbl = ctk.CTkLabel(info_f, text=sub_txt, font=ctk.CTkFont(size=11, weight="bold"), text_color="gray70", anchor="w")
            s_lbl.pack(anchor="w")

            # Right: Daily Closing Amount
            amt_lbl = ctk.CTkLabel(
                c_card,
                text=f"Total: {day_curr} {day['total_amount']:,.2f}",
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=("#1f6aa5", "#38bdf8"),
                width=160,
                anchor="e"
            )
            amt_lbl.grid(row=0, column=3, padx=10, pady=10, sticky="e")

            # Action Buttons
            btn_f = ctk.CTkFrame(c_card, fg_color="transparent")
            btn_f.grid(row=0, column=4, padx=(6, 14), pady=10, sticky="e")

            cash_card_btn = ctk.CTkButton(
                btn_f,
                text="💵 + Cash",
                font=ctk.CTkFont(size=12, weight="bold"),
                width=80,
                height=32,
                fg_color=("#0284c7", "#0369a1"),
                hover_color=("#0369a1", "#075985"),
                command=lambda d=d_str: self._open_cash_entry_dialog(initial_date=d)
            )
            cash_card_btn.pack(side="left", padx=3)

            view_btn = ctk.CTkButton(
                btn_f,
                text="📋 Day Book",
                font=ctk.CTkFont(size=12, weight="bold"),
                width=90,
                height=32,
                command=lambda d=d_str: self._open_day_closing_modal(d)
            )
            view_btn.pack(side="left", padx=3)

            exp_btn = ctk.CTkButton(
                btn_f,
                text="📥",
                width=34,
                height=32,
                fg_color=("gray75", "gray35"),
                hover_color=("gray65", "gray45"),
                command=lambda d=d_str: self._export_single_day_action(d)
            )
            exp_btn.pack(side="left", padx=3)

    def _open_cash_entry_dialog(self, initial_date=None, on_saved=None):
        """Open the Manual Cash Entry dialog."""
        def on_cash_done(d_str):
            self._update_sidebar_stats()
            if self.current_tab == "closing":
                self._refresh_closing_tab()
            elif self.current_tab == "dashboard":
                self._refresh_dashboard()
            elif self.current_tab == "transactions":
                self._refresh_transactions_table()
            if on_saved:
                on_saved(d_str)

        CashEntryDialog(self, initial_date=initial_date, on_saved=on_cash_done)

    def _open_day_closing_modal(self, target_date: str):
        day_data = db.get_closing_summary_for_date(target_date)
        txs = day_data.get("transactions", [])
        curr = db.get_setting("currency", "PKR ")

        dlg = ctk.CTkToplevel(self)
        dlg.title(f"Daily Closing Report - {target_date}")
        dlg.geometry("750x600")
        dlg.transient(self)
        dlg.grab_set()

        dlg.grid_columnconfigure(0, weight=1)
        dlg.grid_rowconfigure(2, weight=1)

        # Header Box
        h_box = ctk.CTkFrame(dlg, fg_color=("gray85", "gray17"), corner_radius=10)
        h_box.grid(row=0, column=0, sticky="ew", padx=16, pady=16)
        h_box.grid_columnconfigure(0, weight=1)

        exp_tot = day_data.get("total_expense", 0.0)
        crd_tot = day_data.get("total_credit", 0.0)
        cash_crd = day_data.get("cash_credit", 0.0)
        bank_crd = day_data.get("bank_credit", 0.0)
        udh_tot = day_data.get("total_udhaar", 0.0)
        udh_ret_tot = day_data.get("total_udhaar_returned", 0.0)
        exp_cash = day_data.get("expense_cash", 0.0)
        exp_bank = day_data.get("expense_bank", 0.0)
        net_tot = crd_tot - exp_tot
        net_sign = "+" if net_tot >= 0 else ""

        ctk.CTkLabel(h_box, text=f"📅 Day Closing Settlement: {target_date}", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, padx=14, pady=(12, 2), sticky="w")
        
        info_banner = f"💵 CASH: {curr} {cash_crd:,.2f}  |  🏦 BANK: {curr} {bank_crd:,.2f}  |  🟣 UDHAAR RETURNED: {curr} {udh_ret_tot:,.2f}  |  🔵 UDHAAR GIVEN: {curr} {udh_tot:,.2f}  |  🔴 EXPENSE: {curr} {exp_cash:,.2f}  |  💎 NET: {net_sign}{curr} {net_tot:,.2f}"
        ctk.CTkLabel(h_box, text=info_banner, font=ctk.CTkFont(size=11, weight="bold"), text_color="gray70").grid(row=1, column=0, padx=14, pady=(0, 12), sticky="w")

        # Payment Method Breakdown Pill Row
        pay_box = ctk.CTkFrame(dlg, fg_color="transparent")
        pay_box.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))
        for p in day_data.get("payment_methods", []):
            badge = ctk.CTkLabel(
                pay_box,
                text=f" {p['payment_method']}: {curr} {p['total']:,.2f} ({p['count']} tx) ",
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color=("gray80", "gray25"),
                corner_radius=6
            )
            badge.pack(side="left", padx=(0, 8))

        # Transactions List (Row 2)
        scroll = ctk.CTkScrollableFrame(dlg, corner_radius=8)
        scroll.grid(row=2, column=0, sticky="nsew", padx=16, pady=4)
        scroll.grid_columnconfigure(2, weight=1)

        for t in txs:
            row = ctk.CTkFrame(scroll, fg_color=("gray90", "gray22"), corner_radius=6)
            row.pack(fill="x", pady=3)
            row.grid_columnconfigure(2, weight=1)

            t_type = t.get("tx_type") or "Expense"
            is_settled = "[PAID" in (t.get("notes") or "")

            if t_type == "Udhaar Recovery" or t.get("category") == "Udhaar Recovery":
                type_badge_color = ("#9333ea", "#7e22ce")
                amt_color = ("#9333ea", "#c084fc")
                amt_prefix = "+"
            elif t_type == "Udhaar":
                type_badge_color = ("#4f46e5", "#4338ca")
                amt_color = ("#4f46e5", "#818cf8")
                amt_prefix = "⏳ "
            elif t_type == "Credit":
                type_badge_color = ("#10b981", "#059669")
                amt_color = ("#10b981", "#34d399")
                amt_prefix = "+"
            elif t_type == "Expense":
                type_badge_color = ("#ef4444", "#dc2626")
                amt_color = ("#ef4444", "#f87171")
                amt_prefix = "-"
            else:
                type_badge_color = ("gray60", "gray40")
                amt_color = ("gray60", "gray50")
                amt_prefix = "📸 "

            ctk.CTkLabel(row, text=f"#{t['id']}", font=ctk.CTkFont(size=11), text_color="gray60", width=35).grid(row=0, column=0, padx=(8, 2), pady=8, sticky="w")
            
            ctk.CTkLabel(row, text=f" {t_type} ", font=ctk.CTkFont(size=10, weight="bold"), fg_color=type_badge_color, text_color="white", corner_radius=4).grid(row=0, column=1, padx=(2, 6), sticky="w")

            m_f = ctk.CTkFrame(row, fg_color="transparent")
            m_f.grid(row=0, column=2, padx=6, pady=6, sticky="w")
            ctk.CTkLabel(m_f, text=t["merchant"], font=ctk.CTkFont(weight="bold"), anchor="w").pack(anchor="w")
            
            sub_t = f"{t['category']} • {t['payment_method']}"
            if t.get("notes"):
                sub_t += f" • {t['notes']}"
            ctk.CTkLabel(m_f, text=sub_t, font=ctk.CTkFont(size=11), text_color="gray60", anchor="w").pack(anchor="w")

            ctk.CTkLabel(row, text=f"{amt_prefix}{t['currency']} {t['total_amount']:,.2f}", font=ctk.CTkFont(size=14, weight="bold"), text_color=amt_color).grid(row=0, column=3, padx=8, pady=8, sticky="e")

            # If Udhaar and not settled, show quick Receive Payment button
            if t_type == "Udhaar" and not is_settled:
                def make_settle(tid=t["id"], cname=t["merchant"]):
                    def do_settle():
                        if messagebox.askyesno("Receive Udhaar Payment", f"Mark Udhaar from {cname} as received into today's Cash closing?"):
                            db.settle_udhaar_transaction(tid, settle_into="Cash")
                            dlg.destroy()
                            self._open_day_closing_modal(target_date)
                            self._refresh_closing_tab()
                    return do_settle

                s_btn = ctk.CTkButton(row, text="Receive Pay", font=ctk.CTkFont(size=11, weight="bold"), width=85, height=28, fg_color=("#10b981", "#059669"), hover_color=("#059669", "#047857"), command=make_settle())
                s_btn.grid(row=0, column=4, padx=(4, 8), pady=6, sticky="e")
            elif t_type == "Udhaar" and is_settled:
                ctk.CTkLabel(row, text="✓ Settled", font=ctk.CTkFont(size=10, weight="bold"), text_color="#10b981").grid(row=0, column=4, padx=(4, 8), pady=6, sticky="e")

        # Footer Buttons
        bot_f = ctk.CTkFrame(dlg, fg_color="transparent")
        bot_f.grid(row=3, column=0, sticky="ew", padx=16, pady=14)
        
        ctk.CTkButton(bot_f, text="📥 Export Day CSV", command=lambda: self._export_single_day_action(target_date), width=130).pack(side="left", padx=(0, 6))
        ctk.CTkButton(bot_f, text="💵 + Add Entry to Date", fg_color=("#0284c7", "#0369a1"), hover_color=("#0369a1", "#075985"), command=lambda: self._open_cash_entry_dialog(initial_date=target_date, on_saved=lambda d: (dlg.destroy(), self._open_day_closing_modal(target_date))), width=155).pack(side="left")
        ctk.CTkButton(bot_f, text="Close", command=dlg.destroy, width=90, fg_color="gray40", hover_color="gray30").pack(side="right")

    def _export_single_day_action(self, target_date: str):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
            initialfile=f"closing_{target_date.replace('-', '')}.csv",
            title=f"Export Closing Report for {target_date}"
        )
        if filepath:
            count = db.export_daily_closing_csv(target_date, filepath)
            messagebox.showinfo("Export Successful", f"Exported {count} transactions for {target_date} to:\n{filepath}")

    def _export_all_closings_action(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
            initialfile=f"Expense_Detail_Month_{datetime.now().strftime('%B_%Y')}.csv",
            title="Export Closing Summary (Rion Month Template)"
        )
        if not filepath:
            return

        count = db.export_rion_template_csv(filepath)
        if count == 0:
            messagebox.showinfo("Export", "No daily closing records found to export.")
            return

        messagebox.showinfo("Export Successful", f"Exported {count} daily closing rows in Rion template format to:\n{filepath}")

    # =========================================================================
    # 3. UPLOAD & SCAN TAB
    # =========================================================================
    def _build_upload_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(2, weight=1)

        # Header
        head = ctk.CTkLabel(parent, text="Scan Receipts & Transactions", font=ctk.CTkFont(size=24, weight="bold"))
        head.grid(row=0, column=0, sticky="w", pady=(0, 4))

        sub = ctk.CTkLabel(
            parent,
            text="Upload one or more photos of receipts, invoices, or transfer slips. Gemini Vision will extract and add them.",
            font=ctk.CTkFont(size=13),
            text_color="gray60"
        )
        sub.grid(row=1, column=0, sticky="w", pady=(0, 14))

        # Main Split Content: Upload Area & Queue
        content_frame = ctk.CTkFrame(parent, fg_color="transparent")
        content_frame.grid(row=2, column=0, sticky="nsew")
        content_frame.grid_columnconfigure(0, weight=4)
        content_frame.grid_columnconfigure(1, weight=6)
        content_frame.grid_rowconfigure(0, weight=1)

        # Left: Drop Zone / Select Button Box (Scrollable to fit all steps)
        drop_box = ctk.CTkScrollableFrame(content_frame, corner_radius=12)
        drop_box.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        drop_box.grid_columnconfigure(0, weight=1)

        # 1. Closing Date Card
        date_card = ctk.CTkFrame(drop_box, fg_color=("gray85", "gray17"), corner_radius=10)
        date_card.pack(padx=10, pady=(10, 10), fill="x")

        ctk.CTkLabel(date_card, text="📅 Step 1: Select Closing Date", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=12, pady=(10, 2))
        ctk.CTkLabel(date_card, text="All receipts uploaded below will close under this date:", font=ctk.CTkFont(size=11), text_color="gray60").pack(anchor="w", padx=12, pady=(0, 6))

        date_input_row = ctk.CTkFrame(date_card, fg_color="transparent")
        date_input_row.pack(fill="x", padx=12, pady=(0, 6))
        date_input_row.grid_columnconfigure(0, weight=1)

        self.closing_date_entry = ctk.CTkEntry(date_input_row, height=34, font=ctk.CTkFont(size=13, weight="bold"))
        self.closing_date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.closing_date_entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        cal_btn = ctk.CTkButton(
            date_input_row,
            text="🗓️ Calendar",
            width=90,
            height=34,
            command=self._open_calendar_for_upload
        )
        cal_btn.grid(row=0, column=1)

        # Quick preset buttons
        preset_row = ctk.CTkFrame(date_card, fg_color="transparent")
        preset_row.pack(fill="x", padx=12, pady=(0, 6))

        today_btn = ctk.CTkButton(
            preset_row,
            text="Today",
            height=26,
            width=65,
            font=ctk.CTkFont(size=11),
            fg_color=("gray75", "gray25"),
            text_color=("gray10", "gray90"),
            command=lambda: self._set_upload_date(datetime.now().strftime("%Y-%m-%d"))
        )
        today_btn.pack(side="left", padx=(0, 4))

        yest_btn = ctk.CTkButton(
            preset_row,
            text="Yesterday",
            height=26,
            width=75,
            font=ctk.CTkFont(size=11),
            fg_color=("gray75", "gray25"),
            text_color=("gray10", "gray90"),
            command=lambda: self._set_upload_date((datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"))
        )
        yest_btn.pack(side="left", padx=4)

        self.override_date_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            date_card,
            text="Use this Closing Date (Ignore slip date)",
            variable=self.override_date_var,
            font=ctk.CTkFont(size=11, weight="bold")
        ).pack(anchor="w", padx=12, pady=(0, 8))

        # 2. Upload Receipts Card (Step 2 - Bank Receipts)
        upload_card = ctk.CTkFrame(drop_box, fg_color=("gray85", "gray17"), corner_radius=10)
        upload_card.pack(padx=10, pady=(0, 10), fill="x")

        ctk.CTkLabel(upload_card, text="📸 Step 2: Upload Bank Slips / Receipts", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=12, pady=(10, 2))
        ctk.CTkLabel(upload_card, text="Select files or a folder to auto-sort under this Closing Date:", font=ctk.CTkFont(size=11), text_color="gray60").pack(anchor="w", padx=12, pady=(0, 8))

        upload_btns_row = ctk.CTkFrame(upload_card, fg_color="transparent")
        upload_btns_row.pack(fill="x", padx=12, pady=(0, 6))
        upload_btns_row.grid_columnconfigure(0, weight=1)
        upload_btns_row.grid_columnconfigure(1, weight=1)

        choose_btn = ctk.CTkButton(
            upload_btns_row,
            text="📁 Select Slip Files...",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=36,
            command=self._select_images_dialog
        )
        choose_btn.grid(row=0, column=0, padx=(0, 4), sticky="ew")

        import_folder_btn = ctk.CTkButton(
            upload_btns_row,
            text="📂 Import Folder...",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=36,
            command=self._import_folder_dialog
        )
        import_folder_btn.grid(row=0, column=1, padx=(4, 0), sticky="ew")

        folder_actions = ctk.CTkFrame(upload_card, fg_color="transparent")
        folder_actions.pack(padx=12, pady=(0, 8), fill="x")
        folder_actions.grid_columnconfigure(0, weight=1)
        folder_actions.grid_columnconfigure(1, weight=1)

        open_folder_btn = ctk.CTkButton(
            folder_actions,
            text="📂 Open Date Folder",
            font=ctk.CTkFont(size=11),
            height=28,
            fg_color=("gray75", "gray30"),
            text_color=("gray10", "gray90"),
            hover_color=("gray65", "gray40"),
            command=self._open_receipts_folder
        )
        open_folder_btn.grid(row=0, column=0, padx=(0, 4), sticky="ew")

        load_folder_btn = ctk.CTkButton(
            folder_actions,
            text="🔄 Re-Scan Folder",
            font=ctk.CTkFont(size=11),
            height=28,
            fg_color=("gray75", "gray30"),
            text_color=("gray10", "gray90"),
            hover_color=("gray65", "gray40"),
            command=self._load_from_receipts_folder
        )
        load_folder_btn.grid(row=0, column=1, padx=(4, 0), sticky="ew")

        # SECTION 1: Extras Deducted Frame
        extras_frame = ctk.CTkFrame(upload_card, fg_color=("gray80", "gray14"), corner_radius=8)
        extras_frame.pack(padx=12, pady=(0, 6), fill="x")

        ctk.CTkLabel(extras_frame, text="✂️ Extras Deducted Section (Optional):", font=ctk.CTkFont(size=11, weight="bold"), text_color="#f87171").pack(anchor="w", padx=10, pady=(6, 2))
        
        ext_grid = ctk.CTkFrame(extras_frame, fg_color="transparent")
        ext_grid.pack(fill="x", padx=10, pady=(0, 6))
        ext_grid.grid_columnconfigure(0, weight=1)
        ext_grid.grid_columnconfigure(1, weight=1)

        self.scan_extras_amount_entry = ctk.CTkEntry(ext_grid, height=28, placeholder_text="Deduction (PKR)")
        self.scan_extras_amount_entry.grid(row=0, column=0, padx=(0, 4), sticky="ew")

        self.scan_extras_reason_entry = ctk.CTkEntry(ext_grid, height=28, placeholder_text="Reason (e.g. Bank Fee)")
        self.scan_extras_reason_entry.grid(row=0, column=1, padx=(4, 0), sticky="ew")

        # SECTION 2: Customer Udhaar Frame
        udhaar_frame = ctk.CTkFrame(upload_card, fg_color=("gray80", "gray14"), corner_radius=8)
        udhaar_frame.pack(padx=12, pady=(0, 10), fill="x")

        ctk.CTkLabel(udhaar_frame, text="📒 Customer Udhaar Section (Optional):", font=ctk.CTkFont(size=11, weight="bold"), text_color="#fbbf24").pack(anchor="w", padx=10, pady=(6, 2))

        self.upload_slip_type_segmented = ctk.CTkSegmentedButton(
            udhaar_frame,
            values=["🏦 Bank Receipt", "📒 Customer Udhaar (Khata)"],
            selected_color=("#0284c7", "#0284c7"),
            height=28
        )
        self.upload_slip_type_segmented.set("🏦 Bank Receipt")
        self.upload_slip_type_segmented.pack(fill="x", padx=10, pady=(0, 4))

        udh_grid = ctk.CTkFrame(udhaar_frame, fg_color="transparent")
        udh_grid.pack(fill="x", padx=10, pady=(0, 6))
        udh_grid.grid_columnconfigure(0, weight=2)
        # Customer List from Khata
        try:
            khata_cust_list = [c["customer_name"] for c in db.get_khata_customers_summary().get("clients", [])]
        except Exception:
            khata_cust_list = []
        if not khata_cust_list:
            khata_cust_list = ["-- Select Customer from Khata --"]

        self.upload_slip_customer_combo = ctk.CTkComboBox(
            udh_grid,
            values=khata_cust_list,
            height=28,
            font=ctk.CTkFont(size=11)
        )
        self.upload_slip_customer_combo.set("-- Select Customer from Khata --")
        self.upload_slip_customer_combo.grid(row=0, column=0, padx=(0, 4), sticky="ew")

        self.upload_udhaar_amount_entry = ctk.CTkEntry(udh_grid, height=28, placeholder_text="Udhaar Amount (PKR)")
        self.upload_udhaar_amount_entry.grid(row=0, column=1, padx=(4, 0), sticky="ew")

        # 3. Write Manual Cash & Cash Expenses Card (Step 3 - CASH & EXPENSE CASH)
        cash_scan_card = ctk.CTkFrame(drop_box, fg_color=("gray85", "gray17"), corner_radius=10)
        cash_scan_card.pack(padx=10, pady=(0, 10), fill="x")

        ctk.CTkLabel(cash_scan_card, text="💵 Step 3: Write Manual Cash & Cash Expense", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=12, pady=(10, 2))
        ctk.CTkLabel(cash_scan_card, text="Manual sales go to CASH, manual expenses go to EXPENSE CASH:", font=ctk.CTkFont(size=11), text_color="gray60").pack(anchor="w", padx=12, pady=(0, 6))

        # Expense vs Credit Selector
        self.scan_cash_type_segmented = ctk.CTkSegmentedButton(
            cash_scan_card,
            values=["🔴 Expense (Expense Cash)", "🟢 Credit (Cash In / Sales)"],
            selected_color=("#0284c7", "#0284c7"),
            height=32
        )
        self.scan_cash_type_segmented.set("🔴 Expense (Expense Cash)")
        self.scan_cash_type_segmented.pack(fill="x", padx=12, pady=(0, 6))

        # Amount & Category Row
        amt_f = ctk.CTkFrame(cash_scan_card, fg_color="transparent")
        amt_f.pack(fill="x", padx=12, pady=(0, 6))
        amt_f.grid_columnconfigure(0, weight=1)

        self.scan_cash_amount_entry = ctk.CTkEntry(amt_f, height=34, font=ctk.CTkFont(size=14, weight="bold"), placeholder_text=f"Amount ({self.currency}) e.g. 5000")
        self.scan_cash_amount_entry.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self.scan_cash_cat_menu = ctk.CTkOptionMenu(
            amt_f,
            values=["Counter Cash", "Sales", "Petty Cash", "Groceries", "Dining & Food", "Utilities", "Supplies", "Salary", "Rent", "Other"],
            width=120,
            height=34
        )
        self.scan_cash_cat_menu.set("Counter Cash")
        self.scan_cash_cat_menu.grid(row=0, column=1)

        # Description Row (feeds REASON for expenses)
        self.scan_cash_desc_entry = ctk.CTkEntry(cash_scan_card, height=32, placeholder_text="Reason / Description (e.g. Canteen, Salary, Petty Cash)")
        self.scan_cash_desc_entry.pack(fill="x", padx=12, pady=(0, 8))
        self.scan_cash_desc_entry.bind("<Return>", lambda e: self._add_quick_cash_to_queue())
        self.scan_cash_amount_entry.bind("<Return>", lambda e: self._add_quick_cash_to_queue())

        add_cash_queue_btn = ctk.CTkButton(
            cash_scan_card,
            text="➕ Add Cash / Expense to Day's Batch",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=34,
            fg_color=("#0284c7", "#0369a1"),
            hover_color=("#0369a1", "#075985"),
            command=self._add_quick_cash_to_queue
        )
        add_cash_queue_btn.pack(padx=12, pady=(0, 10), fill="x")

        # 4. Save & Record Day Closing Button
        self.start_scan_btn = ctk.CTkButton(
            drop_box,
            text="⚡ Save & Record Day Closing",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=44,
            fg_color="#10b981",
            hover_color="#059669",
            command=self._start_scanning_queue
        )
        self.start_scan_btn.pack(padx=10, pady=(0, 14), fill="x")

        # Right: Batch Queue & Results
        queue_box = ctk.CTkFrame(content_frame, corner_radius=12)
        queue_box.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        queue_box.grid_columnconfigure(0, weight=1)
        queue_box.grid_rowconfigure(1, weight=1)

        q_head_frame = ctk.CTkFrame(queue_box, fg_color="transparent")
        q_head_frame.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 6))
        q_head_frame.grid_columnconfigure(0, weight=1)

        self.q_title = ctk.CTkLabel(q_head_frame, text="Batch Queue (0 files)", font=ctk.CTkFont(size=16, weight="bold"))
        self.q_title.grid(row=0, column=0, sticky="w")

        clear_q_btn = ctk.CTkButton(
            q_head_frame,
            text="Clear Queue",
            width=90,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color="gray40",
            hover_color="gray30",
            command=self._clear_queue
        )
        clear_q_btn.grid(row=0, column=1, sticky="e")

        self.scan_progress = ctk.CTkProgressBar(queue_box, height=6)
        self.scan_progress.set(0)
        self.scan_progress.grid(row=2, column=0, sticky="ew", padx=16, pady=(6, 12))

        self.queue_scroll = ctk.CTkScrollableFrame(queue_box, fg_color="transparent")
        self.queue_scroll.grid(row=1, column=0, sticky="nsew", padx=12, pady=4)

        self._render_queue_empty_message()

    def _render_queue_empty_message(self):
        for w in self.queue_scroll.winfo_children():
            w.destroy()
        lbl = ctk.CTkLabel(
            self.queue_scroll,
            text="No receipts in queue.\nClick 'Browse Files' to select pictures.",
            text_color="gray50"
        )
        lbl.pack(pady=50)

    def _open_calendar_for_upload(self):
        """Open visual calendar modal to pick closing date."""
        cur = self.closing_date_entry.get().strip() or datetime.now().strftime("%Y-%m-%d")
        CalendarDialog(self, initial_date=cur, on_select=self._set_upload_date, title="Select Day Closing Date")

    def _set_upload_date(self, date_str: str):
        """Set the closing date in entry field."""
        self.closing_date_entry.delete(0, "end")
        self.closing_date_entry.insert(0, date_str)

    def _start_day_closing_from_calendar(self):
        """Open calendar from Closing tab and immediately switch to upload for that day."""
        def on_pick(d_str):
            self._set_upload_date(d_str)
            self._show_tab("upload")
        CalendarDialog(self, initial_date=datetime.now().strftime("%Y-%m-%d"), on_select=on_pick, title="Pick Closing Date to Upload")

    def _open_receipts_folder(self):
        """Open the local date-sorted folder in Finder."""
        target_date = self.closing_date_entry.get().strip() or datetime.now().strftime("%Y-%m-%d")
        date_folder = os.path.join(RECEIPTS_DIR, target_date)
        os.makedirs(date_folder, exist_ok=True)
        try:
            ret = subprocess.run(["open", date_folder], capture_output=True, text=True)
            if ret.returncode != 0:
                os.system(f'open "{date_folder}" 2>/dev/null')
        except Exception:
            pass

    def _load_from_receipts_folder(self):
        """Load images for this date from the date folder or receipts dir."""
        target_date = self.closing_date_entry.get().strip() or datetime.now().strftime("%Y-%m-%d")
        date_folder = os.path.join(RECEIPTS_DIR, target_date)
        os.makedirs(date_folder, exist_ok=True)

        valid_exts = (".png", ".jpg", ".jpeg", ".webp", ".heic", ".pdf")
        found = 0
        for root, _, files in os.walk(date_folder):
            for fname in sorted(files):
                if fname.lower().endswith(valid_exts):
                    fpath = os.path.join(root, fname)
                    if not any(item.get("path") == fpath for item in self.batch_queue):
                        self.batch_queue.append({
                            "path": fpath,
                            "filename": f"🏦 BANK: {fname}",
                            "status": "Ready",
                            "is_manual_cash": False,
                            "target_date": target_date,
                            "result": None,
                            "error": None
                        })
                        found += 1
        
        self._update_queue_ui()
        if found > 0:
            messagebox.showinfo("Slips Loaded", f"✅ Loaded {found} slip(s) from {target_date} folder!")
    def _add_quick_cash_to_queue(self):
        raw_amt = self.scan_cash_amount_entry.get().strip()
        if not raw_amt:
            messagebox.showwarning("Cash Amount Missing", "Please enter a valid cash amount in the cash amount field.")
            return

        try:
            amt = float(raw_amt.replace(",", ""))
            if amt <= 0:
                raise ValueError("Must be positive")
        except ValueError:
            messagebox.showwarning("Invalid Amount", "Please enter a valid positive numeric amount.")
            return

        is_credit = "Credit" in self.scan_cash_type_segmented.get()
        tx_type = "Credit" if is_credit else "Expense"
        default_desc = "Counter Cash Sales" if is_credit else "Cash Expense"
        desc = self.scan_cash_desc_entry.get().strip() or default_desc
        cat = self.scan_cash_cat_menu.get()
        curr = db.get_setting("currency", "PKR ")

        type_icon = "🟢 CASH IN" if is_credit else "🔴 EXPENSE CASH"
        self.batch_queue.append({
            "path": None,
            "filename": f"💵 {type_icon}: {curr}{amt:,.2f} - {desc}",
            "status": "Ready",
            "is_manual_cash": True,
            "cash_data": {
                "amount": amt,
                "title": desc,
                "category": cat,
                "tx_type": tx_type,
                "payment_method": "Cash",
                "notes": desc
            },
            "result": None,
            "error": None
        })

        # Reset input fields
        self.scan_cash_amount_entry.delete(0, "end")
        self.scan_cash_desc_entry.delete(0, "end")
        self._update_queue_ui()

    def _import_slip_to_date_folder(self, src_path: str, target_date: str) -> str:
        """
        Safely copies and sorts the slip picture into: receipt_images/<target_date>/
        Uses multiple copy strategies to guarantee success from any location on macOS.
        """
        date_folder = os.path.join(RECEIPTS_DIR, target_date)
        os.makedirs(date_folder, exist_ok=True)

        base_name = os.path.basename(src_path)
        dest_path = os.path.join(date_folder, base_name)

        if os.path.exists(dest_path) and os.path.abspath(dest_path) != os.path.abspath(src_path):
            root, ext = os.path.splitext(base_name)
            dest_path = os.path.join(date_folder, f"{root}_{int(time.time() * 1000) % 1000000}{ext}")

        if os.path.abspath(dest_path) == os.path.abspath(src_path):
            return dest_path

        # 1. Binary streaming copy
        try:
            with open(src_path, "rb") as fsrc:
                with open(dest_path, "wb") as fdst:
                    shutil.copyfileobj(fsrc, fdst)
            return dest_path
        except Exception:
            pass

        # 2. Subprocess cp
        try:
            ret = subprocess.run(["cp", "-f", src_path, dest_path], capture_output=True)
            if ret.returncode == 0 and os.path.exists(dest_path):
                return dest_path
        except Exception:
            pass

        # 3. Shutil copy2
        try:
            shutil.copy2(src_path, dest_path)
            return dest_path
        except Exception:
            pass

        return src_path

    def _select_images_dialog(self):
        target_date = self.closing_date_entry.get().strip() or datetime.now().strftime("%Y-%m-%d")
        filetypes = [
            ("Image Files", "*.png *.jpg *.jpeg *.webp *.heic *.pdf"),
            ("PNG images", "*.png"),
            ("JPEG images", "*.jpg *.jpeg"),
            ("All Files", "*.*")
        ]
        files = filedialog.askopenfilenames(
            title=f"Select Slip Photos to Upload for {target_date}",
            filetypes=filetypes
        )
        if not files:
            return

        added = 0
        for fpath in files:
            final_path = self._import_slip_to_date_folder(fpath, target_date)
            if not any(item.get("path") == final_path for item in self.batch_queue):
                self.batch_queue.append({
                    "path": final_path,
                    "filename": f"🏦 BANK: {os.path.basename(final_path)}",
                    "status": "Ready",
                    "is_manual_cash": False,
                    "target_date": target_date,
                    "result": None,
                    "error": None
                })
                added += 1

        self._update_queue_ui()
        if added > 0:
            messagebox.showinfo("Slips Uploaded", f"✅ Added {added} slip(s) automatically sorted into {target_date} folder!\n\nClick '⚡ Save & Record Day Closing' to process.")

    def _import_folder_dialog(self):
        target_date = self.closing_date_entry.get().strip() or datetime.now().strftime("%Y-%m-%d")
        folder_path = filedialog.askdirectory(
            title=f"Select Folder containing Slips for {target_date}"
        )
        if not folder_path:
            return

        valid_exts = (".png", ".jpg", ".jpeg", ".webp", ".heic", ".pdf")
        added = 0
        for root, _, files in os.walk(folder_path):
            for fname in sorted(files):
                if fname.lower().endswith(valid_exts):
                    fpath = os.path.join(root, fname)
                    final_path = self._import_slip_to_date_folder(fpath, target_date)
                    if not any(item.get("path") == final_path for item in self.batch_queue):
                        self.batch_queue.append({
                            "path": final_path,
                            "filename": f"🏦 BANK: {fname}",
                            "status": "Ready",
                            "is_manual_cash": False,
                            "target_date": target_date,
                            "result": None,
                            "error": None
                        })
                        added += 1

        self._update_queue_ui()
        if added > 0:
            messagebox.showinfo("Folder Imported", f"✅ Imported {added} slip(s) from folder and sorted into {target_date}!\n\nClick '⚡ Save & Record Day Closing' to process.")
        else:
            messagebox.showinfo("No Photos Found", f"No valid image files found in:\n{folder_path}")

    def _clear_queue(self):
        if self.is_scanning:
            messagebox.showwarning("Busy", "Cannot clear queue while scanning is active.")
            return
        self.batch_queue = []
        self._update_queue_ui()

    def _update_queue_ui(self):
        self.q_title.configure(text=f"Batch Queue ({len(self.batch_queue)} items)")
        for w in self.queue_scroll.winfo_children():
            w.destroy()

        if not self.batch_queue:
            self._render_queue_empty_message()
            self.scan_progress.set(0)
            return

        for item in self.batch_queue:
            card = ctk.CTkFrame(self.queue_scroll, fg_color=("gray90", "gray20"), corner_radius=8)
            card.pack(fill="x", pady=4)
            card.grid_columnconfigure(1, weight=1)

            # Icon based on status
            if item.get("is_manual_cash"):
                cdata = item.get("cash_data", {})
                status_icon = "🟢" if cdata.get("tx_type") == "Credit" else "🔴"
            else:
                status_icon = "⏳" if item["status"] == "Scanning..." else ("✅" if item["status"] == "Saved" else ("❌" if item["status"] == "Error" else "📄"))
            icon = ctk.CTkLabel(card, text=status_icon, font=ctk.CTkFont(size=18), width=30)
            icon.grid(row=0, column=0, padx=(10, 5), pady=8)

            info_f = ctk.CTkFrame(card, fg_color="transparent")
            info_f.grid(row=0, column=1, sticky="w", padx=5, pady=8)

            fname = ctk.CTkLabel(info_f, text=item["filename"], font=ctk.CTkFont(weight="bold"), anchor="w")
            fname.pack(anchor="w")

            if item.get("is_manual_cash"):
                cdata = item["cash_data"]
                st_type = cdata.get("tx_type", "Expense")
                color_tag = "#10b981" if st_type == "Credit" else "#ef4444"
                sub_txt = f"{st_type} • {cdata['category']} • Cash Amount: {self.currency}{cdata['amount']:,.2f}"
                sub_lbl = ctk.CTkLabel(info_f, text=sub_txt, font=ctk.CTkFont(size=11, weight="bold"), text_color=color_tag, anchor="w")
                sub_lbl.pack(anchor="w")
            elif item["result"]:
                r = item["result"]
                res_txt = f"{r.get('date', '')} | {r.get('merchant', '')} | {r.get('category', '')} | {r.get('currency', '$')}{r.get('total_amount', 0):.2f}"
                sub_lbl = ctk.CTkLabel(info_f, text=res_txt, font=ctk.CTkFont(size=11), text_color=("#10b981", "#34d399"), anchor="w")
                sub_lbl.pack(anchor="w")
            elif item["error"]:
                err_lbl = ctk.CTkLabel(
                    info_f,
                    text=f"Error: {item['error']}",
                    font=ctk.CTkFont(size=11),
                    text_color="#ef4444",
                    anchor="w",
                    justify="left",
                    wraplength=420
                )
                err_lbl.pack(anchor="w")
            else:
                st_lbl = ctk.CTkLabel(info_f, text="Ready to scan", font=ctk.CTkFont(size=11), text_color="gray50", anchor="w")
                st_lbl.pack(anchor="w")

            # Status Badge
            st_color = "#3b82f6" if item["status"] == "Scanning..." else ("#10b981" if item["status"] == "Saved" else ("#ef4444" if item["status"] == "Error" else "gray50"))
            badge = ctk.CTkLabel(card, text=item["status"], font=ctk.CTkFont(size=11, weight="bold"), text_color=st_color, width=90)
            badge.grid(row=0, column=2, padx=(5, 12), pady=8, sticky="e")

    def _start_scanning_queue(self):
        if self.is_scanning:
            return

        # If user typed cash amount without clicking add, automatically add it
        if self.scan_cash_amount_entry.get().strip():
            self._add_quick_cash_to_queue()

        api_key = db.get_setting("gemini_api_key", "")
        # If there are receipt images to scan, check API key
        has_images = any(not i.get("is_manual_cash") and i["status"] in ["Ready", "Error"] for i in self.batch_queue)
        if has_images and not api_key:
            messagebox.showwarning("API Key Missing", "Please enter your Gemini API Key in the Settings tab before scanning.")
            self._show_tab("settings")
            return

        items_to_process = [i for i in self.batch_queue if i["status"] in ["Ready", "Error"]]
        if not items_to_process:
            messagebox.showinfo("Queue Empty", "No new items (receipts or cash entries) in queue to record.")
            return

        self.is_scanning = True
        self.start_scan_btn.configure(state="disabled", text="⏳ Recording Day Closing...")

        # Run extraction in worker thread
        threading.Thread(target=self._scan_worker, args=(items_to_process, api_key), daemon=True).start()

    def _scan_worker(self, items: List[Dict[str, Any]], api_key: str):
        total = len(items)
        completed = 0
        lock = threading.Lock()
        curr_model = db.get_setting("model_name", extractor.DEFAULT_MODEL)

        # Get the selected closing date from user
        target_closing_date = self.closing_date_entry.get().strip() or datetime.now().strftime("%Y-%m-%d")
        override_date = self.override_date_var.get()

        def process_single(item):
            nonlocal completed
            item["status"] = "Processing..."
            self.after(0, self._update_queue_ui)

            if item.get("is_manual_cash"):
                try:
                    cdata = item["cash_data"]
                    db.add_manual_cash_entry(
                        date=target_closing_date,
                        title=cdata["title"],
                        amount=cdata["amount"],
                        category=cdata["category"],
                        currency=self.currency,
                        payment_method=cdata.get("payment_method", "Cash"),
                        notes=f"Manual Cash {cdata['tx_type']}",
                        tx_type=cdata["tx_type"]
                    )
                    with lock:
                        item["status"] = "Saved"
                        item["result"] = {
                            "merchant": cdata["title"],
                            "total_amount": cdata["amount"],
                            "category": cdata["category"],
                            "currency": self.currency,
                            "date": target_closing_date,
                            "tx_type": cdata["tx_type"]
                        }
                        item["error"] = None
                except Exception as e:
                    with lock:
                        item["status"] = "Error"
                        item["error"] = str(e)
            else:
                try:
                    # Call Gemini Vision Extractor (with model failover & optimized payload)
                    result = extractor.extract_transaction_from_image(item["path"], api_key, model_name=curr_model)

                    # If override is active, use the chosen Closing Date
                    if override_date:
                        final_date = target_closing_date
                        printed_info = f"Slip Date: {result.get('date', 'N/A')}"
                        notes = f"{printed_info} | {result.get('notes', '')}" if result.get('notes') else printed_info
                    else:
                        final_date = result.get("date", target_closing_date)
                        notes = result.get("notes", "")

                    raw_amount = float(result.get("total_amount", 0.0))
                    try:
                        manual_extras = float(self.scan_extras_amount_entry.get().strip().replace(",", "") or "0")
                    except Exception:
                        manual_extras = 0.0
                    manual_reason = self.scan_extras_reason_entry.get().strip()

                    ai_extras = float(result.get("extras_deducted", 0.0))
                    ai_reason = result.get("extras_reason", "")

                    applied_ded = manual_extras if manual_extras > 0 else ai_extras
                    applied_rsn = manual_reason if manual_reason else ai_reason

                    if applied_ded > 0:
                        final_amount = max(0.0, raw_amount - applied_ded)
                        ded_note = f"[✂️ Extras Deducted: PKR {applied_ded:,.2f} ({applied_rsn or 'Deduction'}) | Gross: PKR {raw_amount:,.2f}]"
                        notes = f"{ded_note} {notes}".strip()
                    else:
                        final_amount = raw_amount

                    chosen_cust = self.upload_slip_customer_combo.get().strip()
                    if chosen_cust.startswith("--"):
                        chosen_cust = ""
                    is_udhaar = "Udhaar" in self.upload_slip_type_segmented.get() or bool(chosen_cust)
                    cust_name = chosen_cust

                    try:
                        manual_udh_amt = float(self.upload_udhaar_amount_entry.get().strip().replace(",", "") or "0")
                    except Exception:
                        manual_udh_amt = 0.0

                    if is_udhaar:
                        final_merchant = cust_name or result.get("merchant", "Customer Credit")
                        final_cat = "Customer Credit"
                        final_pm = "Credit / Udhaar"
                        final_type = "Udhaar"
                        if manual_udh_amt > 0:
                            final_amount = manual_udh_amt
                            notes = f"[Udhaar Amount Specified: PKR {manual_udh_amt:,.2f}] {notes}".strip()
                    else:
                        final_merchant = result.get("merchant", "Bank Receipt")
                        final_cat = result.get("category", "Bank Receipt")
                        final_pm = "Bank"
                        final_type = "Credit"

                    with lock:
                        db.add_transaction(
                            date=final_date,
                            merchant=final_merchant,
                            category=final_cat,
                            total_amount=final_amount,
                            currency=result.get("currency", "PKR"),
                            tax_amount=result.get("tax_amount", 0.0),
                            items=result.get("items", []),
                            payment_method=final_pm,
                            image_path=item["path"],
                            notes=notes or f"Slip - {final_merchant}",
                            tx_type=final_type
                        )

                        item["status"] = "Saved"
                        item["result"] = result
                        item["result"]["total_amount"] = final_amount
                        item["error"] = None
                except Exception as e:
                    with lock:
                        item["status"] = "Error"
                        item["error"] = str(e)

            with lock:
                completed += 1
                progress = completed / total
                self.after(0, lambda p=progress: self.scan_progress.set(p))
                self.after(0, self._update_queue_ui)

        # Run 3 workers in parallel for speed
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(process_single, item) for item in items]
            concurrent.futures.wait(futures)

        self.is_scanning = False
        self.after(0, lambda: self._finish_scanning(target_closing_date, completed))

    def _finish_scanning(self, closing_date: str = "", count: int = 0):
        self.start_scan_btn.configure(state="normal", text="⚡ Save & Record Day Closing")
        self._update_sidebar_stats()
        date_msg = f" for Closing Date: {closing_date}" if closing_date else ""
        messagebox.showinfo(
            "Day Closing Saved",
            f"✅ Finished recording {count} item(s){date_msg}!\n\nManual Expenses & Credits have been updated in your ledger.\nAny receipt photos were attached as reference slips."
        )

    # =========================================================================
    # 3. TRANSACTIONS TABLE TAB
    # =========================================================================
    def _build_transactions_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(2, weight=1)

        # Header
        top_frame = ctk.CTkFrame(parent, fg_color="transparent")
        top_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        top_frame.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(top_frame, text="Transactions Explorer", font=ctk.CTkFont(size=24, weight="bold"))
        title.grid(row=0, column=0, sticky="w")

        action_f = ctk.CTkFrame(top_frame, fg_color="transparent")
        action_f.grid(row=0, column=1, sticky="e")

        cash_btn = ctk.CTkButton(
            action_f,
            text="💵 + Add Cash",
            width=110,
            fg_color=("#0284c7", "#0369a1"),
            hover_color=("#0369a1", "#075985"),
            command=self._open_cash_entry_dialog
        )
        cash_btn.pack(side="left", padx=5)

        export_btn = ctk.CTkButton(
            action_f,
            text="📥 Export CSV",
            width=110,
            command=self._export_csv_action
        )
        export_btn.pack(side="left", padx=5)

        manual_btn = ctk.CTkButton(
            action_f,
            text="+ Add Manual",
            width=110,
            command=self._open_manual_add_dialog
        )
        manual_btn.pack(side="left", padx=5)

        # Filter & Search Toolbar (Row 1)
        filter_frame = ctk.CTkFrame(parent, corner_radius=8)
        filter_frame.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        filter_frame.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(filter_frame, placeholder_text="🔍 Search merchant, items, notes...", height=36)
        self.search_entry.grid(row=0, column=0, padx=10, pady=8, sticky="ew")
        self.search_entry.bind("<KeyRelease>", lambda e: self._refresh_transactions_table())

        self.type_filter_menu = ctk.CTkOptionMenu(
            filter_frame,
            values=["All Types", "🔴 Expenses", "🟢 Credits"],
            command=lambda v: self._refresh_transactions_table(),
            width=130,
            height=36
        )
        self.type_filter_menu.grid(row=0, column=1, padx=4, pady=8)

        self.cat_filter_menu = ctk.CTkOptionMenu(
            filter_frame,
            values=["All", "Groceries", "Dining & Food", "Shopping", "Utilities", "Transport & Travel", "Entertainment", "Healthcare", "Business", "Housing", "General", "Other"],
            command=lambda v: self._refresh_transactions_table(),
            width=140,
            height=36
        )
        self.cat_filter_menu.grid(row=0, column=2, padx=4, pady=8)

        self.sort_menu = ctk.CTkOptionMenu(
            filter_frame,
            values=["Newest First", "Oldest First", "Highest Amount", "Lowest Amount", "Merchant A-Z"],
            command=lambda v: self._refresh_transactions_table(),
            width=140,
            height=36
        )
        self.sort_menu.grid(row=0, column=3, padx=(4, 10), pady=8)

        # Transactions Scrollable List (Row 2)
        self.table_scroll = ctk.CTkScrollableFrame(parent, corner_radius=10)
        self.table_scroll.grid(row=2, column=0, sticky="nsew")
        self.table_scroll.grid_columnconfigure(0, weight=1)

    def _refresh_transactions_table(self):
        # Read filter settings
        query = self.search_entry.get().strip()
        cat = self.cat_filter_menu.get()
        sort_choice = self.sort_menu.get()
        type_choice = self.type_filter_menu.get()
        type_filter = "Credit" if "Credit" in type_choice else ("Expense" if "Expense" in type_choice else None)

        sort_map = {
            "Newest First": "date_desc",
            "Oldest First": "date_asc",
            "Highest Amount": "amount_desc",
            "Lowest Amount": "amount_asc",
            "Merchant A-Z": "merchant_asc"
        }
        sort_by = sort_map.get(sort_choice, "date_desc")

        txs = db.get_all_transactions(
            category=cat if cat != "All" else None,
            tx_type=type_filter,
            search_query=query if query else None,
            sort_by=sort_by
        )

        for w in self.table_scroll.winfo_children():
            w.destroy()

        if not txs:
            lbl = ctk.CTkLabel(self.table_scroll, text="No transactions match your search.", text_color="gray50")
            lbl.pack(pady=40)
            return

        for t in txs:
            card = ctk.CTkFrame(self.table_scroll, fg_color=("gray90", "gray20"), corner_radius=8)
            card.pack(fill="x", pady=4)
            card.grid_columnconfigure(3, weight=1)

            t_type = t.get("tx_type") or "Expense"
            t_badge_col = ("#10b981", "#059669") if t_type == "Credit" else ("#ef4444", "#dc2626")
            amt_col = ("#10b981", "#34d399") if t_type == "Credit" else ("#1f6aa5", "#38bdf8")
            amt_prefix = "+" if t_type == "Credit" else "-"

            # Date
            d_lbl = ctk.CTkLabel(card, text=t["date"], font=ctk.CTkFont(size=12), width=85, anchor="w")
            d_lbl.grid(row=0, column=0, padx=(10, 4), pady=10, sticky="w")

            # Type Tag (Credit / Expense)
            type_badge = ctk.CTkLabel(
                card,
                text=f" {t_type} ",
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color=t_badge_col,
                text_color="white",
                corner_radius=4
            )
            type_badge.grid(row=0, column=1, padx=(0, 4), pady=10, sticky="w")

            # Category Tag
            cat_badge = ctk.CTkLabel(
                card,
                text=f" {t['category']} ",
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color=("gray75", "gray30"),
                corner_radius=4
            )
            cat_badge.grid(row=0, column=2, padx=4, pady=10, sticky="w")

            # Merchant & items summary
            info_f = ctk.CTkFrame(card, fg_color="transparent")
            info_f.grid(row=0, column=3, padx=8, pady=6, sticky="w")

            m_lbl = ctk.CTkLabel(info_f, text=t["merchant"], font=ctk.CTkFont(size=14, weight="bold"), anchor="w")
            m_lbl.pack(anchor="w")

            items = t.get("items", [])
            item_text = f"{len(items)} item(s) • {t.get('payment_method', 'Unknown')}"
            if t.get("notes"):
                item_text += f" • {t['notes']}"
            sub_lbl = ctk.CTkLabel(info_f, text=item_text, font=ctk.CTkFont(size=11), text_color="gray60", anchor="w")
            sub_lbl.pack(anchor="w")

            # Amount
            amt_lbl = ctk.CTkLabel(
                card,
                text=f"{amt_prefix}{t['currency']}{t['total_amount']:,.2f}",
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=amt_col,
                width=110,
                anchor="e"
            )
            amt_lbl.grid(row=0, column=4, padx=10, pady=10, sticky="e")

            # Action Buttons
            btn_f = ctk.CTkFrame(card, fg_color="transparent")
            btn_f.grid(row=0, column=5, padx=(6, 12), pady=10, sticky="e")

            view_btn = ctk.CTkButton(
                btn_f,
                text="👁️",
                width=32,
                height=28,
                fg_color="transparent",
                hover_color=("gray80", "gray30"),
                command=lambda tx=t: self._open_details_modal(tx)
            )
            view_btn.pack(side="left", padx=2)

            del_btn = ctk.CTkButton(
                btn_f,
                text="🗑️",
                width=32,
                height=28,
                fg_color="transparent",
                hover_color="#ef4444",
                command=lambda tid=t["id"]: self._delete_transaction_action(tid)
            )
            del_btn.pack(side="left", padx=2)

    def _delete_transaction_action(self, tx_id: int):
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this transaction?"):
            db.delete_transaction(tx_id)
            self._refresh_transactions_table()
            self._update_sidebar_stats()

    def _export_csv_action(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
            initialfile=f"transactions_{datetime.now().strftime('%Y%m%d')}.csv",
            title="Export Transactions to CSV"
        )
        if filepath:
            count = db.export_to_csv(filepath)
            messagebox.showinfo("Export Successful", f"Successfully exported {count} transactions to:\n{filepath}")

    def _open_manual_add_dialog(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Add Transaction Manually")
        dlg.geometry("450x520")
        dlg.transient(self)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text="Add Transaction", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(16, 12))

        form = ctk.CTkFrame(dlg, fg_color="transparent")
        form.pack(padx=24, fill="x")

        # Type Selector (Expense vs Credit)
        ctk.CTkLabel(form, text="Transaction Type:").pack(anchor="w", pady=(4, 2))
        e_type = ctk.CTkSegmentedButton(
            form,
            values=["🔴 Expense", "🟢 Credit"],
            selected_color=("#0284c7", "#0284c7"),
            height=32
        )
        e_type.set("🔴 Expense")
        e_type.pack(fill="x", pady=(0, 8))

        # Merchant
        ctk.CTkLabel(form, text="Merchant / Store / Customer Name:").pack(anchor="w", pady=(4, 2))
        e_merchant = ctk.CTkEntry(form, placeholder_text="e.g. Target, Uber, Customer Name")
        e_merchant.pack(fill="x", pady=(0, 8))

        # Amount & Currency
        row1 = ctk.CTkFrame(form, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 8))
        row1.grid_columnconfigure(0, weight=3)
        row1.grid_columnconfigure(1, weight=1)

        f_amt = ctk.CTkFrame(row1, fg_color="transparent")
        f_amt.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkLabel(f_amt, text="Total Amount:").pack(anchor="w", pady=(0, 2))
        e_amt = ctk.CTkEntry(f_amt, placeholder_text="0.00")
        e_amt.pack(fill="x")

        f_curr = ctk.CTkFrame(row1, fg_color="transparent")
        f_curr.grid(row=0, column=1, sticky="ew")
        ctk.CTkLabel(f_curr, text="Currency:").pack(anchor="w", pady=(0, 2))
        e_curr = ctk.CTkEntry(f_curr)
        e_curr.insert(0, db.get_setting("currency", "PKR "))
        e_curr.pack(fill="x")

        # Date
        ctk.CTkLabel(form, text="Date (YYYY-MM-DD):").pack(anchor="w", pady=(4, 2))
        e_date = ctk.CTkEntry(form)
        e_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        e_date.pack(fill="x", pady=(0, 8))

        # Category
        ctk.CTkLabel(form, text="Category:").pack(anchor="w", pady=(4, 2))
        e_cat = ctk.CTkComboBox(form, values=["Sales", "Groceries", "Dining & Food", "Shopping", "Utilities", "Transport & Travel", "Entertainment", "Healthcare", "Business", "Housing", "General", "Other"])
        e_cat.set("General")
        e_cat.pack(fill="x", pady=(0, 8))

        # Notes
        ctk.CTkLabel(form, text="Notes / Invoice #:").pack(anchor="w", pady=(4, 2))
        e_notes = ctk.CTkEntry(form, placeholder_text="Optional note")
        e_notes.pack(fill="x", pady=(0, 16))

        def save():
            m = e_merchant.get().strip()
            a_str = e_amt.get().strip()
            if not m or not a_str:
                messagebox.showerror("Error", "Merchant and Total Amount are required.", parent=dlg)
                return
            try:
                amt = float(a_str)
            except ValueError:
                messagebox.showerror("Error", "Amount must be a valid number.", parent=dlg)
                return

            chosen_type = "Credit" if "Credit" in e_type.get() else "Expense"
            db.add_transaction(
                date=e_date.get().strip(),
                merchant=m,
                category=e_cat.get(),
                total_amount=amt,
                currency=e_curr.get().strip() or "$",
                notes=e_notes.get().strip(),
                tx_type=chosen_type
            )
            dlg.destroy()
            self._refresh_transactions_table()
            self._update_sidebar_stats()

        ctk.CTkButton(dlg, text="Save Transaction", command=save, height=38, font=ctk.CTkFont(weight="bold")).pack(padx=24, pady=10, fill="x")

    def _open_details_modal(self, tx: Dict[str, Any]):
        dlg = ctk.CTkToplevel(self)
        dlg.title(f"Receipt Details - {tx['merchant']}")
        dlg.geometry("700x580")
        dlg.transient(self)
        dlg.grab_set()

        dlg.grid_columnconfigure(0, weight=1)
        dlg.grid_columnconfigure(1, weight=1)
        dlg.grid_rowconfigure(0, weight=1)

        # Left Column: Image Preview (if image exists)
        left_frame = ctk.CTkFrame(dlg, corner_radius=8)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(16, 8), pady=16)

        img_path = tx.get("image_path", "")
        if img_path and os.path.exists(img_path):
            try:
                pil_img = Image.open(img_path)
                pil_img.thumbnail((300, 480))
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(pil_img.width, pil_img.height))
                img_lbl = ctk.CTkLabel(left_frame, image=ctk_img, text="")
                img_lbl.pack(padx=10, pady=10, expand=True)
            except Exception as e:
                ctk.CTkLabel(left_frame, text=f"Could not load image:\n{e}", text_color="gray50").pack(expand=True)
        else:
            ctk.CTkLabel(left_frame, text="No receipt image attached.", text_color="gray50").pack(expand=True)

        # Right Column: Extracted Info & Line Items
        right_frame = ctk.CTkFrame(dlg, corner_radius=8)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 16), pady=16)
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(right_frame, text=tx["merchant"], font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, padx=14, pady=(14, 4), sticky="w")
        ctk.CTkLabel(right_frame, text=f"Date: {tx['date']} | Category: {tx['category']}", font=ctk.CTkFont(size=12), text_color="gray60").grid(row=1, column=0, padx=14, pady=(0, 8), sticky="w")

        # Total highlight
        tot_box = ctk.CTkFrame(right_frame, fg_color=("gray85", "gray17"), corner_radius=6)
        tot_box.grid(row=2, column=0, padx=14, pady=(0, 10), sticky="ew")
        ctk.CTkLabel(tot_box, text=f"Total: {tx['currency']}{tx['total_amount']:,.2f}", font=ctk.CTkFont(size=18, weight="bold"), text_color=("#1f6aa5", "#38bdf8")).pack(padx=10, pady=8, anchor="w")

        # Items List
        items_scroll = ctk.CTkScrollableFrame(right_frame, fg_color="transparent")
        items_scroll.grid(row=3, column=0, padx=10, pady=4, sticky="nsew")

        items = tx.get("items", [])
        if items:
            ctk.CTkLabel(items_scroll, text="Itemized Breakdown:", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=(0, 4))
            for itm in items:
                row = ctk.CTkFrame(items_scroll, fg_color=("gray90", "gray25"), corner_radius=4)
                row.pack(fill="x", pady=2)
                row.grid_columnconfigure(0, weight=1)

                i_name = itm.get("name", "Item")
                i_qty = itm.get("qty", 1)
                i_pr = itm.get("price", "")

                ctk.CTkLabel(row, text=f"{i_name} (x{i_qty})", font=ctk.CTkFont(size=12)).grid(row=0, column=0, padx=8, pady=4, sticky="w")
                if i_pr:
                    ctk.CTkLabel(row, text=f"{i_pr}", font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=1, padx=8, pady=4, sticky="e")
        else:
            ctk.CTkLabel(items_scroll, text="No itemized breakdown extracted.", text_color="gray50").pack(pady=20)

        # Close button
        ctk.CTkButton(right_frame, text="Close", command=dlg.destroy).grid(row=4, column=0, padx=14, pady=14, sticky="ew")

    # =========================================================================
    # 4. AI ASSISTANT TAB (NATURAL LANGUAGE Q&A)
    # =========================================================================
    def _build_chat_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(2, weight=1)

        # Header
        head = ctk.CTkLabel(parent, text="AI Spending Assistant", font=ctk.CTkFont(size=24, weight="bold"))
        head.grid(row=0, column=0, sticky="w", pady=(0, 4))

        sub = ctk.CTkLabel(
            parent,
            text="Ask natural language questions about your transactions, calculate totals, compare merchants, or ask for insights.",
            font=ctk.CTkFont(size=13),
            text_color="gray60"
        )
        sub.grid(row=1, column=0, sticky="w", pady=(0, 12))

        # Chat History Viewport (Row 2)
        chat_box = ctk.CTkFrame(parent, corner_radius=12)
        chat_box.grid(row=2, column=0, sticky="nsew", pady=(0, 12))
        chat_box.grid_columnconfigure(0, weight=1)
        chat_box.grid_rowconfigure(0, weight=1)

        self.chat_scroll = ctk.CTkScrollableFrame(chat_box, fg_color="transparent")
        self.chat_scroll.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        self.chat_scroll.grid_columnconfigure(0, weight=1)

        # Initial Welcome Message
        self._add_chat_bubble(
            "assistant",
            "🎱 Welcome to Rion Snooker Lounge AI Manager!\n"
            "I have direct access to your local club database, table receipts, daily closings, and customer Khata.\n\n"
            "You can ask me questions like:\n"
            "• 'What is our total table cash vs bank slips this month?'\n"
            "• 'Who owes the highest pending customer Udhaar?'\n"
            "• 'What was our total net profit for August 2026?'\n"
            "• 'How much was spent on staff wages, marker salaries, or generator fuel?'"
        )

        # Quick Suggestion Chips (Row 3)
        chips_frame = ctk.CTkFrame(parent, fg_color="transparent")
        chips_frame.grid(row=3, column=0, sticky="ew", pady=(0, 8))

        suggestions = [
            "🎱 August Net Profit?",
            "👥 Who owes Udhaar?",
            "💵 Total Table Cash?",
            "🔴 Marker Salaries & Expenses"
        ]

        for s in suggestions:
            clean_q = s.split(" ", 1)[1] if " " in s else s
            btn = ctk.CTkButton(
                chips_frame,
                text=s,
                height=28,
                font=ctk.CTkFont(size=12),
                fg_color=("gray85", "gray20"),
                text_color=("gray10", "gray90"),
                hover_color=("gray75", "gray30"),
                command=lambda q=clean_q: self._send_chat_query(q)
            )
            btn.pack(side="left", padx=(0, 6))

        # Chat Input Box (Row 4)
        input_frame = ctk.CTkFrame(parent, corner_radius=10)
        input_frame.grid(row=4, column=0, sticky="ew")
        input_frame.grid_columnconfigure(0, weight=1)

        self.chat_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="Type your question here (e.g. 'How much did I spend at Starbucks?')...",
            height=44
        )
        self.chat_entry.grid(row=0, column=0, padx=(10, 8), pady=8, sticky="ew")
        self.chat_entry.bind("<Return>", lambda e: self._on_chat_submit())

        self.send_btn = ctk.CTkButton(
            input_frame,
            text="Ask AI 🚀",
            font=ctk.CTkFont(weight="bold"),
            width=100,
            height=44,
            command=self._on_chat_submit
        )
        self.send_btn.grid(row=0, column=1, padx=(0, 8), pady=8)

    def _add_chat_bubble(self, role: str, text: str):
        bubble_frame = ctk.CTkFrame(self.chat_scroll, fg_color="transparent")
        bubble_frame.pack(fill="x", pady=6)
        bubble_frame.grid_columnconfigure(0, weight=1)

        is_user = (role == "user")
        bg_color = ("#3b82f6", "#2563eb") if is_user else ("gray85", "gray20")
        txt_color = "white" if is_user else ("gray10", "gray90")
        align = "e" if is_user else "w"

        box = ctk.CTkFrame(bubble_frame, fg_color=bg_color, corner_radius=12)
        box.pack(anchor=align, padx=10)

        lbl = ctk.CTkLabel(
            box,
            text=text,
            font=ctk.CTkFont(size=13),
            text_color=txt_color,
            justify="left",
            wraplength=620
        )
        lbl.pack(padx=14, pady=10)

    def _on_chat_submit(self):
        q = self.chat_entry.get().strip()
        if not q:
            return
        self.chat_entry.delete(0, "end")
        self._send_chat_query(q)

    def _send_chat_query(self, query: str):
        api_key = db.get_setting("gemini_api_key", "")
        if not api_key:
            messagebox.showwarning("API Key Missing", "Please configure your Gemini API Key in Settings first.")
            self._show_tab("settings")
            return

        self._add_chat_bubble("user", query)
        self.send_btn.configure(state="disabled", text="Thinking...")

        # Run AI assistant query in worker thread
        threading.Thread(target=self._chat_worker, args=(query, api_key), daemon=True).start()

    def _chat_worker(self, query: str, api_key: str):
        transactions = db.get_all_transactions()
        stats = db.get_stats()
        model_name = db.get_setting("model_name", extractor.DEFAULT_MODEL)

        answer = extractor.ask_gemini_transactions_question(
            question=query,
            transactions=transactions,
            stats=stats,
            api_key=api_key,
            model_name=model_name
        )

        self.after(0, lambda: self._add_chat_bubble("assistant", answer))
        self.after(0, lambda: self.send_btn.configure(state="normal", text="Ask AI 🚀"))

    # =========================================================================
    # 5. SETTINGS TAB
    # =========================================================================
    def _build_settings_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(parent, corner_radius=10)
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        head = ctk.CTkLabel(scroll, text="Application Settings", font=ctk.CTkFont(size=24, weight="bold"))
        head.pack(anchor="w", pady=(0, 16))

        # 1. Cloud Sync Card (AT TOP)
        cloud_card = ctk.CTkFrame(scroll, corner_radius=10, fg_color=("gray85", "gray17"))
        cloud_card.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(cloud_card, text="☁️ Cloud Database Sync & Backup", font=ctk.CTkFont(size=16, weight="bold"), text_color=("#4f46e5", "#818cf8")).pack(anchor="w", padx=16, pady=(14, 4))
        ctk.CTkLabel(
            cloud_card,
            text="Synchronize your Mac's database with the 24/7 online cloud server (Render / Mobile).",
            font=ctk.CTkFont(size=12),
            text_color="gray60"
        ).pack(anchor="w", padx=16, pady=(0, 12))

        sync_url_f = ctk.CTkFrame(cloud_card, fg_color="transparent")
        sync_url_f.pack(fill="x", padx=16, pady=(0, 10))
        sync_url_f.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(sync_url_f, text="Cloud URL:", font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=0, padx=(0, 8), sticky="w")
        self.cloud_url_entry = ctk.CTkEntry(sync_url_f, height=34)
        self.cloud_url_entry.insert(0, db.get_setting("cloud_url", "https://rion-snooker-lounge-rk51.onrender.com"))
        self.cloud_url_entry.grid(row=0, column=1, sticky="ew", padx=(0, 8))

        sync_btns = ctk.CTkFrame(cloud_card, fg_color="transparent")
        sync_btns.pack(fill="x", padx=16, pady=(0, 16))
        sync_btns.grid_columnconfigure(0, weight=1)
        sync_btns.grid_columnconfigure(1, weight=1)

        pull_btn = ctk.CTkButton(
            sync_btns,
            text="⬇️ Pull Database from Cloud",
            fg_color="#4f46e5",
            hover_color="#4338ca",
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._pull_cloud_database
        )
        pull_btn.grid(row=0, column=0, padx=(0, 6), sticky="ew")

        push_btn = ctk.CTkButton(
            sync_btns,
            text="⬆️ Push Local Database to Cloud",
            fg_color="#059669",
            hover_color="#047857",
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._push_local_database_to_cloud
        )
        push_btn.grid(row=0, column=1, padx=(6, 0), sticky="ew")

        # 2. API Key Section
        api_card = ctk.CTkFrame(scroll, corner_radius=10)
        api_card.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(api_card, text="🔑 Google Gemini API Configuration", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=16, pady=(14, 4))
        ctk.CTkLabel(
            api_card,
            text="Used for optical receipt extraction and the AI spending assistant. You can get a free API key at aistudio.google.com.",
            font=ctk.CTkFont(size=12),
            text_color="gray60"
        ).pack(anchor="w", padx=16, pady=(0, 12))

        key_row = ctk.CTkFrame(api_card, fg_color="transparent")
        key_row.pack(fill="x", padx=16, pady=(0, 10))
        key_row.grid_columnconfigure(0, weight=1)

        self.api_key_entry = ctk.CTkEntry(key_row, placeholder_text="AIzaSy...", show="*", height=38)
        self.api_key_entry.insert(0, db.get_setting("gemini_api_key", ""))
        self.api_key_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.show_key_var = ctk.BooleanVar(value=False)
        show_btn = ctk.CTkCheckBox(key_row, text="Show", variable=self.show_key_var, command=self._toggle_show_key, width=60)
        show_btn.grid(row=0, column=1, padx=(0, 8))

        test_btn = ctk.CTkButton(key_row, text="Test Connection", width=120, height=38, command=self._test_api_key)
        test_btn.grid(row=0, column=2, padx=(0, 8))

        save_key_btn = ctk.CTkButton(key_row, text="Save Key", width=90, height=38, fg_color="#10b981", hover_color="#059669", command=self._save_api_key)
        save_key_btn.grid(row=0, column=3)

        self.api_status_label = ctk.CTkLabel(api_card, text="", font=ctk.CTkFont(size=12))
        self.api_status_label.pack(anchor="w", padx=16, pady=(0, 12))

        # 3. Model & Currency Preferences
        pref_card = ctk.CTkFrame(scroll, corner_radius=10)
        pref_card.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(pref_card, text="⚙️ Preferences", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=16, pady=(14, 12))

        p_grid = ctk.CTkFrame(pref_card, fg_color="transparent")
        p_grid.pack(fill="x", padx=16, pady=(0, 16))
        p_grid.grid_columnconfigure(1, weight=1)

        # AI Model
        ctk.CTkLabel(p_grid, text="AI Vision Model:").grid(row=0, column=0, sticky="w", pady=8)
        self.model_opt = ctk.CTkOptionMenu(
            p_grid,
            values=["gemini-3.6-flash", "gemini-3.1-pro-preview"],
            command=self._on_model_change,
            width=220
        )
        self.model_opt.set(db.get_setting("model_name", extractor.DEFAULT_MODEL))
        self.model_opt.grid(row=0, column=1, sticky="w", padx=16, pady=8)

        # Currency Symbol
        ctk.CTkLabel(p_grid, text="Default Currency:").grid(row=1, column=0, sticky="w", pady=8)
        self.curr_opt = ctk.CTkComboBox(
            p_grid,
            values=["PKR", "Rs", "$", "AED", "SAR", "€", "£", "CAD"],
            command=self._on_currency_change,
            width=220
        )
        self.curr_opt.set(db.get_setting("currency", "PKR "))
        self.curr_opt.grid(row=1, column=1, sticky="w", padx=16, pady=8)

        # 4. Data Management / Danger Zone
        danger_card = ctk.CTkFrame(scroll, corner_radius=10)
        danger_card.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(danger_card, text="🗑️ Data Management", font=ctk.CTkFont(size=16, weight="bold"), text_color="#ef4444").pack(anchor="w", padx=16, pady=(14, 4))
        ctk.CTkLabel(danger_card, text="Permanently delete all transaction records from your local SQLite database.", font=ctk.CTkFont(size=12), text_color="gray60").pack(anchor="w", padx=16, pady=(0, 12))

        clear_btn = ctk.CTkButton(
            danger_card,
            text="Clear All Transactions",
            fg_color="#ef4444",
            hover_color="#dc2626",
            command=self._clear_all_data
        )
        clear_btn.pack(anchor="w", padx=16, pady=(0, 16))

    def _pull_cloud_database(self):
        cloud_url = self.cloud_url_entry.get().strip().rstrip("/")
        if not cloud_url:
            messagebox.showwarning("Error", "Please enter a valid Cloud URL.")
            return
        db.set_setting("cloud_url", cloud_url)
        self._do_pull_from_cloud(cloud_url)

    def _do_pull_from_cloud(self, cloud_url: str):
        if not messagebox.askyesno("Confirm Sync", "Are you sure you want to pull the latest database from the Cloud? This will update your local database records with the cloud data."):
            return

        try:
            import requests
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

            res = requests.get(f"{cloud_url}/api/backup/download-db", timeout=30, verify=False)
            if res.status_code != 200:
                raise Exception(f"Server returned status {res.status_code}: {res.text}")

            content = res.content
            if len(content) < 100:
                raise Exception("Downloaded database is empty or invalid.")

            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transactions.db")
            temp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transactions_temp.db")
            with open(temp_path, "wb") as f:
                f.write(content)
            shutil.move(temp_path, db_path)
            db.init_db()

            self._refresh_dashboard()
            self._refresh_closing_tab()
            self._refresh_khata_tab()
            self._refresh_staff_tab()
            self._update_sidebar_stats()
            messagebox.showinfo("Sync Success", "✅ Successfully pulled latest database from Cloud!")
        except Exception as e:
            messagebox.showerror("Sync Failed", f"Failed to pull from Cloud:\n{str(e)}")

    def _push_local_database_to_cloud(self):
        cloud_url = self.cloud_url_entry.get().strip().rstrip("/")
        if not cloud_url:
            messagebox.showwarning("Error", "Please enter a valid Cloud URL.")
            return
        db.set_setting("cloud_url", cloud_url)
        self._do_push_to_cloud(cloud_url)

    def _do_push_to_cloud(self, cloud_url: str):
        if not messagebox.askyesno("Confirm Upload", "Are you sure you want to push your local database to the Cloud? This will update the online web database with your Mac's current records."):
            return

        try:
            import requests
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transactions.db")
            with open(db_path, "rb") as f:
                files = {"file": ("transactions.db", f, "application/x-sqlite3")}
                res = requests.post(f"{cloud_url}/api/backup/upload-db", files=files, timeout=30, verify=False)

            if res.status_code == 200:
                messagebox.showinfo("Upload Success", "✅ Successfully pushed local database to Cloud!")
            else:
                messagebox.showerror("Upload Failed", f"Cloud server responded with error: {res.text}")
        except Exception as e:
            messagebox.showerror("Upload Failed", f"Failed to push to Cloud:\n{str(e)}")

    def _toggle_show_key(self):
        if self.show_key_var.get():
            self.api_key_entry.configure(show="")
        else:
            self.api_key_entry.configure(show="*")

    def _save_api_key(self):
        k = self.api_key_entry.get().strip()
        db.set_setting("gemini_api_key", k)
        self.api_status_label.configure(text="✅ API Key saved locally.", text_color="#10b981")

    def _test_api_key(self):
        k = self.api_key_entry.get().strip()
        if not k:
            self.api_status_label.configure(text="❌ Please enter an API key first.", text_color="#ef4444")
            return

        self.api_status_label.configure(text="Testing connection to Gemini API...", text_color="gray60")

        def test_worker():
            res = extractor.test_api_connection(k, self.model_opt.get())
            if res["success"]:
                self.after(0, lambda: self.api_status_label.configure(text=f"✅ {res['message']}", text_color="#10b981"))
            else:
                self.after(0, lambda: self.api_status_label.configure(text=f"❌ {res['error']}", text_color="#ef4444"))

        threading.Thread(target=test_worker, daemon=True).start()

    def _on_model_change(self, choice: str):
        db.set_setting("model_name", choice)

    def _on_currency_change(self, choice: str):
        db.set_setting("currency", choice)
        self._update_sidebar_stats()

    def _clear_all_data(self):
        if messagebox.askyesno("Confirm Clear All", "⚠️ Are you sure you want to delete ALL transactions?\nThis action cannot be undone."):
            db.clear_all_transactions()
            self._update_sidebar_stats()
            messagebox.showinfo("Cleared", "All transactions have been deleted.")



    def _open_resign_dialog(self, staff_id, staff_name):
        dlg = ctk.CTkToplevel(self)
        dlg.title(f"🚪 Settle Resignation: {staff_name}")
        dlg.geometry("480x520")
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text=f"Staff Resignation & Settlement: {staff_name}", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(16, 4))
        ctk.CTkLabel(dlg, text="Calculates earned days in final month + 10-day security deposit refund.", font=ctk.CTkFont(size=11), text_color="gray60").pack(pady=(0, 12))

        form = ctk.CTkFrame(dlg, fg_color="transparent")
        form.pack(fill="x", padx=20)

        # 1. Leave Date
        ctk.CTkLabel(form, text="Leaving Date (YYYY-MM-DD):", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(0, 2))
        date_entry = ctk.CTkEntry(form, height=32)
        date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        date_entry.pack(fill="x", pady=(0, 8))

        # 2. Refund Security Checkbox & Deductions
        opt_f = ctk.CTkFrame(form, fg_color=("gray85", "gray20"), corner_radius=8)
        opt_f.pack(fill="x", pady=(0, 10))

        refund_sec_var = ctk.BooleanVar(value=True)
        sec_chk = ctk.CTkCheckBox(opt_f, text="🔒 Refund 10 Days Security Deposit", variable=refund_sec_var, font=ctk.CTkFont(size=12, weight="bold"))
        sec_chk.pack(anchor="w", padx=12, pady=(10, 6))

        ded_f = ctk.CTkFrame(opt_f, fg_color="transparent")
        ded_f.pack(fill="x", padx=12, pady=(0, 10))
        ctk.CTkLabel(ded_f, text="Deductions (Damages/Loss):", font=ctk.CTkFont(size=11)).pack(side="left")
        ded_entry = ctk.CTkEntry(ded_f, width=110, height=28)
        ded_entry.insert(0, "0")
        ded_entry.pack(side="right")

        # 3. Calculated Settlement Box
        calc_box = ctk.CTkFrame(form, fg_color=("gray80", "gray15"), corner_radius=8)
        calc_box.pack(fill="x", pady=(0, 10))

        days_lbl = ctk.CTkLabel(calc_box, text="Days worked in final month: ...", font=ctk.CTkFont(size=11), text_color="gray60")
        days_lbl.pack(anchor="w", padx=12, pady=(8, 2))

        earned_lbl = ctk.CTkLabel(calc_box, text="Earned month salary: ...", font=ctk.CTkFont(size=11), text_color="#10b981")
        earned_lbl.pack(anchor="w", padx=12, pady=(0, 2))

        sec_lbl = ctk.CTkLabel(calc_box, text="Security refund: ...", font=ctk.CTkFont(size=11), text_color="#818cf8")
        sec_lbl.pack(anchor="w", padx=12, pady=(0, 2))

        total_lbl = ctk.CTkLabel(calc_box, text="Net Final Settlement: PKR 0.00", font=ctk.CTkFont(size=14, weight="bold"), text_color=("#d97706", "#f59e0b"))
        total_lbl.pack(anchor="w", padx=12, pady=(2, 8))

        calc_res = {"amount": 0.0}

        def recalc(*args):
            l_date = date_entry.get().strip() or datetime.now().strftime("%Y-%m-%d")
            r_sec = refund_sec_var.get()
            try:
                d_val = float(ded_entry.get().strip() or "0")
            except Exception:
                d_val = 0.0

            try:
                res = db.calculate_staff_settlement(staff_id=staff_id, leave_date=l_date, refund_security=r_sec, deductions=d_val)
                days_lbl.configure(text=f"Days worked in final month: {res['days_worked_in_final_month']} days")
                earned_lbl.configure(text=f"Earned final month salary: {self.currency}{res['earned_salary']:,.2f}")
                sec_lbl.configure(text=f"Security refund: +{self.currency}{res['security_refund_amount']:,.2f}")
                total_lbl.configure(text=f"Net Final Settlement: {self.currency}{res['net_settlement_payable']:,.2f}")
                calc_res["amount"] = res["net_settlement_payable"]
            except Exception as e:
                total_lbl.configure(text=f"Calculation Error: {e}")

        date_entry.bind("<KeyRelease>", recalc)
        ded_entry.bind("<KeyRelease>", recalc)
        sec_chk.configure(command=recalc)
        recalc()

        ctk.CTkLabel(form, text="Payment Method:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", pady=(0, 2))
        method_opt = ctk.CTkOptionMenu(form, values=["Cash", "Bank"], height=30)
        method_opt.set("Cash")
        method_opt.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(form, text="Notes / Handover Reason:", font=ctk.CTkFont(size=11)).pack(anchor="w", pady=(0, 2))
        notes_entry = ctk.CTkEntry(form, height=30, placeholder_text="e.g. Left with clean handover / Full security refunded")
        notes_entry.pack(fill="x", pady=(0, 14))

        def confirm_resignation():
            amt = calc_res["amount"]
            l_date = date_entry.get().strip() or datetime.now().strftime("%Y-%m-%d")
            if messagebox.askyesno("Confirm Settlement", f"Confirm resignation and final settlement for {staff_name}?\n\nTotal Payout: {self.currency}{amt:,.2f}\nEffective Date: {l_date}"):
                try:
                    d_val = float(ded_entry.get().strip() or "0")
                except Exception:
                    d_val = 0.0

                db.settle_resigned_staff(
                    staff_id=staff_id,
                    leave_date=l_date,
                    final_amount=amt,
                    refund_security=refund_sec_var.get(),
                    deductions=d_val,
                    payment_method=method_opt.get(),
                    notes=notes_entry.get().strip(),
                    pay_now=True
                )
                dlg.destroy()
                messagebox.showinfo("Success", f"Recorded resignation & settlement of {self.currency}{amt:,.2f} for {staff_name}!")
                self._refresh_staff_tab()
                if hasattr(self, "_refresh_closing_tab"):
                    self._refresh_closing_tab()

        ctk.CTkButton(dlg, text="🚪 Confirm Resignation & Pay Settlement", height=38, font=ctk.CTkFont(weight="bold"), fg_color="#d97706", hover_color="#b45309", command=confirm_resignation).pack(fill="x", padx=20)


if __name__ == "__main__":
    app = TransactionApp()
    app.mainloop()
