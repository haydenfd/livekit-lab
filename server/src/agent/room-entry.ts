import type { JobContext } from '@livekit/agents';
import { createVoiceSession } from '../voice/session.ts';
import { createBasicAgent } from './nodes/intro.ts';

/**
 * Entry handler for an assigned agent job.
 *
 * Connects to the assigned room, starts the voice session with the basic
 * conversational agent, and lets LiveKit's normal lifecycle handle cleanup
 * when the room disconnects.
 */
export async function runRoomEntry(ctx: JobContext): Promise<void> {
  console.log(
    `[agent] job "${ctx.job.id}" received for room "${ctx.room.name}"`,
  );

  await ctx.connect();

  console.log(
    `[agent] connected to room "${ctx.room.name}" as "${ctx.agent?.identity}"`,
  );

  const session = createVoiceSession();
  const agent = createBasicAgent();

  session.start({ agent, room: ctx.room });

  await new Promise<void>((resolve) => {
    ctx.room.on('disconnected', () => {
      console.log(`[agent] room "${ctx.room.name}" disconnected`);
      resolve();
    });
  });
}
