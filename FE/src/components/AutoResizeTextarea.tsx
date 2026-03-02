import { useRef, useLayoutEffect } from 'react';
import type { TextareaHTMLAttributes } from 'react';

type Props = TextareaHTMLAttributes<HTMLTextAreaElement>;

export default function AutoResizeTextarea({ value, ...props }: Props) {
  const ref = useRef<HTMLTextAreaElement>(null);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;

    const resize = () => {
      el.style.height = '0';
      el.style.height = `${el.scrollHeight}px`;
    };

    resize(); // initial size on mount / value change

    const ro = new ResizeObserver(resize);
    ro.observe(el);
    return () => ro.disconnect();
  }, [value]);

  return <textarea ref={ref} value={value} rows={1} {...props} />;
}
