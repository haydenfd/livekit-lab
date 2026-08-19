import { TTS as DeepgramTTS } from '@livekit/agents-plugin-deepgram';

/**
 * Deepgram TTS using our own DEEPGRAM_API_KEY.
 * The Aura-2 voice is selected via the `model` option.
 */
export function createTTS(): DeepgramTTS {
  return new DeepgramTTS({
    model: 'aura-2-andromeda-en',
    encoding: 'linear16',
  });
}
