import Foundation
import SQLite3

public class DatabaseManager: ObservableObject {
    public static let shared = DatabaseManager()
    private var db: OpaquePointer?
    private let dbName = "transactions.db"

    public var dbURL: URL {
        let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        return docs.appendingPathComponent(dbName)
    }

    private init() {
        openDatabase()
        createTables()
        seedInitialData()
    }

    deinit {
        if db != nil {
            sqlite3_close(db)
        }
    }

    private func openDatabase() {
        let path = dbURL.path
        let fileManager = FileManager.default

        // If local documents db doesn't exist, copy the pre-seeded bundled transactions.db
        if !fileManager.fileExists(atPath: path) {
            if let bundleDB = Bundle.main.url(forResource: "transactions", withExtension: "db") {
                try? fileManager.copyItem(at: bundleDB, to: dbURL)
                print("✅ Seeded iPhone database from bundled transactions.db")
            }
        }

        if sqlite3_open(path, &db) != SQLITE_OK {
            print("❌ Error opening SQLite database at \(path)")
        } else {
            print("✅ SQLite database connected at: \(path)")
        }
    }

    private func createTables() {
        let createTxTable = """
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            merchant TEXT NOT NULL,
            category TEXT NOT NULL,
            total_amount REAL NOT NULL,
            currency TEXT DEFAULT 'PKR ',
            tax_amount REAL DEFAULT 0.0,
            items_json TEXT DEFAULT '[]',
            payment_method TEXT DEFAULT 'Cash',
            image_path TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            tx_type TEXT DEFAULT 'Credit',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """

        let createCustTable = """
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            phone TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """

        let createStaffTable = """
        CREATE TABLE IF NOT EXISTS staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT DEFAULT 'Marker',
            phone TEXT DEFAULT '',
            salary_type TEXT DEFAULT 'Monthly',
            base_salary REAL DEFAULT 0.0,
            hire_date TEXT DEFAULT '',
            leave_date TEXT DEFAULT '',
            status TEXT DEFAULT 'Active',
            settlement_amount REAL DEFAULT 0.0,
            security_refunded REAL DEFAULT 0.0,
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """

        let createSettingsTable = """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """

        var err: UnsafeMutablePointer<Int8>?
        sqlite3_exec(db, createTxTable, nil, nil, &err)
        sqlite3_exec(db, createCustTable, nil, nil, &err)
        sqlite3_exec(db, createStaffTable, nil, nil, &err)
        sqlite3_exec(db, createSettingsTable, nil, nil, &err)

        // Ensure default PIN is 6861
        sqlite3_exec(db, "INSERT OR IGNORE INTO settings (key, value) VALUES ('admin_pin', '6861');", nil, nil, &err)
        sqlite3_exec(db, "INSERT OR IGNORE INTO settings (key, value) VALUES ('currency', 'PKR ');", nil, nil, &err)
    }

    private func seedInitialData() {
        var stmt: OpaquePointer?
        var count = 0
        if sqlite3_prepare_v2(db, "SELECT COUNT(*) FROM transactions;", -1, &stmt, nil) == SQLITE_OK {
            if sqlite3_step(stmt) == SQLITE_ROW {
                count = Int(sqlite3_column_int(stmt, 0))
            }
        }
        sqlite3_finalize(stmt)

        if count == 0 {
            print("🚀 Seeding all 105 transactions into local SQLite database...")
        let seedTransactions: [(String, String, String, Double, String, String, String)] = [
            ("2026-08-01", "Counter Cash Sales", "Counter Cash", 10500.0, "Credit", "Cash", "Manual Cash Sales"),
            ("2026-08-01", "Bank Transfer / Slips", "Bank Receipt", 29810.0, "Credit", "Bank", "Bank Slips & Online Payments"),
            ("2026-08-01", "Daily Expense", "Daily Expense", 900.0, "Expense", "Cash", "Daily Cash Expense"),
            ("2026-08-02", "Counter Cash Sales", "Counter Cash", 14897.0, "Credit", "Cash", "Manual Cash Sales"),
            ("2026-08-02", "Bank Transfer / Slips", "Bank Receipt", 23000.0, "Credit", "Bank", "Bank Slips & Online Payments"),
            ("2026-08-02", "Daily Expense", "Daily Expense", 900.0, "Expense", "Cash", "Daily Cash Expense"),
            ("2026-08-03", "Counter Cash Sales", "Counter Cash", 12399.0, "Credit", "Cash", "Manual Cash Sales"),
            ("2026-08-03", "Bank Transfer / Slips", "Bank Receipt", 15625.0, "Credit", "Bank", "Bank Slips & Online Payments"),
            ("2026-08-03", "Daily Expense", "Daily Expense", 1200.0, "Expense", "Cash", "Daily Cash Expense"),
            ("2026-08-04", "Counter Cash Sales", "Counter Cash", 7309.0, "Credit", "Cash", "Manual Cash Sales"),
            ("2026-08-04", "Bank Transfer / Slips", "Bank Receipt", 23780.0, "Credit", "Bank", "Bank Slips & Online Payments"),
            ("2026-08-04", "Daily Expense", "Daily Expense", 900.0, "Expense", "Cash", "Daily Cash Expense"),
            ("2026-08-05", "Counter Cash Sales", "Counter Cash", 14400.0, "Credit", "Cash", "Manual Cash Sales"),
            ("2026-08-05", "Bank Transfer / Slips", "Bank Receipt", 23104.0, "Credit", "Bank", "Bank Slips & Online Payments"),
            ("2026-08-05", "Daily Expense", "Daily Expense", 900.0, "Expense", "Cash", "Daily Cash Expense"),
            ("2026-08-06", "Counter Cash Sales", "Counter Cash", 12599.0, "Credit", "Cash", "Manual Cash Sales"),
            ("2026-08-06", "Bank Transfer / Slips", "Bank Receipt", 17320.0, "Credit", "Bank", "Bank Slips & Online Payments"),
            ("2026-08-06", "Daily Expense", "Daily Expense", 900.0, "Expense", "Cash", "Daily Cash Expense"),
            ("2026-08-07", "Counter Cash Sales", "Counter Cash", 15505.0, "Credit", "Cash", "Manual Cash Sales"),
            ("2026-08-07", "Bank Transfer / Slips", "Bank Receipt", 14240.0, "Credit", "Bank", "Bank Slips & Online Payments"),
            ("2026-08-07", "Daily Expense", "Daily Expense", 900.0, "Expense", "Cash", "Daily Cash Expense"),
            ("2026-08-08", "Counter Cash Sales", "Counter Cash", 20466.0, "Credit", "Cash", "Manual Cash Sales"),
            ("2026-08-08", "Bank Transfer / Slips", "Bank Receipt", 30125.0, "Credit", "Bank", "Bank Slips & Online Payments"),
            ("2026-08-08", "Daily Expense", "Daily Expense", 1200.0, "Expense", "Cash", "Daily Cash Expense"),
            ("2026-08-09", "Counter Cash Sales", "Counter Cash", 14626.0, "Credit", "Cash", "Manual Cash Sales"),
            ("2026-08-09", "Bank Transfer / Slips", "Bank Receipt", 30610.0, "Credit", "Bank", "Bank Slips & Online Payments"),
            ("2026-08-09", "Daily Expense", "Daily Expense", 1200.0, "Expense", "Cash", "Daily Cash Expense"),
            ("2026-08-10", "Counter Cash Sales", "Counter Cash", 19074.0, "Credit", "Cash", "Manual Cash Sales"),
            ("2026-08-10", "Bank Transfer / Slips", "Bank Receipt", 18100.0, "Credit", "Bank", "Bank Slips & Online Payments"),
            ("2026-08-10", "Daily Expense", "Daily Expense", 1200.0, "Expense", "Cash", "Daily Cash Expense"),
            ("2026-08-11", "Counter Cash Sales", "Counter Cash", 14824.0, "Credit", "Cash", "Manual Cash Sales"),
            ("2026-08-11", "Bank Transfer / Slips", "Bank Receipt", 18420.0, "Credit", "Bank", "Bank Slips & Online Payments"),
            ("2026-08-11", "Daily Expense", "Daily Expense", 1200.0, "Expense", "Cash", "Daily Cash Expense"),
            ("2026-08-12", "Counter Cash Sales", "Counter Cash", 15719.0, "Credit", "Cash", "Manual Cash Sales"),
            ("2026-08-12", "Bank Transfer / Slips", "Bank Receipt", 10170.0, "Credit", "Bank", "Bank Slips & Online Payments"),
            ("2026-08-12", "Daily Expense", "Daily Expense", 1200.0, "Expense", "Cash", "Daily Cash Expense"),
            ("2026-08-13", "Counter Cash Sales", "Counter Cash", 23371.0, "Credit", "Cash", "Manual Cash Sales"),
            ("2026-08-13", "Bank Transfer / Slips", "Bank Receipt", 10810.0, "Credit", "Bank", "Bank Slips & Online Payments"),
            ("2026-08-13", "Daily Expense", "Daily Expense", 2290.0, "Expense", "Cash", "Daily Cash Expense"),
            ("2026-08-14", "Counter Cash Sales", "Counter Cash", 21749.0, "Credit", "Cash", "Manual Cash Sales"),
            ("2026-08-14", "Bank Transfer / Slips", "Bank Receipt", 19920.0, "Credit", "Bank", "Bank Slips & Online Payments"),
            ("2026-08-14", "Daily Expense", "Daily Expense", 1200.0, "Expense", "Cash", "Daily Cash Expense"),
            ("2026-08-15", "Counter Cash Sales", "Counter Cash", 16041.0, "Credit", "Cash", "Manual Cash Sales"),
            ("2026-08-15", "Bank Transfer / Slips", "Bank Receipt", 18910.0, "Credit", "Bank", "Bank Slips & Online Payments"),
            ("2026-08-15", "Daily Expense", "Daily Expense", 1200.0, "Expense", "Cash", "Daily Cash Expense"),
            ("2026-08-16", "Counter Cash Sales", "Counter Cash", 13798.0, "Credit", "Cash", "Manual Cash Sales"),
            ("2026-08-16", "Bank Transfer / Slips", "Bank Receipt", 14780.0, "Credit", "Bank", "Bank Slips & Online Payments"),
            ("2026-08-16", "Daily Expense", "Daily Expense", 1180.0, "Expense", "Cash", "Daily Cash Expense"),
            ("2026-08-17", "Counter Cash Sales", "Counter Cash", 12757.0, "Credit", "Cash", "Manual Cash Sales"),
            ("2026-08-17", "Bank Transfer / Slips", "Bank Receipt", 16465.0, "Credit", "Bank", "Bank Slips & Online Payments"),
            ("2026-08-17", "Daily Expense", "Daily Expense", 900.0, "Expense", "Cash", "Daily Cash Expense"),
            ("2026-08-18", "Counter Cash Sales", "Counter Cash", 9728.0, "Credit", "Cash", "Manual Cash Sales"),
            ("2026-08-18", "Bank Transfer / Slips", "Bank Receipt", 16820.0, "Credit", "Bank", "Bank Slips & Online Payments"),
            ("2026-08-18", "Daily Expense", "Daily Expense", 900.0, "Expense", "Cash", "Daily Cash Expense"),
            ("2026-08-19", "Counter Cash Sales", "Counter Cash", 14241.0, "Credit", "Cash", "Manual Cash Sales"),
            ("2026-08-19", "Bank Transfer / Slips", "Bank Receipt", 15380.0, "Credit", "Bank", "Bank Slips & Online Payments"),
            ("2026-08-19", "Daily Expense", "Daily Expense", 1200.0, "Expense", "Cash", "Daily Cash Expense"),
            ("2026-08-20", "Counter Cash Sales", "Counter Cash", 16259.0, "Credit", "Cash", "Manual Cash Sales"),
            ("2026-08-20", "Bank Transfer / Slips", "Bank Receipt", 17240.0, "Credit", "Bank", "Bank Slips & Online Payments"),
            ("2026-08-20", "Daily Expense", "Daily Expense", 1200.0, "Expense", "Cash", "Daily Cash Expense"),
            ("2026-08-21", "Counter Cash Sales", "Counter Cash", 15678.0, "Credit", "Cash", "Manual Cash Sales"),
            ("2026-08-21", "Bank Transfer / Slips", "Bank Receipt", 19350.0, "Credit", "Bank", "Bank Slips & Online Payments"),
            ("2026-08-21", "Daily Expense", "Daily Expense", 1200.0, "Expense", "Cash", "Daily Cash Expense"),
            ("2026-08-22", "Counter Cash Sales", "Counter Cash", 13271.0, "Credit", "Cash", "Manual Cash Sales"),
            ("2026-08-22", "Bank Transfer / Slips", "Bank Receipt", 27244.0, "Credit", "Bank", "Bank Slips & Online Payments"),
            ("2026-08-22", "Daily Expense", "Daily Expense", 1200.0, "Expense", "Cash", "Daily Cash Expense"),
            ("2026-08-23", "Counter Cash Sales", "Counter Cash", 20125.0, "Credit", "Cash", "Manual Cash Sales"),
            ("2026-08-23", "Bank Transfer / Slips", "Bank Receipt", 18350.0, "Credit", "Bank", "Bank Slips & Online Payments"),
            ("2026-08-23", "Daily Expense", "Daily Expense", 3150.0, "Expense", "Cash", "Daily Cash Expense"),
            ("2026-08-24", "Counter Cash Sales", "Counter Cash", 6453.0, "Credit", "Cash", "Manual Cash Sales"),
            ("2026-08-24", "Bank Transfer / Slips", "Bank Receipt", 16050.0, "Credit", "Bank", "Bank Slips & Online Payments"),
            ("2026-08-24", "Daily Expense", "Daily Expense", 2200.0, "Expense", "Cash", "Daily Cash Expense"),
            ("2026-08-25", "Counter Cash Sales", "Counter Cash", 14397.0, "Credit", "Cash", "Manual Cash Sales"),
            ("2026-08-25", "Bank Transfer / Slips", "Bank Receipt", 16638.0, "Credit", "Bank", "Bank Slips & Online Payments"),
            ("2026-08-25", "Daily Expense", "Daily Expense", 1200.0, "Expense", "Cash", "Daily Cash Expense"),
            ("2026-08-26", "Tanveer", "Customer Credit", 540.0, "Udhaar", "Credit / Udhaar", "Opening Customer Credit (from Credit list.xlsx)"),
            ("2026-08-26", "Fahad", "Customer Credit", 300.0, "Udhaar", "Credit / Udhaar", "Opening Customer Credit (from Credit list.xlsx)"),
            ("2026-08-26", "Faraz", "Customer Credit", 800.0, "Udhaar", "Credit / Udhaar", "Opening Customer Credit (from Credit list.xlsx)"),
            ("2026-08-26", "Moez", "Customer Credit", 450.0, "Udhaar", "Credit / Udhaar", "Opening Customer Credit (from Credit list.xlsx)"),
            ("2026-08-26", "Cheema", "Customer Credit", 200.0, "Udhaar", "Credit / Udhaar", "Opening Customer Credit (from Credit list.xlsx)"),
            ("2026-08-26", "Chatta", "Customer Credit", 5137.0, "Udhaar", "Credit / Udhaar", "Opening Customer Credit (from Credit list.xlsx)"),
            ("2026-08-26", "Shareef", "Customer Credit", 1650.0, "Udhaar", "Credit / Udhaar", "Opening Customer Credit (from Credit list.xlsx)"),
            ("2026-08-26", "Ijaz", "Customer Credit", 250.0, "Udhaar", "Credit / Udhaar", "Opening Customer Credit (from Credit list.xlsx)"),
            ("2026-08-26", "Reyan", "Customer Credit", 700.0, "Udhaar", "Credit / Udhaar", "Opening Customer Credit (from Credit list.xlsx)"),
            ("2026-08-26", "Gujjar", "Customer Credit", 518.0, "Udhaar", "Credit / Udhaar", "Opening Customer Credit (from Credit list.xlsx)"),
            ("2026-08-26", "Abdulrehman", "Customer Credit", 800.0, "Udhaar", "Credit / Udhaar", "Opening Customer Credit (from Credit list.xlsx)"),
            ("2026-08-26", "Hafeez", "Customer Credit", 750.0, "Udhaar", "Credit / Udhaar", "Opening Customer Credit (from Credit list.xlsx)"),
            ("2026-08-26", "Shah", "Customer Credit", 350.0, "Udhaar", "Credit / Udhaar", "Opening Customer Credit (from Credit list.xlsx)"),
            ("2026-08-26", "Ashil", "Customer Credit", 250.0, "Udhaar", "Credit / Udhaar", "Opening Customer Credit (from Credit list.xlsx)"),
            ("2026-08-26", "Shani", "Customer Credit", 300.0, "Udhaar", "Credit / Udhaar", "Opening Customer Credit (from Credit list.xlsx)"),
            ("2026-08-26", "Zahir", "Customer Credit", 250.0, "Udhaar", "Credit / Udhaar", "Opening Customer Credit (from Credit list.xlsx)"),
            ("2026-08-26", "Ubaid", "Customer Credit", 620.0, "Udhaar", "Credit / Udhaar", "Opening Customer Credit (from Credit list.xlsx)"),
            ("2026-08-26", "Asif", "Customer Credit", 200.0, "Udhaar", "Credit / Udhaar", "Opening Customer Credit (from Credit list.xlsx)"),
            ("2026-08-26", "Moez", "Customer Credit", 450.0, "Udhaar", "Credit / Udhaar", "Opening Customer Credit (from Credit list.xlsx)"),
            ("2026-08-26", "Hamza", "Customer Credit", 950.0, "Udhaar", "Credit / Udhaar", "Opening Customer Credit (from Credit list.xlsx)"),
            ("2026-08-26", "Viki", "Customer Credit", 100.0, "Udhaar", "Credit / Udhaar", "Opening Customer Credit (from Credit list.xlsx)"),
            ("2026-08-26", "Zain", "Customer Credit", 370.0, "Udhaar", "Credit / Udhaar", "Opening Customer Credit (from Credit list.xlsx)"),
            ("2026-08-26", "Raza", "Customer Credit", 150.0, "Udhaar", "Credit / Udhaar", "Opening Customer Credit (from Credit list.xlsx)"),
            ("2026-08-26", "Umer", "Customer Credit", 1000.0, "Udhaar", "Credit / Udhaar", "Opening Customer Credit (from Credit list.xlsx)"),
            ("2026-08-26", "Yasir", "Customer Credit", 630.0, "Udhaar", "Credit / Udhaar", "Opening Customer Credit (from Credit list.xlsx)"),
            ("2026-08-26", "Umair", "Customer Credit", 150.0, "Udhaar", "Credit / Udhaar", "Opening Customer Credit (from Credit list.xlsx)"),
            ("2026-08-26", "Jamshaid", "Customer Credit", 700.0, "Udhaar", "Credit / Udhaar", "Opening Customer Credit (from Credit list.xlsx)"),
            ("2026-08-26", "Ali Property", "Customer Credit", 900.0, "Udhaar", "Credit / Udhaar", "Opening Customer Credit (from Credit list.xlsx)"),
            ("2026-08-26", "Zain Shah", "Customer Credit", 690.0, "Udhaar", "Credit / Udhaar", "Opening Customer Credit (from Credit list.xlsx)"),
            ("2026-08-26", "Motu", "Customer Credit", 400.0, "Udhaar", "Credit / Udhaar", "Opening Customer Credit (from Credit list.xlsx)"),
        ]

        for (d, m, c, amt, tt, pm, nt) in seedTransactions {
            let q = "INSERT INTO transactions (date, merchant, category, total_amount, tx_type, payment_method, notes) VALUES (?, ?, ?, ?, ?, ?, ?);"
            var stmt: OpaquePointer?
            if sqlite3_prepare_v2(db, q, -1, &stmt, nil) == SQLITE_OK {
                sqlite3_bind_text(stmt, 1, (d as NSString).utf8String, -1, nil)
                sqlite3_bind_text(stmt, 2, (m as NSString).utf8String, -1, nil)
                sqlite3_bind_text(stmt, 3, (c as NSString).utf8String, -1, nil)
                sqlite3_bind_double(stmt, 4, amt)
                sqlite3_bind_text(stmt, 5, (tt as NSString).utf8String, -1, nil)
                sqlite3_bind_text(stmt, 6, (pm as NSString).utf8String, -1, nil)
                sqlite3_bind_text(stmt, 7, (nt as NSString).utf8String, -1, nil)
                sqlite3_step(stmt)
            }
            sqlite3_finalize(stmt)
        }
        }

        let initialCustomers = [
            "Abdullah", "Adnan", "Ali Raza", "Amir", "Asad",
            "Bilal", "Daniyal", "Farhan", "Hamza", "Hassan",
            "Ibrahim", "Junaid", "Kamran", "Kashif", "Mohsin",
            "Nabeel", "Nasir", "Omer", "Raza", "Rehman",
            "Saad", "Salman", "Shahid", "Taimoor", "Tariq",
            "Usman", "Waqas", "Zahid", "Zain"
        ]

        for name in initialCustomers {
            let query = "INSERT OR IGNORE INTO customers (name) VALUES (?);"
            if sqlite3_prepare_v2(db, query, -1, &stmt, nil) == SQLITE_OK {
                sqlite3_bind_text(stmt, 1, (name as NSString).utf8String, -1, nil)
                sqlite3_step(stmt)
            }
            sqlite3_finalize(stmt)
        }

        var staffCount = 0
        if sqlite3_prepare_v2(db, "SELECT COUNT(*) FROM staff;", -1, &stmt, nil) == SQLITE_OK {
            if sqlite3_step(stmt) == SQLITE_ROW {
                staffCount = Int(sqlite3_column_int(stmt, 0))
            }
        }
        sqlite3_finalize(stmt)

        if staffCount == 0 {
            let staffSeed = [
                ("Ali Marker", "Marker", "Daily Shift", 1200.0),
                ("Zubair Head Marker", "Marker", "Monthly", 35000.0),
                ("Rashid Canteen", "Canteen", "Monthly", 25000.0),
                ("Asif Cleaning", "Staff", "Monthly", 20000.0)
            ]
            for (name, role, stype, base) in staffSeed {
                let ins = "INSERT INTO staff (name, role, salary_type, base_salary, status) VALUES (?, ?, ?, ?, 'Active');"
                if sqlite3_prepare_v2(db, ins, -1, &stmt, nil) == SQLITE_OK {
                    sqlite3_bind_text(stmt, 1, (name as NSString).utf8String, -1, nil)
                    sqlite3_bind_text(stmt, 2, (role as NSString).utf8String, -1, nil)
                    sqlite3_bind_text(stmt, 3, (stype as NSString).utf8String, -1, nil)
                    sqlite3_bind_double(stmt, 4, base)
                    sqlite3_step(stmt)
                }
                sqlite3_finalize(stmt)
            }
        }
    }

    // =========================================================================
    // TRANSACTIONS
    // =========================================================================
    public func addTransaction(
        date: String,
        merchant: String,
        category: String,
        amount: Double,
        txType: String = "Credit",
        paymentMethod: String = "Cash",
        notes: String = "",
        imagePath: String = ""
    ) -> Int64 {
        let query = """
        INSERT INTO transactions (date, merchant, category, total_amount, tx_type, payment_method, notes, image_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """
        var stmt: OpaquePointer?
        var newId: Int64 = -1
        if sqlite3_prepare_v2(db, query, -1, &stmt, nil) == SQLITE_OK {
            sqlite3_bind_text(stmt, 1, (date as NSString).utf8String, -1, nil)
            sqlite3_bind_text(stmt, 2, (merchant as NSString).utf8String, -1, nil)
            sqlite3_bind_text(stmt, 3, (category as NSString).utf8String, -1, nil)
            sqlite3_bind_double(stmt, 4, amount)
            sqlite3_bind_text(stmt, 5, (txType as NSString).utf8String, -1, nil)
            sqlite3_bind_text(stmt, 6, (paymentMethod as NSString).utf8String, -1, nil)
            sqlite3_bind_text(stmt, 7, (notes as NSString).utf8String, -1, nil)
            sqlite3_bind_text(stmt, 8, (imagePath as NSString).utf8String, -1, nil)

            if sqlite3_step(stmt) == SQLITE_DONE {
                newId = sqlite3_last_insert_rowid(db)
            }
        }
        sqlite3_finalize(stmt)
        return newId
    }

    public func deleteTransaction(id: Int64) -> Bool {
        let query = "DELETE FROM transactions WHERE id = ?;"
        var stmt: OpaquePointer?
        var success = false
        if sqlite3_prepare_v2(db, query, -1, &stmt, nil) == SQLITE_OK {
            sqlite3_bind_int64(stmt, 1, id)
            success = (sqlite3_step(stmt) == SQLITE_DONE)
        }
        sqlite3_finalize(stmt)
        return success
    }

    public func getDailyClosing(for date: String) -> DailyClosingSummary {
        var txList: [Transaction] = []
        let query = "SELECT id, date, merchant, category, total_amount, currency, tax_amount, items_json, payment_method, image_path, notes, tx_type, created_at FROM transactions WHERE date = ? ORDER BY id DESC;"
        var stmt: OpaquePointer?

        var cashSales = 0.0
        var bankSlips = 0.0
        var udhaarReturned = 0.0
        var totalExpense = 0.0
        var udhaarGiven = 0.0

        if sqlite3_prepare_v2(db, query, -1, &stmt, nil) == SQLITE_OK {
            sqlite3_bind_text(stmt, 1, (date as NSString).utf8String, -1, nil)

            while sqlite3_step(stmt) == SQLITE_ROW {
                let id = sqlite3_column_int64(stmt, 0)
                let d = String(cString: sqlite3_column_text(stmt, 1))
                let m = String(cString: sqlite3_column_text(stmt, 2))
                let cat = String(cString: sqlite3_column_text(stmt, 3))
                let amt = sqlite3_column_double(stmt, 4)
                let cur = String(cString: sqlite3_column_text(stmt, 5))
                let tax = sqlite3_column_double(stmt, 6)
                let items = String(cString: sqlite3_column_text(stmt, 7))
                let pm = String(cString: sqlite3_column_text(stmt, 8))
                let img = String(cString: sqlite3_column_text(stmt, 9))
                let notes = String(cString: sqlite3_column_text(stmt, 10))
                let txtype = String(cString: sqlite3_column_text(stmt, 11))
                let created = String(cString: sqlite3_column_text(stmt, 12))

                let tx = Transaction(
                    id: id, date: d, merchant: m, category: cat, totalAmount: amt,
                    currency: cur, taxAmount: tax, itemsJson: items, paymentMethod: pm,
                    imagePath: img, notes: notes, txType: txtype, createdAt: created
                )
                txList.append(tx)

                if txtype == "Expense" {
                    totalExpense += amt
                } else if txtype == "Udhaar" {
                    udhaarGiven += amt
                } else if txtype == "Udhaar Recovery" || cat == "Udhaar Recovery" {
                    udhaarReturned += amt
                } else if txtype == "Credit" {
                    if pm.contains("Cash") || cat.contains("Cash") || cat == "Table Play" {
                        cashSales += amt
                    } else {
                        bankSlips += amt
                    }
                }
            }
        }
        sqlite3_finalize(stmt)

        let totalCredit = cashSales + bankSlips + udhaarReturned
        let netBalance = totalCredit - totalExpense

        return DailyClosingSummary(
            date: date,
            cashSales: cashSales,
            bankSlips: bankSlips,
            udhaarReturned: udhaarReturned,
            totalCredit: totalCredit,
            totalExpense: totalExpense,
            udhaarGiven: udhaarGiven,
            netClosingBalance: netBalance,
            transactions: txList
        )
    }

    // =========================================================================
    // KHATA / CUSTOMER DIRECTORY
    // =========================================================================
    public func getAllCustomers() -> [Customer] {
        var list: [Customer] = []

        // Auto-seed customers if table is empty
        let initialCustomers = [
            "Abdullah", "Adnan", "Ali Raza", "Amir", "Asad",
            "Bilal", "Daniyal", "Farhan", "Hamza", "Hassan",
            "Ibrahim", "Junaid", "Kamran", "Kashif", "Mohsin",
            "Nabeel", "Nasir", "Omer", "Raza", "Rehman",
            "Saad", "Salman", "Shahid", "Taimoor", "Tariq",
            "Usman", "Waqas", "Zahid", "Zain"
        ]
        for name in initialCustomers {
            let q = "INSERT OR IGNORE INTO customers (name) VALUES (?);"
            var s: OpaquePointer?
            if sqlite3_prepare_v2(db, q, -1, &s, nil) == SQLITE_OK {
                sqlite3_bind_text(s, 1, (name as NSString).utf8String, -1, nil)
                sqlite3_step(s)
            }
            sqlite3_finalize(s)
        }

        // Also add any customers from transactions
        let addFromTx = """
        INSERT OR IGNORE INTO customers (name)
        SELECT DISTINCT merchant FROM transactions
        WHERE tx_type IN ('Udhaar', 'Udhaar Recovery')
           OR category IN ('Customer Credit', 'Udhaar Recovery')
           OR payment_method = 'Credit / Udhaar';
        """
        var err: UnsafeMutablePointer<Int8>?
        sqlite3_exec(db, addFromTx, nil, nil, &err)

        let query = """
        SELECT 
            c.id, 
            c.name, 
            COALESCE(c.phone, ''), 
            COALESCE(c.notes, ''), 
            COALESCE(c.created_at, ''),
            COALESCE(SUM(CASE WHEN t.tx_type = 'Udhaar' OR t.category = 'Customer Credit' THEN t.total_amount ELSE 0 END), 0.0) as total_given,
            COALESCE(SUM(CASE WHEN t.tx_type = 'Udhaar Recovery' OR t.category = 'Udhaar Recovery' THEN t.total_amount ELSE 0 END), 0.0) as total_returned,
            COUNT(t.id) as total_entries,
            COALESCE(MAX(t.date), '') as last_date,
            COALESCE(MIN(t.date), '') as first_date
        FROM customers c
        LEFT JOIN transactions t ON LOWER(TRIM(t.merchant)) = LOWER(TRIM(c.name))
        GROUP BY c.name
        ORDER BY c.name ASC;
        """
        var stmt: OpaquePointer?
        if sqlite3_prepare_v2(db, query, -1, &stmt, nil) == SQLITE_OK {
            while sqlite3_step(stmt) == SQLITE_ROW {
                let id = sqlite3_column_int64(stmt, 0)
                let name = String(cString: sqlite3_column_text(stmt, 1))
                let phone = sqlite3_column_text(stmt, 2) != nil ? String(cString: sqlite3_column_text(stmt, 2)) : ""
                let notes = sqlite3_column_text(stmt, 3) != nil ? String(cString: sqlite3_column_text(stmt, 3)) : ""
                let created = sqlite3_column_text(stmt, 4) != nil ? String(cString: sqlite3_column_text(stmt, 4)) : ""
                let given = sqlite3_column_double(stmt, 5)
                let returned = sqlite3_column_double(stmt, 6)
                let entries = Int(sqlite3_column_int(stmt, 7))
                let lastD = sqlite3_column_text(stmt, 8) != nil ? String(cString: sqlite3_column_text(stmt, 8)) : ""
                let firstD = sqlite3_column_text(stmt, 9) != nil ? String(cString: sqlite3_column_text(stmt, 9)) : ""

                let cust = Customer(
                    id: id, name: name, phone: phone, notes: notes,
                    totalGiven: given, totalReturned: returned,
                    pendingBalance: given - returned, totalEntries: entries,
                    lastDate: lastD, firstDate: firstD, createdAt: created
                )
                list.append(cust)
            }
        }
        sqlite3_finalize(stmt)
        return list
    }

    public func addCustomer(name: String, phone: String = "", notes: String = "") -> Bool {
        let query = "INSERT OR IGNORE INTO customers (name, phone, notes) VALUES (?, ?, ?);"
        var stmt: OpaquePointer?
        var ok = false
        if sqlite3_prepare_v2(db, query, -1, &stmt, nil) == SQLITE_OK {
            sqlite3_bind_text(stmt, 1, (name as NSString).utf8String, -1, nil)
            sqlite3_bind_text(stmt, 2, (phone as NSString).utf8String, -1, nil)
            sqlite3_bind_text(stmt, 3, (notes as NSString).utf8String, -1, nil)
            ok = (sqlite3_step(stmt) == SQLITE_DONE)
        }
        sqlite3_finalize(stmt)
        return ok
    }

    // =========================================================================
    // STAFF MANAGEMENT
    // =========================================================================
    public func getAllStaff() -> [StaffMember] {
        var list: [StaffMember] = []
        let query = "SELECT id, name, role, phone, salary_type, base_salary, hire_date, leave_date, status, settlement_amount, security_refunded, notes, created_at FROM staff ORDER BY status ASC, name ASC;"
        var stmt: OpaquePointer?
        if sqlite3_prepare_v2(db, query, -1, &stmt, nil) == SQLITE_OK {
            while sqlite3_step(stmt) == SQLITE_ROW {
                let id = sqlite3_column_int64(stmt, 0)
                let name = String(cString: sqlite3_column_text(stmt, 1))
                let role = String(cString: sqlite3_column_text(stmt, 2))
                let phone = sqlite3_column_text(stmt, 3) != nil ? String(cString: sqlite3_column_text(stmt, 3)) : ""
                let stype = String(cString: sqlite3_column_text(stmt, 4))
                let base = sqlite3_column_double(stmt, 5)
                let hire = sqlite3_column_text(stmt, 6) != nil ? String(cString: sqlite3_column_text(stmt, 6)) : ""
                let leave = sqlite3_column_text(stmt, 7) != nil ? String(cString: sqlite3_column_text(stmt, 7)) : ""
                let status = String(cString: sqlite3_column_text(stmt, 8))
                let settle = sqlite3_column_double(stmt, 9)
                let refund = sqlite3_column_double(stmt, 10)
                let notes = sqlite3_column_text(stmt, 11) != nil ? String(cString: sqlite3_column_text(stmt, 11)) : ""
                let created = sqlite3_column_text(stmt, 12) != nil ? String(cString: sqlite3_column_text(stmt, 12)) : ""

                let member = StaffMember(
                    id: id, name: name, role: role, phone: phone, salaryType: stype,
                    baseSalary: base, hireDate: hire, leaveDate: leave, status: status,
                    settlementAmount: settle, securityRefunded: refund, notes: notes, createdAt: created
                )
                list.append(member)
            }
        }
        sqlite3_finalize(stmt)
        return list
    }

    // =========================================================================
    // SETTINGS & PIN
    // =========================================================================
    public func getAdminPIN() -> String {
        let query = "SELECT value FROM settings WHERE key = 'admin_pin';"
        var stmt: OpaquePointer?
        var pin = "6861"
        if sqlite3_prepare_v2(db, query, -1, &stmt, nil) == SQLITE_OK {
            if sqlite3_step(stmt) == SQLITE_ROW {
                pin = String(cString: sqlite3_column_text(stmt, 0))
            }
        }
        sqlite3_finalize(stmt)
        return pin
    }

    public func setAdminPIN(_ newPin: String) -> Bool {
        let query = "INSERT OR REPLACE INTO settings (key, value) VALUES ('admin_pin', ?);"
        var stmt: OpaquePointer?
        var ok = false
        if sqlite3_prepare_v2(db, query, -1, &stmt, nil) == SQLITE_OK {
            sqlite3_bind_text(stmt, 1, (newPin as NSString).utf8String, -1, nil)
            ok = (sqlite3_step(stmt) == SQLITE_DONE)
        }
        sqlite3_finalize(stmt)
        return ok
    }

    // =========================================================================
    // CLOUD & MAC SYNC
    // =========================================================================
    public func syncWithCloud(completion: @escaping (Bool, String) -> Void) {
        guard let url = URL(string: "https://rion-snooker-lounge-rk51.onrender.com/api/backup/download-db") else {
            completion(false, "Invalid Cloud URL")
            return
        }

        URLSession.shared.downloadTask(with: url) { tempURL, response, error in
            guard let tempURL = tempURL, error == nil else {
                DispatchQueue.main.async {
                    completion(false, error?.localizedDescription ?? "Cloud connection failed")
                }
                return
            }

            if self.db != nil {
                sqlite3_close(self.db)
                self.db = nil
            }

            let fileManager = FileManager.default
            do {
                if fileManager.fileExists(atPath: self.dbURL.path) {
                    try fileManager.removeItem(at: self.dbURL)
                }
                try fileManager.moveItem(at: tempURL, to: self.dbURL)
                self.openDatabase()
                DispatchQueue.main.async {
                    completion(true, "✅ Successfully synced all transactions, Khata and staff records!")
                }
            } catch {
                self.openDatabase()
                DispatchQueue.main.async {
                    completion(false, "Sync error: \(error.localizedDescription)")
                }
            }
        }.resume()
    }
}
