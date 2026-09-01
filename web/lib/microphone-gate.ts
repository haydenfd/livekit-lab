import type { AudioCaptureOptions } from 'livekit-client';

export const MICROPHONE_CAPTURE_CONSTRAINTS = {
  echoCancellation: true,
  noiseSuppression: true,
  autoGainControl: true,
  voiceIsolation: true,
} satisfies AudioCaptureOptions;
