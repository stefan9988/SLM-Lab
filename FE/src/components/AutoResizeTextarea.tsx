import { useRef, useLayoutEffect } from 'react';
import type { TextareaHTMLAttributes } from 'react';

type Props = TextareaHTMLAttributes<HTMLTextAreaElement>;

export default function AutoResizeTextarea({ value, ...props }: Props) {
  const ref = useRef<HTMLTextAreaElement>(null);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${el.scrollHeight}px`;
  }, [value]);

  return <textarea ref={ref} value={value} rows={1} {...props} />;
}
