import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SchemasPanel from './SchemasPanel';

const mockFetchSchemas = vi.fn();
const mockCreateSchema = vi.fn();
const mockUpdateSchemaApi = vi.fn();
const mockDeleteSchemaApi = vi.fn();

const mockAddToast = vi.fn();
vi.mock('../contexts/ToastContext', () => ({
  useToast: () => ({ addToast: mockAddToast }),
  ToastProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock('../utils/api', () => ({
  fetchSchemas: (...args: unknown[]) => mockFetchSchemas(...args),
  createSchema: (...args: unknown[]) => mockCreateSchema(...args),
  updateSchemaApi: (...args: unknown[]) => mockUpdateSchemaApi(...args),
  deleteSchemaApi: (...args: unknown[]) => mockDeleteSchemaApi(...args),
}));

beforeEach(() => {
  vi.clearAllMocks();
  mockFetchSchemas.mockResolvedValue([]);
});

describe('SchemasPanel', () => {
  it('renders header with title and buttons', async () => {
    render(<SchemasPanel onBack={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('Extraction Schemas')).toBeInTheDocument();
      expect(screen.getByText('+ New Schema')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /back to chat/i })).toBeInTheDocument();
    });
  });

  it('shows loading state initially', () => {
    mockFetchSchemas.mockReturnValue(new Promise(() => {})); // never resolves
    render(<SchemasPanel onBack={vi.fn()} />);

    expect(screen.getByText('Loading schemas...')).toBeInTheDocument();
  });

  it('shows error state when fetch fails', async () => {
    mockFetchSchemas.mockRejectedValue(new Error('Server error'));
    render(<SchemasPanel onBack={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('Server error')).toBeInTheDocument();
    });
  });

  it('shows empty state when no schemas exist', async () => {
    render(<SchemasPanel onBack={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('No extraction schemas yet.')).toBeInTheDocument();
    });
  });

  it('renders schema cards when schemas exist', async () => {
    mockFetchSchemas.mockResolvedValue([
      { id: '1', name: 'Schema A', fields: [{ id: 'f1', key: 'k', description: '' }] },
    ]);

    render(<SchemasPanel onBack={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByDisplayValue('Schema A')).toBeInTheDocument();
    });
  });

  it('creates a new schema when "+ New Schema" is clicked', async () => {
    const newSchema = { id: '2', name: 'New Schema', fields: [{ id: 'f1', key: '', description: '' }] };
    mockCreateSchema.mockResolvedValue(newSchema);

    render(<SchemasPanel onBack={vi.fn()} />);

    await waitFor(() => {
      expect(screen.queryByText('Loading schemas...')).not.toBeInTheDocument();
    });

    await userEvent.click(screen.getByText('+ New Schema'));

    await waitFor(() => {
      expect(screen.getByDisplayValue('New Schema')).toBeInTheDocument();
    });
  });

  it('calls onBack when back button is clicked', async () => {
    const onBack = vi.fn();
    render(<SchemasPanel onBack={onBack} />);

    await userEvent.click(screen.getByRole('button', { name: /back to chat/i }));
    expect(onBack).toHaveBeenCalledOnce();
  });

  it('deletes a schema when its Delete button is clicked', async () => {
    mockFetchSchemas.mockResolvedValue([
      { id: '1', name: 'To Delete', fields: [] },
    ]);
    mockDeleteSchemaApi.mockResolvedValue(undefined);

    render(<SchemasPanel onBack={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByDisplayValue('To Delete')).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText('Delete'));

    await waitFor(() => {
      expect(screen.getByText('No extraction schemas yet.')).toBeInTheDocument();
    });
  });

  it('saves a schema when Save button is clicked', async () => {
    mockFetchSchemas.mockResolvedValue([
      { id: '1', name: 'My Schema', fields: [{ id: 'f1', key: 'title', description: '' }] },
    ]);
    mockUpdateSchemaApi.mockResolvedValue({
      id: '1', name: 'My Schema', fields: [{ id: 'f1', key: 'title', description: '' }],
    });

    render(<SchemasPanel onBack={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByDisplayValue('My Schema')).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText('Save'));

    await waitFor(() => {
      expect(mockUpdateSchemaApi).toHaveBeenCalledWith(
        '1', 'My Schema', [{ id: 'f1', key: 'title', description: '' }]
      );
    });
  });
});
