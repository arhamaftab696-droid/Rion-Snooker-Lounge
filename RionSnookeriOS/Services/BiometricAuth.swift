import Foundation
import LocalAuthentication

public class BiometricAuth: ObservableObject {
    public static let shared = BiometricAuth()

    @Published public var isUnlocked: Bool = false
    @Published public var errorMessage: String = ""

    private init() {}

    public func authenticateWithBiometrics(completion: @escaping (Bool) -> Void) {
        let context = LAContext()
        var error: NSError?

        if context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &error) {
            let reason = "Unlock Rion Snooker Lounge"
            context.evaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, localizedReason: reason) { success, authError in
                DispatchQueue.main.async {
                    if success {
                        self.isUnlocked = true
                        completion(true)
                    } else {
                        self.errorMessage = authError?.localizedDescription ?? "Face ID Failed"
                        completion(false)
                    }
                }
            }
        } else {
            // Biometrics not available on device / simulator
            DispatchQueue.main.async {
                self.errorMessage = "Face ID not available. Use PIN."
                completion(false)
            }
        }
    }

    public func verifyPIN(_ inputPIN: String) -> Bool {
        let adminPIN = DatabaseManager.shared.getAdminPIN()
        if inputPIN == adminPIN {
            self.isUnlocked = true
            return true
        }
        return false
    }

    public func lockApp() {
        self.isUnlocked = false
    }
}
