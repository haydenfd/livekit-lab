import {
  RoomAudioRenderer,
  StartAudio,
  useSession,
  SessionProvider,
} from '@livekit/components-react';
import { AgentSessionView_01 } from '@/components/agents-ui/blocks/agent-session-view-01';
import { Button } from '@/components/ui/button';
import { roomName, tokenSource } from '@/livekit/session';

/**
 * Thin wrapper around the generated LiveKit Agents UI session block.
 * Owns the session lifecycle (start/end) and nothing else.
 */
export function VoiceConsole() {
  const session = useSession(tokenSource, { roomName });

  return (
    <SessionProvider session={session}>
      <div data-lk-theme="default" className="h-dvh w-full">
        {session.isConnected ? (
          <AgentSessionView_01
            supportsVideoInput={false}
            supportsScreenShare={false}
            audioVisualizerType="bar"
            audioVisualizerColor="#93a5cf"
            themeMode="dark"
            preConnectMessage="Listening..."
          />
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-6">
            <p className="text-muted-foreground text-sm">Status: disconnected</p>
            <Button size="lg" onClick={() => void session.start()}>
              Start Session
            </Button>
          </div>
        )}
        {session.isConnected && (
          <>
            <RoomAudioRenderer volume={1} />
            <StartAudio label="Enable audio" />
          </>
        )}
      </div>
    </SessionProvider>
  );
}
