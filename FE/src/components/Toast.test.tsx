import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Toast from './Toast';
import type { ToastItem } from '../contexts/ToastContext';

const successToast: ToastItem = { id: 'toast-1', message: 'Chat deleted', type: 'success' };
const errorToast: ToastItem = { id: 'toast-2', message: 'Failed to delete chat', type: 'error' };

describe('Toast', () => {
  it('renders the toast message', () => {
    render(<Toast toast={successToast} onDismiss={vi.fn()} />);
    expect(screen.getByText('Chat deleted')).toBeInTheDocument();
  });

  it('has role="alert" for accessibility', () => {
    render(<Toast toast={successToast} onDismiss={vi.fn()} />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('renders dismiss button with accessible label', () => {
    render(<Toast toast={successToast} onDismiss={vi.fn()} />);
    expect(screen.getByRole('button', { name: /dismiss notification/i })).toBeInTheDocument();
  });

  it('calls onDismiss with the toast id when dismiss button is clicked', async () => {
    const onDismiss = vi.fn();
    render(<Toast toast={successToast} onDismiss={onDismiss} />);

    await userEvent.click(screen.getByRole('button', { name: /dismiss notification/i }));

    expect(onDismiss).toHaveBeenCalledOnce();
    expect(onDismiss).toHaveBeenCalledWith('toast-1');
  });

  it('applies green color classes for type="success"', () => {
    render(<Toast toast={successToast} onDismiss={vi.fn()} />);
    const alert = screen.getByRole('alert');
    expect(alert.className).toContain('text-[#22c55e]');
  });

  it('applies red color classes for type="error"', () => {
    render(<Toast toast={errorToast} onDismiss={vi.fn()} />);
    const alert = screen.getByRole('alert');
    expect(alert.className).toContain('text-[#ef4444]');
  });
});
