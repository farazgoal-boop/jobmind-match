# JobMind Match Android Wrapper

This folder contains a Capacitor-based Android wrapper for JobMind Match.

## What It Does

- Wraps the deployed JobMind Match web app inside an Android app shell.
- Lets you generate an APK or AAB once the live app URL is configured.
- Supports repo-driven web updates for most UI and backend changes.

## Before You Build

You need:

- Node.js 20+
- Android Studio
- Android SDK
- Java 17
- A live HTTPS deployment URL for JobMind Match

## App Icon (Owl Logo)

All icons are generated from the root `icon.png` (your owl logo):

```powershell
# From project root
.\.venv\Scripts\python.exe scripts\generate_icons.py
```

This updates:
- `app/static/` — desktop web, PWA, favicon (16px to 512px)
- `mobile-wrapper/resources/icon.png` — Capacitor source (1024px)
- `mobile-wrapper/android/.../mipmap-*` — Android launcher icons (after `npx cap add android`)

From `mobile-wrapper` folder:

```powershell
npm run icons:sync
```

## Setup

From this folder:

```powershell
npm install
$env:JOBMIND_APP_URL="https://your-live-domain.com/dashboard"
npx cap add android
npx cap sync android
npx cap open android
```

## Local Emulator Testing

If you want the Android emulator to load your local FastAPI app instead of production:

```powershell
cd "C:\Users\HAROON TRADERS\OneDrive\Desktop\JobMind Match"
& ".\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000

cd "C:\Users\HAROON TRADERS\OneDrive\Desktop\JobMind Match\mobile-wrapper"
npm run android:sync:local
npx cap open android
```

Android emulators reach the host machine through `http://10.0.2.2:8000`, which is already wired into the local sync script.

## CLI Build Shortcuts

```powershell
npm run android:prepare:jdk17
npm run android:sync:prod
npm run android:build:debug
npm run android:build:release
```

If this machine only has JDK 17 installed, run the prepare step before the Android build. It patches the Capacitor-generated Android Gradle files back to Java 17 compatibility.

## Build APK In Android Studio

1. Open the generated Android project.
2. Wait for Gradle sync.
3. Set app icon, splash, package name, and signing config.
4. Use `Build > Generate Signed Bundle / APK`.
5. Export release APK.

## Update Model

### Web changes
- Dashboard/UI changes from the FastAPI repo can be deployed to the live server.
- The Android wrapper will show the latest live app without rebuilding in many cases.

### Native changes
- App icon
- package ID
- splash screen
- native permissions
- plugins

These require a new APK build.