"""Read-only AprilTag layout history for the Robot Lab web UI."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from html import escape
from urllib.parse import quote


def _text(value: object, fallback: str = "—") -> str:
    if value is None or value == "":
        return fallback
    return str(value)


def _tag_ids(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError):
            parsed = [part.strip() for part in value.split(",") if part.strip()]
        value = parsed
    if not isinstance(value, (list, tuple, set)):
        value = [value]

    def sort_key(item: object) -> tuple[int, object]:
        text = str(item)
        try:
            return (0, int(text))
        except ValueError:
            return (1, text)

    return [str(item) for item in sorted(value, key=sort_key)]


def _status(revision: Mapping[str, object]) -> str:
    supplied = str(revision.get("status") or "").lower().replace("_", "-")
    aliases = {"current": "active", "ready": "candidate", "pending": "candidate"}
    supplied = aliases.get(supplied, supplied)
    if supplied in {"active", "candidate", "incomplete", "superseded", "stale"}:
        return supplied
    if revision.get("is_current") or revision.get("current"):
        return "active"
    if revision.get("effective_until") or revision.get("superseded_at"):
        return "superseded"
    if revision.get("effective_from") or revision.get("activated_at"):
        return "active"
    return "candidate" if revision.get("review_ready") else "incomplete"


def _revision_card(revision: Mapping[str, object]) -> str:
    status = _status(revision)
    revision_id = _text(revision.get("id"))
    revision_number = revision.get("revision_number", revision.get("sequence"))
    heading = f"Revision {revision_number}" if revision_number not in (None, "") else "Layout revision"
    layout_hash = _text(
        revision.get("layout_sha256", revision.get("sha256", revision.get("hash")))
    )
    effective_from = revision.get("effective_from")
    effective_until = revision.get("effective_until", revision.get("superseded_at"))
    if effective_from:
        interval = f"{_text(effective_from)} → {_text(effective_until, 'present')}"
    else:
        interval = "Not activated"

    observed_at = revision.get("observed_at", revision.get("created_at"))
    changed_ids = _tag_ids(
        revision.get("changed_tag_ids", revision.get("changed_tag_ids_json"))
    )
    if changed_ids:
        changed_html = "".join(
            f"<span class='lh-tag'>#{escape(tag_id)}</span>" for tag_id in changed_ids
        )
    else:
        changed_html = "<span class='lh-none'>No tag rotation changes recorded</span>"

    source_id = revision.get("source_experiment_id")
    if source_id:
        source_label = revision.get("source_experiment_name") or f"Experiment {source_id}"
        source_html = (
            f"<a href='/experiments/{quote(str(source_id), safe='')}'>"
            f"{escape(str(source_label))}</a>"
        )
    else:
        source_html = escape(_text(revision.get("source_kind"), "System baseline"))

    return f"""
    <article class='lh-card lh-{status}'>
      <div class='lh-card-head'>
        <div>
          <span class='lh-status'>{escape(status)}</span>
          <h2>{escape(heading)}</h2>
        </div>
        <code class='lh-id'>{escape(revision_id)}</code>
      </div>
      <dl class='lh-facts'>
        <div><dt>Effective interval</dt><dd>{escape(interval)}</dd></div>
        <div><dt>Observed</dt><dd>{escape(_text(observed_at))}</dd></div>
        <div class='lh-wide'><dt>Layout SHA-256</dt><dd><code>{escape(layout_hash)}</code></dd></div>
        <div class='lh-wide'><dt>Source</dt><dd>{source_html}</dd></div>
      </dl>
      <div class='lh-changes'><h3>Changed tag IDs</h3><div>{changed_html}</div></div>
    </article>"""


def layout_history_page(
    revisions: Iterable[Mapping[str, object]], *, available: bool = True
) -> str:
    """Return a responsive, read-only body for the shared ``page`` wrapper."""
    items = list(revisions)
    cards = "".join(_revision_card(revision) for revision in items)
    if not cards:
        cards = """
        <div class='lh-empty'>
          <strong>No layout revisions yet.</strong>
          <span>The first verified AprilTag layout will establish this timeline.</span>
        </div>"""

    unavailable = "" if available else """
      <aside class='lh-alert' role='status'>
        Layout history is unavailable because the AprilTag configuration is not installed on this host.
      </aside>"""

    return f"""
<style>
  .lh-shell{{--lh-cyan:#69e5ee;--lh-orange:#ffb13b;--lh-green:#8df07b;--lh-red:#ff817b;--lh-blue:#7dc5ff;max-width:860px;margin:0 auto}}
  .lh-nav{{display:inline-flex;align-items:center;gap:.5rem;margin-bottom:2rem;text-decoration:none}}
  .lh-hero{{padding:clamp(1.25rem,5vw,2.4rem);border:1px solid var(--line);border-radius:24px;background:radial-gradient(circle at 95% 5%,rgba(105,229,238,.13),transparent 38%),var(--panel)}}
  .lh-kicker{{margin:0 0 .7rem;color:var(--lh-cyan);font-size:.75rem;font-weight:800;letter-spacing:.13em;text-transform:uppercase}}
  .lh-hero h1{{margin:0 0 1rem;font-size:clamp(2.35rem,10vw,5rem)}}
  .lh-explain{{max-width:46rem;margin:0;color:var(--muted);font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text",Inter,system-ui,sans-serif;font-size:1.06rem}}
  .lh-note{{display:flex;gap:.7rem;align-items:flex-start;margin-top:1.3rem;padding:1rem;border:1px solid rgba(105,229,238,.25);border-radius:14px;background:rgba(105,229,238,.06);color:#cfe4e4;font-size:.86rem}}
  .lh-note strong{{flex:0 0 auto;color:var(--lh-cyan)}}
  .lh-alert{{margin:1.2rem 0;padding:1rem;border:1px solid rgba(255,129,123,.45);border-radius:14px;background:rgba(255,129,123,.08);color:#ffd4d1}}
  .lh-legend{{display:flex;flex-wrap:wrap;gap:.55rem 1rem;margin:1.4rem 0 2.4rem;color:var(--muted);font-size:.76rem;text-transform:uppercase;letter-spacing:.05em}}
  .lh-legend span{{display:inline-flex;align-items:center;gap:.38rem}}
  .lh-legend i{{width:.55rem;height:.55rem;border-radius:50%;background:currentColor}}
  .lh-legend .active{{color:var(--lh-green)}}.lh-legend .candidate{{color:var(--lh-orange)}}.lh-legend .incomplete,.lh-legend .stale{{color:var(--lh-red)}}.lh-legend .superseded{{color:var(--lh-blue)}}
  .lh-timeline{{position:relative;display:grid;gap:1rem;padding-left:1.65rem}}
  .lh-timeline:before{{content:"";position:absolute;left:.38rem;top:.5rem;bottom:.5rem;width:1px;background:var(--line)}}
  .lh-card{{position:relative;display:block;padding:1.25rem;border:1px solid var(--line);border-radius:18px;background:var(--panel)}}
  .lh-card:before{{content:"";position:absolute;left:-1.62rem;top:1.55rem;width:.68rem;height:.68rem;border:3px solid var(--bg);border-radius:50%;background:var(--muted)}}
  .lh-active:before{{background:var(--lh-green)}}.lh-candidate:before{{background:var(--lh-orange)}}.lh-incomplete:before,.lh-stale:before{{background:var(--lh-red)}}.lh-superseded:before{{background:var(--lh-blue)}}
  .lh-card-head{{display:flex;align-items:flex-start;justify-content:space-between;gap:1rem}}
  .lh-card h2{{margin:.45rem 0 0;font-size:1.3rem;letter-spacing:-.025em}}
  .lh-status{{display:inline-block;padding:.18rem .52rem;border:1px solid currentColor;border-radius:999px;font-size:.68rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase}}
  .lh-active .lh-status{{color:var(--lh-green)}}.lh-candidate .lh-status{{color:var(--lh-orange)}}.lh-incomplete .lh-status,.lh-stale .lh-status{{color:var(--lh-red)}}.lh-superseded .lh-status{{color:var(--lh-blue)}}
  .lh-id{{max-width:45%;overflow:hidden;color:var(--muted);font-size:.72rem;text-overflow:ellipsis;white-space:nowrap}}
  .lh-facts{{display:grid;grid-template-columns:1fr 1fr;gap:.85rem 1.2rem;margin:1.2rem 0}}
  .lh-facts div{{min-width:0}}.lh-facts .lh-wide{{grid-column:1/-1}}
  .lh-facts dt,.lh-changes h3{{margin:0 0 .2rem;color:var(--muted);font-size:.68rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase}}
  .lh-facts dd{{margin:0;font-size:.83rem;overflow-wrap:anywhere}}.lh-facts code{{color:#c9d6d0;font-size:.75rem}}
  .lh-changes{{padding-top:1rem;border-top:1px solid var(--line)}}.lh-changes h3{{margin-bottom:.5rem}}
  .lh-changes>div{{display:flex;flex-wrap:wrap;gap:.4rem}}.lh-tag{{padding:.2rem .48rem;border-radius:7px;background:#202c27;color:var(--ink);font-size:.78rem}}.lh-none{{color:var(--muted);font-size:.8rem}}
  .lh-empty{{display:grid;gap:.35rem;padding:2rem;border:1px dashed var(--line);border-radius:18px;color:var(--muted);text-align:center}}.lh-empty strong{{color:var(--ink)}}
  @media(max-width:600px){{.lh-hero{{border-radius:18px}}.lh-note{{display:block}}.lh-note strong{{display:block;margin-bottom:.3rem}}.lh-card-head{{display:block}}.lh-id{{display:block;max-width:100%;margin-top:.7rem}}.lh-facts{{grid-template-columns:1fr}}.lh-facts .lh-wide{{grid-column:auto}}}}
</style>
<div class='lh-shell'>
  <a class='lh-nav' href='/' aria-label='Back to experiment queue'>← Queue</a>
  <header class='lh-hero'>
    <p class='lh-kicker'>Robot Lab · AprilTag record</p>
    <h1>Layout history</h1>
    <p class='lh-explain'>Every recording is pinned to the exact, immutable tag layout that was effective when it was captured. Activating a newer orientation never rewrites an older video, so replay uses the geometry that the camera actually saw.</p>
    <div class='lh-note'><strong>Read only</strong><span>Review and activation happen on the source experiment. This page is the permanent timeline.</span></div>
  </header>
  {unavailable}
  <div class='lh-legend' aria-label='Revision statuses'>
    <span class='active'><i></i>Active</span><span class='candidate'><i></i>Candidate</span>
    <span class='incomplete'><i></i>Incomplete</span><span class='stale'><i></i>Stale</span><span class='superseded'><i></i>Superseded</span>
  </div>
  <main class='lh-timeline'>{cards}</main>
</div>"""
