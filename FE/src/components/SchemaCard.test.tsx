import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SchemaCard from './SchemaCard';
import type { ExtractionSchema } from '../types';

const baseSchema: ExtractionSchema = {
  id: 's1',
  name: 'Invoice Schema',
  fields: [
    { id: 'f1', key: 'vendor', description: 'Vendor name' },
    { id: 'f2', key: 'amount', description: '' },
  ],
};

describe('SchemaCard', () => {
  it('renders schema name input with current value', () => {
    render(<SchemaCard schema={baseSchema} onUpdate={vi.fn()} onDelete={vi.fn()} onSave={vi.fn()} />);
    expect(screen.getByDisplayValue('Invoice Schema')).toBeInTheDocument();
  });

  it('renders all field rows', () => {
    render(<SchemaCard schema={baseSchema} onUpdate={vi.fn()} onDelete={vi.fn()} onSave={vi.fn()} />);
    expect(screen.getByDisplayValue('vendor')).toBeInTheDocument();
    expect(screen.getByDisplayValue('amount')).toBeInTheDocument();
  });

  it('calls onUpdate when schema name is edited', async () => {
    const onUpdate = vi.fn();
    render(<SchemaCard schema={baseSchema} onUpdate={onUpdate} onDelete={vi.fn()} onSave={vi.fn()} />);

    const nameInput = screen.getByDisplayValue('Invoice Schema');
    await userEvent.type(nameInput, '!');

    expect(onUpdate).toHaveBeenCalledWith({ ...baseSchema, name: 'Invoice Schema!' });
  });

  it('calls onUpdate with new field when "+ Add Field" is clicked', async () => {
    const onUpdate = vi.fn();
    render(<SchemaCard schema={baseSchema} onUpdate={onUpdate} onDelete={vi.fn()} onSave={vi.fn()} />);

    await userEvent.click(screen.getByText('+ Add Field'));

    expect(onUpdate).toHaveBeenCalledOnce();
    const updatedSchema = onUpdate.mock.calls[0][0];
    expect(updatedSchema.fields).toHaveLength(3);
    expect(updatedSchema.fields[2].key).toBe('');
  });

  it('calls onDelete when Delete button is clicked', async () => {
    const onDelete = vi.fn();
    render(<SchemaCard schema={baseSchema} onUpdate={vi.fn()} onDelete={onDelete} onSave={vi.fn()} />);

    await userEvent.click(screen.getByText('Delete'));
    expect(onDelete).toHaveBeenCalledOnce();
  });

  it('calls onSave when Save button is clicked', async () => {
    const onSave = vi.fn();
    render(<SchemaCard schema={baseSchema} onUpdate={vi.fn()} onDelete={vi.fn()} onSave={onSave} />);

    await userEvent.click(screen.getByText('Save'));
    expect(onSave).toHaveBeenCalledOnce();
  });

  it('removes a field when its delete button is clicked', async () => {
    const onUpdate = vi.fn();
    render(<SchemaCard schema={baseSchema} onUpdate={onUpdate} onDelete={vi.fn()} onSave={vi.fn()} />);

    const deleteButtons = screen.getAllByRole('button', { name: /delete field/i });
    await userEvent.click(deleteButtons[0]);

    expect(onUpdate).toHaveBeenCalledOnce();
    const updatedSchema = onUpdate.mock.calls[0][0];
    expect(updatedSchema.fields).toHaveLength(1);
    expect(updatedSchema.fields[0].id).toBe('f2');
  });
});
