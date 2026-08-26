import Foundation

public struct Customer: Identifiable, Codable {
    public var id: Int64
    public var name: String
    public var phone: String
    public var notes: String
    public var totalGiven: Double
    public var totalReturned: Double
    public var pendingBalance: Double
    public var totalEntries: Int
    public var lastDate: String
    public var firstDate: String
    public var createdAt: String

    public init(
        id: Int64 = 0,
        name: String,
        phone: String = "",
        notes: String = "",
        totalGiven: Double = 0.0,
        totalReturned: Double = 0.0,
        pendingBalance: Double = 0.0,
        totalEntries: Int = 0,
        lastDate: String = "",
        firstDate: String = "",
        createdAt: String = ""
    ) {
        self.id = id
        self.name = name
        self.phone = phone
        self.notes = notes
        self.totalGiven = totalGiven
        self.totalReturned = totalReturned
        self.pendingBalance = pendingBalance
        self.totalEntries = totalEntries
        self.lastDate = lastDate
        self.firstDate = firstDate
        self.createdAt = createdAt
    }
}
