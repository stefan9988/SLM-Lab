import { useState, useCallback, useEffect } from 'react';
import type { ExtractionSchema } from '../types';
import { fetchSchemas, createSchema as apiCreate, updateSchemaApi, deleteSchemaApi } from '../utils/api';

export function useSchemas() {
  const [schemas, setSchemas] = useState<ExtractionSchema[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadSchemas = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchSchemas();
      setSchemas(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load schemas');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSchemas();
  }, [loadSchemas]);

  const addSchema = useCallback(async () => {
    try {
      const schema = await apiCreate('New Schema', [{ id: crypto.randomUUID(), key: '', description: '' }]);
      setSchemas((prev) => [schema, ...prev]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create schema');
    }
  }, []);

  const deleteSchema = useCallback(async (id: string) => {
    try {
      await deleteSchemaApi(id);
      setSchemas((prev) => prev.filter((s) => s.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete schema');
      throw err;
    }
  }, []);

  const saveSchema = useCallback(async (schema: ExtractionSchema) => {
    try {
      const updated = await updateSchemaApi(schema.id, schema.name, schema.fields);
      setSchemas((prev) => prev.map((s) => (s.id === updated.id ? updated : s)));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save schema');
      throw err;
    }
  }, []);

  const duplicateSchema = useCallback(async (schema: ExtractionSchema) => {
    try {
      const newName = `${schema.name}_copy`;
      const newFields = schema.fields.map((f) => ({ ...f, id: crypto.randomUUID() }));
      const created = await apiCreate(newName, newFields);
      setSchemas((prev) => [created, ...prev]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to duplicate schema');
      throw err;
    }
  }, []);

  return { schemas, loading, error, addSchema, deleteSchema, saveSchema, duplicateSchema };
}
