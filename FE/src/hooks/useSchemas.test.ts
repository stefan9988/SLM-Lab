import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useSchemas } from './useSchemas';

const mockSchemas = [
  { id: '1', name: 'Schema A', fields: [{ id: 'f1', key: 'title', description: '' }] },
  { id: '2', name: 'Schema B', fields: [] },
];

const mockFetchSchemas = vi.fn();
const mockCreateSchema = vi.fn();
const mockUpdateSchemaApi = vi.fn();
const mockDeleteSchemaApi = vi.fn();

vi.mock('../utils/api', () => ({
  fetchSchemas: (...args: unknown[]) => mockFetchSchemas(...args),
  createSchema: (...args: unknown[]) => mockCreateSchema(...args),
  updateSchemaApi: (...args: unknown[]) => mockUpdateSchemaApi(...args),
  deleteSchemaApi: (...args: unknown[]) => mockDeleteSchemaApi(...args),
}));

beforeEach(() => {
  vi.clearAllMocks();
  mockFetchSchemas.mockResolvedValue(mockSchemas);
});

describe('useSchemas', () => {
  it('fetches schemas on mount and sets loading to false', async () => {
    const { result } = renderHook(() => useSchemas());

    expect(result.current.loading).toBe(true);

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.schemas).toEqual(mockSchemas);
    expect(result.current.error).toBeNull();
    expect(mockFetchSchemas).toHaveBeenCalledOnce();
  });

  it('sets error when fetchSchemas fails', async () => {
    mockFetchSchemas.mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => useSchemas());

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.schemas).toEqual([]);
    expect(result.current.error).toBe('Network error');
  });

  it('addSchema calls API and prepends to state', async () => {
    const newSchema = { id: '3', name: 'New Schema', fields: [{ id: 'f2', key: '', description: '' }] };
    mockCreateSchema.mockResolvedValue(newSchema);

    const { result } = renderHook(() => useSchemas());
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.addSchema();
    });

    expect(result.current.schemas[0]).toEqual(newSchema);
    expect(result.current.schemas).toHaveLength(3);
  });

  it('deleteSchema calls API and removes from state', async () => {
    mockDeleteSchemaApi.mockResolvedValue(undefined);

    const { result } = renderHook(() => useSchemas());
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.deleteSchema('1');
    });

    expect(result.current.schemas).toHaveLength(1);
    expect(result.current.schemas[0].id).toBe('2');
    expect(mockDeleteSchemaApi).toHaveBeenCalledWith('1');
  });

  it('saveSchema calls API and replaces in state', async () => {
    const updated = { id: '1', name: 'Updated', fields: [] };
    mockUpdateSchemaApi.mockResolvedValue(updated);

    const { result } = renderHook(() => useSchemas());
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.saveSchema(updated);
    });

    expect(result.current.schemas[0]).toEqual(updated);
    expect(mockUpdateSchemaApi).toHaveBeenCalledWith('1', 'Updated', []);
  });

  it('sets error when addSchema fails', async () => {
    mockCreateSchema.mockRejectedValue(new Error('Create failed'));

    const { result } = renderHook(() => useSchemas());
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.addSchema();
    });

    expect(result.current.error).toBe('Create failed');
  });

  it('sets error when deleteSchema fails', async () => {
    mockDeleteSchemaApi.mockRejectedValue(new Error('Delete failed'));

    const { result } = renderHook(() => useSchemas());
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.deleteSchema('1');
    });

    expect(result.current.error).toBe('Delete failed');
  });

  it('sets error when saveSchema fails', async () => {
    mockUpdateSchemaApi.mockRejectedValue(new Error('Save failed'));

    const { result } = renderHook(() => useSchemas());
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.saveSchema({ id: '1', name: 'X', fields: [] });
    });

    expect(result.current.error).toBe('Save failed');
  });
});
