package com.jobmind.match;

import android.os.Bundle;
import android.webkit.WebSettings;
import android.webkit.WebView;

import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
	@Override
	public void onCreate(Bundle savedInstanceState) {
		super.onCreate(savedInstanceState);

		WebView webView = getBridge().getWebView();
		WebSettings settings = webView.getSettings();

		settings.setUseWideViewPort(false);
		settings.setLoadWithOverviewMode(false);
		settings.setBuiltInZoomControls(false);
		settings.setDisplayZoomControls(false);
		settings.setTextZoom(100);
	}
}
