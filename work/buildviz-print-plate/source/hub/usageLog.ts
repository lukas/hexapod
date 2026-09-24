// ---------------------------------------------------------------------------
// Lightweight, best-effort usage logging so a later "what's used vs. unused"
// audit is CONCLUSIVE rather than inferred. One compact JSON object per line
// (JSONL) is appended to ~/.buildviz/usage.jsonl:
//   * source:"cli"  — one line per known CLI invocation (command metadata only)
//   * source:"hub"  — one line per hub HTTP request to /__buildviz/* or /builds/*
//
// Design rules (see the task brief):
//   * Best-effort / NEVER throws: every fs operation is wrapped so logging can
//     never affect the command result or an HTTP response. Failures are silently
//     ignored (fire-and-forget).
//   * Metadata ONLY: we log command/endpoint names, flag NAMES (never values),
//     status/timing, etc. We NEVER log payload contents (scene JSON, file
//     bodies, asset bytes) so nothing leaks design data and lines stay small.
//   * No rotation: if usage.jsonl grows past a few MB we simply keep appending.
//     Rotation is deliberately out of scope — a re-audit reads the whole file,
//     and truncating/rotating would risk dropping the very history it needs.
// ---------------------------------------------------------------------------
import { appendFile, mkdir, readFile } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import path from 'node:path'
// Reuse the single ~/.buildviz directory helper from the cycle-free shared
// module (cliShared imports neither hub nor usageLog), so there is no import
// cycle and one source of truth for the directory path.
import { buildvizHome } from './cliShared'

export const usageLogPath = path.join(buildvizHome, 'usage.jsonl')

// A CLI invocation: command + (optional) grouped subcommand + whitelisted flag
// NAMES (never values) + the buildviz version + the cwd basename (never a full
// path).
export type CliUsageEvent = {
  source: 'cli'
  command: string
  subcommand?: string
  flags?: string[]
  version?: string
  cwd?: string
}

// A hub HTTP request: method + route path (query stripped) + status + duration
// + whether the hub was in read-only mode.
export type HubUsageEvent = {
  source: 'hub'
  method: string
  path: string
  status: number
  durationMs: number
  readOnly: boolean
}

export type UsageEvent = CliUsageEvent | HubUsageEvent

// Append one event as a JSONL line. Fire-and-forget: returns a promise that
// NEVER rejects (all errors are swallowed). CLI callers may await it to make
// sure the line is flushed before a short-lived process exits; the hub calls it
// without awaiting so a request is never delayed by disk I/O.
export const appendUsageEvent = async (event: UsageEvent): Promise<void> => {
  try {
    await mkdir(buildvizHome, { recursive: true })
    const line = `${JSON.stringify({ ts: new Date().toISOString(), ...event })}\n`
    await appendFile(usageLogPath, line, 'utf8')
  } catch {
    // Intentionally ignored — usage logging must never affect the caller.
  }
}

export type UsageSummaryEntry = {
  key: string
  count: number
  firstSeen: string
  lastSeen: string
}

export type UsageSummary = {
  ok: true
  logPath: string
  exists: boolean
  totalEvents: number
  cliInvocations: number
  hubRequests: number
  malformedLines: number
  firstSeen: string | null
  lastSeen: string | null
  commands: UsageSummaryEntry[]
  endpoints: UsageSummaryEntry[]
}

const emptySummary = (exists: boolean): UsageSummary => ({
  ok: true,
  logPath: usageLogPath,
  exists,
  totalEvents: 0,
  cliInvocations: 0,
  hubRequests: 0,
  malformedLines: 0,
  firstSeen: null,
  lastSeen: null,
  commands: [],
  endpoints: [],
})

// Fold a single event into a keyed accumulator, tracking count + first/last ts.
const accumulate = (
  map: Map<string, UsageSummaryEntry>,
  key: string,
  ts: string,
) => {
  const existing = map.get(key)
  if (!existing) {
    map.set(key, { key, count: 1, firstSeen: ts, lastSeen: ts })
    return
  }
  existing.count += 1
  if (ts < existing.firstSeen) existing.firstSeen = ts
  if (ts > existing.lastSeen) existing.lastSeen = ts
}

// Most-used first, ties broken alphabetically for stable output.
const sortEntries = (map: Map<string, UsageSummaryEntry>): UsageSummaryEntry[] =>
  [...map.values()].sort((a, b) => b.count - a.count || a.key.localeCompare(b.key))

// Read + summarize ~/.buildviz/usage.jsonl. Best-effort: a missing/empty file
// yields an empty summary (exists:false), and individual malformed lines are
// counted and skipped rather than throwing.
export const summarizeUsage = async (): Promise<UsageSummary> => {
  if (!existsSync(usageLogPath)) return emptySummary(false)

  let raw: string
  try {
    raw = await readFile(usageLogPath, 'utf8')
  } catch {
    return emptySummary(true)
  }

  const summary = emptySummary(true)
  const commands = new Map<string, UsageSummaryEntry>()
  const endpoints = new Map<string, UsageSummaryEntry>()

  for (const line of raw.split('\n')) {
    const trimmed = line.trim()
    if (trimmed.length === 0) continue
    let event: UsageEvent & { ts?: string }
    try {
      event = JSON.parse(trimmed) as UsageEvent & { ts?: string }
    } catch {
      summary.malformedLines += 1
      continue
    }
    const ts = typeof event.ts === 'string' ? event.ts : ''
    if (ts) {
      if (summary.firstSeen === null || ts < summary.firstSeen) summary.firstSeen = ts
      if (summary.lastSeen === null || ts > summary.lastSeen) summary.lastSeen = ts
    }
    summary.totalEvents += 1

    if (event.source === 'cli' && typeof event.command === 'string') {
      summary.cliInvocations += 1
      const key = event.subcommand ? `${event.command} ${event.subcommand}` : event.command
      accumulate(commands, key, ts)
    } else if (event.source === 'hub' && typeof event.path === 'string') {
      summary.hubRequests += 1
      const method = typeof event.method === 'string' ? event.method : '?'
      accumulate(endpoints, `${method} ${event.path}`, ts)
    }
  }

  summary.commands = sortEntries(commands)
  summary.endpoints = sortEntries(endpoints)
  return summary
}
