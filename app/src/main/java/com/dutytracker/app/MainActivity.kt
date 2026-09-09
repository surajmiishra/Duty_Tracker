package com.dutytracker.app

import android.annotation.SuppressLint
import android.graphics.Color
import android.os.Bundle
import android.view.ViewGroup
import android.webkit.CookieManager
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.OnBackPressedCallback

class MainActivity : ComponentActivity() {

    private lateinit var webView: WebView

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Create WebView
        webView = WebView(this)

        webView.layoutParams = ViewGroup.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.MATCH_PARENT
        )

        webView.setBackgroundColor(Color.WHITE)

        // WebView settings
        webView.settings.apply {

            javaScriptEnabled = true
            domStorageEnabled = true
            databaseEnabled = true

            allowFileAccess = true
            allowContentAccess = true

            loadsImagesAutomatically = true
            blockNetworkImage = false
            blockNetworkLoads = false

            mixedContentMode =
                WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE

            javaScriptCanOpenWindowsAutomatically = true
            setSupportMultipleWindows(false)

            cacheMode = WebSettings.LOAD_DEFAULT

            userAgentString =
                "Mozilla/5.0 (Linux; Android 13) " +
                        "AppleWebKit/537.36 (KHTML, like Gecko) " +
                        "Chrome/140.0.0.0 Mobile Safari/537.36"
        }

        // ---------------------------------------------------------
        // COOKIE SETTINGS
        // ---------------------------------------------------------

        val cookieManager = CookieManager.getInstance()

        // Allow cookies
        cookieManager.setAcceptCookie(true)

        // Allow third-party cookies
        cookieManager.setAcceptThirdPartyCookies(webView, true)

        // ---------------------------------------------------------
        // WEBVIEW CLIENT
        // ---------------------------------------------------------

        webView.webViewClient = object : WebViewClient() {

            override fun shouldOverrideUrlLoading(
                view: WebView,
                request: WebResourceRequest
            ): Boolean {
                return false
            }

            override fun onReceivedError(
                view: WebView,
                request: WebResourceRequest,
                error: WebResourceError
            ) {
                super.onReceivedError(view, request, error)

                if (request.isForMainFrame) {
                    Toast.makeText(
                        this@MainActivity,
                        "Unable to load Duty Tracker. Check your internet connection.",
                        Toast.LENGTH_LONG
                    ).show()
                }
            }

            override fun onPageFinished(
                view: WebView,
                url: String
            ) {
                super.onPageFinished(view, url)

                // Make sure cookies are written to persistent storage
                cookieManager.flush()
            }
        }

        webView.webChromeClient = WebChromeClient()

        // ---------------------------------------------------------
        // DISPLAY WEBVIEW
        // ---------------------------------------------------------

        setContentView(webView)

        // ---------------------------------------------------------
        // RESTORE WEBVIEW STATE IF AVAILABLE
        // ---------------------------------------------------------

        if (savedInstanceState == null) {

            webView.loadUrl(
                "https://dutytracker.streamlit.app/"
            )

        } else {

            webView.restoreState(savedInstanceState)
        }

        // ---------------------------------------------------------
        // ANDROID BACK BUTTON
        // ---------------------------------------------------------

        onBackPressedDispatcher.addCallback(
            this,
            object : OnBackPressedCallback(true) {

                override fun handleOnBackPressed() {

                    if (webView.canGoBack()) {
                        webView.goBack()
                    } else {
                        finish()
                    }
                }
            }
        )
    }

    // -------------------------------------------------------------
    // SAVE WEBVIEW STATE
    // -------------------------------------------------------------

    override fun onSaveInstanceState(outState: Bundle) {
        webView.saveState(outState)
        super.onSaveInstanceState(outState)
    }

    // -------------------------------------------------------------
    // MAKE SURE COOKIES ARE SAVED
    // -------------------------------------------------------------

    override fun onPause() {
        super.onPause()

        CookieManager.getInstance().flush()
    }

    // -------------------------------------------------------------
    // CLEANUP
    // -------------------------------------------------------------

    override fun onDestroy() {

        CookieManager.getInstance().flush()

        webView.stopLoading()
        webView.clearHistory()
        webView.removeAllViews()
        webView.destroy()

        super.onDestroy()
    }
}