import SwiftUI

@main
struct RionSnookerApp: App {
    @StateObject private var auth = BiometricAuth.shared

    var body: some Scene {
        WindowGroup {
            ZStack {
                Color(red: 2/255, green: 6/255, blue: 23/255)
                    .ignoresSafeArea()

                if auth.isUnlocked {
                    NativeWebView()
                        .ignoresSafeArea(.keyboard, edges: .bottom)
                } else {
                    LockView()
                }
            }
        }
    }
}
