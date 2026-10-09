import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '../../../_local_data/native_platform_v0/ensemble');
const context = { console: { log() {}, warn() {}, error() {} }, __groups: [], __group: null };
context.$ = selector => {
  const obj = { classes: [], appendTo() { return this; }, append(x) { if (x?.classes?.includes('testPassed')) context.__groups.push('PASS'); else if (x?.classes?.includes('testFailed')) context.__groups.push('FAIL'); return this; }, addClass(c) { this.classes.push(c); return this; } };
  if (selector === '#testResults') obj.append = x => { context.__groups.push(x?.classes?.includes('testPassed') ? 'PASS' : 'FAIL'); return obj; };
  return obj;
};
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(root, 'build/ensemble-test.js'), 'utf8'), context, { filename: 'official build/ensemble-test.js' });
const dataDir = path.join(root, 'tests/data');
for (const f of fs.readdirSync(dataDir).filter(f => f.endsWith('.json'))) context[path.basename(f, '.json')] = fs.readFileSync(path.join(dataDir, f), 'utf8');
for (const f of ['Tests.js', 'ActionLibraryUnitTests.js', 'ensembleUnitTests.js', 'ExternalApplicationTest.js', 'RuleLibraryUnitTests.js', 'SocialRecordUnitTests.js', 'ValidateUnitTests.js', 'VolitionUnitTests.js']) {
  vm.runInContext(fs.readFileSync(path.join(root, 'tests/js', f), 'utf8'), context, { filename: `official tests/js/${f}` });
}
vm.runInContext(`ensemble.init(); socialRecord.init(); ensembleUnitTests.runTests(); socialRecordUnitTests.runTests(); ruleLibraryUnitTests.runTests(); volitionUnitTests.runTests(); validateUnitTests.runTests(); actionLibraryUnitTests.runTests();`, context);
const groups = context.__groups;
const passed = groups.filter(x => x === 'PASS').length;
const failed = groups.filter(x => x === 'FAIL').length;
process.stdout.write(JSON.stringify({ suite: 'official upstream core JS unit tests', groups: groups.length, passed, failed, omitted: 'ExternalApplicationTest requires browser document events; not executed in Node VM', harness: 'Node VM; upstream original core test source and generated test bundle; minimal DOM append shim', doActionTest: 'disabled upstream at ActionLibraryUnitTests.js:23 (legacy API incompatibility comment at line 102)' }, null, 2) + '\n');
if (failed) process.exitCode = 1;
