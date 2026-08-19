import { LLM as OpenAILLM } from '@livekit/agents-plugin-openai';

/**
 * Groq chat LLM via LiveKit's OpenAI-compatible plugin.
 * Reads GROQ_API_KEY from the environment; no OpenAI credentials involved.
 */
export function createLLM(): OpenAILLM {
  return OpenAILLM.withGroq({
    model: 'llama-3.1-8b-instant',
  });
}
