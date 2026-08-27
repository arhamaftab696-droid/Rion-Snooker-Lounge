import SwiftUI

public struct KhataView: View {
    @State private var customers: [Customer] = []
    @State private var searchText: String = ""
    @State private var showPaymentModal: Bool = false
    @State private var selectedCustomer: Customer?
    @State private var paymentAmount: String = ""

    public init() {}

    private var filteredCustomers: [Customer] {
        if searchText.isEmpty {
            return customers
        }
        return customers.filter { $0.name.localizedCaseInsensitiveContains(searchText) }
    }

    private var totalPending: Double {
        customers.reduce(0) { $0 + max(0, $1.pendingBalance) }
    }

    public var body: some View {
        NavigationView {
            ZStack {
                Color.darkBg.ignoresSafeArea()

                VStack(spacing: 14) {
                    // Summary Banner
                    HStack {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("TOTAL OUTSTANDING UDHAAR")
                                .font(.system(size: 10, weight: .bold))
                                .foregroundColor(.orange)
                            Text("PKR \(totalPending, specifier: "%.2f")")
                                .font(.system(size: 22, weight: .black, design: .rounded))
                                .foregroundColor(.white)
                        }
                        Spacer()
                        VStack(alignment: .trailing, spacing: 4) {
                            Text("TOTAL CLIENTS")
                                .font(.system(size: 10, weight: .bold))
                                .foregroundColor(.gray)
                            Text("\(customers.count)")
                                .font(.system(size: 20, weight: .bold))
                                .foregroundColor(.emeraldGreen)
                        }
                    }
                    .padding()
                    .background(Color.slateCard)
                    .cornerRadius(16)
                    .padding(.horizontal)

                    // Search Field
                    HStack {
                        Image(systemName: "magnifyingglass")
                            .foregroundColor(.gray)
                        TextField("Search customer name...", text: $searchText)
                            .foregroundColor(.white)
                    }
                    .padding(12)
                    .background(Color.slateCard)
                    .cornerRadius(12)
                    .padding(.horizontal)

                    // Customer List
                    ScrollView {
                        if filteredCustomers.isEmpty {
                            VStack(spacing: 14) {
                                Image(systemName: "person.2.slash")
                                    .font(.system(size: 40))
                                    .foregroundColor(.gray.opacity(0.5))
                                Text("No Khata records found.")
                                    .font(.system(size: 14, weight: .semibold))
                                    .foregroundColor(.gray)

                                Button(action: {
                                    DatabaseManager.shared.syncWithCloud { _, _ in
                                        loadCustomers()
                                    }
                                }) {
                                    HStack {
                                        Image(systemName: "arrow.triangle.2.circlepath")
                                        Text("🔄 Sync All 29 Clients Now")
                                            .font(.system(size: 14, weight: .bold))
                                    }
                                    .foregroundColor(.white)
                                    .padding(.horizontal, 16)
                                    .padding(.vertical, 10)
                                    .background(Color.emeraldGreen)
                                    .cornerRadius(10)
                                }
                            }
                            .padding(.vertical, 40)
                        } else {
                            LazyVStack(spacing: 8) {
                                ForEach(filteredCustomers) { cust in
                                    CustomerRow(customer: cust) {
                                        selectedCustomer = cust
                                        paymentAmount = ""
                                        showPaymentModal = true
                                    }
                                }
                            }
                            .padding(.horizontal)
                        }
                    }
                }
                .padding(.top, 8)
            }
            .navigationTitle("👥 Customer Khata")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button(action: {
                        DatabaseManager.shared.syncWithCloud { success, msg in
                            loadCustomers()
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
            }
            .sheet(isPresented: $showPaymentModal) {
                if let cust = selectedCustomer {
                    KhataPaymentSheet(customer: cust) {
                        loadCustomers()
                    }
                }
            }
            .onAppear { loadCustomers() }
        }
    }

    private func loadCustomers() {
        customers = DatabaseManager.shared.getAllCustomers()
    }
}

struct CustomerRow: View {
    let customer: Customer
    let onSettle: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            Circle()
                .fill(customer.pendingBalance > 0 ? Color.orange.opacity(0.2) : Color.emeraldGreen.opacity(0.2))
                .frame(width: 40, height: 40)
                .overlay(
                    Text(String(customer.name.prefix(1)))
                        .font(.system(size: 16, weight: .bold))
                        .foregroundColor(customer.pendingBalance > 0 ? .orange : .emeraldGreen)
                )

            VStack(alignment: .leading, spacing: 3) {
                Text(customer.name)
                    .font(.system(size: 15, weight: .semibold))
                    .foregroundColor(.white)
                Text("Given: PKR \(customer.totalGiven, specifier: "%.0f") • Ret: PKR \(customer.totalReturned, specifier: "%.0f")")
                    .font(.system(size: 11))
                    .foregroundColor(.gray)
            }

            Spacer()

            VStack(alignment: .trailing, spacing: 4) {
                Text("PKR \(customer.pendingBalance, specifier: "%.0f")")
                    .font(.system(size: 14, weight: .bold, design: .rounded))
                    .foregroundColor(customer.pendingBalance > 0 ? .orange : .emeraldGreen)

                Button(action: onSettle) {
                    Text("Settle / Pay")
                        .font(.system(size: 10, weight: .bold))
                        .foregroundColor(.white)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(Color.emeraldGreen)
                        .cornerRadius(6)
                }
            }
        }
        .padding(12)
        .background(Color.slateCard)
        .cornerRadius(12)
    }
}

struct KhataPaymentSheet: View {
    let customer: Customer
    var onSaved: () -> Void
    @Environment(\.presentationMode) var presentationMode

    @State private var amount: String = ""
    @State private var paymentType: String = "Return Payment" // Return Payment or Give Credit
    @State private var notes: String = ""

    var body: some View {
        NavigationView {
            ZStack {
                Color.darkBg.ignoresSafeArea()

                VStack(spacing: 20) {
                    VStack(spacing: 6) {
                        Text(customer.name)
                            .font(.system(size: 20, weight: .bold))
                            .foregroundColor(.white)
                        Text("Current Balance: PKR \(customer.pendingBalance, specifier: "%.2f")")
                            .font(.system(size: 14, weight: .semibold))
                            .foregroundColor(customer.pendingBalance > 0 ? .orange : .emeraldGreen)
                    }
                    .padding()
                    .frame(maxWidth: .infinity)
                    .background(Color.slateCard)
                    .cornerRadius(14)

                    Picker("Action", selection: $paymentType) {
                        Text("💵 Payment Returned").tag("Return Payment")
                        Text("➕ Give New Udhaar").tag("Give Credit")
                    }
                    .pickerStyle(SegmentedPickerStyle())

                    TextField("Amount (PKR)", text: $amount)
                        .keyboardType(.decimalPad)
                        .font(.system(size: 22, weight: .bold))
                        .padding()
                        .background(Color.slateCard)
                        .foregroundColor(.emeraldGreen)
                        .cornerRadius(12)

                    TextField("Notes (optional)", text: $notes)
                        .padding()
                        .background(Color.slateCard)
                        .foregroundColor(.white)
                        .cornerRadius(12)

                    Spacer()

                    Button(action: savePayment) {
                        Text("Confirm Transaction")
                            .font(.system(size: 16, weight: .bold))
                            .foregroundColor(.white)
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(paymentType == "Return Payment" ? Color.emeraldGreen : Color.orange)
                            .cornerRadius(14)
                    }
                }
                .padding()
            }
            .navigationTitle("Khata Entry")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { presentationMode.wrappedValue.dismiss() }
                        .foregroundColor(.gray)
                }
            }
        }
    }

    private func savePayment() {
        guard let amt = Double(amount), amt > 0 else { return }

        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        let today = formatter.string(from: Date())

        if paymentType == "Return Payment" {
            _ = DatabaseManager.shared.addTransaction(
                date: today,
                merchant: customer.name,
                category: "Udhaar Recovery",
                amount: amt,
                txType: "Udhaar Recovery",
                paymentMethod: "Cash",
                notes: notes.isEmpty ? "Khata Payment Returned" : notes
            )
        } else {
            _ = DatabaseManager.shared.addTransaction(
                date: today,
                merchant: customer.name,
                category: "Customer Credit",
                amount: amt,
                txType: "Udhaar",
                paymentMethod: "Credit / Udhaar",
                notes: notes.isEmpty ? "Customer Credit Given" : notes
            )
        }

        onSaved()
        presentationMode.wrappedValue.dismiss()
    }
}
