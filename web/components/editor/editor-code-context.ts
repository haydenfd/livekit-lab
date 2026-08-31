import { type Room, RpcError, type RpcInvocationData } from 'livekit-client';

export const EDITOR_CODE_CONTEXT_RPC_METHOD = 'editor.get_code_context';
export const EDITOR_LANGUAGE = 'python';

export interface EditorCodeContext {
  version: 1;
  revision: number;
  language: typeof EDITOR_LANGUAGE;
  code: string;
}

interface EditorSnapshotRefs {
  codeRef: { current: string };
  revisionRef: { current: number };
}

interface EditorCodeContextHandlerOptions extends EditorSnapshotRefs {
  room: Room;
}

export function createEditorCodeContextHandler({
  room,
  codeRef,
  revisionRef,
}: EditorCodeContextHandlerOptions) {
  return async (data: RpcInvocationData): Promise<string> => {
    const caller = room.getParticipantByIdentity(data.callerIdentity);
    if (caller?.isAgent !== true) {
      throw new RpcError(
        RpcError.ErrorCode.APPLICATION_ERROR,
        'Only LiveKit agents can request editor code context'
      );
    }

    const response: EditorCodeContext = {
      version: 1,
      revision: revisionRef.current,
      language: EDITOR_LANGUAGE,
      code: codeRef.current,
    };
    const serialized = JSON.stringify(response);
    const responseBytes = new TextEncoder().encode(serialized).byteLength;

    if (responseBytes > RpcError.MAX_DATA_BYTES) {
      throw new RpcError(
        RpcError.ErrorCode.RESPONSE_PAYLOAD_TOO_LARGE,
        'Editor code context exceeds the 15 KiB RPC response limit'
      );
    }

    return serialized;
  };
}

export function registerEditorCodeContext(
  room: Room,
  codeRef: { current: string },
  revisionRef: { current: number }
) {
  room.registerRpcMethod(
    EDITOR_CODE_CONTEXT_RPC_METHOD,
    createEditorCodeContextHandler({ room, codeRef, revisionRef })
  );

  return () => room.unregisterRpcMethod(EDITOR_CODE_CONTEXT_RPC_METHOD);
}
