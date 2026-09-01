import { useEffect, useMemo, useState } from 'react'
import type {
  CalibrationJoint,
  CalibrationReport,
  Detection,
  FootTip,
  JointState,
  VisionState,
} from './types'

const POLL_MS = 350

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    cache: 'no-store',
    headers: {'Content-Type': 'application/json'},
    ...init,
  })
  const body = await response.json()
  if (!response.ok) throw new Error(body.error || `${response.status} ${response.statusText}`)
  return body as T
}

function formatAngle(value: number | null | undefined, digits = 1) {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—'
  return `${value >= 0 ? '+' : ''}${value.toFixed(digits)}°`
}

function classForVerdict(verdict?: string) {
  return verdict === 'safe' ? 'good' : verdict === 'unsafe' ? 'bad' : 'warn'
}

function CoveragePill({label, value, total}: {label: string; value: number; total: number}) {
  const complete = value >= total
  return (
    <div className={`coverage-pill ${complete ? 'complete' : ''}`}>
      <span>{label}</span>
      <b>{value}/{total}</b>
    </div>
  )
}

function VideoOverlay({
  state,
  showTags,
  showFeet,
  showLabels,
}: {
  state: VisionState
  showTags: boolean
  showFeet: boolean
  showLabels: boolean
}) {
  const size = state.pose.image_size_px
  if (!size) return null
  const [width, height] = size
  return (
    <svg
      className="vision-overlay"
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="xMidYMid meet"
      aria-hidden="true"
    >
      {showTags && state.pose.tags.map((tag: Detection) => {
        const points = tag.corners_px.map((point) => point.join(',')).join(' ')
        const inferred = tag.source !== 'detected'
        return (
          <g key={tag.tag_id} className={inferred ? 'tag inferred' : 'tag'}>
            <polygon points={points} />
            <circle cx={tag.center_px[0]} cy={tag.center_px[1]} r={6} />
            {showLabels && (
              <g className="marker-label">
                <rect x={tag.center_px[0] + 9} y={tag.center_px[1] - 18} width={42} height={28} rx={7} />
                <text x={tag.center_px[0] + 30} y={tag.center_px[1] + 2}>#{tag.tag_id}</text>
              </g>
            )}
          </g>
        )
      })}
      {showFeet && state.pose.feet.map((foot: FootTip) => {
        const inferred = foot.source !== 'color'
        return (
          <g key={foot.leg} className={inferred ? 'foot inferred' : 'foot'}>
            <circle cx={foot.point_px[0]} cy={foot.point_px[1]} r={13} />
            <line x1={foot.point_px[0] - 19} y1={foot.point_px[1]} x2={foot.point_px[0] + 19} y2={foot.point_px[1]} />
            <line x1={foot.point_px[0]} y1={foot.point_px[1] - 19} x2={foot.point_px[0]} y2={foot.point_px[1] + 19} />
            {showLabels && <text x={foot.point_px[0] + 20} y={foot.point_px[1] - 14}>L{foot.leg}</text>}
          </g>
        )
      })}
    </svg>
  )
}

function JointCell({joint}: {joint?: JointState}) {
  if (!joint) return <div className="joint-cell missing">not observed</div>
  const kneeVisionUnavailable = joint.joint.endsWith('_knee')
  const delta = kneeVisionUnavailable ? undefined : joint.visual_minus_encoder_deg
  const deltaClass = delta === undefined ? '' : Math.abs(delta) <= 6 ? 'delta-ok' : 'delta-bad'
  return (
    <div className="joint-cell">
      <div className="joint-main">
        <b>{formatAngle(joint.value_deg)}</b>
        <span>{joint.source.replaceAll('_', ' ')}</span>
      </div>
      <div className={`joint-delta ${deltaClass}`}>
        {kneeVisionUnavailable ? 'encoder only · no visual knee' : delta === undefined ? 'no visual comparison' : `vision − encoder ${formatAngle(delta)}`}
      </div>
    </div>
  )
}

function LegMatrix({joints}: {joints: JointState[]}) {
  const byName = useMemo(() => new Map(joints.map((joint) => [joint.joint, joint])), [joints])
  return (
    <section className="panel leg-panel">
      <div className="panel-heading">
        <div>
          <div className="eyebrow">Live pose</div>
          <h2>Six-leg joint check</h2>
        </div>
        <div className="legend"><i /> within 6° <i className="red" /> investigate</div>
      </div>
      <div className="joint-grid">
        <div className="grid-head">Leg</div>
        <div className="grid-head">Yaw</div>
        <div className="grid-head">Hip</div>
        <div className="grid-head">Knee</div>
        {Array.from({length: 6}, (_, leg) => (
          <div className="joint-row" key={leg}>
            <div className="leg-name">L{leg}</div>
            <JointCell joint={byName.get(`L${leg}_yaw`)} />
            <JointCell joint={byName.get(`L${leg}_hip`)} />
            <JointCell joint={byName.get(`L${leg}_knee`)} />
          </div>
        ))}
      </div>
    </section>
  )
}

function ReportTable({
  report,
  busy,
  onApply,
}: {
  report: CalibrationReport
  busy: boolean
  onApply: () => void
}) {
  const signed = report.joints.filter((joint: CalibrationJoint) => joint.signed)
  return (
    <section className="panel report-panel">
      <div className="panel-heading">
        <div>
          <div className="eyebrow">Latest capture</div>
          <h2>Visual calibration report</h2>
        </div>
        <span className={`quality ${report.quality}`}>{report.quality}</span>
      </div>
      <div className="report-summary">
        <b>{report.good_signed_joint_count}/{report.signed_joint_count}</b>
        <span>signed lid joints stable across {report.sample_count} frames</span>
        <a href="/api/vision/calibration/report" download="visual-calibration.json">Download JSON</a>
      </div>
      <div className="report-table">
        {signed.map((joint) => (
          <div className="report-row" key={joint.joint}>
            <b>{joint.joint.replace('_', ' ')}</b>
            <span className={Math.abs(joint.visual_minus_encoder_deg || 0) > 6 ? 'text-bad' : ''}>
              {formatAngle(joint.visual_minus_encoder_deg)}
            </span>
            <small>MAD {formatAngle(joint.median_absolute_deviation_deg, 2)}</small>
          </div>
        ))}
      </div>
      <button
        className="primary full"
        disabled={busy || report.configuration_changed || report.good_signed_joint_count !== 12}
        onClick={onApply}
      >
        {report.configuration_changed ? 'Visual calibration applied' : 'Apply visual calibration'}
      </button>
      <p className="safety-note">Applying changes only the vision bias config. It never moves the robot or changes servo zeros.</p>
    </section>
  )
}

export default function App() {
  const [state, setState] = useState<VisionState | null>(null)
  const [report, setReport] = useState<CalibrationReport | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [cameraInput, setCameraInput] = useState('0')
  const [showTags, setShowTags] = useState(true)
  const [showFeet, setShowFeet] = useState(true)
  const [showLabels, setShowLabels] = useState(true)

  useEffect(() => {
    let cancelled = false
    const refresh = async () => {
      try {
        const next = await api<VisionState>('/api/vision/state')
        if (!cancelled) {
          setState(next)
          setError(null)
        }
      } catch (caught) {
        if (!cancelled) setError(caught instanceof Error ? caught.message : String(caught))
      }
    }
    void refresh()
    const timer = window.setInterval(refresh, POLL_MS)
    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [])

  useEffect(() => {
    if (!state?.calibration.report_available) return
    api<CalibrationReport>('/api/vision/calibration/report').then(setReport).catch(() => undefined)
  }, [state?.calibration.report_available, state?.calibration.status])

  useEffect(() => {
    if (state?.camera.requested_index === undefined) return
    setCameraInput(String(state.camera.requested_index))
  }, [state?.camera.requested_index])

  const switchCamera = async (index: number) => {
    setBusy(true)
    setCameraInput(String(index))
    try {
      await api('/api/vision/camera', {method: 'POST', body: JSON.stringify({index})})
      setError(null)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught))
    } finally {
      setBusy(false)
    }
  }

  const setCameraEnabled = async (enabled: boolean) => {
    setBusy(true)
    try {
      await api(`/api/vision/camera/${enabled ? 'start' : 'stop'}`, {
        method: 'POST',
        body: enabled ? JSON.stringify({index: Number(cameraInput)}) : '{}',
      })
      setError(null)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught))
    } finally {
      setBusy(false)
    }
  }

  const startCalibration = async () => {
    setBusy(true)
    try {
      await api('/api/vision/calibration/start', {method: 'POST', body: '{}'})
      setError(null)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught))
    } finally {
      setBusy(false)
    }
  }

  const cancelCalibration = async () => {
    await api('/api/vision/calibration/cancel', {method: 'POST', body: '{}'})
  }

  const applyCalibration = async () => {
    setBusy(true)
    try {
      await api('/api/vision/calibration/apply', {method: 'POST', body: '{}'})
      const latest = await api<CalibrationReport>('/api/vision/calibration/report')
      setReport(latest)
      setError(null)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught))
    } finally {
      setBusy(false)
    }
  }

  const safety = state?.pose.safety
  const readiness = state?.readiness
  const collecting = state?.calibration.status === 'collecting'
  const safetyReasons = safety?.unsafe_reasons.length
    ? safety.unsafe_reasons
    : safety?.unknown_reasons || []
  const safetyMessage = !state?.camera.enabled
    ? 'Camera is off; pose safety has not been evaluated.'
    : safetyReasons[0] || safety?.warnings[0] || 'No unsafe condition is currently detected.'

  return (
    <main>
      <header className="topbar">
        <div className="brand-lockup">
          <div className="brand-mark">HX</div>
          <div>
            <div className="eyebrow">STS3215 · Vision lab</div>
            <h1>Visual calibration</h1>
          </div>
        </div>
        <div className="top-status">
          <span className="readonly-dot" /> Read-only observation
          <span className="divider" />
          <b>{state?.performance.fps.toFixed(1) || '—'} fps</b>
          <span>{state?.performance.frame_age_ms === null || state?.performance.frame_age_ms === undefined ? '—' : `${state.performance.frame_age_ms.toFixed(0)} ms`}</span>
        </div>
      </header>

      {error && <div className="error-banner"><b>Vision service:</b> {error}</div>}

      <div className="workspace">
        <section className="video-column">
          <div className="video-stage">
            {state?.camera.enabled && <img src="/api/vision/frame.mjpg" alt="Live camera feed of the hexapod" />}
            {state && <VideoOverlay state={state} showTags={showTags} showFeet={showFeet} showLabels={showLabels} />}
            {!state?.camera.enabled ? (
              <div className="video-empty camera-off-prompt">
                <b>Camera is off</b>
                <span>Choose an input, then start the camera when you are ready.</span>
                <button className="primary" disabled={busy} onClick={() => void setCameraEnabled(true)}>Start camera</button>
              </div>
            ) : !state?.ok && <div className="video-empty">Waiting for the first camera frame…</div>}
            <div className="video-badges">
              <span>Camera {state?.camera.active_index ?? '—'}</span>
              <span>{state?.pose.pose_reference || 'no pose'} frame</span>
              <span>preview {state?.performance.image_size_px?.join(' × ') || '—'}</span>
              {state?.camera.native_luma && (
                <span className="native-badge">tags {state.performance.detection_image_size_px?.join(' × ')} luma</span>
              )}
            </div>
          </div>
          <div className="video-toolbar">
            <div className="overlay-options">
              <span>Overlay</span>
              <label><input type="checkbox" checked={showTags} onChange={(event) => setShowTags(event.target.checked)} /> Tags</label>
              <label><input type="checkbox" checked={showFeet} onChange={(event) => setShowFeet(event.target.checked)} /> Feet</label>
              <label><input type="checkbox" checked={showLabels} onChange={(event) => setShowLabels(event.target.checked)} /> IDs</label>
            </div>
            <span className="camera-message">{state?.camera.error || 'Latest-frame streaming: stale frames are dropped.'}</span>
          </div>
          <LegMatrix joints={state?.pose.joints || []} />
          {report && <ReportTable report={report} busy={busy} onApply={() => void applyCalibration()} />}
        </section>

        <aside className="control-column">
          <section className={`panel safety-card ${classForVerdict(safety?.verdict)}`}>
            <div className="eyebrow">Pose safety</div>
            <div className="big-status">{safety?.verdict?.toUpperCase() || 'WAITING'}</div>
            <p>{safetyMessage}</p>
            <div className="safety-metrics">
              <span>IMU tilt <b>{formatAngle(safety?.imu_tilt_deg)}</b></span>
              <span>vision tilt <b>{formatAngle(state?.pose.body_tilt_deg)}</b></span>
              <span>reference <b>{state?.pose.pose_reference || '—'}</b></span>
            </div>
          </section>

          <section className="panel">
            <div className="panel-heading compact">
              <div>
                <div className="eyebrow">Input</div>
                <h2>Camera</h2>
              </div>
              <span className={`camera-state ${state?.camera.status}`}>{state?.camera.status || 'offline'}</span>
            </div>
            <div className="camera-picks">
              {state?.camera.indexes.map((index) => (
                <button
                  key={index}
                  className={state.camera.active_index === index || (!state.camera.enabled && state.camera.requested_index === index) ? 'selected' : ''}
                  disabled={busy}
                  onClick={() => void switchCamera(index)}
                >
                  <b>{index}</b>
                  <span>{index === 1 ? 'iPhone / external' : index === 0 ? 'Built-in / first' : 'Additional'}</span>
                </button>
              ))}
            </div>
            <form className="camera-custom" onSubmit={(event) => {
              event.preventDefault()
              void switchCamera(Number(cameraInput))
            }}>
              <label htmlFor="camera-index">Camera index</label>
              <input id="camera-index" type="number" min="0" max="12" value={cameraInput} onChange={(event) => setCameraInput(event.target.value)} />
              <button disabled={busy || cameraInput === ''}>{state?.camera.enabled ? 'Switch' : 'Select'}</button>
            </form>
            <div className={`capture-pipeline ${state?.camera.native_luma ? 'native' : ''}`}>
              <div>
                <span>Capture pipeline</span>
                <b>{state?.camera.native_luma ? 'Native luminance' : state?.camera.backend || 'Waiting'}</b>
              </div>
              <div>
                <span>Camera stream</span>
                <b>{state?.performance.capture_image_size_px?.join(' × ') || '—'} {state?.camera.pixel_format || ''}</b>
              </div>
              <small>
                {state?.camera.native_luma
                  ? 'AprilTags use the full-resolution Y plane; color conversion is limited to the preview and feet.'
                  : 'Auto mode will use native iPhone YUV when macOS and FFmpeg expose it.'}
              </small>
            </div>
            <button
              className={state?.camera.enabled ? 'camera-power stop' : 'camera-power'}
              disabled={busy || (!state?.camera.enabled && cameraInput === '')}
              onClick={() => void setCameraEnabled(!state?.camera.enabled)}
            >
              {state?.camera.enabled ? 'Stop camera' : 'Start camera'}
            </button>
          </section>

          <section className="panel coverage-card">
            <div className="eyebrow">Direct visibility</div>
            <div className="coverage-row">
              <CoveragePill label="Robot tags" value={state?.coverage.robot_tags || 0} total={state?.coverage.robot_tags_required || 13} />
              <CoveragePill label="Floor tags" value={state?.coverage.floor_tags || 0} total={2} />
              <CoveragePill label="Feet" value={state?.coverage.feet || 0} total={6} />
            </div>
            <div className="tag-id-line">
              Seen IDs: {state?.coverage.robot_tag_ids.join(', ') || 'none'}
            </div>
          </section>

          <section className={`panel readiness-card ${readiness?.ready ? 'is-ready' : ''}`}>
            <div className="eyebrow">Calibration gate</div>
            <h2>{readiness?.headline || 'Waiting for vision'}</h2>
            <div className="progress-track">
              <div style={{width: `${(readiness?.progress || 0) * 100}%`}} />
            </div>
            <div className="progress-caption">
              <span>stable frames</span>
              <b>{readiness?.stable_frames || 0}/{readiness?.required_stable_frames || 12}</b>
            </div>
            {!!readiness?.blockers.length && (
              <ul className="issue-list blockers">
                {readiness.blockers.slice(0, 4).map((item) => <li key={item}>{item}</li>)}
              </ul>
            )}
            {!!readiness?.warnings.length && (
              <ul className="issue-list warnings">
                {readiness.warnings.map((item) => <li key={item}>{item}</li>)}
              </ul>
            )}
            <div className="scope-line">
              Capture scope <b>{readiness?.scope === 'lid_joints' ? '12 signed yaw/hip joints' : 'not established'}</b>
            </div>
          </section>

          <section className="panel capture-card">
            <div className="eyebrow">Stationary capture</div>
            <h2>{collecting ? 'Collecting calibration' : state?.calibration.status === 'complete' ? 'Capture complete' : 'Visual calibration'}</h2>
            {collecting ? (
              <>
                <div className="capture-count">
                  <b>{state?.calibration.accepted_frames}</b>
                  <span>of {state?.calibration.target_frames} accepted frames</span>
                </div>
                <div className="progress-track active">
                  <div style={{width: `${(state?.calibration.progress || 0) * 100}%`}} />
                </div>
                {state?.calibration.last_rejection && <p className="mini-warning">Paused: {state.calibration.last_rejection}</p>}
                <button className="secondary full" onClick={() => void cancelCalibration()}>Cancel capture</button>
              </>
            ) : (
              <>
                <p>Capture robust median vision-to-encoder offsets. Nothing is applied to the robot.</p>
                <button className="primary full" disabled={!readiness?.ready || busy} onClick={() => void startCalibration()}>
                  {readiness?.ready ? 'Start visual calibration' : 'Waiting for readiness'}
                </button>
              </>
            )}
          </section>
        </aside>
      </div>
    </main>
  )
}
