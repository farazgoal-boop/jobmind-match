# Android APK Build Steps For JobMind Match

## 1. Deploy The App First

You need a public HTTPS URL before building the Android wrapper.

Examples:
- Render
- Railway
- VPS with Nginx
- Custom domain

Example target URL:

`https://jobmind-match.yourdomain.com/dashboard`

## 2. Install Local Tools

- Node.js 20+
- Android Studio
- Android SDK Platform Tools
- Java 17

## 3. Open The Mobile Wrapper Folder

Path:

[mobile-wrapper/package.json](/c:/Users/HAROON%20TRADERS/OneDrive/Desktop/JobMind%20Match/mobile-wrapper/package.json)

## 4. Install Dependencies

```powershell
cd "C:\Users\HAROON TRADERS\OneDrive\Desktop\JobMind Match\mobile-wrapper"
npm install
```

## 5. Set Live App URL

```powershell
$env:JOBMIND_APP_URL="https://your-live-domain.com/dashboard"
```

## 6. Add Android Project

```powershell
npx cap add android
```

## 7. Sync Wrapper

```powershell
npx cap sync android
```

## 8. Open Android Studio

```powershell
npx cap open android
```

## 9. Generate APK

In Android Studio:

1. Open `Build`
2. Click `Generate Signed Bundle / APK`
3. Choose `APK`
4. Create or select keystore
5. Select `release`
6. Build the APK

## 10. Future Updates

### No new APK usually needed
- backend fixes
- dashboard text changes
- filters and scoring logic
- job source updates
- styling changes

### New APK needed
- native permissions
- splash screen changes
- package name changes
- new native plugins
- store-signing changes

## Best Delivery Option

For clients on Fiverr/Upwork, offer these 3 levels:

1. Mobile responsive web app
2. Installable PWA
3. Android APK wrapper