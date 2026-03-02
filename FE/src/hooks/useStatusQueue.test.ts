import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useStatusQueue } from './useStatusQueue';

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe('useStatusQueue', () => {
  it('shows a single enqueued message immediately', () => {
    const { result } = renderHook(() => useStatusQueue());

    act(() => {
      result.current.enqueueStatus('Searching...');
    });

    expect(result.current.toolStatus).toBe('Searching...');
  });

  it('clears a single message after 1200ms', () => {
    const { result } = renderHook(() => useStatusQueue());

    act(() => {
      result.current.enqueueStatus('Searching...');
    });

    expect(result.current.toolStatus).toBe('Searching...');

    act(() => {
      vi.advanceTimersByTime(1200);
    });

    expect(result.current.toolStatus).toBeNull();
  });

  it('shows second message after 1200ms when two are enqueued', () => {
    const { result } = renderHook(() => useStatusQueue());

    act(() => {
      result.current.enqueueStatus('First');
      result.current.enqueueStatus('Second');
    });

    expect(result.current.toolStatus).toBe('First');

    act(() => {
      vi.advanceTimersByTime(1200);
    });

    expect(result.current.toolStatus).toBe('Second');

    act(() => {
      vi.advanceTimersByTime(1200);
    });

    expect(result.current.toolStatus).toBeNull();
  });

  it('clearStatus drains queue and hides message immediately', () => {
    const { result } = renderHook(() => useStatusQueue());

    act(() => {
      result.current.enqueueStatus('First');
      result.current.enqueueStatus('Second');
    });

    expect(result.current.toolStatus).toBe('First');

    act(() => {
      result.current.clearStatus();
    });

    expect(result.current.toolStatus).toBeNull();

    // Advancing time should not show any queued message
    act(() => {
      vi.advanceTimersByTime(2400);
    });

    expect(result.current.toolStatus).toBeNull();
  });

  it('enqueue after clear works correctly', () => {
    const { result } = renderHook(() => useStatusQueue());

    act(() => {
      result.current.enqueueStatus('First');
    });

    act(() => {
      result.current.clearStatus();
    });

    expect(result.current.toolStatus).toBeNull();

    act(() => {
      result.current.enqueueStatus('After clear');
    });

    expect(result.current.toolStatus).toBe('After clear');

    act(() => {
      vi.advanceTimersByTime(1200);
    });

    expect(result.current.toolStatus).toBeNull();
  });

  it('starts idle with null toolStatus', () => {
    const { result } = renderHook(() => useStatusQueue());
    expect(result.current.toolStatus).toBeNull();
  });
});
