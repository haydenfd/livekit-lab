import { RpcError } from 'livekit-client';
import { describe, expect, it, vi } from 'vitest';
import {
  GET_CURRENT_CODE_RPC_METHOD,
  createGetCurrentCodeHandler,
  registerGetCurrentCode,
} from './editor-code-context';

function makeRoom(callerIsAgent: boolean) {
  return {
    getParticipantByIdentity: vi.fn(() => ({ isAgent: callerIsAgent })),
    registerRpcMethod: vi.fn(),
    unregisterRpcMethod: vi.fn(),
  };
}

const invocation = {
  callerIdentity: 'agent',
  payload: '',
  requestId: 'request',
  responseTimeout: 1000,
};

describe('editor.get_current_code', () => {
  it('returns the latest code from its ref', async () => {
    const room = makeRoom(true);
    const codeRef = { current: 'def solve():\n    pass' };
    const handler = createGetCurrentCodeHandler({
      room: room as never,
      codeRef,
    });

    codeRef.current = 'def solve():\n    return 42';
    await expect(handler(invocation)).resolves.toBe(codeRef.current);
  });

  it('rejects callers that are not agents', async () => {
    const room = makeRoom(false);
    const handler = createGetCurrentCodeHandler({
      room: room as never,
      codeRef: { current: '' },
    });

    await expect(handler(invocation)).rejects.toMatchObject({
      code: RpcError.ErrorCode.APPLICATION_ERROR,
      message: 'Only LiveKit agents can request current editor code',
    });
  });

  it("rejects responses over LiveKit's 15 KiB limit", async () => {
    const room = makeRoom(true);
    const handler = createGetCurrentCodeHandler({
      room: room as never,
      codeRef: { current: 'x'.repeat(RpcError.MAX_DATA_BYTES + 1) },
    });

    await expect(handler(invocation)).rejects.toMatchObject({
      code: RpcError.ErrorCode.RESPONSE_PAYLOAD_TOO_LARGE,
    });
  });

  it('registers and unregisters the handler during cleanup', () => {
    const room = makeRoom(true);
    const cleanup = registerGetCurrentCode(room as never, { current: '' });

    expect(room.registerRpcMethod).toHaveBeenCalledWith(
      GET_CURRENT_CODE_RPC_METHOD,
      expect.any(Function)
    );

    cleanup();

    expect(room.unregisterRpcMethod).toHaveBeenCalledWith(GET_CURRENT_CODE_RPC_METHOD);
  });
});
