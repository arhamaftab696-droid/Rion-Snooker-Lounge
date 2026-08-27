"""
extractor.py - Gemini Vision Extraction & AI Q&A Engine
Uses Google Gemini API to parse transaction receipts and answer natural language financial questions.
"""

import base64
import json
import mimetypes
import re
import os
from typing import Dict, Any, List, Optional
import requests

import io
from PIL import Image, ImageOps

import time

DEFAULT_MODEL = "gemini-3.1-flash-lite-preview"
MODEL_POOL = ["gemini-3.1-flash-lite-preview", "gemini-3.1-flash-lite", "gemini-flash-lite-latest"]

SYSTEM_PROMPT_EXTRACTION = """You are an expert financial receipt and bank transfer OCR AI for Pakistani businesses and snooker lounges.
Analyze the provided image of a receipt, invoice, bank transfer screenshot, mobile banking app screen (EasyPaisa, JazzCash, SadaPay, NayaPay, Raast, HBL, Meezan, Bank Alfalah, UBL, MCB, Allied Bank, Faisal Bank, etc.), paper slip, or handwritten transaction.

CRITICAL INSTRUCTIONS FOR AMOUNT EXTRACTION:
1. In mobile banking apps (EasyPaisa, JazzCash, SadaPay, Raast, NayaPay, HBL, Meezan, etc.):
   - The primary transaction amount is the largest prominent number on the screen (e.g. 'Rs. 5,000', 'PKR 12,500.00', '5000', 'Amount: 3,500', 'Money Sent: 1,000', 'Transaction Amount').
   - NEVER return total_amount as 0.00 if there is any monetary digit or currency number visible in the image!
   - Extract the full number without comma (e.g. 5000.0 from 'Rs. 5,000').
2. If fees or extra charges are explicitly deducted, set extras_deducted (float), and total_amount = gross_amount - extras_deducted.

Extract the transaction data into a strictly valid JSON object matching this schema:
{
  "merchant": "Sender Name / Receiver Name / Bank Name / Customer Name",
  "date": "YYYY-MM-DD format (if missing, use current date)",
  "gross_amount": 0.00,
  "extras_deducted": 0.00,
  "extras_reason": "e.g. Bank Fee, Service Charges, Discount, Marker Cut (or null)",
  "total_amount": 0.00,
  "currency": "PKR",
  "tax_amount": 0.00,
  "category": "Bank Receipt",
  "payment_method": "Bank",
  "items": [
    {
      "name": "Description of transfer or items",
      "qty": 1,
      "price": 0.00
    }
  ],
  "notes": "Transaction ID, Sender/Receiver info, Bank name or reference"
}

Important: Return ONLY the JSON object.
"""


def prepare_image_payload(image_path: str) -> tuple[str, str]:
    """
    Loads, normalizes EXIF rotation, optimizes size for fast network transfer, and returns (base64_str, mime_type).
    """
    ext = os.path.splitext(image_path)[1].lower()
    
    # If PDF, send raw bytes
    if ext == ".pdf":
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return b64, "application/pdf"

    try:
        with Image.open(image_path) as img:
            try:
                img = ImageOps.exif_transpose(img)
            except Exception:
                pass
            
            if img.mode != "RGB":
                img = img.convert("RGB")

            # Optimal dimension for fast OCR & low token count
            max_dimension = 1024
            if max(img.size) > max_dimension:
                img.thumbnail((max_dimension, max_dimension), Image.Resampling.BILINEAR)

            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=75, optimize=True)
            jpeg_bytes = buffer.getvalue()

        b64 = base64.b64encode(jpeg_bytes).decode("utf-8")
        return b64, "image/jpeg"
    except Exception:
        with open(image_path, "rb") as f:
            raw = f.read()
        b64 = base64.b64encode(raw).decode("utf-8")
        mime = get_image_mime_type(image_path)
        return b64, mime


def get_image_mime_type(image_path: str) -> str:
    """Determine MIME type for the image."""
    mime_type, _ = mimetypes.guess_type(image_path)
    if mime_type:
        return mime_type
    ext = os.path.splitext(image_path)[1].lower()
    if ext in ['.jpg', '.jpeg']:
        return 'image/jpeg'
    elif ext == '.png':
        return 'image/png'
    elif ext == '.webp':
        return 'image/webp'
    elif ext == '.heic':
        return 'image/heic'
    elif ext == '.pdf':
        return 'application/pdf'
    return 'image/jpeg'


def test_api_connection(api_key: str, model_name: str = DEFAULT_MODEL) -> Dict[str, Any]:
    """Test if the provided Gemini API key is valid."""
    if not api_key or not api_key.strip():
        return {"success": False, "error": "API Key is empty. Please enter a valid Gemini API Key."}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key.strip()}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": "Respond with 'OK' if you receive this message."}
                ]
            }
        ]
    }
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=12)
        if response.status_code == 200:
            return {"success": True, "message": "Connection successful! Gemini API is ready."}
        else:
            try:
                err_data = response.json()
                err_msg = err_data.get("error", {}).get("message", response.text)
            except Exception:
                err_msg = response.text
            return {"success": False, "error": f"API Error ({response.status_code}): {err_msg}"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Network error: {str(e)}"}


def extract_transaction_from_image(
    image_path: str,
    api_key: str,
    model_name: str = DEFAULT_MODEL
) -> Dict[str, Any]:
    """
    Reads an image file, sends it to Gemini Vision API, and parses the structured transaction details.
    """
    if not api_key or not api_key.strip():
        raise ValueError("Google Gemini API Key is required. Please set it in the Settings tab.")

    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    # Prepare optimized base64 payload
    b64_data, mime_type = prepare_image_payload(image_path)

    # Build model failover sequence
    models_to_try = [model_name]
    for m in MODEL_POOL:
        if m not in models_to_try:
            models_to_try.append(m)

    last_error = None

    for current_model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{current_model}:generateContent?key={api_key.strip()}"
        
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": SYSTEM_PROMPT_EXTRACTION},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": b64_data
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 2048,
                "response_mime_type": "application/json"
            }
        }
        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                text_content = ""
                candidates = data.get("candidates", [])
                if candidates and "content" in candidates[0]:
                    parts = candidates[0]["content"].get("parts", [])
                    if parts:
                        text_content = parts[0].get("text", "")

                # Parse JSON
                parsed_json = _clean_and_parse_json(text_content)
                if parsed_json:
                    parsed_json["image_path"] = image_path
                    return parsed_json
                else:
                    raise ValueError(f"Could not parse valid JSON from AI response: {text_content[:200]}")
            elif response.status_code == 429:
                # Rate limited: short pause and failover to next model
                time.sleep(0.4)
                last_error = f"Model {current_model} rate limited, switching..."
                continue
            else:
                try:
                    err_info = response.json().get("error", {}).get("message", response.text)
                except Exception:
                    err_info = response.text
                last_error = f"Gemini API ({current_model}) returned {response.status_code}: {err_info}"
        except requests.exceptions.RequestException as e:
            last_error = f"Network connection error ({current_model}): {str(e)}"

    raise RuntimeError(last_error or "Failed to extract transaction data from image.")


def _normalize_extracted_dict(res: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize extracted dictionary fields and types with zero-amount recovery."""
    res["merchant"] = str(res.get("merchant") or "Bank Transfer / Slip")
    res["date"] = str(res.get("date") or "")
    try:
        res["total_amount"] = float(res.get("total_amount") or 0.0)
    except (ValueError, TypeError):
        res["total_amount"] = 0.0
    try:
        res["gross_amount"] = float(res.get("gross_amount") or res.get("total_amount") or 0.0)
    except (ValueError, TypeError):
        res["gross_amount"] = res.get("total_amount", 0.0)
    try:
        res["extras_deducted"] = float(res.get("extras_deducted") or 0.0)
    except (ValueError, TypeError):
        res["extras_deducted"] = 0.0
    try:
        res["tax_amount"] = float(res.get("tax_amount") or 0.0)
    except (ValueError, TypeError):
        res["tax_amount"] = 0.0

    # If amount came back 0.0, attempt recovery from notes or items
    if res["total_amount"] <= 0.0:
        notes_str = str(res.get("notes") or "")
        merchant_str = str(res.get("merchant") or "")
        search_blob = f"{notes_str} {merchant_str}"
        m_amt = re.search(r'(?:Rs\.?|PKR|Amount|Paid|Transferred|Total)[\s:]*([0-9,]+(?:\.[0-9]{1,2})?)', search_blob, re.IGNORECASE)
        if m_amt:
            try:
                rec_val = float(m_amt.group(1).replace(",", ""))
                if rec_val > 0:
                    res["total_amount"] = rec_val
                    res["gross_amount"] = max(res.get("gross_amount", 0.0), rec_val)
            except Exception:
                pass

    res["currency"] = str(res.get("currency") or "PKR")
    res["category"] = str(res.get("category") or "Bank Receipt")
    res["payment_method"] = str(res.get("payment_method") or "Bank")
    res["notes"] = str(res.get("notes") or "")
    if not isinstance(res.get("items"), list):
        res["items"] = []
    return res


def _clean_and_parse_json(raw_text: str) -> Optional[Dict[str, Any]]:
    """Clean markdown code blocks and extract valid JSON dict with regex fallback."""
    if not raw_text:
        return None

    cleaned = raw_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        res = json.loads(cleaned)
        if isinstance(res, dict):
            return _normalize_extracted_dict(res)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                res = json.loads(match.group(0))
                if isinstance(res, dict):
                    return _normalize_extracted_dict(res)
            except Exception:
                pass

    # Regex field extraction fallback
    try:
        merchant_m = re.search(r'"merchant"\s*:\s*"([^"]+)"', cleaned)
        total_m = re.search(r'"total_amount"\s*:\s*([0-9.]+)', cleaned) or re.search(r'"gross_amount"\s*:\s*([0-9.]+)', cleaned)
        date_m = re.search(r'"date"\s*:\s*"([0-9-]+)"', cleaned)
        notes_m = re.search(r'"notes"\s*:\s*"([^"]+)"', cleaned)

        if total_m or merchant_m:
            total_val = float(total_m.group(1)) if total_m else 0.0
            merchant_val = merchant_m.group(1) if merchant_m else "Bank Transfer / Slip"
            date_val = date_m.group(1) if date_m else ""
            notes_val = notes_m.group(1) if notes_m else ""

            return {
                "merchant": merchant_val,
                "date": date_val,
                "total_amount": total_val,
                "gross_amount": total_val,
                "extras_deducted": 0.0,
                "extras_reason": "",
                "currency": "PKR",
                "tax_amount": 0.0,
                "category": "Bank Receipt",
                "payment_method": "Bank",
                "items": [],
                "notes": notes_val
            }
    except Exception:
        pass

    return None


def ask_gemini_transactions_question(
    question: str,
    transactions: List[Dict[str, Any]],
    stats: Dict[str, Any],
    api_key: str,
    model_name: str = DEFAULT_MODEL
) -> str:
    """
    Answers natural language queries about the user's transaction history.
    """
    if not api_key or not api_key.strip():
        return "⚠️ Error: Please configure your Gemini API Key in Settings first."

    # Simplify transaction list for prompt context
    tx_summary = []
    for t in transactions:
        tx_summary.append({
            "id": t.get("id"),
            "date": t.get("date"),
            "merchant": t.get("merchant"),
            "category": t.get("category"),
            "amount": t.get("total_amount"),
            "currency": t.get("currency"),
            "payment_method": t.get("payment_method"),
            "items": t.get("items", []),
            "notes": t.get("notes", "")
        })

    prompt = f"""You are the AI Financial Manager and Club Accountant for **Rion Snooker Lounge** (a premier snooker & billiard club, cafe, and entertainment lounge).
Here is the club's complete local transaction dataset, daily closings, and financial statistics:

CLUB FINANCIAL POLICIES & RULES:
- Currency: PKR
- Staff Salary Schedule: Salaries are paid on the **10th of every month**.
- Security Deposit Policy: Security is NOT taken upfront before working. Security is automatically accumulated and withheld from the staff member's wages as they work their first 10 days (up to 10 days of base salary held in reserve).

OVERVIEW STATISTICS:
- Total Revenue / Spend: {stats.get('total_spent', 0)}
- Transaction Count: {stats.get('count', 0)}
- Spending by Category: {json.dumps(stats.get('by_category', []), indent=2)}
- Spending by Month: {json.dumps(stats.get('by_month', []), indent=2)}
- Spending by Payment Method: {json.dumps(stats.get('by_payment', []), indent=2)}

ALL TRANSACTIONS & CLOSINGS:
{json.dumps(tx_summary, indent=2)}

USER QUESTION:
"{question}"

INSTRUCTIONS:
1. Provide a precise, well-formatted, polite, and helpful response tailored for Rion Snooker Lounge management.
2. If math is required (sums, averages, comparisons), perform exact arithmetic calculations using the club dataset.
3. If specific dates, counter cash, bank slips, expenses, staff salaries (10th of month rule / 10-day security), or customer khata are asked about, list them clearly with dates and PKR amounts.
4. Keep the tone professional, encouraging, and clear. Use markdown bullet points and bold highlights.
"""

    models_to_try = [model_name]
    for m in MODEL_POOL:
        if m not in models_to_try:
            models_to_try.append(m)

    for current_model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{current_model}:generateContent?key={api_key.strip()}"
        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.2
            }
        }
        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=25)
            if response.status_code == 200:
                data = response.json()
                candidates = data.get("candidates", [])
                if candidates and "content" in candidates[0]:
                    parts = candidates[0]["content"].get("parts", [])
                    if parts:
                        return parts[0].get("text", "No response received.")
                return "Unable to parse AI response."
            elif response.status_code == 429:
                continue
            else:
                try:
                    err_msg = response.json().get("error", {}).get("message", response.text)
                except Exception:
                    err_msg = response.text
                return f"❌ Gemini API Error ({response.status_code}): {err_msg}"
        except requests.exceptions.RequestException as e:
            continue

    return "❌ All AI models are currently busy. Please retry in a few seconds."
