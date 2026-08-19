import { TokenSource } from 'livekit-client';

/**
 * TokenSource pointing at the local dev token endpoint in
 * `server/src/dev/token-server.ts`. The Session API fetches tokens from here,
 * so no secrets ever reach the browser.
 */
export const tokenSource = TokenSource.endpoint('http://127.0.0.1:1591/token');

/** Fixed local room name for the lab. */
export const roomName = 'voice-lab';
