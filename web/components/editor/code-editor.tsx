'use client';

import { useEffect, useRef, useState } from 'react';
import { useSessionContext } from '@livekit/components-react';
import { cn } from '@/lib/shadcn/utils';
import { registerEditorCodeContext } from './editor-code-context';

export function CodeEditor({ className }: { className?: string }) {
  const { room } = useSessionContext();
  const [code, setCode] = useState('');
  const [revision, setRevision] = useState(0);
  const codeRef = useRef(code);
  const revisionRef = useRef(revision);

  useEffect(() => {
    return registerEditorCodeContext(room, codeRef, revisionRef);
  }, [room]);

  const handleCodeChange = (nextCode: string) => {
    const nextRevision = revisionRef.current + 1;
    codeRef.current = nextCode;
    revisionRef.current = nextRevision;
    setCode(nextCode);
    setRevision(nextRevision);
  };

  return (
    <aside
      aria-label="Code editor"
      className={cn(
        'bg-muted/20 flex min-h-0 flex-col border-b md:h-full md:w-[42%] md:min-w-[360px] md:border-r md:border-b-0',
        className
      )}
    >
      <header className="border-border/60 flex items-center justify-between border-b px-5 py-4">
        <div>
          <p className="text-sm font-semibold">Code editor</p>
          <p className="text-muted-foreground mt-1 font-mono text-[11px] tracking-wide uppercase">
            Candidate workspace
          </p>
        </div>
        <div className="flex items-center gap-3 font-mono text-xs">
          <span className="text-muted-foreground" aria-label="Programming language">
            python
          </span>
          <span className="text-muted-foreground/70" aria-label={`Revision ${revision}`}>
            rev {revision}
          </span>
        </div>
      </header>

      <textarea
        aria-label="Python code editor"
        value={code}
        onChange={(event) => handleCodeChange(event.target.value)}
        placeholder="Write your solution here..."
        spellCheck={false}
        wrap="off"
        className="placeholder:text-muted-foreground/50 min-h-0 flex-1 resize-none bg-transparent p-5 font-mono text-sm leading-6 outline-none"
      />
    </aside>
  );
}
