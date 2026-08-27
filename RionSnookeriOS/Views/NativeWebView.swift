import SwiftUI
import WebKit

public struct NativeWebView: UIViewRepresentable {
    public let url: URL

    public init(url: URL = URL(string: "https://rion-snooker-lounge-rk51.onrender.com")!) {
        self.url = url
    }

    public func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }

    public func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.allowsInlineMediaPlayback = true
        config.mediaTypesRequiringUserActionForPlayback = []
        config.preferences.javaScriptCanOpenWindowsAutomatically = true

        let webView = WKWebView(frame: .zero, configuration: config)
        webView.navigationDelegate = context.coordinator
        webView.isOpaque = false
        webView.backgroundColor = UIColor(red: 2/255, green: 6/255, blue: 23/255, alpha: 1)
        webView.scrollView.backgroundColor = UIColor(red: 2/255, green: 6/255, blue: 23/255, alpha: 1)

        // Add native iOS Pull-to-Refresh
        let refreshControl = UIRefreshControl()
        refreshControl.tintColor = UIColor(red: 16/255, green: 185/255, blue: 129/255, alpha: 1)
        refreshControl.addTarget(context.coordinator, action: #selector(Coordinator.handleRefresh(_:)), for: .valueChanged)
        webView.scrollView.refreshControl = refreshControl

        let request = URLRequest(url: url, cachePolicy: .reloadIgnoringLocalAndRemoteCacheData, timeoutInterval: 45)
        webView.load(request)
        return webView
    }

    public func updateUIView(_ uiView: WKWebView, context: Context) {}

    public class Coordinator: NSObject, WKNavigationDelegate {
        var parent: NativeWebView

        init(_ parent: NativeWebView) {
            self.parent = parent
        }

        @objc func handleRefresh(_ sender: UIRefreshControl) {
            sender.endRefreshing()
            // Reload page from fresh network without disk cache on pull-down
            if let webView = sender.superview as? UIScrollView, let parentView = webView.superview as? WKWebView {
                let req = URLRequest(url: parent.url, cachePolicy: .reloadIgnoringLocalAndRemoteCacheData, timeoutInterval: 45)
                parentView.load(req)
            }
        }

        public func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
            let js = """
            sessionStorage.setItem('rion_auth_token', 'rion_auth_session_valid');
            const overlay = document.getElementById('login-overlay');
            if (overlay) overlay.classList.add('hidden');
            document.body.style.backgroundColor = '#020617';
            if (typeof refreshDayView === 'function') refreshDayView();
            """
            webView.evaluateJavaScript(js, completionHandler: nil)
        }
    }
}
