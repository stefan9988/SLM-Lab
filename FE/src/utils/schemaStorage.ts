import type { ExtractionSchema } from '../types';
import logger from './logger';

const KEY = 'slm-extraction-schemas';

export function loadSchemas(): ExtractionSchema[] {
  try {
    const data = JSON.parse(localStorage.getItem(KEY) || '[]');
    logger.info('[SchemaStorage] Loaded', data.length, 'schemas from localStorage');
    return data;
  } catch (err) {
    logger.error('[SchemaStorage] Failed to load schemas:', err);
    return [];
  }
}

export function saveSchemas(schemas: ExtractionSchema[]): void {
  logger.info('[SchemaStorage] Saving', schemas.length, 'schemas to localStorage');
  localStorage.setItem(KEY, JSON.stringify(schemas));
}

export function addSchema(schema: ExtractionSchema): ExtractionSchema[] {
  logger.info('[SchemaStorage] Adding schema:', schema.id, schema.name);
  const list = loadSchemas();
  list.unshift(schema);
  saveSchemas(list);
  return list;
}

export function removeSchema(id: string): ExtractionSchema[] {
  logger.info('[SchemaStorage] Removing schema:', id);
  const list = loadSchemas().filter((s) => s.id !== id);
  saveSchemas(list);
  return list;
}

export function updateSchema(updated: ExtractionSchema): ExtractionSchema[] {
  logger.info('[SchemaStorage] Updating schema:', updated.id, updated.name);
  const list = loadSchemas().map((s) => (s.id === updated.id ? updated : s));
  saveSchemas(list);
  return list;
}
