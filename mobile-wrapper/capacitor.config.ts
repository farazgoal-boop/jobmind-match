import type { CapacitorConfig } from '@capacitor/cli';

/** Standalone mobile client — opens JobMind cloud (no PC / no LAN pairing). */
const config: CapacitorConfig = {
  appId: 'com.jobmind.match',
  appName: 'JobMind Match',
  webDir: 'www',
  android: {
    allowMixedContent: true,
  },
};

export default config;
