import type { CatalogItem } from '../../core/catalogModel'
import type { BuildsIndexBuild } from '../../core/buildModel'
type Source = CatalogItem['source']

export const catalogHref = (id: string) => `?catalog=${encodeURIComponent(id)}`
export const projectHref = (id: string) => `?project=${encodeURIComponent(id)}`
export const projectLabel = (id: string) => {
  const label = id.replace(/[-_]+/g, ' ')
  return label.charAt(0).toLocaleUpperCase() + label.slice(1)
}

export const sourceHref = (source: Source, contextId?: string) => {
  const params = new URLSearchParams({ build: source.buildId })
  if (source.branch) params.set('branch', source.branch)
  if (source.version) params.set('version', source.version)
  if (contextId) params.set('catalogContext', contextId)
  return `?${params}`
}

export const sourceLabel = (source: Source) =>
  `${source.branch ?? 'default branch'} · ${source.version ?? 'current revision'}`

export const sourceProblem = (source: Source, builds: BuildsIndexBuild[] | null): string | null => {
  if (builds === null) return 'The build index is unavailable, so this reference cannot be verified.'
  const build = builds.find((candidate) => candidate.id === source.buildId)
  if (!build) return `The source build “${source.buildId}” is unavailable on this hub.`
  const branchName = source.branch ?? build.defaultBranch ?? 'main'
  const branch = build.branches?.find((candidate) => candidate.name === branchName)
  if (!branch && branchName !== (build.defaultBranch ?? 'main')) {
    return `The source branch “${branchName}” is unavailable on this hub.`
  }
  const versions = branch?.versions ?? build.versions
  const defaultVersion = branch?.defaultVersion ?? build.defaultVersion
  if (source.version && source.version !== 'latest' && source.version !== defaultVersion && !versions.some((version) => version.name === source.version)) {
    return `The source revision “${source.version}” is unavailable on this hub.`
  }
  return null
}
