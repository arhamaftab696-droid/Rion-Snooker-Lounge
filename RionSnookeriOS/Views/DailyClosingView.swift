import SwiftUI

public struct DailyClosingView: View {
    @State private var selectedDate: Date = Date()
    @State private var summary: DailyClosingSummary = DailyClosingSummary(date: "")
    @State private var showEntryModal: Bool = false

    private var dateString: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter.string(from: selectedDate)
    }

    public init() {}

    public var body: some View {
        NavigationView {
            ZStack {
                Color.darkBg.ignoresSafeArea()

                ScrollView {
                    VStack(spacing: 16) {
                        // Date Bar
                        HStack {
                            Button(action: { changeDay(by: -1) }) {
                                Image(systemName: "chevron.left")
                                    .foregroundColor(.white)
                                    .padding(10)
                                    .background(Color.slateCard)
                                    .clipShape(Circle())
                            }

                            Spacer()

                            DatePicker("", selection: $selectedDate, displayedComponents: .date)
                                .datePickerStyle(.compact)
                                .labelsHidden()
                                .onChange(of: selectedDate) { _ in loadData() }

                            Spacer()

                            Button(action: { changeDay(by: 1) }) {
                                Image(systemName: "chevron.right")
                                    .foregroundColor(.white)
                                    .padding(10)
                                    .background(Color.slateCard)
                                    .clipShape(Circle())
                            }
                        }
                        .padding(.horizontal)

                        // 4 Summary Metrics Cards
                        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
                            MetricCard(title: "💵 CASH IN", amount: summary.cashSales, color: .emeraldGreen, icon: "banknote")
                            MetricCard(title: "🏛️ BANK SLIPS", amount: summary.bankSlips, color: .blue, icon: "building.columns")
                            MetricCard(title: "✂️ EXPENSES", amount: summary.totalExpense, color: .red, icon: "scissors")
                            MetricCard(title: "👥 UDHAAR GIVEN", amount: summary.udhaarGiven, color: .orange, icon: "person.crop.circle.badge.plus")
                        }
                        .padding(.horizontal)

                        // Net Closing Banner
                        HStack {
                            VStack(alignment: .leading, spacing: 4) {
                                Text("NET DAY CLOSING BALANCE")
                                    .font(.system(size: 11, weight: .bold))
                                    .foregroundColor(.gray)
                                Text("PKR \(summary.netClosingBalance, specifier: "%.2f")")
                                    .font(.system(size: 22, weight: .black, design: .rounded))
                                    .foregroundColor(.emeraldGreen)
                            }
                            Spacer()
                            Image(systemName: "checkmark.seal.fill")
                                .font(.system(size: 32))
                                .foregroundColor(.emeraldGreen.opacity(0.8))
                        }
                        .padding()
                        .background(Color.slateCard)
                        .cornerRadius(16)
                        .overlay(
                            RoundedRectangle(cornerRadius: 16)
                                .stroke(Color.emeraldGreen.opacity(0.3), lineWidth: 1)
                        )
                        .padding(.horizontal)

                        // Action Quick Buttons
                        HStack(spacing: 12) {
                            Button(action: { showEntryModal = true }) {
                                HStack {
                                    Image(systemName: "plus.circle.fill")
                                    Text("Add Cash / Expense")
                                        .font(.system(size: 14, weight: .bold))
                                }
                                .foregroundColor(.white)
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 12)
                                .background(Color.emeraldGreen)
                                .cornerRadius(12)
                            }
                        }
                        .padding(.horizontal)

                        // Transactions List Header
                        HStack {
                            Text("TRANSACTIONS (\(summary.transactions.count))")
                                .font(.system(size: 12, weight: .bold))
                                .foregroundColor(.gray)
                            Spacer()
                        }
                        .padding(.horizontal)
                        .padding(.top, 8)

                        // Transactions List
                        if summary.transactions.isEmpty {
                            VStack(spacing: 8) {
                                Image(systemName: "tray")
                                    .font(.system(size: 36))
                                    .foregroundColor(.gray.opacity(0.5))
                                Text("No transactions recorded for this day.")
                                    .font(.system(size: 13))
                                    .foregroundColor(.gray)
                            }
                            .padding(.vertical, 30)
                        } else {
                            VStack(spacing: 8) {
                                ForEach(summary.transactions) { tx in
                                    TransactionRow(tx: tx, onDelete: {
                                        _ = DatabaseManager.shared.deleteTransaction(id: tx.id)
                                        loadData()
                                    })
                                }
                            }
                            .padding(.horizontal)
                        }
                    }
                    .padding(.vertical)
                }
            }
            .navigationTitle("🎱 Daily Closing")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button(action: {
                        DatabaseManager.shared.syncWithCloud { success, msg in
                            loadData()
                        }
                    }) {
                        HStack(spacing: 4) {
                            Image(systemName: "arrow.triangle.2.circlepath")
                            Text("Sync")
                                .font(.system(size: 13, weight: .bold))
                        }
                        .foregroundColor(.emeraldGreen)
                    }
                }
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button(action: { BiometricAuth.shared.lockApp() }) {
                        Image(systemName: "lock.fill")
                            .foregroundColor(.red)
                    }
                }
            }
            .sheet(isPresented: $showEntryModal) {
                CashEntryModal { loadData() }
            }
            .onAppear { loadData() }
        }
    }

    private func changeDay(by offset: Int) {
        if let newDate = Calendar.current.date(byAdding: .day, value: offset, to: selectedDate) {
            selectedDate = newDate
            loadData()
        }
    }

    private func loadData() {
        summary = DatabaseManager.shared.getDailyClosing(for: dateString)
    }
}

struct MetricCard: View {
    let title: String
    let amount: Double
    let color: Color
    let icon: String

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(title)
                    .font(.system(size: 10, weight: .bold))
                    .foregroundColor(color)
                Spacer()
                Image(systemName: icon)
                    .font(.system(size: 12))
                    .foregroundColor(color)
            }
            Text("PKR \(amount, specifier: "%.2f")")
                .font(.system(size: 15, weight: .bold, design: .rounded))
                .foregroundColor(.white)
        }
        .padding(12)
        .background(Color.slateCard)
        .cornerRadius(14)
        .overlay(
            RoundedRectangle(cornerRadius: 14)
                .stroke(color.opacity(0.2), lineWidth: 1)
        )
    }
}

struct TransactionRow: View {
    let tx: Transaction
    let onDelete: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            Circle()
                .fill(isCredit ? Color.emeraldGreen.opacity(0.2) : Color.red.opacity(0.2))
                .frame(width: 36, height: 36)
                .overlay(
                    Image(systemName: isCredit ? "arrow.down.left" : "arrow.up.right")
                        .font(.system(size: 14, weight: .bold))
                        .foregroundColor(isCredit ? .emeraldGreen : .red)
                )

            VStack(alignment: .leading, spacing: 2) {
                Text(tx.merchant)
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundColor(.white)
                Text("\(tx.category) • \(tx.paymentMethod)")
                    .font(.system(size: 11))
                    .foregroundColor(.gray)
            }

            Spacer()

            VStack(alignment: .trailing, spacing: 2) {
                Text("\(isCredit ? "+" : "-")PKR \(tx.totalAmount, specifier: "%.2f")")
                    .font(.system(size: 14, weight: .bold, design: .rounded))
                    .foregroundColor(isCredit ? .emeraldGreen : .red)

                Button(action: onDelete) {
                    Image(systemName: "trash")
                        .font(.system(size: 11))
                        .foregroundColor(.gray.opacity(0.6))
                }
            }
        }
        .padding(12)
        .background(Color.slateCard)
        .cornerRadius(12)
    }

    private var isCredit: Bool {
        return tx.txType == "Credit" || tx.txType == "Udhaar Recovery"
    }
}
