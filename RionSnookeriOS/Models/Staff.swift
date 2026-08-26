import Foundation

public struct StaffMember: Identifiable, Codable {
    public var id: Int64
    public var name: String
    public var role: String
    public var phone: String
    public var salaryType: String
    public var baseSalary: Double
    public var hireDate: String
    public var leaveDate: String
    public var status: String // "Active" or "Resigned"
    public var settlementAmount: Double
    public var securityRefunded: Double
    public var notes: String
    public var createdAt: String

    public var isResigned: Bool {
        return status.lowercased() == "resigned"
    }

    public init(
        id: Int64 = 0,
        name: String,
        role: String = "Marker",
        phone: String = "",
        salaryType: String = "Monthly",
        baseSalary: Double = 0.0,
        hireDate: String = "",
        leaveDate: String = "",
        status: String = "Active",
        settlementAmount: Double = 0.0,
        securityRefunded: Double = 0.0,
        notes: String = "",
        createdAt: String = ""
    ) {
        self.id = id
        self.name = name
        self.role = role
        self.phone = phone
        self.salaryType = salaryType
        self.baseSalary = baseSalary
        self.hireDate = hireDate
        self.leaveDate = leaveDate
        self.status = status
        self.settlementAmount = settlementAmount
        self.securityRefunded = securityRefunded
        self.notes = notes
        self.createdAt = createdAt
    }
}
