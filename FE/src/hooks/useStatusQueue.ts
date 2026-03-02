import { useCallback, useEffect, useRef, useState } from 'react';

const STATUS_DELAY_MS = 1200;

export function useStatusQueue() {
  const queueRef = useRef<string[]>([]);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const advanceRef = useRef<() => void>(() => {});
  const [toolStatus, setToolStatus] = useState<string | null>(null);

  const advance = useCallback(() => {
    const next = queueRef.current.shift();
    if (next !== undefined) {
      setToolStatus(next);
      timerRef.current = setTimeout(advanceRef.current, STATUS_DELAY_MS);
    } else {
      setToolStatus(null);
      timerRef.current = null;
    }
  }, []);
  advanceRef.current = advance; // always call the latest version

  const enqueueStatus = useCallback(
    (msg: string) => {
      queueRef.current.push(msg);
      if (timerRef.current === null) advance(); // start immediately if idle
    },
    [advance],
  );

  const clearStatus = useCallback(() => {
    queueRef.current = [];
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    setToolStatus(null);
  }, []);

  // Cleanup on unmount
  useEffect(
    () => () => {
      if (timerRef.current !== null) clearTimeout(timerRef.current);
    },
    [],
  );

  return { toolStatus, enqueueStatus, clearStatus };
}
