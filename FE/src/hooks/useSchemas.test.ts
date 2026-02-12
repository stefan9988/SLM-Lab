import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useSchemas } from './useSchemas';

const KEY = 'slm-extraction-schemas';

beforeEach(() => {
  localStorage.clear();
});

describe('useSchemas', () => {
  it('initializes with empty schemas from localStorage', () => {
    const { result } = renderHook(() => useSchemas());
    expect(result.current.schemas).toEqual([]);
  });

  it('initializes with existing schemas from localStorage', () => {
    const existing = [{ id: '1', name: 'Test', fields: [] }];
    localStorage.setItem(KEY, JSON.stringify(existing));
    const { result } = renderHook(() => useSchemas());
    expect(result.current.schemas).toEqual(existing);
  });

  it('addSchema creates a new schema with default name and one empty field', () => {
    const { result } = renderHook(() => useSchemas());

    act(() => {
      result.current.addSchema();
    });

    expect(result.current.schemas).toHaveLength(1);
    expect(result.current.schemas[0].name).toBe('New Schema');
    expect(result.current.schemas[0].fields).toHaveLength(1);
    expect(result.current.schemas[0].fields[0].key).toBe('');
    expect(result.current.schemas[0].fields[0].description).toBe('');
  });

  it('deleteSchema removes a schema by id', () => {
    const existing = [
      { id: '1', name: 'First', fields: [] },
      { id: '2', name: 'Second', fields: [] },
    ];
    localStorage.setItem(KEY, JSON.stringify(existing));
    const { result } = renderHook(() => useSchemas());

    act(() => {
      result.current.deleteSchema('1');
    });

    expect(result.current.schemas).toHaveLength(1);
    expect(result.current.schemas[0].id).toBe('2');
  });

  it('updateSchema replaces a schema in state and localStorage', () => {
    const existing = [{ id: '1', name: 'Original', fields: [] }];
    localStorage.setItem(KEY, JSON.stringify(existing));
    const { result } = renderHook(() => useSchemas());

    act(() => {
      result.current.updateSchema({ id: '1', name: 'Updated', fields: [] });
    });

    expect(result.current.schemas[0].name).toBe('Updated');
    expect(JSON.parse(localStorage.getItem(KEY)!)[0].name).toBe('Updated');
  });
});
