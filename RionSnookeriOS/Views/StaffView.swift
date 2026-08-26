import SwiftUI

public struct StaffView: View {
    @State private var staffList: [StaffMember] = []

    public init() {}

    public var body: some View {
        NavigationView {
            ZStack {
                Color.darkBg.ignoresSafeArea()

                ScrollView {
                    VStack(spacing: 14) {
                        ForEach(staffList) { staff in
                            StaffCard(member: staff)
                        }
                    }
                    .padding()
                }
            }
            .navigationTitle("👔 Staff & Marker Salaries")
            .navigationBarTitleDisplayMode(.inline)
            .onAppear {
                staffList = DatabaseManager.shared.getAllStaff()
            }
        }
    }
}

struct StaffCard: View {
    let member: StaffMember

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text(member.name)
                        .font(.system(size: 16, weight: .bold))
                        .foregroundColor(.white)
                    Text("\(member.role) • \(member.salaryType)")
                        .font(.system(size: 12))
                        .foregroundColor(.gray)
                }
                Spacer()
                Text(member.status)
                    .font(.system(size: 11, weight: .bold))
                    .foregroundColor(member.isResigned ? .red : .emeraldGreen)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background((member.isResigned ? Color.red : Color.emeraldGreen).opacity(0.15))
                    .cornerRadius(6)
            }

            Divider().background(Color.gray.opacity(0.3))

            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text("BASE SALARY")
                        .font(.system(size: 9, weight: .bold))
                        .foregroundColor(.gray)
                    Text("PKR \(member.baseSalary, specifier: "%.0f")")
                        .font(.system(size: 14, weight: .bold))
                        .foregroundColor(.white)
                }
                Spacer()
                VStack(alignment: .trailing, spacing: 2) {
                    Text("10-DAY SECURITY")
                        .font(.system(size: 9, weight: .bold))
                        .foregroundColor(.gray)
                    Text("PKR \((member.baseSalary / 30.0) * 10.0, specifier: "%.0f")")
                        .font(.system(size: 14, weight: .bold))
                        .foregroundColor(.orange)
                }
            }
        }
        .padding(14)
        .background(Color.slateCard)
        .cornerRadius(14)
    }
}
