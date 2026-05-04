import type { CapacitorConfig } from '@capacitor/cli';

const appUrl = process.env.JOBMIND_APP_URL || 'https://jobmind-match.onrender.com/dashboard';

const config: CapacitorConfig = {
  appId: 'com.jobmind.match',
  appName: 'JobMind Match',
  webDir: 'www',
  server: {
    url: appUrl,
    cleartext: false,
  },
  android: {
    allowMixedContent: false,
  },
};

export default config;