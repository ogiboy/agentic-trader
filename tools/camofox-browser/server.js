import { loadConfig } from './lib/config.js';
import { createJsonLogger } from './lib/logging.js';
import { startCamofoxRuntime } from './lib/server/runtime-bootstrap.js';
import { createCamofoxServerRuntime } from './lib/server/runtime-dependencies.js';

const config = loadConfig();
const log = createJsonLogger();
const runtime = await createCamofoxServerRuntime({ config, log });

await startCamofoxRuntime(runtime);
