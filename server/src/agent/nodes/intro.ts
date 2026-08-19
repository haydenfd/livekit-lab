import { Agent } from '@livekit/agents';

/**
 * The minimal conversational agent: tiny instructions, no tools, no workflow.
 * Speaks a deterministic greeting when it enters the session.
 */
export function createBasicAgent(): Agent {
  return Agent.create({
    instructions: [
      'You are a concise conversational voice assistant.',
      'Respond naturally and briefly to the user.',
    ].join(' '),
    allowInterruptions: false,
    onEnter: async (ctx) => {
      await ctx.agent.session.say('How are you today?', {
        allowInterruptions: false,
      });
    },
  });
}
