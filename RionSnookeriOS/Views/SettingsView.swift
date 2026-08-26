import SwiftUI

public struct SettingsView: View {
    @ObservedObject var auth = BiometricAuth.shared
    @State private var currentPIN: String = ""
    @State private var newPIN: String = ""
    @State private var confirmPIN: String = ""
    @State private var pinMessage: String = ""

    public init() {}

    public var body: some View {
        NavigationView {
            ZStack {
                Color.darkBg.ignoresSafeArea()

                ScrollView {
                    VStack(spacing: 20) {
                        // Security Section
                        VStack(alignment: .leading, spacing: 14) {
                            Text("SECURITY & ACCESS")
                                .font(.system(size: 11, weight: .bold))
                                .foregroundColor(.gray)

                            VStack(spacing: 12) {
                                SecureField("Current PIN (Default: 6861)", text: $currentPIN)
                                    .keyboardType(.numberPad)
                                    .padding()
                                    .background(Color.slateCard)
                                    .cornerRadius(12)
                                    .foregroundColor(.white)

                                SecureField("New 4-Digit PIN", text: $newPIN)
                                    .keyboardType(.numberPad)
                                    .padding()
                                    .background(Color.slateCard)
                                    .cornerRadius(12)
                                    .foregroundColor(.white)

                                SecureField("Confirm New PIN", text: $confirmPIN)
                                    .keyboardType(.numberPad)
                                    .padding()
                                    .background(Color.slateCard)
                                    .cornerRadius(12)
                                    .foregroundColor(.white)

                                if !pinMessage.isEmpty {
                                    Text(pinMessage)
                                        .font(.system(size: 12, weight: .bold))
                                        .foregroundColor(pinMessage.contains("✅") ? .emeraldGreen : .red)
                                }

                                Button(action: updatePIN) {
                                    Text("Change Security PIN")
                                        .font(.system(size: 14, weight: .bold))
                                        .foregroundColor(.white)
                                        .frame(maxWidth: .infinity)
                                        .padding(.vertical, 12)
                                        .background(Color.emeraldGreen)
                                        .cornerRadius(10)
                                }
                            }
                        }
                        .padding()
                        .background(Color.slateCard)
                        .cornerRadius(16)
                        .padding(.horizontal)

                        // Database Info Card
                        VStack(alignment: .leading, spacing: 10) {
                            Text("LOCAL IPHONE DATABASE")
                                .font(.system(size: 11, weight: .bold))
                                .foregroundColor(.gray)

                            HStack {
                                Image(systemName: "internaldrive.fill")
                                    .foregroundColor(.emeraldGreen)
                                Text("Storage: On-Device SQLite (Offline)")
                                    .font(.system(size: 13, weight: .semibold))
                                    .foregroundColor(.white)
                            }

                            Text("File: \(DatabaseManager.shared.dbURL.lastPathComponent)")
                                .font(.system(size: 11))
                                .foregroundColor(.gray)
                        }
                        .padding()
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(Color.slateCard)
                        .cornerRadius(16)
                        .padding(.horizontal)

                        // Lock App Button
                        Button(action: {
                            auth.lockApp()
                        }) {
                            HStack {
                                Image(systemName: "lock.fill")
                                Text("Lock Software Now")
                                    .font(.system(size: 15, weight: .bold))
                            }
                            .foregroundColor(.white)
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(Color.red.opacity(0.8))
                            .cornerRadius(14)
                        }
                        .padding(.horizontal)
                    }
                    .padding(.vertical)
                }
            }
            .navigationTitle("⚙️ Settings")
            .navigationBarTitleDisplayMode(.inline)
        }
    }

    private func updatePIN() {
        let savedPIN = DatabaseManager.shared.getAdminPIN()
        if currentPIN != savedPIN {
            pinMessage = "❌ Current PIN is incorrect."
            return
        }
        if newPIN.count != 4 {
            pinMessage = "⚠️ New PIN must be exactly 4 digits."
            return
        }
        if newPIN != confirmPIN {
            pinMessage = "❌ New PINs do not match."
            return
        }

        if DatabaseManager.shared.setAdminPIN(newPIN) {
            pinMessage = "✅ PIN updated successfully to \(newPIN)!"
            currentPIN = ""
            newPIN = ""
            confirmPIN = ""
        } else {
            pinMessage = "❌ Error saving new PIN."
        }
    }
}
