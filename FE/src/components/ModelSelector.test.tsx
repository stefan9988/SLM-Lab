import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ModelSelector from './ModelSelector';
import { PROVIDER_LABELS } from '../constants/models';

const defaultProps = {
  currentProvider: 'ollama',
  currentModelName: 'qwen3:14b',
  onModelChange: vi.fn(),
  disabled: false,
};

describe('ModelSelector', () => {
  it('renders the current model display name', () => {
    render(<ModelSelector {...defaultProps} />);
    expect(screen.getByText('Qwen 3 14B Local')).toBeInTheDocument();
  });

  it('falls back to raw model name when model is not in the list', () => {
    render(
      <ModelSelector
        {...defaultProps}
        currentProvider="ollama"
        currentModelName="custom-model:latest"
      />,
    );
    expect(screen.getByText('custom-model:latest')).toBeInTheDocument();
  });

  it('opens dropdown on button click', () => {
    render(<ModelSelector {...defaultProps} />);
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button'));
    expect(screen.getByRole('listbox')).toBeInTheDocument();
  });

  it('closes dropdown on outside click', () => {
    render(<ModelSelector {...defaultProps} />);
    fireEvent.click(screen.getByRole('button'));
    expect(screen.getByRole('listbox')).toBeInTheDocument();

    fireEvent.mouseDown(document.body);
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
  });

  it('closes dropdown on Escape key', () => {
    render(<ModelSelector {...defaultProps} />);
    fireEvent.click(screen.getByRole('button'));
    expect(screen.getByRole('listbox')).toBeInTheDocument();

    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
  });

  it('calls onModelChange with correct provider and model name when a model is selected', () => {
    const onModelChange = vi.fn();
    render(<ModelSelector {...defaultProps} onModelChange={onModelChange} />);
    fireEvent.click(screen.getByRole('button'));

    // Select Claude Sonnet 4.6 (anthropic provider)
    fireEvent.click(screen.getByText('Claude Sonnet 4.6'));
    expect(onModelChange).toHaveBeenCalledWith('anthropic', 'claude-sonnet-4-6');
  });

  it('closes dropdown after selecting a model', () => {
    render(<ModelSelector {...defaultProps} />);
    fireEvent.click(screen.getByRole('button'));
    fireEvent.click(screen.getByText('Claude Sonnet 4.6'));
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
  });

  it('shows models grouped by provider label', () => {
    render(<ModelSelector {...defaultProps} />);
    fireEvent.click(screen.getByRole('button'));

    for (const label of Object.values(PROVIDER_LABELS)) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });

  it('highlights the currently selected model', () => {
    render(
      <ModelSelector
        {...defaultProps}
        currentProvider="anthropic"
        currentModelName="claude-sonnet-4-6"
      />,
    );
    fireEvent.click(screen.getByRole('button'));

    const selectedOption = screen.getByRole('option', { name: 'Claude Sonnet 4.6' });
    expect(selectedOption).toHaveAttribute('aria-selected', 'true');
  });

  it('does not open dropdown when disabled', () => {
    render(<ModelSelector {...defaultProps} disabled={true} />);
    fireEvent.click(screen.getByRole('button'));
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
  });

  it('shows "Unavailable" when error prop is true and model is not found', () => {
    render(
      <ModelSelector
        currentProvider=""
        currentModelName=""
        onModelChange={vi.fn()}
        error={true}
      />,
    );
    expect(screen.getByText('Unavailable')).toBeInTheDocument();
  });
});
