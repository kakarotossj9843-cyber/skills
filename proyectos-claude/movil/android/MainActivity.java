package __PACKAGE__;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.view.Window;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

import java.io.OutputStream;

/** Cáscara de la app: muestra la web incluida en el APK (assets/index.html) a pantalla completa. */
public class MainActivity extends Activity {
    private static final int PICK_FILE = 1;
    private static final int SAVE_FILE = 2;

    private WebView web;
    private ValueCallback<Uri[]> fileCallback;
    private String pendingText;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        Window w = getWindow();
        w.setStatusBarColor(Color.parseColor("__THEME__"));
        w.setNavigationBarColor(Color.parseColor("__BG__"));

        web = new WebView(this);
        web.setBackgroundColor(Color.parseColor("__BG__"));
        setContentView(web);

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setAllowFileAccess(true);
        s.setAllowFileAccessFromFileURLs(true);
        s.setAllowUniversalAccessFromFileURLs(true);
        s.setTextZoom(100);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);

        web.addJavascriptInterface(new Bridge(), "Android");
        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, String url) {
                if (url.startsWith("file:")) return false;
                openUrl(url);
                return true;
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback, FileChooserParams params) {
                if (fileCallback != null) fileCallback.onReceiveValue(null);
                fileCallback = callback;
                Intent i = new Intent(Intent.ACTION_GET_CONTENT);
                i.addCategory(Intent.CATEGORY_OPENABLE);
                i.setType("*/*");
                try {
                    startActivityForResult(Intent.createChooser(i, "Elegir archivo"), PICK_FILE);
                } catch (ActivityNotFoundException e) {
                    fileCallback = null;
                    return false;
                }
                return true;
            }
        });

        if (state != null) web.restoreState(state);
        else web.loadUrl("file:///android_asset/index.html");
    }

    @Override
    protected void onSaveInstanceState(Bundle out) {
        super.onSaveInstanceState(out);
        web.saveState(out);
    }

    @Override
    public void onBackPressed() {
        if (web.canGoBack()) web.goBack();
        else super.onBackPressed();
    }

    @Override
    protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (request == PICK_FILE && fileCallback != null) {
            Uri[] uris = (result == RESULT_OK && data != null && data.getData() != null) ? new Uri[]{data.getData()} : null;
            fileCallback.onReceiveValue(uris);
            fileCallback = null;
        } else if (request == SAVE_FILE) {
            if (result == RESULT_OK && data != null && data.getData() != null && pendingText != null) {
                try {
                    OutputStream os = getContentResolver().openOutputStream(data.getData());
                    os.write(pendingText.getBytes("UTF-8"));
                    os.close();
                    Toast.makeText(this, "Copia guardada", Toast.LENGTH_SHORT).show();
                } catch (Exception e) {
                    Toast.makeText(this, "No se pudo guardar", Toast.LENGTH_LONG).show();
                }
            }
            pendingText = null;
        }
    }

    private void openUrl(String url) {
        try {
            startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url)));
        } catch (ActivityNotFoundException e) {
            Toast.makeText(this, "No hay navegador para abrir el enlace", Toast.LENGTH_SHORT).show();
        }
    }

    /** Funciones que la web puede llamar como window.Android.* */
    private class Bridge {
        @JavascriptInterface
        public void copy(final String text) {
            runOnUiThread(new Runnable() {
                public void run() {
                    ClipboardManager cm = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
                    cm.setPrimaryClip(ClipData.newPlainText("texto", text));
                }
            });
        }

        @JavascriptInterface
        public void openUrl(final String url) {
            runOnUiThread(new Runnable() {
                public void run() { MainActivity.this.openUrl(url); }
            });
        }

        @JavascriptInterface
        public void shareFile(final String filename, final String text) {
            runOnUiThread(new Runnable() {
                public void run() {
                    pendingText = text;
                    Intent i = new Intent(Intent.ACTION_CREATE_DOCUMENT);
                    i.addCategory(Intent.CATEGORY_OPENABLE);
                    i.setType("application/json");
                    i.putExtra(Intent.EXTRA_TITLE, filename);
                    try {
                        startActivityForResult(i, SAVE_FILE);
                    } catch (ActivityNotFoundException e) {
                        pendingText = null;
                        Toast.makeText(MainActivity.this, "No se pudo abrir el selector de archivos", Toast.LENGTH_LONG).show();
                    }
                }
            });
        }
    }
}
