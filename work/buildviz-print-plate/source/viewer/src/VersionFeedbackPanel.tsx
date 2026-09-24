import { useEffect, useState } from 'react'
import type { VersionFeedback } from '../../core/versionFeedback'

const quote = (value: string) => `'${value.replaceAll("'", "'\\''")}'`

export function VersionFeedbackPanel({ buildId, branch, version, reason }: {
  buildId: string; branch: string; version: string; reason?: string
}) {
  const [open, setOpen] = useState(false)
  const [refresh, setRefresh] = useState(0)
  const [data, setData] = useState<VersionFeedback | null>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    if (!open) return
    const controller = new AbortController()
    const query = new URLSearchParams({ buildId, branch, version })
    fetch(`/__buildviz/feedback?${query}`, { signal: controller.signal, cache: 'no-store' })
      .then(async (response) => {
        if (!response.ok) throw new Error(`Feedback could not be loaded (${response.status}).`)
        return await response.json() as VersionFeedback
      })
      .then((result) => { setData(result); setError('') })
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setError(caught instanceof Error ? caught.message : String(caught))
      })
    return () => controller.abort()
  }, [open, buildId, branch, version, refresh])
  const command = `npx buildviz feedback ${quote(`${buildId}@${branch}@${version}`)} --url ${quote(window.location.origin)} ` +
    '--kind issue --basis user-report -m "Describe what went wrong, affected parts and uncertainty" --evidence "Describe the report or test evidence"'
  return (
    <details className="version-feedback" onToggle={(event) => setOpen(event.currentTarget.open)}>
      <summary>Why this version · issues &amp; lessons</summary>
      <p><strong>Why {version}:</strong> {data?.reason ?? reason ?? 'No separate reason recorded at publish time.'}</p>
      <p>Record what went wrong on the version where it happened. Append follow-up evidence; do not rewrite its history.</p>
      {error ? <p role="alert">{error}</p> : !data ? <p>Loading feedback…</p> : (
        data.entries.length ? <ol className="version-feedback-entries">
          {data.entries.map((entry) => <li key={entry.id}>
            <strong>{entry.kind} · {entry.basis}</strong>
            <small>{new Date(entry.createdAt).toLocaleString()}</small>
            <p>{entry.message}</p>
            {entry.parts?.length ? <p>Parts: {entry.parts.join(', ')}</p> : null}
            {entry.evidence ? <p>Evidence: {entry.evidence}</p> : null}
            {entry.relatedVersion ? <p>Related version: {entry.relatedVersion}</p> : null}
            {entry.relatedFeedbackId ? <small>Follow-up to {entry.relatedFeedbackId}</small> : null}
            <small>ID: {entry.id}</small>
          </li>)}
        </ol> : <p>No feedback recorded. This does not mean the design has been validated.</p>
      )}
      <button type="button" onClick={() => setRefresh((value) => value + 1)}>Refresh feedback</button>
      <details className="build-publish-help">
        <summary>Record an issue with an agent or CLI…</summary>
        <p>Ask your agent to use <code>record_version_feedback</code>, or edit and run this command. Set the basis to observed, user-report, hypothesis, or test-result. A cloud write requires your API key.</p>
        <textarea aria-label="Record version feedback command" value={command} readOnly rows={6}
          onFocus={(event) => event.currentTarget.select()} />
        <p>After testing a fix, append a resolution with the original issue ID, tested version, and evidence. A new version alone is not a verified fix.</p>
      </details>
    </details>
  )
}
