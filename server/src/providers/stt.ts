import { STT as DeepgramSTT } from '@livekit/agents-plugin-deepgram';

/**
 * Deepgram realtime STT using our own DEEPGRAM_API_KEY.
 */
export function createSTT(): DeepgramSTT {
  return new DeepgramSTT({
    model: 'nova-3',
    language: 'en',
    interimResults: true,
    punctuate: true,
    smartFormat: true,
    noDelay: true,
    endpointing: 250,
    fillerWords: true,
  });
}
