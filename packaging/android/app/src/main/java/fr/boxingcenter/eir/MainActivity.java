package fr.boxingcenter.eir;

import android.app.Activity;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.Inet4Address;
import java.net.InetAddress;
import java.net.NetworkInterface;
import java.net.URL;
import java.util.ArrayList;
import java.util.Enumeration;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;

public class MainActivity extends Activity {
    private WebView web;
    private LinearLayout splash;
    private TextView status;
    private Button retry;
    private SharedPreferences prefs;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        prefs = getSharedPreferences("eir", MODE_PRIVATE);

        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(Color.parseColor("#070B18"));

        web = new WebView(this);
        WebSettings settings = web.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        web.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageFinished(WebView view, String url) {
                splash.setVisibility(View.GONE);
            }
        });
        web.setWebChromeClient(new WebChromeClient());
        root.addView(web, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT));

        splash = new LinearLayout(this);
        splash.setOrientation(LinearLayout.VERTICAL);
        splash.setGravity(Gravity.CENTER);
        splash.setBackgroundColor(Color.parseColor("#070B18"));
        splash.setPadding(dp(24), dp(24), dp(24), dp(24));

        ImageView logo = new ImageView(this);
        logo.setImageResource(R.mipmap.ic_launcher);
        LinearLayout.LayoutParams logoParams = new LinearLayout.LayoutParams(dp(96), dp(96));
        logoParams.bottomMargin = dp(18);
        splash.addView(logo, logoParams);

        TextView title = new TextView(this);
        title.setText("EIR");
        title.setTextColor(Color.WHITE);
        title.setTextSize(28);
        title.setGravity(Gravity.CENTER);
        splash.addView(title);

        status = new TextView(this);
        status.setText("Connexion a la station");
        status.setTextColor(Color.parseColor("#A4D8C4"));
        status.setTextSize(16);
        status.setGravity(Gravity.CENTER);
        status.setPadding(0, dp(12), 0, dp(16));
        splash.addView(status);

        retry = new Button(this);
        retry.setText("Reessayer");
        retry.setAllCaps(false);
        retry.setMinHeight(dp(48));
        retry.setVisibility(View.GONE);
        retry.setOnClickListener(v -> connect());
        splash.addView(retry, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT));

        root.addView(splash, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT));
        setContentView(root);
        connect();
    }

    private void connect() {
        retry.setVisibility(View.GONE);
        status.setText("Connexion a la station");
        splash.setVisibility(View.VISIBLE);
        new Thread(() -> {
            String saved = prefs.getString("host", "");
            String host = saved.isEmpty() ? null : (reachable(saved) ? saved : null);
            if (host == null) host = scan();
            final String found = host;
            runOnUiThread(() -> {
                if (found == null) {
                    status.setText("La station n'est pas sur ce reseau.");
                    retry.setVisibility(View.VISIBLE);
                    return;
                }
                prefs.edit().putString("host", found).apply();
                web.loadUrl("http://" + found + ":5173/");
            });
        }).start();
    }

    private String scan() {
        List<String> prefixes = new ArrayList<String>();
        try {
            Enumeration<NetworkInterface> interfaces = NetworkInterface.getNetworkInterfaces();
            while (interfaces.hasMoreElements()) {
                NetworkInterface item = interfaces.nextElement();
                Enumeration<InetAddress> addresses = item.getInetAddresses();
                while (addresses.hasMoreElements()) {
                    InetAddress address = addresses.nextElement();
                    if (!(address instanceof Inet4Address) || address.isLoopbackAddress()) continue;
                    byte[] raw = address.getAddress();
                    prefixes.add((raw[0] & 255) + "." + (raw[1] & 255) + "." + (raw[2] & 255) + ".");
                }
            }
        } catch (Exception ignored) {
            return null;
        }
        ExecutorService pool = Executors.newFixedThreadPool(32);
        AtomicBoolean done = new AtomicBoolean(false);
        final String[] found = new String[1];
        for (String prefix : prefixes) {
            for (int i = 1; i < 255; i++) {
                final String host = prefix + i;
                pool.execute(() -> {
                    if (done.get()) return;
                    if (reachable(host)) {
                        synchronized (found) {
                            if (found[0] == null) found[0] = host;
                        }
                        done.set(true);
                    }
                });
            }
        }
        pool.shutdown();
        try {
            pool.awaitTermination(12, java.util.concurrent.TimeUnit.SECONDS);
        } catch (InterruptedException ignored) {
            Thread.currentThread().interrupt();
        }
        return found[0];
    }

    private boolean reachable(String host) {
        HttpURLConnection connection = null;
        try {
            connection = (HttpURLConnection) new URL("http://" + host + ":5173/").openConnection();
            connection.setConnectTimeout(350);
            connection.setReadTimeout(350);
            connection.setInstanceFollowRedirects(true);
            InputStream stream = connection.getInputStream();
            byte[] buffer = new byte[600];
            int read = stream.read(buffer);
            stream.close();
            if (read <= 0) return false;
            String text = new String(buffer, 0, read, "UTF-8");
            return text.contains("EIR");
        } catch (Exception ignored) {
            return false;
        } finally {
            if (connection != null) connection.disconnect();
        }
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}
