# 💳 TransactionAI - Local Mac Receipt Scanner & Spending Assistant

A native macOS desktop application that allows you to upload photos of receipts, bills, invoices, and bank transaction slips. It automatically extracts the amounts, dates, vendors, and line items using Google Gemini Vision, aggregates all your spending in a local database, and lets you ask natural language questions about your expenses.

---

## ✨ Features

- 📸 **Multi-Receipt Upload & Batch Scan**: Upload multiple receipt pictures at once (PNG, JPG, JPEG, WEBP, PDF, HEIC).
- 🧠 **Google Gemini Vision OCR**: Accurately reads merchant names, dates, itemized breakdowns, taxes, totals, and categories even from low-light, wrinkled, or handwritten receipts.
- 📊 **Financial Dashboard**: Real-time spending overview, average receipt amount, top spending categories, and breakdown charts.
- 📋 **Transactions Manager**: Searchable and filterable table with full details, original receipt image viewer, manual entry, and one-click CSV export.
- 💬 **AI Financial Assistant (Q&A)**: Ask questions about your spending in natural language (e.g. *"What did I spend the most on?"*, *"How much did I spend on groceries in August?"*, *"Summarize my spending and give budgeting advice"*).
- 🔒 **100% Local & Private**: All your transaction data and images are stored securely on your Mac in SQLite (`transactions.db`).

---

## 🚀 How to Launch on Your Mac

### Option 1: Double-Click (Quickest)
Simply double-click the **`run_app.command`** file in Finder.

### Option 2: Terminal
Run the following command in Terminal from this directory:
```bash
./venv/bin/python app.py
```

---

## 🔑 Initial Setup (Google Gemini API Key)

1. Open the application.
2. Click on the **⚙️ Settings** tab in the sidebar.
3. Paste your Google Gemini API Key into the field (get a free key at [Google AI Studio](https://aistudio.google.com/)).
4. Click **"Test Connection"** to verify, then click **"Save Key"**.
5. You're all set!

---

## 📂 Project Structure

```
├── app.py              # Main CustomTkinter macOS Desktop Application
├── extractor.py        # Gemini Vision AI extractor & natural language Q&A engine
├── db.py               # Local SQLite database manager (CRUD, statistics, CSV export)
├── run_app.command     # Double-clickable macOS launcher script
├── test_suite.py       # Automated unit tests
├── requirements.txt    # Python dependencies (customtkinter, pillow, requests)
└── transactions.db     # Local SQLite database (created automatically)
```
