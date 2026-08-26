import SwiftUI

public struct MonthlyView: View {
    @State private var selectedMonth: String = "2026-08"

    public init() {}

    public var body: some View {
        NavigationView {
            ZStack {
                Color.darkBg.ignoresSafeArea()

                ScrollView {
                    VStack(spacing: 16) {
                        // Month Header
                        HStack {
                            Text("Month: August 2026")
                                .font(.system(size: 16, weight: .bold))
                                .foregroundColor(.white)
                            Spacer()
                        }
                        .padding(.horizontal)

                        // 3 Key Stats Cards
                        VStack(spacing: 10) {
                            HStack(spacing: 10) {
                                MetricCard(title: "TOTAL REVENUE", amount: 904622.0, color: .emeraldGreen, icon: "chart.line.uptrend.xyaxis")
                                MetricCard(title: "TOTAL EXPENSES", amount: 31620.0, color: .red, icon: "scissors")
                            }
                            HStack(spacing: 10) {
                                MetricCard(title: "NET PROFIT", amount: 820827.0, color: .teal, icon: "checkmark.circle.fill")
                                MetricCard(title: "CUSTOMER UDHAAR", amount: 20555.0, color: .orange, icon: "person.crop.circle.badge.plus")
                            }
                        }
                        .padding(.horizontal)

                        // Share / Export Button
                        Button(action: exportReport) {
                            HStack {
                                Image(systemName: "square.and.arrow.up.fill")
                                Text("Export Statement (Share / AirDrop)")
                                    .font(.system(size: 15, weight: .bold))
                            }
                            .foregroundColor(.white)
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(Color.emeraldGreen)
                            .cornerRadius(14)
                        }
                        .padding(.horizontal)
                    }
                    .padding(.vertical)
                }
            }
            .navigationTitle("📊 Monthly Statement")
            .navigationBarTitleDisplayMode(.inline)
        }
    }

    private func exportReport() {
        // Export logic
    }
}
