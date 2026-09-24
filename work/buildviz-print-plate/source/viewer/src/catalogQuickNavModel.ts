import type { CatalogItem } from '../../core/catalogModel'
import type { BuildsIndexBuild } from '../../core/buildModel'
import { catalogHref, projectHref, projectLabel, sourceHref } from './catalogLinks'

export const QUICK_NAV_GROUPS = [
  { kind: 'assembly', label: 'Assemblies' },
  { kind: 'robot', label: 'Robots' },
  { kind: 'view', label: 'Saved views' },
  { kind: 'study', label: 'Studies' },
  { kind: 'build', label: 'Other builds' },
  { kind: 'project', label: 'Projects' },
] as const

export type QuickNavEntry = {
  key: string
  name: string
  kind: (typeof QUICK_NAV_GROUPS)[number]['kind']
  context: string
  href: string
  current: boolean
  archived?: boolean
  ownText: string
  parentText: string
  nearby: boolean
}

// Treat natural phrases and producer slugs alike: "one motor cat" should
// discover single-motor-cat, including builds named for its TT motor.
const normalize = (value: string) => value.toLocaleLowerCase().normalize('NFKD')
  .replace(/\p{Diacritic}/gu, '').replace(/[^\p{Letter}\p{Number}]+/gu, ' ').trim()
  .split(/\s+/).map((word) => ['one', 'single', '1'].includes(word) ? 'single' : word).join(' ')

export function quickNavEntries({ items, builds = [], currentId, currentBuildId, query = '', projectsOnly = false }: {
  items: CatalogItem[]
  builds?: BuildsIndexBuild[]
  currentId?: string
  currentBuildId?: string
  query?: string
  projectsOnly?: boolean
}): QuickNavEntry[] {
  const byId = new Map(items.map((item) => [item.id, item]))
  const ancestorsOf = (item: CatalogItem) => {
    const ancestors: CatalogItem[] = []
    const seen = new Set([item.id])
    let parentId = item.parentId
    while (parentId && !seen.has(parentId)) {
      seen.add(parentId)
      const parent = byId.get(parentId)
      if (!parent) break
      ancestors.unshift(parent)
      parentId = parent.parentId
    }
    return ancestors
  }
  const currentItem = currentId ? byId.get(currentId) : undefined
  const currentRobot = currentItem?.kind === 'robot' ? currentItem : currentItem && ancestorsOf(currentItem).find((item) => item.kind === 'robot')
  const currentBuild = builds.find((build) => build.id === currentBuildId)
  const coveredBuilds = new Set(items.flatMap((item) => [item.source, item.asBuilt, ...(item.milestones?.map((milestone) => milestone.source) ?? [])].flatMap((source) => source ? [source.buildId] : [])))
  const projects = new Map<string, BuildsIndexBuild[]>()
  builds.forEach((build) => projects.set(build.project, [...(projects.get(build.project) ?? []), build]))

  const entries: QuickNavEntry[] = items
    .filter((item) => item.status !== 'archived' || item.id === currentId)
    .map((item) => {
      const ancestors = ancestorsOf(item)
      const robot = item.kind === 'robot' ? item : ancestors.find((ancestor) => ancestor.kind === 'robot')
      return {
        key: `catalog:${item.id}`, name: item.name, kind: item.kind,
        context: ancestors.map((ancestor) => ancestor.name).join(' › ') || item.collection,
        href: catalogHref(item.id), current: currentId === item.id, archived: item.status === 'archived',
        ownText: [item.name, item.id, item.kind, item.collection, ...(item.aliases ?? [])].join(' '),
        parentText: ancestors.flatMap((ancestor) => [ancestor.name, ancestor.id, ...(ancestor.aliases ?? [])]).join(' '),
        nearby: Boolean(currentRobot && robot?.id === currentRobot.id),
      }
    })

  builds.filter((build) => !coveredBuilds.has(build.id)).forEach((build) => entries.push({
    key: `build:${build.id}`, name: build.name ?? build.build, kind: 'build', context: projectLabel(build.project),
    href: sourceHref({ buildId: build.id }), current: !currentId && currentBuildId === build.id,
    ownText: [build.name, build.build, build.id, 'build'].join(' '), parentText: `${projectLabel(build.project)} project`,
    nearby: currentBuild?.project === build.project,
  }))
  projects.forEach((projectBuilds, id) => entries.push({
    key: `project:${id}`, name: projectLabel(id), kind: 'project',
    context: `${projectBuilds.length} build${projectBuilds.length === 1 ? '' : 's'}`,
    href: projectHref(id), current: false,
    ownText: `${projectLabel(id)} ${id} project`, parentText: projectBuilds.map((build) => `${build.name ?? ''} ${build.build}`).join(' '),
    nearby: currentBuild?.project === id,
  }))

  const normalizedQuery = normalize(query)
  const terms = normalizedQuery.split(/\s+/).filter(Boolean)
  return entries.filter((entry) => !projectsOnly || entry.kind === 'project')
    .map((entry) => {
      const name = normalize(entry.name), own = normalize(entry.ownText), all = `${own} ${normalize(entry.parentText)}`
      const relevance = name === normalizedQuery ? 0 : terms.every((term) => name.includes(term)) ? 1 : terms.every((term) => own.includes(term)) ? 2 : 3
      return { entry, relevance, matches: terms.every((term) => all.includes(term)) }
    })
    .filter((result) => result.matches)
    .sort((a, b) => (terms.length ? a.relevance - b.relevance : 0)
      || QUICK_NAV_GROUPS.findIndex((group) => group.kind === a.entry.kind) - QUICK_NAV_GROUPS.findIndex((group) => group.kind === b.entry.kind)
      || (a.entry.kind === 'project' && b.entry.kind === 'project' ? a.entry.name.localeCompare(b.entry.name, undefined, { numeric: true }) : 0)
      || Number(b.entry.nearby) - Number(a.entry.nearby)
      || a.entry.context.localeCompare(b.entry.context, undefined, { numeric: true })
      || a.entry.name.localeCompare(b.entry.name, undefined, { numeric: true }))
    .map((result) => result.entry)
}
