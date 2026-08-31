import { RpcError } from 'livekit-client';
import { describe, expect, it, vi } from 'vitest';
import {
  EDITOR_CODE_CONTEXT_RPC_METHOD,
  createEditorCodeContextHandler,
  registerEditorCodeContext,
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

describe('editor.get_code_context', () => {
  it('returns the latest code and revision from refs', async () => {
    const room = makeRoom(true);
    const codeRef = { current: 'def solve():\n    pass' };
    const revisionRef = { current: 12 };
    const handler = createEditorCodeContextHandler({
      room: room as never,
      codeRef,
      revisionRef,
    });

    codeRef.current = 'def solve():\n    return 42';
    revisionRef.current = 13;

    await expect(handler(invocation)).resolves.toBe(
      JSON.stringify({ version: 1, revision: 13, language: 'python', code: codeRef.current })
    );
  });

  it('rejects callers that are not agents', async () => {
    const room = makeRoom(false);
    const handler = createEditorCodeContextHandler({
      room: room as never,
      codeRef: { current: '' },
      revisionRef: { current: 0 },
    });

    await expect(handler(invocation)).rejects.toMatchObject({
      code: RpcError.ErrorCode.APPLICATION_ERROR,
      message: 'Only LiveKit agents can request editor code context',
    });
  });

  it("rejects responses over LiveKit's 15 KiB limit", async () => {
    const room = makeRoom(true);
    const handler = createEditorCodeContextHandler({
      room: room as never,
      codeRef: { current: 'x'.repeat(RpcError.MAX_DATA_BYTES) },
      revisionRef: { current: 1 },
    });

    await expect(handler(invocation)).rejects.toMatchObject({
      code: RpcError.ErrorCode.RESPONSE_PAYLOAD_TOO_LARGE,
    });
  });

  it('registers and unregisters the handler during cleanup', () => {
    const room = makeRoom(true);
    const cleanup = registerEditorCodeContext(room as never, { current: '' }, { current: 0 });

    expect(room.registerRpcMethod).toHaveBeenCalledWith(
      EDITOR_CODE_CONTEXT_RPC_METHOD,
      expect.any(Function)
    );

    cleanup();

    expect(room.unregisterRpcMethod).toHaveBeenCalledWith(EDITOR_CODE_CONTEXT_RPC_METHOD);
  });
});
