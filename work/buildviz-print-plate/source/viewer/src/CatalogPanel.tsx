import { useState } from 'react'
import type { CatalogItem } from '../../core/catalogModel'
import { compareVersionNames, groupBuildsByProject, type BuildsIndexBuild } from '../../core/buildModel'
import './CatalogPanel.css'
import { catalogHref, projectHref, projectLabel, sourceHref, sourceLabel, sourceProblem } from './catalogLinks'
import { CatalogQuickNav } from './CatalogQuickNav'

type Source = CatalogItem['source']
const kindLabels = { robot: 'Robot', assembly: 'Assembly', view: 'Saved view', study: 'Study' }
const groupLabels = { assembly: 'Assemblies', view: 'Saved views', study: 'Studies' }

const ItemLink = ({ item }: { item: CatalogItem }) => (
  <a className="catalog-item-link" href={catalogHref(item.id)}>
    <span><strong>{item.name}</strong><small>{kindLabels[item.kind]} · {item.status}</small></span>
    <p>{item.description}</p>
  </a>
)

export function CatalogHome({ items, builds }: { items: CatalogItem[]; builds: BuildsIndexBuild[] | null }) {
  const [showArchived, setShowArchived] = useState(false)
  const visible = items.filter((item) => showArchived || item.status !== 'archived')
  const collections = [...new Set(visible.map((item) => item.collection))]
  const linkedBuilds = new Set(items.map((item) => item.source.buildId))
  const otherBuilds = builds?.filter((build) => !linkedBuilds.has(build.id)) ?? []
  return (
    <main className="catalog-home">
      <header className="catalog-home-header">
        <div><p className="catalog-eyebrow">BuildViz</p><h1>Your workshop</h1><p>Jump to a project or assembly, or choose a robot.</p></div>
        <div className="catalog-home-jump"><CatalogQuickNav items={items} builds={builds ?? []} /><a className="catalog-projects-link" href="?projects=1">Browse all projects →</a></div>
      </header>
      <label className="catalog-archive-toggle"><input type="checkbox" checked={showArchived} onChange={(event) => setShowArchived(event.target.checked)} /> Include archived items</label>
      {collections.map((collection) => {
        const entries = visible.filter((item) => item.collection === collection)
        const robots = entries.filter((item) => item.kind === 'robot')
        const loose = entries.filter((item) => item.kind !== 'robot' && (!item.parentId || (showArchived && item.status === 'archived')))
        return <section className="catalog-collection" key={collection}>
          <div className="catalog-section-heading"><h2>{collection.charAt(0).toLocaleUpperCase() + collection.slice(1)}</h2><small>{robots.length} robot{robots.length === 1 ? '' : 's'}</small></div>
          <div className="catalog-robot-grid">{robots.map((robot) => {
            const children = items.filter((item) => item.parentId === robot.id && item.status !== 'archived')
            const problem = sourceProblem(robot.source, builds)
            return <article className="catalog-robot-card" key={robot.id}>
              <div className="catalog-card-heading"><span className={`catalog-status status-${robot.status}`}>{robot.status}</span><small>Robot</small></div>
              <h3><a href={catalogHref(robot.id)}>{robot.name}</a></h3>
              {children.some((child) => child.kind === 'assembly') ? <nav className="catalog-card-assemblies" aria-label={`${robot.name} assemblies`}>
                {children.filter((child) => child.kind === 'assembly').map((child) => <a key={child.id} href={catalogHref(child.id)}>{child.name}<span aria-hidden="true">→</span></a>)}
              </nav> : null}
              <div className="catalog-card-configurations">
                <a href={catalogHref(robot.id)}><strong>Current design →</strong><small>{sourceLabel(robot.source)}</small></a>
                {robot.asBuilt ? <a href={`${catalogHref(robot.id)}&configuration=as-built`}><strong>As built →</strong><small>{sourceLabel(robot.asBuilt)}</small></a> : <div><strong>{robot.status === 'planned' ? 'Planned build' : 'As built unverified'}</strong><small>{robot.status === 'planned' ? 'No installed configuration yet' : 'Installed revision has not been recorded'}</small></div>}
              </div>
              {problem ? <p className="catalog-notice">{problem}</p> : null}
              <details className="catalog-card-about"><summary>About this robot</summary><p>{robot.description}</p></details>
            </article>
          })}</div>
          {loose.length > 0 ? <div className="catalog-loose-items">{loose.map((item) => <ItemLink key={item.id} item={item} />)}</div> : null}
        </section>
      })}
      {visible.length === 0 ? <p className="catalog-empty">No active catalog items yet.</p> : null}
      {otherBuilds.length > 0 ? <details className="catalog-legacy"><summary>Other builds · {otherBuilds.length}</summary><p>Existing builds that have not been organized into the workshop.</p><div className="catalog-loose-items">{otherBuilds.map((build) => <a className="catalog-item-link" key={build.id} href={sourceHref({ buildId: build.id })}><strong>{build.name ?? build.build}</strong><small>{build.project} · {build.versions.length} revisions</small></a>)}</div></details> : null}
    </main>
  )
}

export function ProjectBrowser({ items, builds, projectId }: { items: CatalogItem[]; builds: BuildsIndexBuild[] | null; projectId?: string }) {
  const projects = groupBuildsByProject(builds ?? [])
  const project = projects.find((entry) => entry.id === projectId)
  return <main className="catalog-home catalog-project-browser">
    <nav className="catalog-project-breadcrumb" aria-label="Project location"><a href="/">Workshop</a>{projectId ? <><span aria-hidden="true">/</span><a href="?projects=1">Projects</a></> : null}</nav>
    <header className="catalog-home-header">
      <div><p className="catalog-eyebrow">{projectId ? 'Project' : 'BuildViz'}</p><h1>{project ? projectLabel(project.id) : projectId ? 'Project unavailable' : 'Projects'}</h1><p>{project ? `${project.builds.length} build${project.builds.length === 1 ? '' : 's'}` : projectId ? `“${projectId}” is not in this hub’s build index.` : `${projects.length} projects in your workshop`}</p></div>
      <div className="catalog-home-jump"><CatalogQuickNav items={items} builds={builds ?? []} /></div>
    </header>
    {builds === null ? <p className="catalog-notice">The build index is unavailable. Reload to try again.</p> : project ? <nav className="catalog-project-rows" aria-label={`${projectLabel(project.id)} builds`}>
      {project.builds.map((build) => <a key={build.id} href={sourceHref({ buildId: build.id })}>
        <span><strong>{build.name || projectLabel(build.build)}</strong><small>{build.build} · {build.defaultBranch ?? 'main'} · {build.defaultVersion}</small></span><span aria-hidden="true">→</span>
      </a>)}
    </nav> : !projectId ? <nav className="catalog-project-rows" aria-label="All projects">
      {projects.map((entry) => <a key={entry.id} href={projectHref(entry.id)}><span><strong>{projectLabel(entry.id)}</strong><small>{entry.builds.length} build{entry.builds.length === 1 ? '' : 's'}</small></span><span aria-hidden="true">→</span></a>)}
    </nav> : null}
  </main>
}

export function CatalogSidebar({ item, items, source, configuration }: { item: CatalogItem; items: CatalogItem[]; source: Source; configuration?: string }) {
  const parent = items.find((candidate) => candidate.id === item.parentId)
  return <section className="catalog-sidebar" aria-label="Design catalog">
    <div className="catalog-location"><a href="/">Workshop</a>{parent ? <><span aria-hidden="true">/</span><a href={catalogHref(parent.id)}>{parent.name}</a></> : null}</div>
    {item.view ? <p className="catalog-reference-label">{item.kind === 'view' ? 'Saved view' : 'Assembly selection'} · pinned to {sourceLabel(source)}</p> :
      <div className="catalog-configuration-links"><a href={catalogHref(item.id)} aria-current={configuration === 'current design' ? 'page' : undefined}>Current design</a>{item.asBuilt ? <a href={`${catalogHref(item.id)}&configuration=as-built`} aria-current={configuration === 'as built' ? 'page' : undefined}>As built</a> : item.kind === 'robot' ? <span>{item.status === 'planned' ? 'Build planned' : 'As built unverified'}</span> : null}</div>}
    {configuration && configuration !== 'current design' && configuration !== 'saved view' ? <p className="catalog-viewing">{configuration} · {sourceLabel(source)}</p> : null}
    {configuration === 'as built' && item.asBuilt?.evidence ? <p className="catalog-evidence">{item.asBuilt.evidence}</p> : null}
  </section>
}

export function CatalogDetails({ item, items, source }: { item: CatalogItem; items: CatalogItem[]; source: Source }) {
  const [showArchived, setShowArchived] = useState(false)
  const children = items.filter((candidate) => candidate.parentId === item.id && (showArchived || candidate.status !== 'archived'))
  const archivedCount = items.filter((candidate) => candidate.parentId === item.id && candidate.status === 'archived').length
  return <details className="catalog-about"><summary>About this design</summary>
    <div className="catalog-card-heading"><small>{kindLabels[item.kind]}</small><span className={`catalog-status status-${item.status}`}>{item.status}</span></div>
    <h2>{item.name}</h2><p className="catalog-description">{item.description}</p>
    <p className="catalog-evidence">Source: {source.buildId} · {sourceLabel(source)}</p>
    {item.kind === 'view' ? <p className="catalog-evidence">Saved view of an existing design. Its source revision and selected parts are preserved.</p> : null}
    {item.milestones?.length ? <details className="catalog-related"><summary>Milestones <small>{item.milestones.length}</small></summary><div className="catalog-related-list">{item.milestones.map((milestone, index) => <a className="catalog-item-link" key={`${milestone.name}-${index}`} href={`${catalogHref(item.id)}&milestone=${index}`}><strong>{milestone.name}</strong><p>{milestone.description}</p><small>{sourceLabel(milestone.source)}</small></a>)}</div></details> : null}
    {(['assembly', 'view', 'study'] as const).map((kind) => {
      const entries = children.filter((candidate) => candidate.kind === kind)
      return entries.length ? <details className="catalog-related" key={kind}><summary>{groupLabels[kind]} <small>{entries.length}</small></summary><div className="catalog-related-list">{entries.map((entry) => <ItemLink key={entry.id} item={entry} />)}</div></details> : null
    })}
    {archivedCount ? <label className="catalog-archive-toggle"><input type="checkbox" checked={showArchived} onChange={(event) => setShowArchived(event.target.checked)} /> {showArchived ? 'Showing' : 'Show'} {archivedCount} archived</label> : null}
  </details>
}

export function RevisionHistory({ build, branch, version, contextId }: { build: BuildsIndexBuild | null; branch: string | null; version: string | null; contextId?: string }) {
  const [allBranches, setAllBranches] = useState(false)
  if (!build) return null
  const activeBranch = branch ?? build.defaultBranch ?? 'main'
  const branches = build.branches?.length ? build.branches : [{ name: build.defaultBranch ?? 'main', versions: build.versions, defaultVersion: build.defaultVersion }]
  const activeVersion = version && version !== 'latest' ? version : branches.find((entry) => entry.name === activeBranch)?.defaultVersion
  const revisions = branches.filter((entry) => allBranches || entry.name === activeBranch).flatMap((entry) => entry.versions.map((revision) => ({ ...revision, branch: entry.name }))).sort((a, b) => {
    const dateDifference = Date.parse(b.pushedAt ?? '') - Date.parse(a.pushedAt ?? '')
    return (Number.isFinite(dateDifference) && dateDifference !== 0) ? dateDifference : compareVersionNames(b.name, a.name)
  })
  return <details className="revision-history"><summary>All revisions <small>{revisions.length}</small></summary>
    {branches.length > 1 ? <label className="catalog-archive-toggle"><input type="checkbox" checked={allBranches} onChange={(event) => setAllBranches(event.target.checked)} /> Include other branches</label> : null}
    <ol>{revisions.map((revision) => {
      const date = revision.pushedAt ? new Date(revision.pushedAt) : null
      return <li key={`${revision.branch}@${revision.name}`} className={revision.name === activeVersion && revision.branch === activeBranch ? 'is-current' : ''}>
        <a href={sourceHref({ buildId: build.id, branch: revision.branch, version: revision.name }, contextId)}><strong>{revision.name}</strong>{allBranches ? <span>{revision.branch}</span> : null}</a>
        <time dateTime={revision.pushedAt ?? undefined}>{date && !Number.isNaN(date.getTime()) ? date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) : 'Date not recorded'}</time>
        {revision.messageSource === 'retrospective' ? <small className="revision-retrospective">Description reconstructed later</small> : null}
        <p>{revision.message?.trim() || 'No description was recorded for this older revision.'}</p>
      </li>
    })}</ol>
  </details>
}
