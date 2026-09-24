import { useCallback, useEffect, useId, useMemo, useRef, useState, type KeyboardEvent } from 'react'
import { createPortal } from 'react-dom'
import type { CatalogItem } from '../../core/catalogModel'
import type { BuildsIndexBuild } from '../../core/buildModel'
import { quickNavEntries, QUICK_NAV_GROUPS } from './catalogQuickNavModel'
import './CatalogQuickNav.css'

type CatalogQuickNavProps = { items: CatalogItem[]; currentId?: string; builds?: BuildsIndexBuild[]; currentBuildId?: string }
type MenuPosition = { left: number; top?: number; bottom?: number; width: number; maxHeight: number }
const positionFor = (trigger: HTMLElement): MenuPosition => {
  const rect = trigger.getBoundingClientRect()
  const width = Math.min(360, Math.max(260, rect.width), window.innerWidth - 24)
  const below = window.innerHeight - rect.bottom - 18
  const above = rect.top - 18
  const upward = below < 260 && above > below
  return {
    left: Math.max(12, Math.min(rect.left, window.innerWidth - width - 12)),
    width,
    maxHeight: Math.max(120, Math.min(330, upward ? above : below)),
    ...(upward ? { bottom: window.innerHeight - rect.top + 6 } : { top: rect.bottom + 6 }),
  }
}

export function CatalogQuickNav({ items, currentId, builds, currentBuildId }: CatalogQuickNavProps) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [tab, setTab] = useState<'all' | 'projects'>('all')
  const [activeId, setActiveId] = useState<string | null>(null)
  const [position, setPosition] = useState<MenuPosition | null>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const panelRef = useRef<HTMLDivElement>(null)
  const searchRef = useRef<HTMLInputElement>(null)
  const linkRefs = useRef(new Map<string, HTMLAnchorElement>())
  const panelId = useId()
  const current = items.find((item) => item.id === currentId)
  const currentBuild = builds?.find((build) => build.id === currentBuildId)
  const currentName = current?.name ?? currentBuild?.name ?? currentBuild?.build
  const shortcut = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform) ? '⌘K' : 'Ctrl K'

  const entries = useMemo(() => quickNavEntries({ items, builds, currentId, currentBuildId, query, projectsOnly: tab === 'projects' }), [items, builds, currentId, currentBuildId, query, tab])
  // Search has one ranked list so keyboard order exactly matches visual order.
  const resultGroups = query.trim() || tab === 'projects'
    ? [{ label: tab === 'projects' ? 'Projects' : 'Matches', entries }]
    : QUICK_NAV_GROUPS.map((group) => ({ label: group.label, entries: entries.filter((entry) => entry.kind === group.kind) }))

  const openMenu = useCallback(() => {
    if (!triggerRef.current) return
    setPosition(positionFor(triggerRef.current))
    setQuery('')
    setTab('all')
    setActiveId(null)
    setOpen(true)
  }, [])

  const closeMenu = useCallback((restoreFocus = false) => {
    setOpen(false)
    if (restoreFocus) triggerRef.current?.focus()
  }, [])

  useEffect(() => {
    const onKeyDown = (event: globalThis.KeyboardEvent) => {
      if (!event.defaultPrevented && open && event.key === 'Escape') {
        event.preventDefault()
        closeMenu(true)
        return
      }
      if (event.defaultPrevented || event.altKey || event.key.toLocaleLowerCase() !== 'k' || !(event.metaKey || event.ctrlKey)) return
      event.preventDefault()
      if (open) closeMenu(true)
      else openMenu()
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [open, openMenu, closeMenu])

  useEffect(() => {
    if (!open) return
    searchRef.current?.focus()
    const onPointerDown = (event: PointerEvent) => {
      if (!panelRef.current?.contains(event.target as Node) && !triggerRef.current?.contains(event.target as Node)) closeMenu()
    }
    const reposition = (event: Event) => {
      if (event.target instanceof Node && panelRef.current?.contains(event.target)) return
      if (triggerRef.current) setPosition(positionFor(triggerRef.current))
    }
    document.addEventListener('pointerdown', onPointerDown)
    window.addEventListener('resize', reposition)
    window.addEventListener('scroll', reposition, true)
    return () => {
      document.removeEventListener('pointerdown', onPointerDown)
      window.removeEventListener('resize', reposition)
      window.removeEventListener('scroll', reposition, true)
    }
  }, [open, closeMenu])

  const onMenuKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Escape') {
      event.preventDefault()
      event.stopPropagation()
      closeMenu(true)
      return
    }
    if ((event.key === 'ArrowDown' || event.key === 'ArrowUp') && entries.length) {
      event.preventDefault()
      const activeIndex = entries.findIndex((entry) => entry.key === activeId)
      const nextIndex = event.key === 'ArrowDown'
        ? (activeIndex + 1) % entries.length
        : (activeIndex < 0 ? entries.length - 1 : (activeIndex - 1 + entries.length) % entries.length)
      const nextId = entries[nextIndex].key
      setActiveId(nextId)
      linkRefs.current.get(nextId)?.focus()
      linkRefs.current.get(nextId)?.scrollIntoView({ block: 'nearest' })
    } else if (event.key === 'Enter' && event.target === searchRef.current && entries.length) {
      event.preventDefault()
      linkRefs.current.get(activeId ?? entries[0].key)?.click()
    } else if (event.target instanceof HTMLAnchorElement && event.key.length === 1 && !event.ctrlKey && !event.metaKey && !event.altKey) {
      event.preventDefault()
      setQuery(event.key)
      setActiveId(null)
      searchRef.current?.focus()
    }
  }

  return <div className="catalog-quick-nav">
    <button ref={triggerRef} type="button" className="catalog-quick-trigger" aria-label="Jump to project or assembly" aria-description={currentName ? `Current: ${currentName}` : undefined} aria-haspopup="dialog" aria-expanded={open} aria-controls={open ? panelId : undefined} title={currentName ? `${currentName} — jump to project or assembly` : 'Jump to project or assembly'} onClick={() => open ? closeMenu() : openMenu()} onKeyDown={(event) => {
      if (event.key === 'ArrowDown') { event.preventDefault(); openMenu() }
    }}>
      <svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="8.5" cy="8.5" r="5" /><path d="m12.5 12.5 4 4" /></svg>
      <span>{currentName ?? 'Jump to project or assembly…'}</span><kbd>{shortcut}</kbd>
    </button>
    {open && position ? createPortal(<div ref={panelRef} id={panelId} role="dialog" aria-label="Jump to project or assembly" className="catalog-quick-popover" style={position} onKeyDown={onMenuKeyDown} onBlur={(event) => {
      if (event.relatedTarget && !event.currentTarget.contains(event.relatedTarget as Node) && event.relatedTarget !== triggerRef.current) closeMenu()
    }}>
      <input ref={searchRef} type="search" value={query} aria-label="Search projects and assemblies" placeholder="Find a project or assembly…" autoComplete="off" spellCheck={false} onChange={(event) => { setQuery(event.target.value); setActiveId(null) }} />
      <div className="catalog-quick-tabs" role="group" aria-label="Navigation scope">
        {(['all', 'projects'] as const).map((scope) => <button key={scope} type="button" aria-pressed={tab === scope} onClick={() => { setTab(scope); setActiveId(null); searchRef.current?.focus() }}>{scope === 'all' ? 'All' : 'Projects'}</button>)}
      </div>
      <nav className="catalog-quick-results" aria-label="Navigation destinations">
        {resultGroups.map((group) => group.entries.length ? <section key={group.label} className="catalog-quick-group" aria-label={group.label}>
          <h3>{group.label}</h3>
          {group.entries.map((entry) => <a key={entry.key} ref={(node) => { if (node) linkRefs.current.set(entry.key, node); else linkRefs.current.delete(entry.key) }} href={entry.href} className={`catalog-quick-result${activeId === entry.key ? ' keyboard-active' : ''}`} aria-current={entry.current ? 'page' : undefined} aria-label={`${entry.name}${entry.context ? ` — ${entry.context}` : ''}${entry.archived ? ' (archived)' : ''}`} title={`${entry.name}${entry.context ? ` — ${entry.context}` : ''}`} onFocus={() => setActiveId(entry.key)}>
            <span>{entry.name}</span><small>{entry.context}{entry.archived ? ' · archived' : ''}</small>
          </a>)}
        </section> : null)}
        {entries.length === 0 ? <p className="catalog-quick-empty" role="status">No matching projects or assemblies.</p> : null}
      </nav>
    </div>, document.body) : null}
  </div>
}
