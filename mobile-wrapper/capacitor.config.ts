import type { CapacitorConfig } from '@capacitor/cli';

/** Standalone mobile app — full UI bundled in APK (no PC, no Render). */
const config: CapacitorConfig = {
  appId: 'com.jobmind.match',
  appName: 'JobMind Match',
  webDir: 'www',
  android: {
    allowMixedContent: true,
  },
};

export default config;
