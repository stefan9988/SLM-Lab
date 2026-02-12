import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SchemasPanel from './SchemasPanel';

const KEY = 'slm-extraction-schemas';

beforeEach(() => {
  localStorage.clear();
});

describe('SchemasPanel', () => {
  it('renders header with title and buttons', () => {
    render(<SchemasPanel onBack={vi.fn()} />);

    expect(screen.getByText('Extraction Schemas')).toBeInTheDocument();
    expect(screen.getByText('+ New Schema')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /back to chat/i })).toBeInTheDocument();
  });

  it('shows empty state when no schemas exist', () => {
    render(<SchemasPanel onBack={vi.fn()} />);

    expect(screen.getByText('No extraction schemas yet.')).toBeInTheDocument();
  });

  it('renders schema cards when schemas exist', () => {
    const schemas = [
      { id: '1', name: 'Schema A', fields: [{ id: 'f1', key: 'k', description: '' }] },
    ];
    localStorage.setItem(KEY, JSON.stringify(schemas));

    render(<SchemasPanel onBack={vi.fn()} />);

    expect(screen.getByDisplayValue('Schema A')).toBeInTheDocument();
  });

  it('creates a new schema when "+ New Schema" is clicked', async () => {
    render(<SchemasPanel onBack={vi.fn()} />);

    await userEvent.click(screen.getByText('+ New Schema'));

    expect(screen.queryByText('No extraction schemas yet.')).not.toBeInTheDocument();
    expect(screen.getByDisplayValue('New Schema')).toBeInTheDocument();
  });

  it('calls onBack when back button is clicked', async () => {
    const onBack = vi.fn();
    render(<SchemasPanel onBack={onBack} />);

    await userEvent.click(screen.getByRole('button', { name: /back to chat/i }));
    expect(onBack).toHaveBeenCalledOnce();
  });

  it('deletes a schema when its Delete button is clicked', async () => {
    const schemas = [
      { id: '1', name: 'To Delete', fields: [] },
    ];
    localStorage.setItem(KEY, JSON.stringify(schemas));

    render(<SchemasPanel onBack={vi.fn()} />);

    await userEvent.click(screen.getByText('Delete'));

    expect(screen.getByText('No extraction schemas yet.')).toBeInTheDocument();
  });
});
