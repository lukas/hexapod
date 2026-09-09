// The header status line must never duplicate an error: the full text is
// rendered once, in the copyable #errbar toast, and the header keeps a short
// marker whose tooltip and Copy output still carry the real message.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const app = readFileSync(new URL('./app.js', import.meta.url), 'utf8');
const slice = app.slice(app.indexOf('const errbarEl = document.getElementById'),
  app.indexOf('// Sticky robot console:'));
assert.ok(slice.includes('function showSent('), 'slice must contain showSent');

class El {
  constructor(){ this.textContent=''; this.title=''; this.style={display:'none'};
    this.attrs={}; this.classes=new Set(); this.innerText=''; }
  get classList(){ const c=this.classes; return {
    toggle:(n,f)=>{ f ? c.add(n) : c.delete(n); }, contains:n=>c.has(n) }; }
  getAttribute(n){ return this.attrs[n] ?? null; }
}
function page(){
  const els = {};
  const byId = id => (els[id] ??= new El());
  let copied = '';
  const ctx = {
    document: { getElementById: byId, querySelector: () => null,
                createElement: () => new El(), body:{appendChild(){}, } ,
                documentElement:{style:{setProperty(){}}} },
    navigator: { clipboard: { writeText: async t => { copied = t; } } },
    window: { addEventListener(){} }, setTimeout: () => 0,
    conn: byId('conn'), sentEl: byId('sent'), gpEl: byId('gp'),
  };
  ctx.gpEl.attrs['aria-label'] = 'pad ok';
  byId('robotact').textContent = 'idle';
  vm.createContext(ctx);
  vm.runInContext(slice, ctx);
  return { ctx, els, copiedText: () => copied };
}
const LONG = 'L0 yaw reads +171.3° — outside its -20..150° range by more than 20°. '
  + 'The logical zero frame looks wrong; hand-set the known pose and POST /api/set_zero before any absolute move.';

test('an error is shown once, in the toast; the header keeps a marker', () => {
  const {ctx, els} = page();
  ctx.showSent(LONG, true);
  assert.equal(els['errbar-text'].textContent, LONG);
  assert.equal(els.errbar.style.display, 'flex');
  assert.notEqual(els.sent.textContent, LONG);
  assert.ok(els.sent.textContent.startsWith('error'));
  assert.equal(els.sent.title, LONG);
  assert.ok(els.sent.classList.contains('bad'));
});

test('a message that merely looks bad is treated the same way', () => {
  const {ctx, els} = page();
  ctx.showSent('demo walk failed');
  assert.equal(els['errbar-text'].textContent, 'demo walk failed');
  assert.ok(els.sent.textContent.startsWith('error'));
});

test('ordinary receipts go to the header line untouched', () => {
  const {ctx, els} = page();
  ctx.showSent('pad A → walk sent…');
  assert.equal(els.sent.textContent, 'pad A → walk sent…');
  assert.equal(els.sent.title, '');
  assert.ok(!els.sent.classList.contains('bad'));
  assert.equal(els.errbar.style.display, 'none');
});

test('the header Copy button copies the real error, not the marker', async () => {
  const {ctx, els, copiedText} = page();
  ctx.showSent(LONG, true);
  await els.statuscopy.onclick();
  assert.ok(copiedText().includes('last: ' + LONG));
  assert.ok(!copiedText().includes('see message below'));
});
