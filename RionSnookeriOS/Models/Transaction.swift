import Foundation

public struct TransactionItem: Identifiable, Codable {
    public var id = UUID()
    public var name: String
    public var qty: Int
    public var price: Double

    public init(name: String, qty: Int = 1, price: Double = 0.0) {
        self.name = name
        self.qty = qty
        self.price = price
    }
}

public struct Transaction: Identifiable, Codable {
    public var id: Int64
    public var date: String
    public var merchant: String
    public var category: String
    public var totalAmount: Double
    public var currency: String
    public var taxAmount: Double
    public var itemsJson: String
    public var paymentMethod: String
    public var imagePath: String
    public var notes: String
    public var txType: String
    public var createdAt: String

    public init(
        id: Int64 = 0,
        date: String,
        merchant: String,
        category: String,
        totalAmount: Double,
        currency: String = "PKR ",
        taxAmount: Double = 0.0,
        itemsJson: String = "[]",
        paymentMethod: String = "Cash",
        imagePath: String = "",
        notes: String = "",
        txType: String = "Credit",
        createdAt: String = ""
    ) {
        self.id = id
        self.date = date
        self.merchant = merchant
        self.category = category
        self.totalAmount = totalAmount
        self.currency = currency
        self.taxAmount = taxAmount
        self.itemsJson = itemsJson
        self.paymentMethod = paymentMethod
        self.imagePath = imagePath
        self.notes = notes
        self.txType = txType
        self.createdAt = createdAt.isEmpty ? ISO8601DateFormatter().string(from: Date()) : createdAt
    }
}

public struct DailyClosingSummary {
    public var date: String
    public var cashSales: Double
    public var bankSlips: Double
    public var udhaarReturned: Double
    public var totalCredit: Double
    public var totalExpense: Double
    public var udhaarGiven: Double
    public var netClosingBalance: Double
    public var transactions: [Transaction]

    public init(
        date: String,
        cashSales: Double = 0.0,
        bankSlips: Double = 0.0,
        udhaarReturned: Double = 0.0,
        totalCredit: Double = 0.0,
        totalExpense: Double = 0.0,
        udhaarGiven: Double = 0.0,
        netClosingBalance: Double = 0.0,
        transactions: [Transaction] = []
    ) {
        self.date = date
        self.cashSales = cashSales
        self.bankSlips = bankSlips
        self.udhaarReturned = udhaarReturned
        self.totalCredit = totalCredit
        self.totalExpense = totalExpense
        self.udhaarGiven = udhaarGiven
        self.netClosingBalance = netClosingBalance
        self.transactions = transactions
    }
}
