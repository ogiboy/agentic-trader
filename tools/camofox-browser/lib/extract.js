const SUPPORTED_TYPES = new Set([
  'string',
  'number',
  'integer',
  'boolean',
  'object',
  'null',
]);

/**
 * Validates a simple JSON-schema-like object ensuring top-level `type: 'object'` and well-formed property definitions.
 * @param {object} schema - Schema expected to have `type: 'object'` and a `properties` object mapping property names to property definitions.
 * @returns {{ok: true}|{ok: false, error: string}} `{ok: true}` when schema is valid; otherwise `{ok: false, error}` with a short validation message.
 */
export function validateSchema(schema) {
  if (!schema || typeof schema !== 'object') {
    return { ok: false, error: 'schema must be an object' };
  }
  if (schema.type !== 'object') {
    return { ok: false, error: 'top-level schema must have type: object' };
  }
  if (!schema.properties || typeof schema.properties !== 'object') {
    return { ok: false, error: 'schema must have a properties object' };
  }
  for (const [prop, def] of Object.entries(schema.properties)) {
    if (!def || typeof def !== 'object') {
      return { ok: false, error: `property "${prop}" must be an object` };
    }
    if (def.type && !SUPPORTED_TYPES.has(def.type)) {
      return {
        ok: false,
        error: `property "${prop}" has unsupported type "${def.type}"`,
      };
    }
  }
  return { ok: true };
}

function coerceValue(raw, type) {
  if (raw == null) return null;
  if (type === 'string' || !type) return String(raw).trim();
  if (type === 'number') {
    const n = parseFloat(String(raw).replace(/[^0-9.eE+-]/g, ''));
    return Number.isFinite(n) ? n : null;
  }
  if (type === 'integer') {
    const n = parseInt(String(raw).replace(/[^0-9-]/g, ''), 10);
    return Number.isFinite(n) ? n : null;
  }
  if (type === 'boolean') {
    const s = String(raw).toLowerCase().trim();
    if (s === 'true' || s === 'yes' || s === '1') return true;
    if (s === 'false' || s === 'no' || s === '0') return false;
    return null;
  }
  return raw;
}

function extractFromRef(refs, refId) {
  const info = refs.get(refId);
  if (!info) return null;
  return info.name || null;
}

/**
 * Extract deterministic values for each property in a schema, optionally using `x-ref` lookups.
 *
 * Given a top-level object schema, attempts to extract a value for every property by resolving
 * `def['x-ref']` against `refs`. When a referenced value is found and the property defines a
 * primitive `type` (not `object`), the value is coerced to that type. Required properties that
 * cannot be extracted cause an error.
 *
 * @param {Object} schema - Top-level JSON Schema object (must have `type: "object"` and a `properties` object).
 * @param {Map<string, Object>} refs - Map of reference metadata keyed by reference id, used to resolve `x-ref`.
 * @returns {Object} An object mapping property names to extracted values (coerced primitives or `null` when absent).
 * @throws {Error} If `schema` is invalid or a required property could not be extracted.
 */
export function extractDeterministic({ schema, refs }) {
  const check = validateSchema(schema);
  if (!check.ok) throw new Error(check.error);

  const result = {};
  for (const [prop, def] of Object.entries(schema.properties)) {
    const refId = def['x-ref'];

    let value = null;
    if (refId) {
      value = extractFromRef(refs, refId);
      if (value != null && def.type && def.type !== 'object') {
        value = coerceValue(value, def.type);
      }
    }

    if (
      value == null &&
      Array.isArray(schema.required) &&
      schema.required.includes(prop)
    ) {
      throw new Error(
        `required property "${prop}" could not be extracted (x-ref=${refId || 'n/a'})`,
      );
    }

    result[prop] = value;
  }

  return result;
}
