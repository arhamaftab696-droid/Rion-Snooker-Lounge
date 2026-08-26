import SwiftUI

public struct LockView: View {
    @ObservedObject var auth = BiometricAuth.shared
    @State private var enteredPIN: String = ""
    @State private var showError: Bool = false

    public init() {}

    public var body: some View {
        ZStack {
            Color(red: 2/255, green: 6/255, blue: 23/255) // Slate-950
                .ignoresSafeArea()

            VStack(spacing: 28) {
                Spacer()

                // 8-Ball Icon & Branding
                VStack(spacing: 12) {
                    ZStack {
                        Circle()
                            .fill(LinearGradient(colors: [Color.emeraldGreen, Color(red: 4/255, green: 120/255, blue: 87/255)], startPoint: .topLeading, endPoint: .bottomTrailing))
                            .frame(width: 80, height: 80)
                            .shadow(color: Color.emeraldGreen.opacity(0.3), radius: 12)

                        Text("🎱")
                            .font(.system(size: 40))
                    }

                    Text("RION SNOOKER")
                        .font(.system(size: 22, weight: .black, design: .rounded))
                        .foregroundColor(.white)
                    
                    Text("Daily Closing & Khata Management")
                        .font(.system(size: 13, weight: .medium))
                        .foregroundColor(.gray)
                }

                // PIN Input Dots
                HStack(spacing: 16) {
                    ForEach(0..<4) { index in
                        Circle()
                            .fill(index < enteredPIN.count ? Color.emeraldGreen : Color.white.opacity(0.15))
                            .frame(width: 16, height: 16)
                    }
                }
                .padding(.vertical, 8)

                if showError {
                    Text("❌ Incorrect PIN. Please try again.")
                        .font(.system(size: 13, weight: .bold))
                        .foregroundColor(.red)
                }

                // Numeric Keypad
                VStack(spacing: 14) {
                    ForEach(0..<3) { row in
                        HStack(spacing: 24) {
                            ForEach(1..<4) { col in
                                let digit = "\(row * 3 + col)"
                                KeypadButton(title: digit) {
                                    appendDigit(digit)
                                }
                            }
                        }
                    }

                    HStack(spacing: 24) {
                        // Face ID Button
                        Button(action: {
                            auth.authenticateWithBiometrics { _ in }
                        }) {
                            Image(systemName: "faceid")
                                .font(.system(size: 26))
                                .foregroundColor(.emeraldGreen)
                                .frame(width: 75, height: 75)
                                .background(Color.white.opacity(0.06))
                                .clipShape(Circle())
                        }

                        KeypadButton(title: "0") {
                            appendDigit("0")
                        }

                        // Backspace
                        Button(action: {
                            if !enteredPIN.isEmpty {
                                enteredPIN.removeLast()
                                showError = false
                            }
                        }) {
                            Image(systemName: "delete.left.fill")
                                .font(.system(size: 22))
                                .foregroundColor(.gray)
                                .frame(width: 75, height: 75)
                                .background(Color.white.opacity(0.06))
                                .clipShape(Circle())
                        }
                    }
                }

                Spacer()
            }
            .padding()
        }
        .onAppear {
            auth.authenticateWithBiometrics { _ in }
        }
    }

    private func appendDigit(_ d: String) {
        if enteredPIN.count < 4 {
            enteredPIN.append(d)
            showError = false

            if enteredPIN.count == 4 {
                if auth.verifyPIN(enteredPIN) {
                    enteredPIN = ""
                } else {
                    showError = true
                    enteredPIN = ""
                }
            }
        }
    }
}

struct KeypadButton: View {
    let title: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.system(size: 26, weight: .semibold, design: .rounded))
                .foregroundColor(.white)
                .frame(width: 75, height: 75)
                .background(Color.white.opacity(0.08))
                .clipShape(Circle())
        }
    }
}

extension Color {
    static let emeraldGreen = Color(red: 16/255, green: 185/255, blue: 129/255)
    static let slateCard = Color(red: 15/255, green: 23/255, blue: 42/255)
    static let darkBg = Color(red: 2/255, green: 6/255, blue: 23/255)
}
