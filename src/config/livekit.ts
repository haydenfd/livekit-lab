import 'dotenv/config';

export interface LiveKitConfig {
  /** WebSocket URL of the LiveKit server. */
  url: string;
  /** LiveKit API key. */
  apiKey: string;
  /** LiveKit API secret. */
  apiSecret: string;
}

/**
 * Local development defaults matching `livekit-server --dev`.
 *
 * These are only ever applied when the process is not running in production,
 * so real credentials are never invented silently.
 */
const DEV_DEFAULTS: LiveKitConfig = {
  url: 'ws://127.0.0.1:7880',
  apiKey: 'devkey',
  apiSecret: 'secret',
};

function isDev(): boolean {
  return process.env.NODE_ENV !== 'production';
}

/**
 * Reads and validates the LiveKit connection configuration from the
 * environment. Falls back to the local dev defaults only in development.
 */
export function loadLiveKitConfig(): LiveKitConfig {
  const url = process.env.LIVEKIT_URL;
  const apiKey = process.env.LIVEKIT_API_KEY;
  const apiSecret = process.env.LIVEKIT_API_SECRET;

  if (isDev()) {
    return {
      url: url ?? DEV_DEFAULTS.url,
      apiKey: apiKey ?? DEV_DEFAULTS.apiKey,
      apiSecret: apiSecret ?? DEV_DEFAULTS.apiSecret,
    };
  }

  const missing = (
    [
      ['LIVEKIT_URL', url],
      ['LIVEKIT_API_KEY', apiKey],
      ['LIVEKIT_API_SECRET', apiSecret],
    ] as const
  )
    .filter(([, value]) => !value)
    .map(([name]) => name);

  if (missing.length > 0) {
    throw new Error(
      `Missing required LiveKit environment variables: ${missing.join(', ')}`,
    );
  }

  return { url: url!, apiKey: apiKey!, apiSecret: apiSecret! };
}
