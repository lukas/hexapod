import { useEffect, useMemo, useRef, useState } from 'react'
import type { Animation, Joint, Pose } from '../../core/buildScene'
import {
  animationDuration,
  defaultJointValues,
  jointHome,
  jointRange,
  jointUnit,
  resolveJointValues,
  sampleAnimation,
  type JointValues,
} from '../../core/buildvizKinematics'

type MotionPanelProps = {
  joints: Joint[]
  poses: Pose[]
  animations?: Animation[]
  jointValues: JointValues
  onChange: (values: JointValues) => void
  open: boolean
  modeKey: string
  onToggleOpen: (open: boolean) => void
}

const PLAYBACK_SPEEDS = [0.25, 0.5, 1, 2]

// Stable default so the "clips changed" render-phase reset below can compare
// by identity without re-triggering when the prop is simply absent.
const NO_ANIMATIONS: Animation[] = []

// Steps a normalized phase 0→1 and maps it to each joint's range so the whole
// mechanism sweeps min→max→min. Pure UI affordance; the per-pose overlap sweep
// in the Checks panel samples the range independently.
const ANIMATE_PERIOD_MS = 2600

const phaseToValues = (joints: Joint[], phase: number): JointValues => {
  // Triangle wave: 0→1→0 over the period, so the sweep returns home smoothly.
  const t = phase < 0.5 ? phase * 2 : 2 - phase * 2
  const values: JointValues = {}
  for (const joint of joints) {
    const range = jointRange(joint)
    values[joint.id] = range.min + (range.max - range.min) * t
  }
  return values
}

export const MotionPanel = ({
  joints,
  poses,
  animations = NO_ANIMATIONS,
  jointValues,
  onChange,
  open,
  modeKey,
  onToggleOpen,
}: MotionPanelProps) => {
  const [animating, setAnimating] = useState(false)
  const frameRef = useRef<number | null>(null)
  const startRef = useRef<number>(0)

  // --- Clip playback transport (time-based keyframed animations) ------------
  const hasClips = animations.length > 0
  const [clipId, setClipId] = useState<string>(animations[0]?.id ?? '')
  const [playing, setPlaying] = useState(false)
  const [loop, setLoop] = useState(true)
  const [speed, setSpeed] = useState(1)
  const [clipTime, setClipTime] = useState(0)
  const clipFrameRef = useRef<number | null>(null)
  const clipTickRef = useRef<number>(0)
  const clipTimeRef = useRef(0)

  const activeClip = useMemo(
    () => animations.find((clip) => clip.id === clipId) ?? animations[0],
    [animations, clipId],
  )
  const clipDuration = activeClip ? animationDuration(activeClip) : 0

  // Reset the transport when the set of clips (i.e. the build) changes.
  // Render-phase state adjustment (react.dev "You Might Not Need an Effect"):
  // compare against the previous prop and reset before committing, instead of
  // a setState-in-effect cascade. The ref is re-synced by the effect below.
  const [prevAnimations, setPrevAnimations] = useState(animations)
  if (animations !== prevAnimations) {
    setPrevAnimations(animations)
    setClipId(animations[0]?.id ?? '')
    setPlaying(false)
    setClipTime(0)
    setLoop(animations[0]?.loop ?? true)
  }

  // Mirror the committed scrub position into the ref the rAF tick reads;
  // event handlers also write it directly so mid-frame reads stay fresh.
  useEffect(() => {
    clipTimeRef.current = clipTime
  }, [clipTime])

  // Keep the sampled pose in sync while scrubbing/selecting (even when paused).
  useEffect(() => {
    if (!activeClip || playing) return
    onChange(sampleAnimation(joints, activeClip, clipTime))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeClip, clipTime, playing])

  useEffect(() => {
    if (!playing || !activeClip) {
      if (clipFrameRef.current !== null) cancelAnimationFrame(clipFrameRef.current)
      clipFrameRef.current = null
      return
    }
    clipTickRef.current = performance.now()
    const tick = () => {
      const now = performance.now()
      const dt = ((now - clipTickRef.current) / 1000) * speed
      clipTickRef.current = now
      let next = clipTimeRef.current + dt
      if (next >= clipDuration) {
        if (loop && clipDuration > 0) {
          next %= clipDuration
        } else {
          next = clipDuration
        }
      }
      clipTimeRef.current = next
      setClipTime(next)
      onChange(sampleAnimation(joints, activeClip, next))
      if (!loop && next >= clipDuration) {
        setPlaying(false)
        return
      }
      clipFrameRef.current = requestAnimationFrame(tick)
    }
    clipFrameRef.current = requestAnimationFrame(tick)
    return () => {
      if (clipFrameRef.current !== null) cancelAnimationFrame(clipFrameRef.current)
      clipFrameRef.current = null
    }
  }, [playing, activeClip, speed, loop, clipDuration, joints, onChange])

  const stopAllPlayback = () => {
    setAnimating(false)
    setPlaying(false)
  }

  useEffect(() => {
    if (!animating) {
      if (frameRef.current !== null) cancelAnimationFrame(frameRef.current)
      frameRef.current = null
      return
    }
    startRef.current = performance.now()
    const tick = () => {
      const elapsed = performance.now() - startRef.current
      const phase = (elapsed % ANIMATE_PERIOD_MS) / ANIMATE_PERIOD_MS
      onChange(phaseToValues(joints, phase))
      frameRef.current = requestAnimationFrame(tick)
    }
    frameRef.current = requestAnimationFrame(tick)
    return () => {
      if (frameRef.current !== null) cancelAnimationFrame(frameRef.current)
      frameRef.current = null
    }
  }, [animating, joints, onChange])

  const setJoint = (id: string, value: number) => {
    stopAllPlayback()
    onChange({ ...jointValues, [id]: value })
  }

  const reset = () => {
    stopAllPlayback()
    setClipTime(0)
    clipTimeRef.current = 0
    onChange(defaultJointValues(joints))
  }

  const applyPose = (pose: Pose) => {
    stopAllPlayback()
    onChange(resolveJointValues(joints, pose.jointValues))
  }

  const movedCount = joints.filter(
    (joint) => Math.abs((jointValues[joint.id] ?? jointHome(joint)) - jointHome(joint)) > 1e-6,
  ).length
  const badge = playing
    ? `▶ ${activeClip?.name ?? 'clip'}`
    : animating
      ? 'sweeping…'
      : movedCount > 0
        ? `${movedCount}/${joints.length} moved`
        : hasClips
          ? `${animations.length} clip${animations.length === 1 ? '' : 's'}`
          : `${joints.length} joints`

  return (
    <details
      className="control-group motion-controls"
      open={open}
      key={`motion-${modeKey}`}
      onToggle={(event) => onToggleOpen(event.currentTarget.open)}
    >
      <summary>
        <span>Motion</span>
        <small>{badge}</small>
      </summary>
      <div className="control-content motion-content">
        {hasClips ? (
          <div className="motion-clips">
            {animations.length > 1 ? (
              <div className="motion-clip-tabs">
                {animations.map((clip) => (
                  <button
                    type="button"
                    key={clip.id}
                    className={clip.id === activeClip?.id ? 'active' : undefined}
                    aria-pressed={clip.id === activeClip?.id}
                    onClick={() => {
                      setPlaying(false)
                      setClipId(clip.id)
                      setClipTime(0)
                      clipTimeRef.current = 0
                      setLoop(clip.loop ?? true)
                    }}
                  >
                    {clip.name}
                  </button>
                ))}
              </div>
            ) : null}

            <div className="motion-transport">
              <button
                type="button"
                className="motion-play"
                onClick={() => {
                  setAnimating(false)
                  setPlaying((current) => !current)
                }}
              >
                {playing ? '❚❚ Pause' : '▶ Play'}
              </button>
              <label className="motion-loop">
                <input
                  type="checkbox"
                  checked={loop}
                  onChange={(event) => setLoop(event.currentTarget.checked)}
                />
                Loop
              </label>
              <label className="motion-speed">
                Speed
                <select
                  value={speed}
                  onChange={(event) => setSpeed(Number(event.currentTarget.value))}
                >
                  {PLAYBACK_SPEEDS.map((option) => (
                    <option key={option} value={option}>
                      {option}×
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <label className="motion-scrubber">
              <input
                type="range"
                min={0}
                max={clipDuration || 1}
                step={0.01}
                value={Math.min(clipTime, clipDuration)}
                onChange={(event) => {
                  setPlaying(false)
                  const value = Number(event.currentTarget.value)
                  setClipTime(value)
                  clipTimeRef.current = value
                }}
                aria-label={`Scrub ${activeClip?.name ?? 'clip'}`}
              />
              <small>
                {clipTime.toFixed(2)}s / {clipDuration.toFixed(2)}s
              </small>
            </label>
          </div>
        ) : null}

        <div className="motion-actions">
          <button
            type="button"
            onClick={() => {
              setPlaying(false)
              setAnimating((current) => !current)
            }}
          >
            {animating ? 'Stop sweep' : 'Animate sweep'}
          </button>
          <button type="button" onClick={reset} disabled={movedCount === 0 && !animating && !playing}>
            Reset to home
          </button>
        </div>

        {poses.length > 0 ? (
          <div className="motion-poses">
            {poses.map((pose) => (
              <button type="button" key={pose.id} onClick={() => applyPose(pose)} title={pose.name}>
                {pose.name}
              </button>
            ))}
          </div>
        ) : null}

        <div className="motion-sliders">
          {joints.map((joint) => {
            const range = jointRange(joint)
            const value = jointValues[joint.id] ?? jointHome(joint)
            const unit = jointUnit(joint)
            return (
              <label className="motion-slider" key={joint.id}>
                <span className="motion-slider-label">
                  <span>{joint.label ?? joint.id}</span>
                  <small>
                    {value.toFixed(0)}
                    {unit}
                  </small>
                </span>
                <input
                  type="range"
                  min={range.min}
                  max={range.max}
                  step={joint.type === 'prismatic' ? 0.5 : 1}
                  value={value}
                  onChange={(event) => setJoint(joint.id, Number(event.currentTarget.value))}
                  aria-label={`${joint.label ?? joint.id} (${range.min}${unit} to ${range.max}${unit})`}
                />
              </label>
            )
          })}
        </div>
      </div>
    </details>
  )
}
