import { createServer, type IncomingMessage, type ServerResponse } from 'node:http';
import { randomUUID } from 'node:crypto';
import { AccessToken, type VideoGrant } from 'livekit-server-sdk';
import { RoomConfiguration, TrackSource } from '@livekit/protocol';
import { loadLiveKitConfig } from '../config/livekit.ts';

const PORT = 1591;
const ALLOWED_ORIGIN = 'http://localhost:1590';
const ROOM_NAME = 'voice-lab';

/**
 * Request body of the LiveKit-standard token endpoint format.
 * `room_config` carries agent dispatch info and is passed straight through
 * to the token builder, per the official endpoint documentation.
 */
interface TokenRequestBody {
  room_name?: string;
  participant_identity?: string;
  participant_name?: string;
  participant_metadata?: string;
  participant_attributes?: Record<string, string>;
  room_config?: RoomConfiguration;
}

function setCors(res: ServerResponse): void {
  res.setHeader('Access-Control-Allow-Origin', ALLOWED_ORIGIN);
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
}

function readBody(req: IncomingMessage): Promise<TokenRequestBody> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    req.on('data', (chunk: Buffer) => chunks.push(chunk));
    req.on('end', () => {
      const raw = Buffer.concat(chunks).toString('utf8');
      resolve(raw.length === 0 ? {} : (JSON.parse(raw) as TokenRequestBody));
    });
    req.on('error', reject);
  });
}

async function handleTokenRequest(
  req: IncomingMessage,
  res: ServerResponse,
): Promise<void> {
  const body = await readBody(req);

  const config = loadLiveKitConfig();
  const roomName = body.room_name ?? ROOM_NAME;
  const identity = body.participant_identity ?? `user-${randomUUID().slice(0, 8)}`;

  const token = new AccessToken(config.apiKey, config.apiSecret, {
    identity,
    name: body.participant_name ?? identity,
    metadata: body.participant_metadata ?? '',
    attributes: body.participant_attributes ?? {},
    ttl: 60 * 60,
  });

  const grant: VideoGrant = {
    room: roomName,
    roomJoin: true,
    canPublish: true,
    // Voice only: no camera or screen share publishing.
    canPublishSources: [TrackSource.MICROPHONE],
    canPublishData: true,
    canSubscribe: true,
  };
  token.addGrant(grant);

  if (body.room_config) {
    token.roomConfig = new RoomConfiguration(body.room_config);
  }

  const participantToken = await token.toJwt();

  res.statusCode = 201;
  res.setHeader('Content-Type', 'application/json');
  res.end(
    JSON.stringify({
      server_url: config.url,
      participant_token: participantToken,
    }),
  );
}

const server = createServer((req, res) => {
  setCors(res);

  if (req.method === 'OPTIONS') {
    res.statusCode = 204;
    res.end();
    return;
  }

  if (req.method === 'POST' && req.url === '/token') {
    handleTokenRequest(req, res).catch((error) => {
      console.error('[token-server] failed to generate token:', error);
      res.statusCode = 500;
      res.setHeader('Content-Type', 'application/json');
      res.end(JSON.stringify({ error: 'Failed to generate token' }));
    });
    return;
  }

  res.statusCode = 404;
  res.end();
});

server.listen(PORT, () => {
  console.log(`[token-server] listening on http://127.0.0.1:${PORT}/token`);
  console.log(`[token-server] allowing origin ${ALLOWED_ORIGIN}`);
});
