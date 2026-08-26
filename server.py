import os
import shutil
import time
import json
import asyncio
from datetime import datetime
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import db
import extractor

# Initialize database
db.init_db()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")
RECEIPTS_DIR = os.path.join(BASE_DIR, "receipt_images")
os.makedirs(WEB_DIR, exist_ok=True)
os.makedirs(RECEIPTS_DIR, exist_ok=True)

app = FastAPI(title="TransactionAI Web", version="2.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Schemas
class ManualEntryRequest(BaseModel):
    date: str
    amount: float
    tx_type: str  # "Credit" or "Expense"
    category: str
    description: str


class SettingsUpdateRequest(BaseModel):
    currency: Optional[str] = None
    gemini_api_key: Optional[str] = None
    theme: Optional[str] = None


class ChatRequest(BaseModel):
    message: str


# =============================================================================
# API ROUTES
# =============================================================================

@app.get("/api/stats")
def get_stats():
    return db.get_stats()


@app.get("/api/closings")
def get_closings(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    sort_by: str = Query("date_desc")
):
    return db.get_daily_closings(date_from=date_from, date_to=date_to, sort_by=sort_by)


@app.get("/api/closings/{target_date}")
def get_closing_for_date(target_date: str):
    return db.get_closing_summary_for_date(target_date)


class SettleUdhaarRequest(BaseModel):
    tx_id: int
    settle_into: str = "Cash"
    settle_date: Optional[str] = None


@app.post("/api/entry")
def add_manual_entry(payload: ManualEntryRequest):
    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than zero.")

    curr = db.get_setting("currency", "PKR ")
    type_lower = payload.tx_type.lower()
    
    if "return" in type_lower or "wapsi" in type_lower or "recovery" in type_lower:
        final_tx_type = "Udhaar Recovery"
        pay_method = "Cash"
        cust_name = payload.description or "Customer"
        notes = f"Udhaar Returned by {cust_name}"
        category = "Udhaar Recovery"
    elif "udhaar" in type_lower or "customer" in type_lower:
        final_tx_type = "Udhaar"
        pay_method = "Udhaar"
        cust_name = payload.description or "Customer Credit"
        notes = f"Customer Udhaar: {cust_name}"
        category = payload.category or "Customer Credit"
    elif type_lower == "credit":
        final_tx_type = "Credit"
        pay_method = "Cash"
        cust_name = payload.description or "Counter Cash Sales"
        notes = payload.description or "Counter Cash Sales"
        category = payload.category or "Counter Cash"
    else:
        final_tx_type = "Expense"
        pay_method = "Cash"
        cust_name = payload.description or "Cash Expense"
        notes = payload.description or "Cash Expense"
        category = payload.category or "Daily Expense"

    tx_id = db.add_manual_cash_entry(
        date=payload.date,
        title=cust_name,
        amount=payload.amount,
        category=category,
        currency=curr,
        payment_method=pay_method,
        notes=notes,
        tx_type=final_tx_type
    )

    return {
        "success": True,
        "transaction_id": tx_id,
        "message": f"Successfully added {final_tx_type} entry of {curr}{payload.amount:,.2f}"
    }


@app.post("/api/settle-udhaar")
def settle_udhaar(payload: SettleUdhaarRequest):
    success = db.settle_udhaar_transaction(
        tx_id=payload.tx_id,
        settle_into=payload.settle_into,
        settle_date=payload.settle_date
    )
    if not success:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    return {"success": True, "message": "Udhaar payment received & recorded into closing!"}


@app.post("/api/upload-slips")
async def upload_slips(
    target_date: str = Form(...),
    slip_type: str = Form("Bank Receipt"),
    customer_name: str = Form(""),
    udhaar_amount: float = Form(0.0),
    extras_deducted: float = Form(0.0),
    extras_reason: str = Form(""),
    files: List[UploadFile] = File(...)
):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    date_dir = os.path.join(RECEIPTS_DIR, target_date)
    os.makedirs(date_dir, exist_ok=True)

    api_key = db.get_setting("gemini_api_key", os.environ.get("GEMINI_API_KEY", ""))
    curr = db.get_setting("currency", "$")

    saved_items = []

    for file in files:
        fname = file.filename or f"slip_{int(time.time()*1000)}.jpg"
        dest_path = os.path.join(date_dir, fname)

        if os.path.exists(dest_path):
            base, ext = os.path.splitext(fname)
            dest_path = os.path.join(date_dir, f"{base}_{int(time.time()*1000)%1000000}{ext}")

        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        try:
            extracted = extractor.extract_transaction_from_image(dest_path, api_key=api_key)
            raw_amount = float(extracted.get("total_amount", 0.0))
            ai_extras = float(extracted.get("extras_deducted", 0.0))
            ai_reason = extracted.get("extras_reason", "")

            # Apply manual user deduction if provided, otherwise use AI-extracted deduction
            applied_deduction = extras_deducted if extras_deducted > 0 else ai_extras
            applied_reason = extras_reason if extras_reason else ai_reason

            if applied_deduction > 0:
                final_amount = max(0.0, raw_amount - applied_deduction)
                deduction_note = f"[✂️ Extras Deducted: PKR {applied_deduction:,.2f} ({applied_reason or 'Deduction'}) | Gross: PKR {raw_amount:,.2f}]"
            else:
                final_amount = raw_amount
                deduction_note = ""

            is_udhaar = slip_type == "Udhaar" or bool(customer_name.strip())

            if is_udhaar:
                final_merchant = customer_name.strip() or extracted.get("merchant") or "Customer Credit"
                final_category = "Customer Credit"
                final_payment_method = "Credit / Udhaar"
                final_tx_type = "Udhaar"
                if udhaar_amount > 0:
                    final_amount = udhaar_amount
                    udhaar_note = f"[Udhaar Amount Specified: PKR {udhaar_amount:,.2f}]"
                    deduction_note = f"{udhaar_note} {deduction_note}".strip()
            else:
                final_merchant = extracted.get("merchant") or "Bank Transfer Slip"
                final_category = "Bank Receipt"
                final_payment_method = "Bank"
                final_tx_type = "Credit"

            base_notes = f"Slip Date: {extracted.get('date', 'N/A')} | {extracted.get('notes', '')}".strip(" |")
            full_notes = f"{deduction_note} {base_notes}".strip()

            tx_id = db.add_transaction(
                date=target_date,
                merchant=final_merchant,
                category=final_category,
                total_amount=final_amount,
                currency=curr,
                tax_amount=float(extracted.get("tax_amount", 0.0)),
                items=extracted.get("items", []),
                payment_method=final_payment_method,
                image_path=dest_path,
                notes=full_notes or f"Slip - {final_merchant}",
                tx_type=final_tx_type
            )

            saved_items.append({
                "transaction_id": tx_id,
                "filename": os.path.basename(dest_path),
                "merchant": final_merchant,
                "category": final_category,
                "tx_type": final_tx_type,
                "gross_amount": raw_amount,
                "extras_deducted": applied_deduction,
                "amount": final_amount,
                "status": "Success"
            })
        except Exception as e:
            tx_id = db.add_transaction(
                date=target_date,
                merchant="Bank Slip (Manual Review)",
                category="Bank Receipt",
                total_amount=0.0,
                currency=curr,
                tax_amount=0.0,
                items=[],
                payment_method="Bank",
                image_path=dest_path,
                notes=f"AI Scan Error: {str(e)}",
                tx_type="Credit"
            )
            saved_items.append({
                "transaction_id": tx_id,
                "filename": os.path.basename(dest_path),
                "merchant": "Bank Slip (Manual Review)",
                "amount": 0.0,
                "status": "Warning",
                "error": str(e)
            })

    return {
        "success": True,
        "date": target_date,
        "processed_count": len(saved_items),
        "items": saved_items
    }


@app.get("/api/khata")
def get_khata_summary():
    return db.get_khata_customers_summary()


@app.get("/api/khata/{customer_name}")
def get_customer_khata(customer_name: str):
    return db.get_customer_khata_history(customer_name)


class CustomerCreateRequest(BaseModel):
    name: str
    phone: str = ""
    initial_balance: float = 0.0
    notes: str = ""
    date: Optional[str] = None


class CustomerUpdateRequest(BaseModel):
    new_name: Optional[str] = None
    phone: str = ""
    notes: str = ""


class AddUdhaarRequest(BaseModel):
    customer_name: str
    amount: float
    date: Optional[str] = None
    notes: str = ""


@app.post("/api/khata/customers")
def create_khata_customer(req: CustomerCreateRequest):
    if not req.name.strip():
        raise HTTPException(status_code=400, detail="Customer name is required")
    res = db.add_khata_customer(
        name=req.name,
        phone=req.phone,
        initial_balance=req.initial_balance,
        notes=req.notes,
        date=req.date or ""
    )
    return {"success": True, "data": res}


@app.put("/api/khata/customers/{customer_name}")
def edit_khata_customer(customer_name: str, req: CustomerUpdateRequest):
    res = db.update_khata_customer(
        old_name=customer_name,
        new_name=req.new_name or customer_name,
        phone=req.phone,
        notes=req.notes
    )
    return {"success": True, "data": res}


@app.delete("/api/khata/customers/{customer_name}")
def delete_customer_from_khata(customer_name: str):
    db.delete_khata_customer(customer_name=customer_name)
    return {"success": True, "message": f"Customer '{customer_name}' removed from directory."}


@app.post("/api/khata/add-udhaar")
def add_udhaar_direct(req: AddUdhaarRequest):
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="Udhaar amount must be greater than 0")
    tx_id = db.add_manual_udhaar_entry(
        customer_name=req.customer_name,
        amount=req.amount,
        date=req.date or "",
        notes=req.notes
    )
    return {"success": True, "transaction_id": tx_id, "message": f"Added PKR {req.amount:,.2f} Udhaar for {req.customer_name}"}


class StaffCreateRequest(BaseModel):
    name: str
    role: str = "Marker"
    phone: str = ""
    salary_type: str = "Monthly"
    base_salary: float = 0.0
    hire_date: Optional[str] = None
    notes: str = ""


class StaffUpdateRequest(BaseModel):
    name: str
    role: str = "Marker"
    phone: str = ""
    salary_type: str = "Monthly"
    base_salary: float = 0.0
    status: str = "Active"
    notes: str = ""


class StaffPayRequest(BaseModel):
    staff_id: int
    amount: float
    pay_date: Optional[str] = None
    payment_method: str = "Cash"
    notes: str = ""


@app.get("/api/monthly-closing")
def get_monthly_closing(month: Optional[str] = Query(None)):
    return db.get_monthly_closing_summary(target_month=month)


@app.get("/api/staff")
def get_staff_summary(month: Optional[str] = Query(None)):
    return db.get_staff_salary_summary(target_month=month)


@app.post("/api/staff")
def create_staff(payload: StaffCreateRequest):
    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="Staff name is required.")
    staff_id = db.add_staff(
        name=payload.name,
        role=payload.role,
        phone=payload.phone,
        salary_type=payload.salary_type,
        base_salary=payload.base_salary,
        hire_date=payload.hire_date or "",
        notes=payload.notes
    )
    return {"success": True, "staff_id": staff_id, "message": f"Added staff member {payload.name}"}


@app.put("/api/staff/{staff_id}")
def edit_staff(staff_id: int, payload: StaffUpdateRequest):
    success = db.update_staff(
        staff_id=staff_id,
        name=payload.name,
        role=payload.role,
        phone=payload.phone,
        salary_type=payload.salary_type,
        base_salary=payload.base_salary,
        status=payload.status,
        notes=payload.notes
    )
    if not success:
        raise HTTPException(status_code=404, detail="Staff member not found.")
    return {"success": True, "message": f"Updated staff member {payload.name}"}


@app.delete("/api/staff/{staff_id}")
def remove_staff(staff_id: int):
    success = db.delete_staff(staff_id)
    if not success:
        raise HTTPException(status_code=404, detail="Staff member not found.")
    return {"success": True, "message": f"Deleted staff member #{staff_id}"}


@app.post("/api/staff/pay")
def pay_salary(payload: StaffPayRequest):
    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than zero.")
    try:
        tx_id = db.pay_staff_salary(
            staff_id=payload.staff_id,
            amount=payload.amount,
            pay_date=payload.pay_date,
            payment_method=payload.payment_method,
            notes=payload.notes
        )
        return {"success": True, "transaction_id": tx_id, "message": "Salary payment recorded successfully."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class StaffResignRequest(BaseModel):
    leave_date: str
    final_amount: float
    refund_security: bool = True
    deductions: float = 0.0
    payment_method: str = "Cash"
    notes: str = ""
    pay_now: bool = True


@app.get("/api/staff/{staff_id}/calculate-settlement")
def calculate_settlement(
    staff_id: int,
    leave_date: Optional[str] = Query(None),
    refund_security: bool = Query(True),
    deductions: float = Query(0.0)
):
    try:
        return db.calculate_staff_settlement(
            staff_id=staff_id,
            leave_date=leave_date or datetime.now().strftime("%Y-%m-%d"),
            refund_security=refund_security,
            deductions=deductions
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/staff/{staff_id}/settle-resignation")
def settle_resignation(staff_id: int, payload: StaffResignRequest):
    try:
        return db.settle_resigned_staff(
            staff_id=staff_id,
            leave_date=payload.leave_date,
            final_amount=payload.final_amount,
            refund_security=payload.refund_security,
            deductions=payload.deductions,
            payment_method=payload.payment_method,
            notes=payload.notes,
            pay_now=payload.pay_now
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/staff/{staff_name}/history")
def get_staff_history(staff_name: str):
    return db.get_staff_payout_history(staff_name)


@app.post("/api/staff/{staff_id}/reopen")
def reopen_staff(staff_id: int):
    success = db.reopen_resigned_staff(staff_id)
    if not success:
        raise HTTPException(status_code=404, detail="Staff member not found.")
    return {"success": True, "message": f"Staff member #{staff_id} reactivated to Active."}


@app.delete("/api/transaction/{tx_id}")
def delete_transaction(tx_id: int):
    success = db.delete_transaction(tx_id)
    if not success:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    return {"success": True, "message": f"Deleted transaction #{tx_id}"}


@app.get("/api/export-csv")
def export_csv(month_year: Optional[str] = Query(None)):
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_filename = f"Expense_Detail_Month_{month_year or datetime.now().strftime('%B_%Y')}_{now_str}.csv"
    temp_path = os.path.join(BASE_DIR, export_filename)

    count = db.export_rion_template_csv(temp_path, month_year=month_year)
    if count == 0:
        raise HTTPException(status_code=404, detail="No closing records found to export.")

    return FileResponse(
        temp_path,
        filename=export_filename,
        media_type="text/csv"
    )


@app.get("/api/settings")
def get_settings():
    return {
        "currency": db.get_setting("currency", "PKR "),
        "has_gemini_key": bool(db.get_setting("gemini_api_key") or os.environ.get("GEMINI_API_KEY")),
        "theme": db.get_setting("theme", "system")
    }


@app.post("/api/settings")
def update_settings(payload: SettingsUpdateRequest):
    if payload.currency is not None:
        db.set_setting("currency", payload.currency)
    if payload.gemini_api_key is not None:
        db.set_setting("gemini_api_key", payload.gemini_api_key)
    if payload.theme is not None:
        db.set_setting("theme", payload.theme)
    return {"success": True, "message": "Settings updated successfully"}


@app.post("/api/chat")
def chat_assistant(payload: ChatRequest):
    api_key = db.get_setting("gemini_api_key", os.environ.get("GEMINI_API_KEY", ""))
    if not api_key:
        return {"reply": "⚠️ Please configure your Gemini API Key in the Settings tab to enable the AI Assistant."}

    stats = db.get_stats()
    closings = db.get_daily_closings()[:10]
    curr = db.get_setting("currency", "PKR ")
    khata = db.get_khata_customers_summary()

    context_prompt = f"""
You are the AI Financial Manager & Club Accountant for **Rion Snooker Lounge** (a premium snooker club, billiard lounge, and cafe in Pakistan).
You manage daily counter cash collections, bank receipts (Meezan Bank, Allied Bank, JazzCash), table frame billing, staff/marker wages, customer credit (Khata), and monthly closings.

Current Club Financial Ledger Summary:
- Currency: {curr}
- Total Sales / Revenues: {curr}{stats.get("total_credit", 0):,.2f}
- Total Expenses: {curr}{stats.get("total_expense", 0):,.2f}
- Net Profit / Closing: {curr}{stats.get("net_balance", 0):,.2f}
- Total Transactions: {stats.get("count", 0)}
- Outstanding Customer Khata: {curr}{khata.get("total_outstanding", 0):,.2f} across {khata.get("total_clients", 0)} clients
- Recent Daily Closings: {json.dumps(closings[:5], default=str)}

User Question: {payload.message}

Please provide a helpful, polite, concise, and accurate financial response tailored for Rion Snooker Lounge operations.
"""
    try:
        import requests
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={api_key}"
        data = {
            "contents": [{"parts": [{"text": context_prompt}]}]
        }
        res = requests.post(url, json=data, timeout=20)
        if res.status_code == 200:
            ans = res.json()["candidates"][0]["content"]["parts"][0]["text"]
            return {"reply": ans}
        else:
            return {"reply": f"API Error ({res.status_code}): {res.text}"}
    except Exception as e:
        return {"reply": f"Assistant Error: {str(e)}"}


@app.get("/healthz")
def health_check():
    return {"status": "ok", "app": "Rion Snooker Lounge"}


# =============================================================================
# BACKUP & RESTORE ROUTES (SYNC LOCAL WITH CLOUD)
# =============================================================================

@app.get("/api/backup/download-db")
def download_database_backup():
    db_path = os.path.join(BASE_DIR, "transactions.db")
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="Database file not found")
    return FileResponse(
        path=db_path,
        filename=f"rion_transactions_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db",
        media_type="application/x-sqlite3"
    )


@app.post("/api/backup/upload-db")
async def upload_database_restore(file: UploadFile = File(...)):
    if not file.filename.endswith(".db"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a .db SQLite file.")
    
    db_path = os.path.join(BASE_DIR, "transactions.db")
    temp_path = os.path.join(BASE_DIR, "transactions_temp.db")
    
    content = await file.read()
    with open(temp_path, "wb") as f:
        f.write(content)
        
    # Replace existing database
    if os.path.exists(db_path):
        backup_old = os.path.join(BASE_DIR, "transactions_pre_restore.db")
        try:
            shutil.copy2(db_path, backup_old)
        except Exception:
            pass
            
    shutil.move(temp_path, db_path)
    db.init_db()
    
    return {"success": True, "message": "Database restored successfully!"}

# Static Assets & Index
@app.get("/", response_class=HTMLResponse)
@app.head("/", response_class=HTMLResponse)
def read_root():
    index_file = os.path.join(WEB_DIR, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>TransactionAI Web Server Running.</h1>"

app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

def main():
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)

if __name__ == "__main__":
    main()
