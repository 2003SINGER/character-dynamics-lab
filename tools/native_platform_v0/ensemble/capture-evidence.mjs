import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '../../..');
const baseDir = path.join(root, 'outputs/native_platform_p1p2_v0/p2_ensemble_20261010/runs');
const runId = process.env.RUN_ID || `${new Date().toISOString().replace(/[-:.TZ]/g, '')}-${process.pid}`;
if (!/^[A-Za-z0-9_-]+$/.test(runId)) throw new Error('RUN_ID must contain only letters, digits, underscore, or hyphen');
const outDir = path.join(baseDir, runId);
if (fs.existsSync(outDir)) throw new Error(`refusing to reuse evidence run directory: ${outDir}`);
const commands = [
  ['node', ['tools/native_platform_v0/ensemble/reproduce.mjs']],
  ['node', ['tools/native_platform_v0/ensemble/run-upstream-tests.mjs']],
  ['node', ['tools/native_platform_v0/ensemble/interface-selftest.mjs']]
];
const evidence = commands.map(([command, args]) => {
  const result = spawnSync(command, args, { cwd: root, encoding: 'utf8' });
  return { command: [command, ...args].join(' '), cwd: root, exitStatus: result.status, signal: result.signal, stdout: result.stdout, stderr: result.stderr };
});
fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(path.join(outDir, 'native-test-evidence.json'), JSON.stringify({ runId, runtime: process.version, commands: evidence }, null, 2) + '\n', { flag: 'wx' });
process.stdout.write(JSON.stringify(evidence.map(({ command, exitStatus, signal, stdout, stderr }) => ({ command, exitStatus, signal, stdout, stderr })), null, 2) + '\n');
if (evidence.some(e => e.exitStatus !== 0)) process.exitCode = 1;
