import { type JobContext, ServerOptions, cli, defineAgent } from '@livekit/agents';
import { fileURLToPath } from 'node:url';
import { runRoomEntry } from './agent/room-entry.ts';

export default defineAgent({
  entry: (ctx: JobContext) => runRoomEntry(ctx),
});

cli.runApp(new ServerOptions({ agent: fileURLToPath(import.meta.url) }));
