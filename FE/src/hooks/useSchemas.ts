import { useState, useCallback } from 'react';
import type { ExtractionSchema } from '../types';
import {
  loadSchemas,
  addSchema as storageAdd,
  removeSchema as storageRemove,
  updateSchema as storageUpdate,
} from '../utils/schemaStorage';

export function useSchemas() {
  const [schemas, setSchemas] = useState<ExtractionSchema[]>(loadSchemas);

  const addSchema = useCallback(() => {
    const schema: ExtractionSchema = {
      id: crypto.randomUUID(),
      name: 'New Schema',
      fields: [{ id: crypto.randomUUID(), key: '', description: '' }],
    };
    setSchemas(storageAdd(schema));
  }, []);

  const deleteSchema = useCallback((id: string) => {
    setSchemas(storageRemove(id));
  }, []);

  const updateSchema = useCallback((schema: ExtractionSchema) => {
    setSchemas(storageUpdate(schema));
  }, []);

  return { schemas, addSchema, deleteSchema, updateSchema };
}
