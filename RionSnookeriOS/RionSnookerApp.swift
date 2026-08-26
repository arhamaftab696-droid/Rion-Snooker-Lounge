import SwiftUI

@main
struct RionSnookerApp: App {
    @StateObject private var auth = BiometricAuth.shared
    @StateObject private var db = DatabaseManager.shared

    init() {
        // Dark theme navigation bar and tab bar styling
        let navBarAppearance = UINavigationBarAppearance()
        navBarAppearance.configureWithOpaqueBackground()
        navBarAppearance.backgroundColor = UIColor(red: 2/255, green: 6/255, blue: 23/255, alpha: 1)
        navBarAppearance.titleTextAttributes = [.foregroundColor: UIColor.white]
        navBarAppearance.largeTitleTextAttributes = [.foregroundColor: UIColor.white]
        UINavigationBar.appearance().standardAppearance = navBarAppearance
        UINavigationBar.appearance().scrollEdgeAppearance = navBarAppearance

        let tabBarAppearance = UITabBarAppearance()
        tabBarAppearance.configureWithOpaqueBackground()
        tabBarAppearance.backgroundColor = UIColor(red: 15/255, green: 23/255, blue: 42/255, alpha: 1)
        UITabBar.appearance().standardAppearance = tabBarAppearance
        UITabBar.appearance().scrollEdgeAppearance = tabBarAppearance
    }

    var body: some Scene {
        WindowGroup {
            if auth.isUnlocked {
                MainTabView()
            } else {
                LockView()
            }
        }
    }
}
