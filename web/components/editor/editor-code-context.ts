import { type Room, RpcError, type RpcInvocationData } from 'livekit-client';

export const GET_CURRENT_CODE_RPC_METHOD = 'editor.get_current_code';

interface GetCurrentCodeHandlerOptions {
  room: Room;
  codeRef: { current: string };
}

export function createGetCurrentCodeHandler({ room, codeRef }: GetCurrentCodeHandlerOptions) {
  return async (data: RpcInvocationData): Promise<string> => {
    const caller = room.getParticipantByIdentity(data.callerIdentity);
    if (caller?.isAgent !== true) {
      throw new RpcError(
        RpcError.ErrorCode.APPLICATION_ERROR,
        'Only LiveKit agents can request current editor code'
      );
    }

    const responseBytes = new TextEncoder().encode(codeRef.current).byteLength;

    if (responseBytes > RpcError.MAX_DATA_BYTES) {
      throw new RpcError(
        RpcError.ErrorCode.RESPONSE_PAYLOAD_TOO_LARGE,
        'Current editor code exceeds the 15 KiB RPC response limit'
      );
    }

    return codeRef.current;
  };
}

export function registerGetCurrentCode(room: Room, codeRef: { current: string }) {
  room.registerRpcMethod(
    GET_CURRENT_CODE_RPC_METHOD,
    createGetCurrentCodeHandler({ room, codeRef })
  );

  return () => room.unregisterRpcMethod(GET_CURRENT_CODE_RPC_METHOD);
}
