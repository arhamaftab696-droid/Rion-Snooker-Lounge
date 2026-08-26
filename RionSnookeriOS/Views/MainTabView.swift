import SwiftUI

public struct MainTabView: View {
    public init() {}

    public var body: some View {
        TabView {
            DailyClosingView()
                .tabItem {
                    Label("Daily", systemImage: "calendar")
                }

            KhataView()
                .tabItem {
                    Label("Khata", systemImage: "person.2.fill")
                }

            StaffView()
                .tabItem {
                    Label("Staff", systemImage: "person.crop.rectangle.stack")
                }

            MonthlyView()
                .tabItem {
                    Label("Monthly", systemImage: "chart.bar.xaxis")
                }

            SettingsView()
                .tabItem {
                    Label("Settings", systemImage: "gearshape.fill")
                }
        }
        .accentColor(.emeraldGreen)
    }
}
