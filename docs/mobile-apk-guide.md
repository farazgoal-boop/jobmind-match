# JobMind Match Mobile And APK Guide

## Current Reality

JobMind Match is a web app built with FastAPI and server-side rendered HTML.
It can be used on mobile right now through the browser.
It can also be made installable as a PWA.

An APK is not the same thing as the FastAPI repo itself.
The repo is the source code.
The APK is a packaged Android app build.

## Best Mobile Path

### Option 1: PWA
- Open the live site on Android Chrome.
- Use `Add to Home Screen` or `Install App`.
- Fast to ship.
- Best for quick client delivery.
- When the web app is updated on the server, users see the update without reinstalling the APK shell.

### Option 2: Android APK Wrapper
- Wrap the live app using Capacitor, Trusted Web Activity, or a WebView shell.
- Good if a client specifically wants an APK file.
- Faster than building a separate native app.

## Can APK Update From Repo?

### Yes, partially
If the APK is only a wrapper around the hosted web app, then:
- UI changes from the repo can go live from the server.
- New dashboard features can appear without reinstalling for many cases.
- Content and logic updates can come from the deployed backend.

### But not always
If you change native Android shell behavior, permissions, splash screen, package name, icons, signing config, or native plugins, then:
- you must rebuild a new APK
- you must send an updated APK or publish an update through Play Store

## Recommended Sales Pitch For Fiverr And Upwork

Use this wording:

`I can deliver this as a mobile-friendly web app, installable PWA, or APK wrapper. Day-to-day feature updates can be pushed from the live server without rebuilding the app shell every time. If you need native Android-specific changes, I can generate a fresh APK release.`

## What Is Already Added In This Repo

- PWA manifest
- Service worker
- Installable app metadata
- Mobile-friendly responsive dashboard

## To Build A Real APK Later

### Recommended stack
- Deploy app on a public HTTPS domain
- Wrap with Capacitor or Bubblewrap/TWA
- Build signed APK with Android Studio

### Typical flow
1. Deploy the app on Render, Railway, VPS, or your domain.
2. Confirm HTTPS works.
3. Create Android wrapper project.
4. Point wrapper to the live URL.
5. Build release APK or AAB.

## Important Note

This workspace now contains a Capacitor Android wrapper project under `mobile-wrapper/`.

What still depends on the local machine or Android Studio environment:
- Android SDK availability
- Gradle wrapper dependency download
- keystore creation/signing
- final signed APK or AAB export

So the repo is build-ready in architecture and wrapper structure, but the final signed APK still depends on the Android toolchain being able to download Gradle and complete the release build.

## Local Emulator Flow

For local testing before a release APK:

1. Run the FastAPI app on your computer.
2. Sync the wrapper with `JOBMIND_APP_URL=http://10.0.2.2:8000/dashboard`.
3. Open Android Studio and run the emulator.

The wrapper now includes Android network security config for `10.0.2.2`, `localhost`, and `127.0.0.1` so local HTTP testing works during development.