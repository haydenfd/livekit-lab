import { type JobContext, ServerOptions, cli, defineAgent } from '@livekit/agents';
import { fileURLToPath } from 'node:url';
import dotenv from 'dotenv';
import { runRoomEntry } from './agent/room-entry.js';

dotenv.config();

export default defineAgent({
  entry: (ctx: JobContext) => runRoomEntry(ctx),
});

cli.runApp(new ServerOptions({ agent: fileURLToPath(import.meta.url) }));
