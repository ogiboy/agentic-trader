#!/usr/bin/env node

/**
 * Generate openapi.json from JSDoc annotations in server.js.
 * Run: node scripts/generate-openapi.js
 */

import { writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import swaggerJsdoc from 'swagger-jsdoc';
import { swaggerDefinition } from '../lib/openapi.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, '..');

const spec = swaggerJsdoc({
  definition: swaggerDefinition,
  apis: [join(root, 'server.js')],
});

const out = join(root, 'openapi.json');
writeFileSync(out, JSON.stringify(spec, null, 2) + '\n');
console.log(`Wrote ${Object.keys(spec.paths).length} paths to openapi.json`);
