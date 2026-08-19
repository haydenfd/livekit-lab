import { AgentSession } from '@livekit/agents';
import { createSTT } from '../providers/stt.ts';
import { createLLM } from '../providers/llm.ts';
import { createTTS } from '../providers/tts.ts';

/**
 * Builds the voice pipeline session: Deepgram STT -> Groq LLM -> Deepgram TTS.
 * Turn handling stays at framework defaults.
 */
export function createVoiceSession(): AgentSession {
  return new AgentSession({
    stt: createSTT(),
    llm: createLLM(),
    tts: createTTS(),
  });
}
