@echo off
setlocal
cd /d "%~dp0..\mobile-wrapper\android"

if not exist keystore mkdir keystore

if not exist "keystore\jobmind-release.jks" (
  echo [1/4] Creating release keystore...
  if "%JOBMIND_KEYSTORE_PASSWORD%"=="" set "JOBMIND_KEYSTORE_PASSWORD=JobMindMatch2026Release"
  keytool -genkeypair -v -storetype PKCS12 -keystore "keystore\jobmind-release.jks" -alias jobmind -keyalg RSA -keysize 2048 -validity 10000 -storepass "%JOBMIND_KEYSTORE_PASSWORD%" -keypass "%JOBMIND_KEYSTORE_PASSWORD%" -dname "CN=JobMind Match, OU=Premium, O=Muhammad Faraz, L=Karachi, ST=Sindh, C=PK"
) else (
  echo [1/4] Keystore already exists.
)

if "%JOBMIND_KEYSTORE_PASSWORD%"=="" set "JOBMIND_KEYSTORE_PASSWORD=JobMindMatch2026Release"
set "JOBMIND_KEYSTORE_FILE=keystore/jobmind-release.jks"
set "JOBMIND_KEY_ALIAS=jobmind"
set "JOBMIND_KEY_PASSWORD=%JOBMIND_KEYSTORE_PASSWORD%"

echo [2/5] Syncing mobile assets...
cd /d "%~dp0..\mobile-wrapper"
call npx cap sync android

echo [3/5] Preparing JDK 17 compatibility...
node scripts\prepare-jdk17.js

echo [4/5] Building signed standalone release APK...
cd android
if "%ANDROID_HOME%"=="" set "ANDROID_HOME=%LOCALAPPDATA%\Android\Sdk"
if "%JAVA_HOME%"=="" set "JAVA_HOME=C:\Program Files\Microsoft\jdk-17.0.19.10-hotspot\"
call gradlew.bat assembleRelease --no-daemon
if errorlevel 1 exit /b 1

echo [5/5] Copying APK to dist...
cd /d "%~dp0.."
if not exist dist mkdir dist
copy /Y "mobile-wrapper\android\app\build\outputs\apk\release\app-release.apk" "dist\JobMind-Match-Release.apk"
copy /Y "mobile-wrapper\android\app\build\outputs\apk\release\app-release.apk" "dist\JobMind-Match.apk"

echo.
echo DONE: dist\JobMind-Match-Release.apk
endlocal
