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

## Setup

From this folder:

```powershell
npm install
$env:JOBMIND_APP_URL="https://your-live-domain.com/dashboard"
npx cap add android
npx cap sync android
npx cap open android
```

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