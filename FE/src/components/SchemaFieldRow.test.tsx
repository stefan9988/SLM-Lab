import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SchemaFieldRow from './SchemaFieldRow';
import type { SchemaField } from '../types';

const baseField: SchemaField = { id: 'f1', key: 'title', description: 'The title' };

describe('SchemaFieldRow', () => {
  it('renders key and description inputs with values', () => {
    render(<SchemaFieldRow field={baseField} onChange={vi.fn()} onDelete={vi.fn()} />);

    const inputs = screen.getAllByRole('textbox');
    expect(inputs[0]).toHaveValue('title');
    expect(inputs[1]).toHaveValue('The title');
  });

  it('renders placeholder text for empty fields', () => {
    const emptyField: SchemaField = { id: 'f2', key: '', description: '' };
    render(<SchemaFieldRow field={emptyField} onChange={vi.fn()} onDelete={vi.fn()} />);

    expect(screen.getByPlaceholderText('Field key')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Description (optional)')).toBeInTheDocument();
  });

  it('calls onChange when key input changes', async () => {
    const onChange = vi.fn();
    render(<SchemaFieldRow field={baseField} onChange={onChange} onDelete={vi.fn()} />);

    const keyInput = screen.getByDisplayValue('title');
    await userEvent.type(keyInput, 'X');

    expect(onChange).toHaveBeenCalledWith({ ...baseField, key: 'titleX' });
  });

  it('calls onChange when description input changes', async () => {
    const onChange = vi.fn();
    render(<SchemaFieldRow field={baseField} onChange={onChange} onDelete={vi.fn()} />);

    const descInput = screen.getByDisplayValue('The title');
    await userEvent.type(descInput, '!');

    expect(onChange).toHaveBeenCalledWith({ ...baseField, description: 'The title!' });
  });

  it('calls onDelete when delete button is clicked', async () => {
    const onDelete = vi.fn();
    render(<SchemaFieldRow field={baseField} onChange={vi.fn()} onDelete={onDelete} />);

    await userEvent.click(screen.getByRole('button', { name: /delete field/i }));
    expect(onDelete).toHaveBeenCalledOnce();
  });
});
