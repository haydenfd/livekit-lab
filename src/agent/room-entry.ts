import type { JobContext } from '@livekit/agents';

/**
 * Entry handler for an assigned agent job.
 *
 * Logs the received job/room, connects the agent to the assigned room, then
 * logs the final room name and agent identity. No AI functionality yet.
 */
export async function runRoomEntry(ctx: JobContext): Promise<void> {
  console.log(
    `[agent] job "${ctx.job.id}" received for room "${ctx.room.name}"`,
  );

  await ctx.connect();

  console.log(
    `[agent] connected to room "${ctx.room.name}" as "${ctx.agent?.identity}"`,
  );
}
