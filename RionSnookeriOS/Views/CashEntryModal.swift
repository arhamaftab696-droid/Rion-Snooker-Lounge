import SwiftUI

public struct CashEntryModal: View {
    @Environment(\.presentationMode) var presentationMode
    var onSaved: () -> Void

    @State private var date: Date = Date()
    @State private var entryType: String = "Counter Cash" // Counter Cash, Bank Slip, Daily Expense, Udhaar
    @State private var selectedCustomer: String = ""
    @State private var newCustomerName: String = ""
    @State private var isNewCustomer: Bool = false
    @State private var amount: String = ""
    @State private var notes: String = ""
    @State private var customers: [Customer] = []

    let entryTypes = ["Counter Cash", "Bank Slip", "Daily Expense", "Customer Udhaar"]

    public init(onSaved: @escaping () -> Void) {
        self.onSaved = onSaved
    }

    public var body: some View {
        NavigationView {
            ZStack {
                Color.darkBg.ignoresSafeArea()

                ScrollView {
                    VStack(spacing: 20) {
                        // Entry Type Picker
                        VStack(alignment: .leading, spacing: 8) {
                            Text("ENTRY TYPE")
                                .font(.system(size: 11, weight: .bold))
                                .foregroundColor(.gray)

                            Picker("Type", selection: $entryType) {
                                ForEach(entryTypes, id: \.self) { t in
                                    Text(t).tag(t)
                                }
                            }
                            .pickerStyle(SegmentedPickerStyle())
                        }

                        // Date Picker
                        DatePicker("Closing Date", selection: $date, displayedComponents: .date)
                            .datePickerStyle(.compact)
                            .foregroundColor(.white)
                            .padding()
                            .background(Color.slateCard)
                            .cornerRadius(12)

                        // Customer Selection (if Udhaar or Counter Cash)
                        if entryType == "Customer Udhaar" {
                            VStack(alignment: .leading, spacing: 8) {
                                Text("SELECT CUSTOMER")
                                    .font(.system(size: 11, weight: .bold))
                                    .foregroundColor(.gray)

                                Menu {
                                    ForEach(customers) { c in
                                        Button(action: {
                                            selectedCustomer = c.name
                                            isNewCustomer = false
                                        }) {
                                            Text(c.name)
                                        }
                                    }
                                    Button(action: {
                                        isNewCustomer = true
                                        selectedCustomer = ""
                                    }) {
                                        Label("➕ Add New Customer", systemImage: "person.badge.plus")
                                    }
                                } label: {
                                    HStack {
                                        Text(isNewCustomer ? "➕ New Customer" : (selectedCustomer.isEmpty ? "Tap to Choose Customer" : selectedCustomer))
                                            .foregroundColor(.white)
                                            .font(.system(size: 15, weight: .semibold))
                                        Spacer()
                                        Image(systemName: "chevron.down")
                                            .foregroundColor(.emeraldGreen)
                                    }
                                    .padding()
                                    .background(Color.slateCard)
                                    .cornerRadius(12)
                                }

                                if isNewCustomer {
                                    TextField("Enter New Customer Name", text: $newCustomerName)
                                        .padding()
                                        .background(Color.slateCard)
                                        .foregroundColor(.white)
                                        .cornerRadius(12)
                                }
                            }
                        }

                        // Amount Input
                        VStack(alignment: .leading, spacing: 8) {
                            Text("AMOUNT (PKR)")
                                .font(.system(size: 11, weight: .bold))
                                .foregroundColor(.gray)

                            TextField("0.00", text: $amount)
                                .keyboardType(.decimalPad)
                                .font(.system(size: 24, weight: .bold, design: .rounded))
                                .padding()
                                .background(Color.slateCard)
                                .foregroundColor(.emeraldGreen)
                                .cornerRadius(12)
                        }

                        // Notes / Reason
                        VStack(alignment: .leading, spacing: 8) {
                            Text("REASON / NOTES")
                                .font(.system(size: 11, weight: .bold))
                                .foregroundColor(.gray)

                            TextField("e.g. Marker cut, Table 3, Generator Diesel", text: $notes)
                                .padding()
                                .background(Color.slateCard)
                                .foregroundColor(.white)
                                .cornerRadius(12)
                        }

                        Spacer(minLength: 20)

                        // Save Button
                        Button(action: saveEntry) {
                            HStack {
                                Image(systemName: "checkmark.circle.fill")
                                Text("Save Record")
                                    .font(.system(size: 16, weight: .bold))
                            }
                            .foregroundColor(.white)
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(Color.emeraldGreen)
                            .cornerRadius(14)
                        }
                    }
                    .padding()
                }
            }
            .navigationTitle("Manual Entry")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        presentationMode.wrappedValue.dismiss()
                    }
                    .foregroundColor(.gray)
                }
            }
            .onAppear {
                customers = DatabaseManager.shared.getAllCustomers()
            }
        }
    }

    private func saveEntry() {
        guard let amtVal = Double(amount), amtVal > 0 else { return }

        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        let dateStr = formatter.string(from: date)

        var merchant = "Counter Play"
        var category = "Counter Cash"
        var txType = "Credit"
        var pm = "Cash"

        if entryType == "Bank Slip" {
            merchant = "Bank Slip"
            category = "Bank Receipt"
            txType = "Credit"
            pm = "Bank"
        } else if entryType == "Daily Expense" {
            merchant = notes.isEmpty ? "Daily Expense" : notes
            category = "Daily Expense"
            txType = "Expense"
            pm = "Cash"
        } else if entryType == "Customer Udhaar" {
            let custName = isNewCustomer ? newCustomerName.trimmingCharacters(in: .whitespaces) : selectedCustomer
            guard !custName.isEmpty else { return }
            merchant = custName
            category = "Customer Credit"
            txType = "Udhaar"
            pm = "Credit / Udhaar"

            if isNewCustomer {
                _ = DatabaseManager.shared.addCustomer(name: custName)
            }
        }

        _ = DatabaseManager.shared.addTransaction(
            date: dateStr,
            merchant: merchant,
            category: category,
            amount: amtVal,
            txType: txType,
            paymentMethod: pm,
            notes: notes
        )

        onSaved()
        presentationMode.wrappedValue.dismiss()
    }
}

