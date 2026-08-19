import { AccessToken, type VideoGrant } from 'livekit-server-sdk';
import { TrackSource } from '@livekit/protocol';
import { loadLiveKitConfig } from '../config/livekit.ts';

export interface ParticipantTokenOptions {
  /** Name of the LiveKit room to join. */
  room: string;
  /** Identity of the participant within the room. */
  identity: string;
  /** Token lifetime in seconds. Defaults to one hour. */
  ttlSeconds?: number;
}

/**
 * Generates a participant access token for a named local room.
 *
 * Grants only the minimum permissions a normal participant needs to join and
 * participate in a room. Strictly for local development.
 */
export function generateParticipantToken(
  options: ParticipantTokenOptions,
): Promise<string> {
  const { apiKey, apiSecret } = loadLiveKitConfig();

  const token = new AccessToken(apiKey, apiSecret, {
    identity: options.identity,
    ttl: options.ttlSeconds ?? 60 * 60,
  });

  const grant: VideoGrant = {
    room: options.room,
    roomJoin: true,
    canPublish: true,
    // No user video needed: only allow microphone, no camera/screen share.
    canPublishSources: [TrackSource.MICROPHONE],
    canPublishData: true,
    canSubscribe: true,
  };

  token.addGrant(grant);
  return token.toJwt();
}
