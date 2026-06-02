import { asRecord, asString, type JsonRecord } from '../json-record';
import { execTrader } from './cli-exec';
import { getDashboardSnapshot } from './dashboard';

export type ToolActionKind =
  | 'enable-local-tools'
  | 'enable-host-fallbacks'
  | 'start-model-service'
  | 'start-camofox-service';

function modelNameFromDashboard(data: JsonRecord): string {
  const modelService = asRecord(data.modelService);
  const doctor = asRecord(data.doctor);
  return (
    asString(modelService.configured_model, '') ||
    asString(doctor.model, '') ||
    'qwen3:8b'
  );
}

export async function runToolAction(kind: ToolActionKind): Promise<{
  message: string;
  dashboard: JsonRecord;
  result?: JsonRecord;
}> {
  if (kind === 'enable-local-tools') {
    const result = (await execTrader(
      [
        'tool-ownership',
        'set',
        '--ollama-owner',
        'app-owned',
        '--firecrawl-owner',
        'app-owned',
        '--camofox-owner',
        'app-owned',
        '--json',
      ],
      { expectJson: true, timeoutMs: 30_000 },
    )) as JsonRecord;
    return {
      dashboard: await getDashboardSnapshot(),
      message: 'Local tool ownership set to app-owned.',
      result,
    };
  }

  if (kind === 'enable-host-fallbacks') {
    const result = (await execTrader(
      [
        'tool-ownership',
        'set',
        '--ollama-owner',
        'host-owned',
        '--firecrawl-owner',
        'host-owned',
        '--camofox-owner',
        'host-owned',
        '--json',
      ],
      { expectJson: true, timeoutMs: 30_000 },
    )) as JsonRecord;
    return {
      dashboard: await getDashboardSnapshot(),
      message: 'Host-managed fallback ownership enabled.',
      result,
    };
  }

  if (kind === 'start-model-service') {
    const data = await getDashboardSnapshot();
    await execTrader(
      ['tool-ownership', 'set', '--ollama-owner', 'app-owned', '--json'],
      { expectJson: true, timeoutMs: 30_000 },
    );
    const result = (await execTrader(
      ['model-service', 'start', '--host', '127.0.0.1', '--json'],
      { expectJson: true, timeoutMs: 45_000 },
    )) as JsonRecord;
    const model = modelNameFromDashboard(data);
    const modelState = result?.model_available
      ? `${model} is listed`
      : `${model} is not listed; pull it explicitly from the CLI before running strict cycles`;
    return {
      dashboard: await getDashboardSnapshot(),
      message: `App-owned model-service started; ${modelState}.`,
      result,
    };
  }

  if (kind === 'start-camofox-service') {
    await execTrader(
      ['tool-ownership', 'set', '--camofox-owner', 'app-owned', '--json'],
      { expectJson: true, timeoutMs: 30_000 },
    );
    const result = (await execTrader(
      ['camofox-service', 'start', '--host', '127.0.0.1', '--json'],
      { expectJson: true, timeoutMs: 45_000 },
    )) as JsonRecord;
    return {
      dashboard: await getDashboardSnapshot(),
      message: 'App-owned Camofox helper started.',
      result,
    };
  }

  throw new Error(`Unsupported tool action: ${kind}`);
}
