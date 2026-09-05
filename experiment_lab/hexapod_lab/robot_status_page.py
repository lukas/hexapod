"""Read-only dashboard panel for the robot's cached state and camera frame."""


def robot_status_panel() -> str:
    return """
<style>
.robot-now{margin:0 0 2.5rem;padding:1.5rem;border:1px solid #35463e;border-radius:18px;background:#141c19;color:#e8f1ec;font:15px/1.5 system-ui,-apple-system,BlinkMacSystemFont,sans-serif}
.robot-now *{box-sizing:border-box}.robot-now h2,.robot-now h3,.robot-now p{margin:0}.robot-now h2{font-size:1.4rem;line-height:1.3;letter-spacing:-.025em}.robot-now h3{font-size:1rem;line-height:1.4}
.robot-now .rn-header{display:flex;align-items:center;justify-content:space-between;gap:1rem;margin-bottom:1rem}.robot-now .rn-badge{display:inline-flex;align-items:center;gap:.45rem;border:1px solid #53665b;border-radius:99px;padding:.25rem .6rem;color:#bac7c0;font-size:.74rem;font-weight:650;white-space:nowrap}.robot-now .rn-dot{width:7px;height:7px;background:currentColor;border-radius:50%;flex:none}
.robot-now .rn-execution{border:1px solid #4b5b4f;border-left:4px solid #93a996;border-radius:12px;padding:1rem 1.15rem;margin-bottom:1.3rem;background:#1a251e}.robot-now .rn-execution h3{font-size:.8rem;letter-spacing:.025em;font-weight:650;color:#bac9bf}.robot-now .rn-execution-headline{font-size:1.2rem;font-weight:700;line-height:1.4;letter-spacing:-.02em;margin-top:.3rem}.robot-now .rn-execution-reason{font-size:.94rem;color:#c7d3cb;line-height:1.55;margin-top:.4rem}.robot-now .rn-next{font-size:.94rem;margin-top:.65rem;line-height:1.5}.robot-now .rn-next strong{color:#e5efe8}.robot-now .rn-task{font-size:.76rem;color:#a7b9ad;margin-top:.6rem;overflow-wrap:anywhere}.robot-now[data-execution='blocked'] .rn-execution{border-left-color:#ffd280}.robot-now[data-execution='preparing'] .rn-execution{border-left-color:#8dcaf2}.robot-now[data-execution='running'] .rn-execution{border-left-color:#b7f34a}.robot-now .rn-health-header{display:flex;justify-content:space-between;align-items:center;gap:.8rem;margin-bottom:.65rem}.robot-now .rn-health-header h3{font-size:.8rem;font-weight:650;color:#adbbb3}
.robot-now[data-health='healthy'] .rn-badge{color:#b7f34a;border-color:#526e36}.robot-now[data-health='needs_attention'] .rn-badge{color:#ffd280;border-color:#826b3d}.robot-now[data-health='offline'] .rn-badge{color:#ffb3aa;border-color:#84534e}
.robot-now .rn-body{display:grid;grid-template-columns:minmax(0,1fr) minmax(220px,30%);gap:1.5rem;align-items:start}.robot-now .rn-body.rn-no-image{grid-template-columns:1fr}.robot-now .rn-summary{font-size:1.05rem;font-weight:650}.robot-now .rn-detail{color:#adbbb3;margin-top:.25rem}.robot-now .rn-metrics{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:.7rem;margin:1.1rem 0 0}.robot-now .rn-metric{min-width:0;border-top:1px solid #35463e;padding-top:.65rem}.robot-now dt{font-size:.74rem;color:#a7b6ac;margin-bottom:.2rem}.robot-now dd{margin:0;font-size:.96rem;font-weight:650;overflow-wrap:anywhere}.robot-now dd[data-tone='good']{color:#b7f34a}.robot-now dd[data-tone='warn']{color:#ffd280}.robot-now .rn-check{font-size:.8rem;font-weight:500}
.robot-now .rn-photo{margin:0;min-width:0}.robot-now .rn-photo img{display:block;width:100%;aspect-ratio:4/3;object-fit:contain;background:#080c0a;border:1px solid #35463e;border-radius:12px}.robot-now figcaption{color:#a7b6ac;font-size:.75rem;margin-top:.4rem}.robot-now [hidden]{display:none!important}
.robot-now .rn-readiness{border-top:1px solid #35463e;margin-top:1.2rem;padding-top:.85rem}.robot-now .rn-readiness summary{cursor:pointer;color:#c0cdc4;font-size:.86rem;font-weight:600}.robot-now .rn-readiness summary:focus-visible{outline:2px solid #b7f34a;outline-offset:4px}.robot-now .rn-reasons{margin:.5rem 0 .7rem;padding-left:1.2rem;color:#b7c4bc;font-size:.85rem;line-height:1.5}.robot-now .rn-reasons li+li{margin-top:.25rem}.robot-now .rn-queue{font-size:.8rem;color:#bac7c0;margin-top:.7rem}.robot-now .rn-issue{margin-top:.55rem;font-size:.85rem;color:#ffd280}.robot-now .rn-refresh{margin-top:.55rem;font-size:.75rem;color:#91a499}
@media(max-width:820px){.robot-now .rn-body{grid-template-columns:1fr}.robot-now .rn-photo{max-width:430px}.robot-now .rn-metrics{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:480px){.robot-now{padding:1.1rem}.robot-now .rn-header{align-items:flex-start;gap:.7rem}.robot-now h2{font-size:1.2rem}.robot-now .rn-badge{font-size:.72rem;padding:.28rem .55rem}.robot-now .rn-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.robot-now .rn-metric:last-child{grid-column:1/-1}}
</style>
<section class="robot-now" id="robot-now" data-health="unknown" data-execution="unknown" aria-labelledby="robot-now-title">
  <div class="rn-header">
    <h2 id="robot-now-title">Robot right now</h2>
  </div>
  <div class="rn-execution" role="status" aria-live="polite" aria-atomic="true">
    <h3 data-rn="execution_label">Execution status</h3>
    <p class="rn-execution-headline" data-rn="execution_headline">Checking what is happening…</p>
    <p class="rn-execution-reason" data-rn="execution_reason">Waiting for the latest execution report.</p>
    <p class="rn-next"><strong>Next:</strong> <span data-rn="execution_next">Wait for the status check.</span></p>
    <p class="rn-task" data-rn="execution_task" hidden></p>
  </div>
  <div class="rn-body rn-no-image" data-rn="body">
    <div>
      <div class="rn-health-header">
        <h3>Motor health and camera</h3>
        <span class="rn-badge"><span class="rn-dot" aria-hidden="true"></span><span data-rn="badge">Checking</span></span>
      </div>
      <div role="status" aria-live="polite" aria-atomic="true">
        <p class="rn-summary" data-rn="headline">Checking the latest robot state…</p>
        <p class="rn-detail" data-rn="detail">Waiting for the cached status feed.</p>
      </div>
      <dl class="rn-metrics">
        <div class="rn-metric"><dt>State</dt><dd data-rn="activity">Unknown</dd></div>
        <div class="rn-metric"><dt>Motors responding</dt><dd data-rn="motors">Unknown</dd></div>
        <div class="rn-metric"><dt>Warmest motor</dt><dd data-rn="temperature">Unknown</dd></div>
        <div class="rn-metric"><dt>Camera</dt><dd data-rn="camera">Checking</dd></div>
        <div class="rn-metric"><dt>Last check</dt><dd class="rn-check" data-rn="checked">Not yet checked</dd></div>
      </dl>
      <p class="rn-issue" data-rn="issue" hidden></p>
    </div>
    <figure class="rn-photo" data-rn="photo" hidden>
      <img data-rn="image" alt="Latest robot camera image" decoding="async">
      <figcaption data-rn="caption">Latest camera image</figcaption>
    </figure>
  </div>
  <details class="rn-readiness" data-rn="readiness_box">
    <summary data-rn="readiness">Readiness checks</summary>
    <ul class="rn-reasons" data-rn="reasons" hidden></ul>
  </details>
  <p class="rn-queue" data-rn="queue">Checking saved plans…</p>
  <p class="rn-refresh" data-rn="refresh">Status refreshes every 5 seconds.</p>
  <noscript><p class="rn-detail">Enable JavaScript to view the latest robot status. Physical tests use the serialized guarded runner.</p></noscript>
</section>
<script>
(() => {
  'use strict';
  const panel = document.getElementById('robot-now');
  if (!panel) return;
  const nodes = {};
  panel.querySelectorAll('[data-rn]').forEach(node => { nodes[node.dataset.rn] = node; });
  const text = (name, value) => {
    const next = String(value);
    if (nodes[name].textContent !== next) nodes[name].textContent = next;
  };
  const phrase = (value, fallback) => typeof value === 'string' && value.trim() ? value : fallback;
  const number = value => typeof value === 'number' && Number.isFinite(value) ? value : null;
  const count = value => Number.isInteger(value) && value >= 0 ? value : null;
  const timeLabel = value => {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date.toLocaleTimeString([], {hour:'numeric',minute:'2-digit',second:'2-digit'});
  };
  const ageLabel = value => {
    const seconds = number(value);
    if (seconds === null || seconds < 0) return '';
    if (seconds < 2) return 'just now';
    if (seconds < 60) return Math.floor(seconds) + ' seconds ago';
    return Math.floor(seconds / 60) + ' minutes ago';
  };
  const labels = {healthy:'Motors normal',checking:'Checking',needs_attention:'Needs attention',unknown:'Unknown',offline:'Offline'};
  let stopped = false;
  let polling = false;
  let pollTimer = null;
  let controller = null;
  let frameRequest = null;
  let frameTimeout = null;
  let frameSequence = 0;
  let lastFrameAttempt = 0;
  let readinessAutoOpen = null;

  function executionUnknown(reason, nextAction) {
    panel.dataset.execution = 'unknown';
    text('execution_label', 'Execution status');
    text('execution_headline', 'Current execution status is unknown');
    text('execution_reason', reason);
    text('execution_next', nextAction);
    text('execution_task', '');
    nodes.execution_task.hidden = true;
  }

  function renderExecution(execution, confirmedIdle) {
    if (!execution || typeof execution !== 'object') {
      executionUnknown('No current execution report is available.', 'Check the current task or controller for its next step.');
      return;
    }
    const report = execution.report && typeof execution.report === 'object' ? execution.report : {};
    const state = ['running','preparing','idle','blocked'].includes(execution.state) ? execution.state : 'unknown';
    if (execution.stale === true || (report.stale === true && state !== 'running')) {
      executionUnknown('The execution report is stale, so the current task cannot be confirmed.', 'Wait for a fresh execution report from the task or controller.');
      return;
    }
    panel.dataset.execution = state;
    const label = state === 'running' ? 'What the robot is doing'
      : state === 'preparing' ? 'Control work'
      : confirmedIdle && (state === 'idle' || state === 'blocked') ? 'Why the robot is idle'
      : state === 'blocked' ? 'Control work' : 'Execution status';
    text('execution_label', label);
    text('execution_headline', phrase(execution.headline, state === 'unknown' ? 'Current execution status is unknown' : 'Execution update received'));
    text('execution_reason', phrase(execution.reason, 'No reason has been reported yet.'));
    text('execution_next', phrase(execution.next_action, 'Check the current task or controller for its next step.'));
    const metadata = [];
    if (report.stale !== true && typeof report.task_name === 'string' && report.task_name.trim()) metadata.push('Task: ' + report.task_name);
    const updated = report.stale !== true && typeof report.updated_at === 'string' ? timeLabel(report.updated_at) : null;
    if (updated) metadata.push('Updated ' + updated);
    text('execution_task', metadata.join(' · '));
    nodes.execution_task.hidden = metadata.length === 0;
  }

  function expandReadiness(shouldOpen) {
    if (readinessAutoOpen !== shouldOpen) nodes.readiness_box.open = shouldOpen;
    readinessAutoOpen = shouldOpen;
  }

  function hideFrame() {
    frameSequence += 1;
    clearTimeout(frameTimeout);
    if (frameRequest) {
      frameRequest.onload = null;
      frameRequest.onerror = null;
      frameRequest.removeAttribute('src');
      frameRequest = null;
    }
    nodes.photo.hidden = true;
    nodes.body.classList.add('rn-no-image');
    nodes.image.removeAttribute('src');
    lastFrameAttempt = 0;
  }

  function refreshFrame(camera) {
    if (camera.available !== true || camera.fresh !== true) {
      hideFrame();
      return;
    }
    if (frameRequest || Date.now() - lastFrameAttempt < 10000) return;
    lastFrameAttempt = Date.now();
    const sequence = ++frameSequence;
    const pending = new Image();
    frameRequest = pending;
    pending.alt = 'Latest robot camera image';
    pending.decoding = 'async';
    pending.dataset.rn = 'image';
    pending.onload = () => {
      if (sequence !== frameSequence || stopped) return;
      clearTimeout(frameTimeout);
      frameRequest = null;
      pending.onload = null;
      pending.onerror = null;
      nodes.image.replaceWith(pending);
      nodes.image = pending;
      nodes.photo.hidden = false;
      nodes.body.classList.remove('rn-no-image');
      const age = ageLabel(camera.age_seconds);
      text('caption', 'Robot camera' + (age ? ' · ' + age : ''));
    };
    pending.onerror = () => {
      if (sequence !== frameSequence || stopped) return;
      clearTimeout(frameTimeout);
      frameRequest = null;
      pending.onload = null;
      pending.onerror = null;
      pending.removeAttribute('src');
      nodes.photo.hidden = true;
      nodes.body.classList.add('rn-no-image');
      nodes.image.removeAttribute('src');
      text('camera', 'Image unavailable');
      nodes.camera.removeAttribute('data-tone');
    };
    frameTimeout = setTimeout(() => pending.onerror && pending.onerror(), 8000);
    pending.src = '/api/robot-status/frame?refresh=' + Date.now();
  }

  function clearMetrics() {
    ['activity','motors','temperature','camera'].forEach(name => {
      text(name, 'Unknown');
      nodes[name].removeAttribute('data-tone');
    });
    nodes.issue.hidden = true;
    text('issue', '');
  }

  function showReasons(reasons) {
    nodes.reasons.replaceChildren();
    const valid = Array.isArray(reasons) ? reasons.filter(item => typeof item === 'string' && item.trim()) : [];
    valid.forEach(reason => {
      const item = document.createElement('li');
      item.textContent = reason;
      nodes.reasons.appendChild(item);
    });
    nodes.reasons.hidden = valid.length === 0;
  }

  function render(data) {
    if (!data || typeof data !== 'object' || !data.health || !data.robot || !data.camera || !data.readiness || !data.queue) {
      throw new Error('Incomplete status response');
    }
    const health = data.health;
    const robot = data.robot;
    const camera = data.camera;
    renderExecution(data.execution, health.fresh === true && robot.busy === false);
    const fresh = health.fresh === true;
    let state = Object.hasOwn(labels, health.state) ? health.state : 'unknown';
    if (!fresh && state === 'healthy') state = 'unknown';
    panel.dataset.health = state;
    text('badge', labels[state]);
    text('headline', phrase(health.headline, fresh ? 'Robot status received' : 'Fresh robot status is unavailable'));
    const age = ageLabel(health.age_seconds);
    const detail = phrase(health.detail, fresh ? 'Showing the latest reported state.' : 'Wait for fresh telemetry before assessing the robot.');
    text('detail', detail + (age ? ' Last telemetry: ' + age + '.' : ''));
    clearMetrics();
    if (fresh) {
      text('activity', phrase(robot.headline, phrase(robot.activity, 'Unknown').replaceAll('_', ' ')));
      const live = count(health.live_motors);
      const expected = count(health.expected_motors);
      if (live !== null) {
        text('motors', live + ' / ' + (expected === null ? 18 : expected));
        if (state === 'healthy') nodes.motors.dataset.tone = 'good';
        else if (expected !== null && live < expected) nodes.motors.dataset.tone = 'warn';
      }
      const temperature = number(health.max_temperature_c);
      if (temperature !== null) text('temperature', temperature.toLocaleString([], {maximumFractionDigits:1}) + ' °C');
      if (typeof robot.last_issue === 'string' && robot.last_issue.trim()) {
        text('issue', 'Last reported issue: ' + robot.last_issue);
        nodes.issue.hidden = false;
      }
    }
    text('camera', phrase(camera.headline, camera.available === true ? (camera.fresh === true ? 'Available' : 'Stale image') : 'Unavailable'));
    const checked = typeof data.observed_at === 'string' ? timeLabel(data.observed_at) : null;
    text('checked', checked || 'Time unavailable');
    text('readiness', phrase(data.readiness.headline, 'Live checks are required before a physical test'));
    showReasons(data.readiness.reasons);
    expandReadiness(state === 'needs_attention' || state === 'offline' || panel.dataset.execution === 'unknown' || !(data.execution && data.execution.report));
    const waiting = count(data.queue.waiting);
    const recorded = count(data.queue.recorded_software_requirements);
    const legacyRecorded = count(data.queue.software_blocked);
    const queue = [];
    if (waiting !== null) queue.push(waiting + (waiting === 1 ? ' saved plan waiting' : ' saved plans waiting'));
    const recordedCount = recorded !== null ? recorded : legacyRecorded;
    if (recordedCount !== null && recordedCount > 0) queue.push(recordedCount + (recordedCount === 1 ? ' plan with recorded software requirements to revalidate' : ' plans with recorded software requirements to revalidate'));
    text('queue', queue.length ? queue.join(' · ') : 'Queue status unavailable');
    text('refresh', 'Status refreshes every 5 seconds. Camera images refresh every 10 seconds.');
    refreshFrame(camera);
  }

  function failed() {
    executionUnknown('The status check failed. No current running or idle state can be confirmed.', 'Wait for the automatic retry, or check the current task directly.');
    panel.dataset.health = 'unknown';
    text('badge', 'Unknown');
    text('headline', 'Robot status is temporarily unavailable');
    text('detail', 'The last check failed. The robot’s current condition has not been verified.');
    clearMetrics();
    text('checked', 'Failed at ' + timeLabel(Date.now()));
    text('readiness', 'Wait for a fresh status check');
    showReasons(['Wait for a fresh camera frame and telemetry before a physical test.']);
    expandReadiness(true);
    text('queue', 'Queue status unavailable');
    text('refresh', 'Retrying automatically.');
    hideFrame();
  }

  async function poll() {
    if (stopped || polling) return;
    polling = true;
    const startedAt = Date.now();
    let didFail = false;
    controller = new AbortController();
    const timeout = setTimeout(() => controller && controller.abort(), 8000);
    try {
      const response = await fetch('/api/robot-status', {
        cache:'no-store', credentials:'same-origin', signal:controller.signal,
        headers:{Accept:'application/json'}
      });
      if (!response.ok) throw new Error('Status request failed');
      const data = await response.json();
      if (!stopped) render(data);
    } catch (_error) {
      if (!stopped) {
        didFail = true;
        failed();
      }
    } finally {
      clearTimeout(timeout);
      controller = null;
      polling = false;
      if (!stopped) {
        const nextDelay = Math.max(0, 5000 - (Date.now() - startedAt));
        if (didFail) text('refresh', 'Next check at ' + timeLabel(Date.now() + nextDelay) + '. Retrying automatically.');
        pollTimer = setTimeout(poll, nextDelay);
      }
    }
  }

  window.addEventListener('pagehide', () => {
    stopped = true;
    clearTimeout(pollTimer);
    if (controller) controller.abort();
    hideFrame();
  });
  window.addEventListener('pageshow', event => {
    if (event.persisted) {
      stopped = false;
      clearMetrics();
      panel.dataset.health = 'unknown';
      text('badge', 'Checking');
      text('headline', 'Checking the latest robot state…');
      executionUnknown('Checking the latest execution report after returning to this page.', 'Wait for the status check.');
      poll();
    }
  });
  poll();
})();
</script>
"""
