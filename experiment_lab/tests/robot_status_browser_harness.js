// Small browser surface for exercising the actual status script and fetch flow.
const fs = require('node:fs');
const vm = require('node:vm');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
class Element {
  constructor(tag = 'div') {
    this.tagName = tag; this.hidden = true; this.textContent = '';
    this.dataset = {}; this.children = []; this.parent = null;
  }
  append(...children) { children.forEach(child => this.appendChild(child)); }
  appendChild(child) { child.parent = this; this.children.push(child); }
  replaceChildren(...children) { this.children = []; this.append(...children); }
  removeAttribute(name) { if (name === 'src') this._src = ''; }
  remove() { if (this.parent) this.parent.children = this.parent.children.filter(child => child !== this); }
  replaceWith(other) {
    if (this.parent) {
      other.parent = this.parent;
      this.parent.children = this.parent.children.map(child => child === this ? other : child);
    }
  }
}
class TestImage extends Element {
  constructor() { super('img'); this.hidden = false; }
  set src(value) { this._src = value; queueMicrotask(() => this.onload && this.onload()); }
}
const nodes = Object.fromEntries(input.node_names.map(name => {
  const node = new Element(); node.dataset.rn = name; return [name, node];
}));
const panel = new Element();
panel.querySelectorAll = () => Object.values(nodes);
const timers = new Map();
let timerId = 0, responseIndex = 0;
const calls = [];
global.document = {getElementById: () => panel, createElement: tag => new Element(tag)};
global.window = {location: {pathname: '/experiments/example', search: '?view=live'}, addEventListener: () => {}};
global.Image = TestImage;
global.setTimeout = (callback, delay) => { timers.set(++timerId, {callback, delay}); return timerId; };
global.clearTimeout = id => timers.delete(id);
URL.createObjectURL = () => 'blob:test-frame';
URL.revokeObjectURL = () => {};
global.fetch = async (url, options) => {
  calls.push(url);
  if (url !== '/api/robot-status') {
    return {ok: !input.frame_status, status: input.frame_status || 200, blob: async () => new Blob(['jpeg'])};
  }
  const response = input.responses[Math.min(responseIndex++, input.responses.length - 1)];
  if (response.error) throw Object.assign(new Error('private network error'), {name: response.error});
  return {ok: !response.status || response.status < 400, status: response.status || 200,
    json: async () => {
      if (response.invalid_json) throw new SyntaxError('private invalid response');
      return response.body;
    }};
};
const settle = () => new Promise(resolve => setImmediate(resolve));
const snapshot = () => ({
  nodes: Object.fromEntries(Object.entries(nodes).map(([key, node]) => [key, {
    text: node.textContent, hidden: node.hidden, href: node.href,
    children: node.children.map(child => child.textContent),
  }])),
  health: panel.dataset.health, execution: panel.dataset.execution,
});
(async () => {
  vm.runInThisContext(input.script);
  await settle();
  const snapshots = [snapshot()];
  for (let i = 1; i < input.responses.length; i++) {
    const next = [...timers].find(([, timer]) => timer.delay <= 5000);
    if (!next) throw new Error('No next poll scheduled');
    timers.delete(next[0]); next[1].callback();
    await settle();
    snapshots.push(snapshot());
  }
  process.stdout.write(JSON.stringify({snapshots, calls}));
})().catch(error => { process.stderr.write(error.stack); process.exitCode = 1; });
