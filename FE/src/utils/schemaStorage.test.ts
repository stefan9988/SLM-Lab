import { describe, it, expect, beforeEach, vi } from 'vitest';
import { loadSchemas, saveSchemas, addSchema, removeSchema, updateSchema } from './schemaStorage';
import type { ExtractionSchema } from '../types';

const KEY = 'slm-extraction-schemas';

const mockSchema: ExtractionSchema = {
  id: 'schema-1',
  name: 'Test Schema',
  fields: [{ id: 'field-1', key: 'title', description: 'The title' }],
};

const mockSchema2: ExtractionSchema = {
  id: 'schema-2',
  name: 'Second Schema',
  fields: [{ id: 'field-2', key: 'author', description: '' }],
};

beforeEach(() => {
  localStorage.clear();
  vi.restoreAllMocks();
});

describe('loadSchemas', () => {
  it('returns empty array when localStorage is empty', () => {
    expect(loadSchemas()).toEqual([]);
  });

  it('returns parsed schemas from localStorage', () => {
    localStorage.setItem(KEY, JSON.stringify([mockSchema]));
    expect(loadSchemas()).toEqual([mockSchema]);
  });

  it('returns empty array on invalid JSON', () => {
    localStorage.setItem(KEY, 'not-json');
    expect(loadSchemas()).toEqual([]);
  });
});

describe('saveSchemas', () => {
  it('writes schemas to localStorage', () => {
    saveSchemas([mockSchema]);
    expect(JSON.parse(localStorage.getItem(KEY)!)).toEqual([mockSchema]);
  });
});

describe('addSchema', () => {
  it('prepends schema and returns updated list', () => {
    localStorage.setItem(KEY, JSON.stringify([mockSchema]));
    const result = addSchema(mockSchema2);
    expect(result).toEqual([mockSchema2, mockSchema]);
    expect(JSON.parse(localStorage.getItem(KEY)!)).toEqual([mockSchema2, mockSchema]);
  });

  it('works with empty storage', () => {
    const result = addSchema(mockSchema);
    expect(result).toEqual([mockSchema]);
  });
});

describe('removeSchema', () => {
  it('removes schema by id and returns updated list', () => {
    localStorage.setItem(KEY, JSON.stringify([mockSchema, mockSchema2]));
    const result = removeSchema('schema-1');
    expect(result).toEqual([mockSchema2]);
    expect(JSON.parse(localStorage.getItem(KEY)!)).toEqual([mockSchema2]);
  });

  it('returns unchanged list when id not found', () => {
    localStorage.setItem(KEY, JSON.stringify([mockSchema]));
    const result = removeSchema('nonexistent');
    expect(result).toEqual([mockSchema]);
  });
});

describe('updateSchema', () => {
  it('replaces matching schema and returns updated list', () => {
    localStorage.setItem(KEY, JSON.stringify([mockSchema, mockSchema2]));
    const updated = { ...mockSchema, name: 'Updated Name' };
    const result = updateSchema(updated);
    expect(result[0].name).toBe('Updated Name');
    expect(result[1]).toEqual(mockSchema2);
    expect(JSON.parse(localStorage.getItem(KEY)!)[0].name).toBe('Updated Name');
  });
});
