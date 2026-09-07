// Exercise the real picker and drive handlers with no browser, network or robot.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const app = readFileSync(new URL('./app.js', import.meta.url), 'utf8');
const defaultFile = 'cpg_controller_robust120_yawtrim.json';
const picker = app.slice(app.indexOf('const wgaitSel ='),
  app.indexOf('// --- Drive telemetry strip'));
const drive = app.slice(app.indexOf('function clamp(v,a,b)'),
  app.indexOf('// --- Debug page:'));

class Element {
  constructor(value = '') {
    this.value = value;
    this.options = [];
    this.disabled = false;
    this.style = {};
    this.dataset = {};
    this.classList = {toggle(){}};
  }
  set innerHTML(html) {
    this.options = [...html.matchAll(/<option value="([^"]*)"[^>]*>(.*?)<\/option>/g)]
      .map(([, value, label]) => Object.assign(new Element(value), {textContent:label}));
    this.value = this.options[0]?.value || '';
  }
  appendChild(option) { this.options.push(option); }
}

async function page(rows, {httpOk = true, networkError = false, loadOk = true} = {}) {
  const elements = new Map();
  const get = id => {
    if(!elements.has(id)) elements.set(id, new Element());
    return elements.get(id);
  };
  get('wgait').options = Array.from({length:11}, (_, i) => new Element(String(i)));
  get('walpha').value = '0';
  get('wvx').value = '20';
  get('wvy').value = '0';
  get('wom').value = '0';
  get('wdur').value = '3';
  const cpgButton = new Element();
  cpgButton.dataset = {gait:'6', cpg:defaultFile};
  const otherButton = new Element();
  otherButton.dataset = {gait:'1'};
  const commands = [], requests = [], messages = [];
  const context = vm.createContext({
    document:{getElementById:get, querySelectorAll:() => [cpgButton, otherButton],
      createElement:() => new Element()},
    window:{addEventListener(){}},
    performance:{now:() => 1000},
    setInterval:() => 1, setTimeout:() => 1, clearInterval(){}, clearTimeout(){},
    fetch:async (url, opts) => {
      requests.push(opts.body);
      if(networkError) throw new Error('offline');
      return {ok:httpOk, text:async () => JSON.stringify(rows)};
    },
    cmd:async line => {
      commands.push(line);
      return loadOk || !line.startsWith('CPGLOAD ')
        ? {ok:true, text:'ok'} : {ok:true, text:'bad CPGLOAD: incompatible'};
    },
    showSent:msg => messages.push(msg), needArm:() => false,
    updateGaitTuneVisibility(){}, sendTripodTune:async () => true,
  });
  vm.runInContext(`
    const $ = id => document.getElementById(id);
    const DEFAULT_CPG_CONTROLLER = ${JSON.stringify(defaultFile)};
    let gait = 6, armed = false, dancePaused = false, servosArmed = true;
    let maxVx = 30, maxVy = 18, maxOmega = 0.35;
  ` + picker + drive, context);
  // Drain the initial async CPGLIST -> optional CPGLOAD -> GAIT sequence.
  await new Promise(resolve => setImmediate(resolve));
  return {get, cpgButton, otherButton, commands, requests, messages,
    run:script => vm.runInContext(script, context)};
}

const incompatible = {file:defaultFile,
  error:"expected joint_frame='robot_abs' and joint_contract='robot_abs_tibia_v2', got None/None"};
const compatible = {file:defaultFile, name:'robust120 yawtrim', gait:'tetrapod',
  gate_pass_dr0:true, gate_slip_per_m:0.05};

test('incompatible default stays disabled and all drive/load entry points refuse it', async () => {
  const p = await page([incompatible]);
  assert.deepEqual(p.requests, ['CPGLIST']);
  assert.deepEqual(p.commands, []);
  assert.equal(p.get('wcpgsel').options.find(o => o.value === defaultFile).disabled, true);
  for(const id of ['wcpgsel', 'wcpgload', 'wstart']) assert.equal(p.get(id).disabled, true);
  assert.equal(p.cpgButton.disabled, true);
  assert.equal(p.get('wgait').options[6].disabled, true);
  assert.match(p.get('wcpgstatus').textContent, /incompatible/);
  assert.doesNotMatch(p.get('wgaitsummary').textContent, /Loading/);

  // Programmatic clicks also exercise the guards behind disabled HTML controls.
  await p.cpgButton.onclick();
  p.get('wcpgsel').value = defaultFile;
  await p.get('wcpgload').onclick();
  await p.get('wgait').onchange();
  await p.get('wstart').onclick();
  assert.equal(p.run('streamScriptedDrive(0, 1, 0)'), false);
  assert.deepEqual(p.commands, []);
  await p.get('wstop').onclick();
  assert.deepEqual(p.commands, ['J 0 0 0']);
});

for(const [name, rows, opts] of [
  ['empty list', [], {}],
  ['network failure', [], {networkError:true}],
  ['HTTP failure', [compatible], {httpOk:false}],
  ['malformed response', {error:'offline'}, {}],
]) {
  test(`${name} never falls through to a default load`, async () => {
    const p = await page(rows, opts);
    assert.deepEqual(p.commands, []);
    assert.equal(p.get('wcpgload').disabled, true);
    assert.equal(p.cpgButton.disabled, true);
    assert.equal(p.get('wstart').disabled, true);
    assert.match(p.get('wcpgstatus').textContent, /no controllers|could not be checked/);
    await p.cpgButton.onclick();
    assert.deepEqual(p.commands, []);
  });
}

test('compatible default retains successful load and gait selection', async () => {
  const p = await page([compatible]);
  assert.deepEqual(p.commands, [`CPGLOAD ${defaultFile}`, 'GAIT 6 0.00']);
  for(const id of ['wcpgsel', 'wcpgload', 'wstart']) assert.equal(p.get(id).disabled, false);
  assert.equal(p.cpgButton.disabled, false);
  assert.equal(p.run('streamScriptedDrive(0, 1, 0)'), true);
  assert.match(p.commands.at(-1), /^J 30 0 0\.000 6$/);
});

test('rejected load never enables CPG walking or selects its gait', async () => {
  const p = await page([compatible], {loadOk:false});
  assert.deepEqual(p.commands, [`CPGLOAD ${defaultFile}`]);
  assert.equal(p.get('wstart').disabled, true);
  await p.get('wstart').onclick();
  p.run('streamScriptedDrive(0, 1, 0)');
  assert.deepEqual(p.commands, [`CPGLOAD ${defaultFile}`]);
});

test('valid alternatives require explicit selection when default is unavailable', async () => {
  const alternate = 'cpg_controller_other.json';
  const p = await page([incompatible, {...compatible, file:alternate}]);
  assert.deepEqual(p.commands, []);
  assert.equal(p.get('wcpgsel').disabled, false);
  assert.equal(p.get('wcpgsel').value, '');
  assert.equal(p.cpgButton.disabled, true);
  p.get('wcpgsel').value = alternate;
  p.get('wcpgsel').onchange();
  assert.equal(p.get('wcpgload').disabled, false);
  await p.get('wgait').onchange();
  assert.deepEqual(p.commands, [`CPGLOAD ${alternate}`, 'GAIT 6 0.00']);
});

test('other gait selection and walking remain available with incompatible CPG', async () => {
  const p = await page([incompatible]);
  await p.otherButton.onclick();
  assert.equal(p.get('wstart').disabled, false);
  await p.get('wstart').onclick();
  assert.deepEqual(p.commands, ['GAIT 1 0.00', 'J 20.0 0.0 0.000 1']);
});
