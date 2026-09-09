"""Read-only dashboard panel for the robot's cached state and camera frame."""


def robot_status_panel() -> str:
    return """
<style>
.robot-now{margin:0 0 2.5rem;padding:1.5rem;border:1px solid #35463e;border-radius:18px;background:#141c19;color:#e8f1ec;font:15px/1.5 system-ui,-apple-system,BlinkMacSystemFont,sans-serif}
.robot-now *{box-sizing:border-box}.robot-now h2,.robot-now h3,.robot-now p{margin:0}.robot-now h2{font-size:1.4rem;line-height:1.3;letter-spacing:-.025em}.robot-now h3{font-size:1rem;line-height:1.4}
.robot-now .rn-header{display:flex;align-items:center;justify-content:space-between;gap:1rem;margin-bottom:1rem}.robot-now .rn-badge{display:inline-flex;align-items:center;gap:.45rem;border:1px solid #53665b;border-radius:99px;padding:.25rem .6rem;color:#bac7c0;font-size:.74rem;font-weight:650;white-space:nowrap}.robot-now .rn-dot{width:7px;height:7px;background:currentColor;border-radius:50%;flex:none}
.robot-now .rn-execution{border:1px solid #4b5b4f;border-left:4px solid #93a996;border-radius:12px;padding:1rem 1.15rem;margin-bottom:1.3rem;background:#1a251e}.robot-now .rn-execution h3{font-size:.8rem;letter-spacing:.025em;font-weight:650;color:#bac9bf}.robot-now .rn-execution-headline{font-size:1.2rem;font-weight:700;line-height:1.4;letter-spacing:-.02em;margin-top:.3rem}.robot-now .rn-execution-reason{font-size:.94rem;color:#c7d3cb;line-height:1.55;margin-top:.4rem}.robot-now .rn-next{font-size:.94rem;margin-top:.65rem;line-height:1.5}.robot-now .rn-next strong{color:#e5efe8}.robot-now .rn-task{font-size:.76rem;color:#a7b9ad;margin-top:.6rem;overflow-wrap:anywhere}.robot-now .rn-log{font-size:.85rem;margin-top:.5rem}.robot-now .rn-log a{color:#b7f34a;text-decoration:none;border-bottom:1px solid #4b5b4f}.robot-now[data-execution='blocked'] .rn-execution{border-left-color:#ffd280}.robot-now[data-execution='preparing'] .rn-execution{border-left-color:#8dcaf2}.robot-now[data-execution='running'] .rn-execution{border-left-color:#b7f34a}.robot-now .rn-health-header{display:flex;justify-content:space-between;align-items:center;gap:.8rem;margin-bottom:.65rem}.robot-now .rn-health-header h3{font-size:.8rem;font-weight:650;color:#adbbb3}
.robot-now[data-health='healthy'] .rn-badge{color:#b7f34a;border-color:#526e36}.robot-now[data-health='needs_attention'] .rn-badge{color:#ffd280;border-color:#826b3d}.robot-now[data-health='offline'] .rn-badge{color:#ffb3aa;border-color:#84534e}
.robot-now .rn-body{display:block}.robot-now .rn-summary{font-size:1.05rem;font-weight:650}.robot-now .rn-detail{color:#adbbb3;margin-top:.25rem}.robot-now .rn-metrics{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:.7rem;margin:1.1rem 0 0}.robot-now .rn-metric{min-width:0;border-top:1px solid #35463e;padding-top:.65rem}.robot-now dt{font-size:.74rem;color:#a7b6ac;margin-bottom:.2rem}.robot-now dd{margin:0;font-size:.96rem;font-weight:650;overflow-wrap:anywhere}.robot-now dd[data-tone='good']{color:#b7f34a}.robot-now dd[data-tone='warn']{color:#ffd280}.robot-now .rn-check{font-size:.8rem;font-weight:500}
.robot-now figcaption{color:#a7b6ac;font-size:.75rem;margin-top:.4rem}.robot-now [hidden]{display:none!important}
.robot-now .rn-observation-cameras{margin-top:1.2rem;padding-top:.85rem;border-top:1px solid #35463e}.robot-now .rn-observation-cameras h3{font-size:.8rem;color:#adbbb3;margin-bottom:.65rem}.robot-now .rn-observation-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:1rem}.robot-now .rn-observation-photo{margin:0;min-width:0;max-width:560px}.robot-now .rn-observation-media{aspect-ratio:4/3;border:1px solid #35463e;border-radius:12px;background:#080c0a;overflow:hidden;display:grid;place-items:center}.robot-now .rn-observation-media img{display:block;width:100%;height:100%;min-height:0;object-fit:contain}.robot-now .rn-observation-photo figcaption{display:flex;flex-wrap:wrap;justify-content:space-between;gap:.15rem .6rem;overflow-wrap:anywhere}.robot-now .rn-observation-name{color:#c7d3cb;font-weight:600}
.robot-now .rn-readiness{border-top:1px solid #35463e;margin-top:1.2rem;padding-top:.85rem}.robot-now .rn-readiness summary{cursor:pointer;color:#c0cdc4;font-size:.86rem;font-weight:600}.robot-now .rn-readiness summary:focus-visible{outline:2px solid #b7f34a;outline-offset:4px}.robot-now .rn-reasons{margin:.5rem 0 .7rem;padding-left:1.2rem;color:#b7c4bc;font-size:.85rem;line-height:1.5}.robot-now .rn-reasons li+li{margin-top:.25rem}.robot-now .rn-queue{font-size:.8rem;color:#bac7c0;margin-top:.7rem}.robot-now .rn-issue{margin-top:.55rem;font-size:.85rem;color:#ffd280}.robot-now .rn-refresh{margin-top:.55rem;font-size:.75rem;color:#91a499}
.robot-now .rn-alert{border:1px solid #826b3d;border-left:4px solid #ffd280;border-radius:12px;background:#29251c;padding:1rem;margin-bottom:1rem}.robot-now .rn-alert h3{color:#ffd280}.robot-now .rn-alert p{margin-top:.35rem;color:#e0d5be}.robot-now .rn-alert a{display:inline-block;margin-top:.65rem;color:#e8f1ec;text-decoration:underline;font-weight:650}.robot-now .rn-camera-notice{margin-bottom:.8rem}.robot-now .rn-camera-notice ul{margin-bottom:0}
.robot-now .rn-recovery[data-state='recovered']{border-color:#526e36;background:#1a251e}.robot-now .rn-recovery[data-state='recovered'] h3{color:#b7f34a}.robot-now .rn-recovery .rn-recovery-meta{font-size:.8rem;color:#bac7c0}
@media(max-width:820px){.robot-now .rn-metrics{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:480px){.robot-now{padding:1.1rem}.robot-now .rn-header{align-items:flex-start;gap:.7rem}.robot-now h2{font-size:1.2rem}.robot-now .rn-badge{font-size:.72rem;padding:.28rem .55rem}.robot-now .rn-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.robot-now .rn-metric:last-child{grid-column:1/-1}.robot-now .rn-observation-grid{grid-template-columns:minmax(0,1fr)}}
</style>
<section class="robot-now" id="robot-now" data-health="unknown" data-execution="unknown" aria-labelledby="robot-now-title">
  <div class="rn-header">
    <h2 id="robot-now-title">Robot Lab right now</h2>
  </div>
  <dl class="rn-metrics" style="margin:0 0 1.3rem;grid-template-columns:repeat(auto-fit,minmax(135px,1fr))" aria-label="Lab availability">
    <div class="rn-metric"><dt>Lab connection</dt><dd data-rn="overview_lab">Checking</dd></div>
    <div class="rn-metric"><dt>Physical robot</dt><dd data-rn="overview_robot">Checking</dd></div>
    <div class="rn-metric"><dt>Robot cameras</dt><dd data-rn="overview_cameras">Checking</dd></div>
    <div class="rn-metric"><dt>Experiment report</dt><dd data-rn="overview_execution">Checking</dd></div>
  </dl>
  <div class="rn-alert" data-rn="service_alert" role="status" aria-live="polite" aria-atomic="true" hidden>
    <h3 data-rn="service_headline"></h3>
    <p data-rn="service_detail"></p>
    <a data-rn="sign_in" href="/login?next=%2F" hidden>Sign in to Robot Lab</a>
  </div>
  <div class="rn-alert" data-rn="alert_delivery" role="status" aria-live="polite" aria-atomic="true" hidden>
    <h3 data-rn="alert_headline"></h3>
    <p data-rn="alert_detail"></p>
    <p data-rn="alert_action"></p>
  </div>
  <div class="rn-alert rn-recovery" data-rn="recovery" role="status" aria-live="polite" aria-atomic="true" hidden>
    <h3 data-rn="recovery_headline"></h3>
    <p data-rn="recovery_summary"></p>
    <p data-rn="recovery_detail"></p>
    <p data-rn="recovery_action"></p>
    <p class="rn-recovery-meta" data-rn="recovery_meta"></p>
  </div>
  <div class="rn-execution" role="status" aria-live="polite" aria-atomic="true">
    <h3 data-rn="execution_label">Execution status</h3>
    <p class="rn-execution-headline" data-rn="execution_headline">Checking what is happening…</p>
    <p class="rn-execution-reason" data-rn="execution_reason">Waiting for the latest execution report.</p>
    <p class="rn-next"><strong>Next:</strong> <span data-rn="execution_next">Wait for the status check.</span></p>
    <p class="rn-task" data-rn="execution_task" hidden></p>
    <p class="rn-log" data-rn="execution_log_wrap" hidden><a data-rn="execution_log" href="#">Open the live agent log &rarr;</a></p>
  </div>
  <div class="rn-body" data-rn="body">
    <div>
      <div class="rn-health-header">
        <h3>Motor health</h3>
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
        <div class="rn-metric"><dt>Vision camera</dt><dd data-rn="camera">Checking</dd></div>
        <div class="rn-metric"><dt>Last check</dt><dd class="rn-check" data-rn="checked">Not yet checked</dd></div>
      </dl>
      <p class="rn-issue" data-rn="issue" hidden></p>
    </div>
  </div>
  <section class="rn-observation-cameras" data-rn="observation_cameras" aria-labelledby="robot-observation-title" hidden>
    <h3 id="robot-observation-title">Live cameras</h3>
    <div class="rn-alert rn-camera-notice" data-rn="camera_notice" role="status" aria-live="polite" hidden>
      <h3 data-rn="camera_headline"></h3>
      <ul class="rn-reasons" data-rn="camera_reasons"></ul>
    </div>
    <div class="rn-observation-grid" data-rn="observation_grid"></div>
  </section>
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
  let readinessAutoOpen = null;
  let registeredCameras = [];
  let lastSuccessfulCheck = null;
  let alertDeliveryBlocked = false;
  const observationFrames = new Map();

  function observationFramePath(camera) {
    if (typeof camera.id !== 'string' || !/^[a-zA-Z0-9_-]+$/.test(camera.id)) return null;
    if (camera.frame_url === '/api/robot-status/frame') return camera.frame_url;
    const path = '/api/robot-status/cameras/' + camera.id + '/frame';
    return camera.frame_url === path ? path : null;
  }

  function cameraProblem(camera) {
    const frame = observationFrames.get(camera.id);
    if (camera.available === true && camera.fresh === true) {
      if (frame && frame.failed) return frame.failed;
      return null;
    }
    if (camera.status === 'paused') return 'Preview capture is paused while a robot recording or hardware task owns the cameras. It resumes when the task releases them.';
    if (camera.status === 'in_use') return 'The camera is in use by another application. Release that camera to restore its preview.';
    if (camera.issue_code === 'macos_privacy_fd_exhaustion') return 'The lab Mac’s privacy service has run out of file handles and cannot authorize camera access. Restart the failed privacy service, then restart Robot Lab while the robot is idle. Saved camera permissions may still be intact.';
    if (camera.permission_status === 'restricted') return 'macOS restricts camera access. Check the lab Mac’s camera privacy restrictions.';
    if (camera.permission_status === 'denied') return 'macOS denied camera access to the capture service. On the lab Mac, open System Settings → Privacy & Security → Camera and allow the capture app, then restart the camera service.';
    if (camera.permission_status === 'not_determined') return 'Camera permission has not been granted. Open the capture app on the lab Mac and allow its camera prompt.';
    if (camera.status === 'stale') return 'The last camera frame is too old to show. Check the capture service if fresh frames do not return.';
    if (camera.status === 'connecting') return 'The capture service is connecting to the camera.';
    if (camera.status === 'stopped') return 'Camera capture is stopped. Start the camera service to restore its preview.';
    if (camera.issue_code === 'vision_service_unavailable') return 'The lab Mac’s vision service is unreachable. Check or restart that service.';
    const error = typeof camera.error === 'string' ? camera.error.toLowerCase() : '';
    if (error.includes('disconnected') || error.includes('unavailable or ambiguous')) return 'The configured camera is disconnected or cannot be identified. Check its cable or wireless connection on the lab Mac.';
    if (error.includes('no useful detail') || error.includes('covered')) return 'The camera view is covered or has no useful detail. Check the camera’s view.';
    return 'No fresh frames are arriving. Check the camera connection and capture service on the lab Mac.';
  }

  function updateCameraVisibility() {
    const visibleFrames = Array.from(observationFrames.values()).filter(state => !state.figure.hidden).length;
    const problems = new Map();
    registeredCameras.forEach(camera => {
      const problem = cameraProblem(camera);
      if (!problem) return;
      if (!problems.has(problem)) problems.set(problem, []);
      problems.get(problem).push(phrase(camera.name, phrase(camera.id, 'Camera')));
    });
    nodes.camera_reasons.replaceChildren();
    problems.forEach((names, problem) => {
      const item = document.createElement('li');
      item.textContent = names.join(', ') + ': ' + problem;
      nodes.camera_reasons.appendChild(item);
    });
    text('camera_headline', visibleFrames ? 'Some camera views are unavailable' : 'No live camera view is available');
    nodes.camera_notice.hidden = problems.size === 0;
    nodes.observation_cameras.hidden = !visibleFrames && !problems.size;
  }

  function clearObservationFrame(state, resetAttempt = true) {
    state.sequence += 1;
    clearTimeout(state.timeout);
    if (state.request) state.request.abort();
    state.request = null;
    if (state.pending) {
      state.pending.onload = null;
      state.pending.onerror = null;
      state.pending.removeAttribute('src');
      state.pending = null;
    }
    state.image.removeAttribute('src');
    state.image.hidden = true;
    if (state.imageUrl) URL.revokeObjectURL(state.imageUrl);
    if (state.pendingUrl) URL.revokeObjectURL(state.pendingUrl);
    state.imageUrl = null;
    state.imageCapturedAt = null;
    state.pendingUrl = null;
    state.figure.hidden = true;
    state.status.textContent = '';
    if (resetAttempt) state.lastAttempt = 0;
    updateCameraVisibility();
  }

  function clearObservationFrames() {
    registeredCameras = [];
    observationFrames.forEach(state => clearObservationFrame(state));
    updateCameraVisibility();
  }

  function createObservationFrame() {
    const figure = document.createElement('figure');
    figure.className = 'rn-observation-photo';
    figure.hidden = true;
    const media = document.createElement('div');
    media.className = 'rn-observation-media';
    const image = document.createElement('img');
    image.hidden = true;
    image.decoding = 'async';
    const caption = document.createElement('figcaption');
    const name = document.createElement('span');
    name.className = 'rn-observation-name';
    const status = document.createElement('span');
    media.append(image);
    caption.append(name, status);
    figure.append(media, caption);
    nodes.observation_grid.appendChild(figure);
    return {figure, image, name, status, sequence:0, request:null, pending:null, timeout:null, imageUrl:null, imageCapturedAt:null, pendingUrl:null, lastAttempt:0, failed:null};
  }

  function observationImageLabel(state) {
    return 'Snapshot · ' + ageLabel(Math.max(0, (Date.now() - state.imageCapturedAt) / 1000));
  }

  async function refreshObservationFrame(state, camera, path) {
    if (state.imageUrl) state.status.textContent = observationImageLabel(state);
    if (state.request || Date.now() - state.lastAttempt < 10000) return;
    state.lastAttempt = Date.now();
    const imageCapturedAt = state.lastAttempt - Math.max(0, number(camera.age_seconds) || 0) * 1000;
    const sequence = ++state.sequence;
    const request = new AbortController();
    state.request = request;
    const failedFrame = (reason = 'The camera image could not be loaded. Retrying automatically.') => {
      if (sequence !== state.sequence || stopped) return;
      state.failed = typeof reason === 'string' ? reason : 'The camera image could not be loaded. Retrying automatically.';
      clearObservationFrame(state, false);
    };
    state.timeout = setTimeout(failedFrame, 8000);
    try {
      const response = await fetch(path + '?refresh=' + Date.now(), {
        cache:'no-store', credentials:'same-origin', mode:'same-origin', redirect:'error', signal:request.signal,
        headers:{Accept:'image/jpeg'}
      });
      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          failed({status:response.status});
          return;
        }
        failedFrame(response.status >= 500 ? 'The camera service could not deliver this image. Retrying automatically.' : undefined);
        return;
      }
      const blob = await response.blob();
      if (sequence !== state.sequence || stopped) return;
      const pending = new Image();
      state.pending = pending;
      const imageUrl = URL.createObjectURL(blob);
      state.pendingUrl = imageUrl;
      pending.alt = state.name.textContent + ' camera image';
      pending.decoding = 'async';
      pending.onload = () => {
        if (sequence !== state.sequence || stopped) return;
        clearTimeout(state.timeout);
        state.request = null;
        state.pending = null;
        state.pendingUrl = null;
        pending.onload = null;
        pending.onerror = null;
        state.image.replaceWith(pending);
        state.image = pending;
        if (state.imageUrl) URL.revokeObjectURL(state.imageUrl);
        state.imageUrl = imageUrl;
        state.imageCapturedAt = imageCapturedAt;
        state.failed = null;
        state.figure.hidden = false;
        state.status.textContent = observationImageLabel(state);
        updateCameraVisibility();
      };
      pending.onerror = failedFrame;
      pending.src = imageUrl;
    } catch (_error) {
      failedFrame();
    }
  }

  function renderObservationCameras(cameras) {
    const current = new Set();
    registeredCameras = Array.isArray(cameras) ? cameras.filter(camera => camera && typeof camera === 'object') : [];
    registeredCameras.forEach(camera => {
      if (camera.available !== true || camera.fresh !== true) return;
      const path = observationFramePath(camera);
      if (!path || current.has(camera.id)) return;
      current.add(camera.id);
      let state = observationFrames.get(camera.id);
      if (!state) {
        state = createObservationFrame();
        observationFrames.set(camera.id, state);
      }
      state.name.textContent = phrase(camera.name, camera.id);
      refreshObservationFrame(state, camera, path);
    });
    observationFrames.forEach((state, id) => {
      if (current.has(id)) return;
      clearObservationFrame(state);
      state.figure.remove();
      observationFrames.delete(id);
    });
    updateCameraVisibility();
  }

  function executionUnknown(reason, nextAction) {
    panel.dataset.execution = 'unknown';
    text('execution_label', 'Execution status');
    text('execution_headline', 'Current execution status is unknown');
    text('execution_reason', reason);
    text('execution_next', nextAction);
    text('execution_task', '');
    nodes.execution_task.hidden = true;
    nodes.execution_log_wrap.hidden = true;
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
    // The report names the experiment it is working on, so link to it rather
    // than leaving the operator to find the run by hand.
    const runId = typeof report.experiment_id === 'string' ? report.experiment_id.trim() : '';
    if (runId && report.stale !== true) {
      nodes.execution_log.href = '/experiments/' + encodeURIComponent(runId);
      nodes.execution_log_wrap.hidden = false;
    } else {
      nodes.execution_log_wrap.hidden = true;
    }
  }

  function expandReadiness(shouldOpen) {
    if (readinessAutoOpen !== shouldOpen) nodes.readiness_box.open = shouldOpen;
    readinessAutoOpen = shouldOpen;
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

  function serviceAlert(headline, detail, signIn = false) {
    text('service_headline', headline);
    text('service_detail', detail);
    nodes.sign_in.hidden = !signIn;
    if (signIn) nodes.sign_in.href = '/login?next=' + encodeURIComponent(window.location.pathname + window.location.search);
    nodes.service_alert.hidden = false;
  }

  function renderAlertDelivery(alerts) {
    alerts = alerts && typeof alerts === 'object' ? alerts : {};
    alertDeliveryBlocked = alerts.status === 'blocked';
    nodes.alert_delivery.hidden = alerts.status === 'ok';
    text('alert_headline', phrase(alerts.headline, 'iMessage alerts have not been verified'));
    text('alert_detail', phrase(alerts.detail, 'The alert monitor’s current status is unavailable.'));
    text('alert_action', phrase(alerts.action, ''));
    nodes.alert_action.hidden = !nodes.alert_action.textContent;
  }

  function renderRecovery(recovery) {
    if (!recovery || typeof recovery !== 'object') {
      nodes.recovery.hidden = true;
      return;
    }
    const state = ['waiting','attempting','verifying','recovered','needs_attention'].includes(recovery.status) ? recovery.status : 'unknown';
    nodes.recovery.hidden = state === 'waiting' && recovery.issue_code === 'none' && !['disabled','hardware_active_or_unobserved'].includes(recovery.reason_code);
    nodes.recovery.dataset.state = state;
    text('recovery_headline', phrase(recovery.headline, 'Automatic recovery status is unavailable'));
    text('recovery_summary', phrase(recovery.summary, ''));
    nodes.recovery_summary.hidden = !nodes.recovery_summary.textContent;
    text('recovery_detail', phrase(recovery.detail, 'Current repair activity cannot be confirmed.'));
    const action = phrase(recovery.action, '');
    const prefix = state === 'attempting' ? 'Repair: ' : state === 'waiting' ? 'Planned repair: ' : state === 'verifying' || state === 'recovered' ? 'Repair attempted: ' : 'Next: ';
    text('recovery_action', action ? prefix + action : '');
    nodes.recovery_action.hidden = !action;
    const attempts = count(recovery.attempts);
    const metadata = [];
    if (attempts !== null && attempts > 0) metadata.push(attempts + (attempts === 1 ? ' repair attempt' : ' repair attempts'));
    const attempted = typeof recovery.last_attempt_at === 'string' ? timeLabel(recovery.last_attempt_at) : null;
    const verified = state === 'recovered' && typeof recovery.verified_at === 'string' ? timeLabel(recovery.verified_at) : null;
    if (verified) metadata.push('Verified at ' + verified);
    else if (attempted) metadata.push('Last attempt at ' + attempted);
    text('recovery_meta', metadata.join(' · '));
    nodes.recovery_meta.hidden = !metadata.length;
  }

  function render(data) {
    if (!data || typeof data !== 'object' || !data.health || !data.robot || !data.camera || !data.readiness || !data.queue) {
      throw new Error('Incomplete status response');
    }
    const health = data.health;
    const robot = data.robot;
    const camera = data.camera;
    text('overview_lab', 'Online · live status received');
    text('overview_robot', health.fresh !== true ? (health.state === 'offline' ? 'Unreachable' : 'Telemetry unavailable') :
      robot.armed === false && robot.busy === false ? 'Stopped · motor power off' :
      robot.busy === true ? 'Running' : robot.armed === true ? 'Stopped · motor power on' : 'Connected');
    const overviewCameras = (Array.isArray(data.cameras) ? data.cameras : data.observation_cameras || [])
      .filter(item => typeof item.id === 'string' && item.id.startsWith('robot-'));
    const liveCameras = overviewCameras.filter(item => item.fresh === true).length;
    text('overview_cameras', overviewCameras.length ? (
      overviewCameras.every(item => item.status === 'paused') ? 'Reserved by a hardware task' :
      liveCameras + ' / ' + overviewCameras.length + ' live' + (liveCameras < overviewCameras.length ? ' · see issue below' : '')
    ) : 'Status unavailable');
    const executionReport = data.execution && data.execution.report;
    text('overview_execution', executionReport && executionReport.stale === true ? 'Stale · activity unconfirmed' :
      data.execution && data.execution.state !== 'unknown' ? phrase(data.execution.headline, 'Activity unconfirmed') : 'Activity unconfirmed');
    renderAlertDelivery(data.alerts);
    renderRecovery(data.recovery);
    lastSuccessfulCheck = Date.now();
    nodes.service_alert.hidden = true;
    nodes.sign_in.hidden = true;
    if (health.state === 'offline') serviceAlert(phrase(health.headline, 'Robot controller unreachable'), phrase(health.detail, 'Robot Lab is online, but cannot reach the robot controller. Check its power, network connection, and web service.'));
    else if (health.issue_code === 'telemetry_stale') serviceAlert('Robot telemetry is stale', 'Robot Lab can answer, but current motor readings are missing. Check the robot controller’s telemetry service.');
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
    renderObservationCameras(Array.isArray(data.cameras) ? data.cameras : [
      {...camera, id:camera.id || 'robot', name:camera.name || 'Robot camera', frame_url:'/api/robot-status/frame'},
      ...(Array.isArray(data.observation_cameras) ? data.observation_cameras : [])
    ]);
  }

  function failed(error = {}) {
    const auth = error.status === 401 || error.status === 403;
    text('overview_lab', auth ? 'Sign-in needed' : 'Connection failed');
    text('overview_robot', 'Current state unknown');
    text('overview_cameras', 'Current views unavailable');
    text('overview_execution', 'Activity unconfirmed');
    let headline, detail;
    if (error.status === 401) {
      headline = 'Your Robot Lab sign-in has expired';
      detail = 'Sign in again to load live status and camera views. The robot’s current state has not been checked.';
    } else if (error.status === 403) {
      headline = 'This account cannot read Robot Lab status';
      detail = 'Sign in with an account that has permission to view Robot Lab.';
    } else if (error.status >= 500) {
      headline = 'Robot Lab service is unavailable';
      detail = 'The website returned HTTP ' + error.status + '. Check the lab service and the connection from the lab Mac to this website.';
    } else if (error.name === 'AbortError') {
      headline = 'Robot Lab is not responding';
      detail = 'The status request timed out after 8 seconds. Check the lab Mac, its network connection, and the lab service.';
    } else if (error.status || error.kind === 'invalid_response') {
      headline = 'Robot Lab status feed returned an error';
      detail = error.status ? 'The status feed returned HTTP ' + error.status + '. Check the lab service logs.' : 'The status feed returned an unreadable or incomplete response. Check the lab service logs.';
    } else {
      headline = 'This browser cannot reach Robot Lab';
      detail = 'Check this device’s connection. The lab Mac, website relay, or network connection may also be offline.';
    }
    serviceAlert(headline, detail + (lastSuccessfulCheck ? ' Last successful status check: ' + timeLabel(lastSuccessfulCheck) + '.' : ''), auth);
    renderRecovery({status:'unknown', headline:'Automatic recovery status is unknown',
      detail:'This page cannot confirm repair activity while the status feed is unavailable.'});
    if (!alertDeliveryBlocked) renderAlertDelivery({
      headline:'iMessage alert status is unknown',
      detail:'This page cannot verify outage notifications while the status feed is unavailable.'
    });
    executionUnknown('Current execution cannot be confirmed until the status feed is available.', auth ? 'Sign in to restore live status.' : 'Check the reported connection issue; this page retries automatically.');
    panel.dataset.health = 'unknown';
    text('badge', auth ? 'Sign-in needed' : 'Unknown');
    text('headline', auth ? 'Sign in to load current robot status' : 'Current robot health is unknown');
    text('detail', 'Fresh motor readings are unavailable while the status feed cannot be read.');
    clearMetrics();
    text('checked', 'Failed at ' + timeLabel(Date.now()));
    text('readiness', 'Wait for a fresh status check');
    showReasons(['Wait for a fresh camera frame and telemetry before a physical test.']);
    expandReadiness(true);
    text('queue', 'Queue status unavailable');
    text('refresh', 'Retrying automatically.');
    clearObservationFrames();
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
      if (!response.ok) throw Object.assign(new Error('Status request failed'), {status:response.status});
      try {
        const data = await response.json();
        if (!stopped) render(data);
      } catch (error) {
        error.kind = 'invalid_response';
        throw error;
      }
    } catch (error) {
      if (!stopped) {
        didFail = true;
        failed(error);
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
    clearObservationFrames();
  });
  window.addEventListener('pageshow', event => {
    if (event.persisted) {
      stopped = false;
      ['overview_lab', 'overview_robot', 'overview_cameras', 'overview_execution'].forEach(name => text(name, 'Checking'));
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
