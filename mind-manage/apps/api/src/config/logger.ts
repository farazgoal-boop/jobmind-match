export const logger = {
  info: (message: string, meta?: unknown) => console.log('[info]', message, meta ?? ''),
  error: (message: string, meta?: unknown) => console.error('[error]', message, meta ?? '')
};
