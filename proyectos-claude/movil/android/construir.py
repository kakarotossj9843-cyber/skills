"""Fabrica los 5 APK (uno por app) sin Android Studio.

    python movil/android/construir.py            # todas
    python movil/android/construir.py panel      # solo una

Necesita (Ubuntu/Debian):  sudo apt install aapt apksigner zipalign android-sdk-platform-23 dalvik-exchange openjdk-17-jdk
Los APK salen en movil/apk/. La firma se guarda en movil/android/firma.keystore: GUÁRDALA, sin ella no podrás
publicar actualizaciones que se instalen encima de las anteriores.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MOVIL = HERE.parent
BUILD = MOVIL / "build"
OUT = MOVIL / "apk"
ANDROID_JAR = Path(os.getenv("ANDROID_JAR", "/usr/lib/android-sdk/platforms/android-23/android.jar"))
KEYSTORE = Path(os.getenv("APK_KEYSTORE", str(HERE / "firma.keystore")))
KS_PASS = os.getenv("APK_KEYSTORE_PASS", "proyectos-claude")
VERSION_CODE = int(os.getenv("APK_VERSION_CODE", "1"))
VERSION_NAME = os.getenv("APK_VERSION_NAME", "1.0")

APPS = {
    #  carpeta     paquete Android                    nombre visible        barra      fondo     archivo APK
    "jarvis":    ("com.proyectosclaude.jarvis",    "Jarvis",            "#04161b", "#04161b", "Jarvis"),
    "cerebro":   ("com.proyectosclaude.cerebro",   "Segundo cerebro",   "#160b2b", "#0e0818", "Segundo-cerebro"),
    "panel":     ("com.proyectosclaude.panel",     "Panel de tu vida",  "#17130b", "#0f0c07", "Panel-de-tu-vida"),
    "contenido": ("com.proyectosclaude.contenido", "Agente de contenido", "#1d1238", "#0d0a1f", "Agente-de-contenido"),
    "equipo":    ("com.proyectosclaude.equipo",    "Equipo de agentes", "#1d120b", "#100905", "Equipo-de-agentes"),
}

MANIFEST = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="{pkg}" android:versionCode="{vc}" android:versionName="{vn}">
    <uses-sdk android:minSdkVersion="23" android:targetSdkVersion="34" />
    <uses-permission android:name="android.permission.INTERNET" />
    <application android:label="@string/app_name" android:icon="@drawable/ic_launcher"
        android:allowBackup="true" android:hardwareAccelerated="true" android:usesCleartextTraffic="false"
        android:theme="@style/AppTheme">
        <activity android:name=".MainActivity" android:exported="true" android:launchMode="singleTask"
            android:configChanges="orientation|screenSize|smallestScreenSize|screenLayout|keyboardHidden|keyboard|uiMode"
            android:windowSoftInputMode="adjustResize">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
"""

STYLES = """<?xml version="1.0" encoding="utf-8"?>
<resources>
    <style name="AppTheme" parent="@android:style/Theme.Material.NoActionBar">
        <item name="android:windowBackground">@color/bg</item>
        <item name="android:colorPrimaryDark">@color/theme</item>
        <item name="android:statusBarColor">@color/theme</item>
    </style>
    <color name="bg">{bg}</color>
    <color name="theme">{theme}</color>
    <string name="app_name">{name}</string>
</resources>
"""


def run(*cmd: str, cwd: Path | None = None) -> None:
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"❌ Falló: {' '.join(cmd)}\n{r.stdout}\n{r.stderr}")


def ensure_keystore() -> None:
    if KEYSTORE.exists():
        return
    print(f"🔑 Creando firma nueva en {KEYSTORE} (guárdala bien)")
    run("keytool", "-genkeypair", "-keystore", str(KEYSTORE), "-storepass", KS_PASS, "-keypass", KS_PASS,
        "-alias", "proyectos-claude", "-keyalg", "RSA", "-keysize", "2048", "-validity", "10000",
        "-dname", "CN=Proyectos Claude, OU=Apps, O=Personal, C=PE")


def build(app: str) -> Path:
    pkg, name, theme, bg, filename = APPS[app]
    src_web = MOVIL / app
    if not (src_web / "index.html").exists():
        raise SystemExit(f"❌ Falta {src_web}/index.html")
    b = BUILD / app
    shutil.rmtree(b, ignore_errors=True)
    for d in ("assets", "res/values", "res/drawable-xxxhdpi", "src", "gen", "classes"):
        (b / d).mkdir(parents=True, exist_ok=True)

    # Web de la app + código común
    shutil.copytree(src_web, b / "assets", dirs_exist_ok=True)
    shutil.copytree(MOVIL / "comun", b / "assets" / "comun", dirs_exist_ok=True)
    shutil.copy(src_web / "icon-192.png", b / "res/drawable-xxxhdpi/ic_launcher.png")

    (b / "AndroidManifest.xml").write_text(MANIFEST.format(pkg=pkg, vc=VERSION_CODE, vn=VERSION_NAME), encoding="utf-8")
    (b / "res/values/values.xml").write_text(STYLES.format(bg=bg, theme=theme, name=name), encoding="utf-8")
    java_dir = b / "src" / Path(*pkg.split("."))
    java_dir.mkdir(parents=True, exist_ok=True)
    java = (HERE / "MainActivity.java").read_text(encoding="utf-8")
    (java_dir / "MainActivity.java").write_text(
        java.replace("__PACKAGE__", pkg).replace("__THEME__", theme).replace("__BG__", bg), encoding="utf-8")

    jar = str(ANDROID_JAR)
    run("aapt", "package", "-f", "-m", "-J", "gen", "-M", "AndroidManifest.xml", "-S", "res", "-I", jar, cwd=b)
    sources = [str(p) for p in (b / "src").rglob("*.java")] + [str(p) for p in (b / "gen").rglob("*.java")]
    run("javac", "--release", "8", "-nowarn", "-encoding", "UTF-8", "-classpath", jar, "-d", "classes", *sources, cwd=b)
    run("dalvik-exchange", "--dex", "--min-sdk-version=23", "--output=classes.dex", "classes", cwd=b)
    run("aapt", "package", "-f", "-M", "AndroidManifest.xml", "-S", "res", "-A", "assets", "-I", jar,
        "-F", "app-unsigned.apk", cwd=b)
    run("aapt", "add", "app-unsigned.apk", "classes.dex", cwd=b)
    run("zipalign", "-f", "-p", "4", "app-unsigned.apk", "app-aligned.apk", cwd=b)
    OUT.mkdir(exist_ok=True)
    apk = OUT / f"{filename}.apk"
    run("apksigner", "sign", "--ks", str(KEYSTORE), "--ks-pass", f"pass:{KS_PASS}", "--key-pass", f"pass:{KS_PASS}",
        "--ks-key-alias", "proyectos-claude", "--min-sdk-version", "23", "--out", str(apk), "app-aligned.apk", cwd=b)
    run("apksigner", "verify", str(apk))
    return apk


def main() -> None:
    wanted = sys.argv[1:] or list(APPS)
    ensure_keystore()
    for app in wanted:
        apk = build(app)
        print(f"✅ {apk.name}  ({apk.stat().st_size / 1024:.0f} KB)")
    print(f"\nAPKs en {OUT}")


if __name__ == "__main__":
    main()
