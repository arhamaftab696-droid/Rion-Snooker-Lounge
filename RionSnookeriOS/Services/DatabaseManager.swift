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
            var stmt: OpaquePointer?
            if sqlite3_prepare_v2(db, query, -1, &stmt, nil) == SQLITE_OK {
                sqlite3_bind_text(stmt, 1, (name as NSString).utf8String, -1, nil)
                sqlite3_step(stmt)
            }
            sqlite3_finalize(stmt)
        }

        // Seed initial staff if empty
        var stmt: OpaquePointer?
        var count = 0
        if sqlite3_prepare_v2(db, "SELECT COUNT(*) FROM staff;", -1, &stmt, nil) == SQLITE_OK {
            if sqlite3_step(stmt) == SQLITE_ROW {
                count = Int(sqlite3_column_int(stmt, 0))
            }
        }
        sqlite3_finalize(stmt)

        if count == 0 {
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
        let query = """
        SELECT c.id, c.name, c.phone, c.notes, c.created_at,
            COALESCE(SUM(CASE WHEN t.tx_type = 'Udhaar' THEN t.total_amount ELSE 0 END), 0.0) as total_given,
            COALESCE(SUM(CASE WHEN t.tx_type = 'Udhaar Recovery' OR t.category = 'Udhaar Recovery' THEN t.total_amount ELSE 0 END), 0.0) as total_returned,
            COUNT(t.id) as total_entries,
            MAX(t.date) as last_date,
            MIN(t.date) as first_date
        FROM customers c
        LEFT JOIN transactions t ON t.merchant = c.name
        GROUP BY c.id
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
}
