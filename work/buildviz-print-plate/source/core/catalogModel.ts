/** Human/agent organization layered over the existing build/branch/revision store. */
export const CATALOG_KINDS = ['robot', 'assembly', 'view', 'study'] as const
export const CATALOG_STATUSES = ['built', 'planned', 'active', 'archived'] as const
export type CatalogKind = (typeof CATALOG_KINDS)[number]
export type CatalogStatus = (typeof CATALOG_STATUSES)[number]
export type CatalogSource = { buildId: string; branch?: string; version?: string }
export type CatalogRevision = { buildId: string; branch: string; version: string }
export type CatalogItem = {
  id: string
  name: string
  kind: CatalogKind
  collection: string
  description: string
  status: CatalogStatus
  parentId?: string
  source: CatalogSource
  asBuilt?: CatalogRevision & { evidence?: string }
  milestones?: Array<{ name: string; description: string; source: CatalogRevision }>
  view?: { instanceIds?: string[]; partTypes?: string[] }
  aliases?: string[]
}
export type Catalog = { schema: 1; items: CatalogItem[] }
export type CatalogFilter = { kind?: string; collection?: string; parentId?: string; query?: string }

export const filterCatalog = (catalog: Catalog, filter: CatalogFilter = {}): Catalog => {
  const query = filter.query?.trim().toLowerCase()
  return {
    schema: 1,
    items: catalog.items.filter((item) =>
      (!filter.kind || item.kind === filter.kind) &&
      (!filter.collection || item.collection === filter.collection) &&
      (!filter.parentId || item.parentId === filter.parentId) &&
      (!query || [item.id, item.name, item.description, item.collection, item.source.buildId,
        item.source.branch, ...(item.aliases ?? [])].join(' ').toLowerCase().includes(query)),
    ),
  }
}

export const catalogItemUrl = (item: CatalogItem, base = '') => {
  const params = new URLSearchParams({ catalog: item.id, build: item.source.buildId })
  if (item.source.branch) params.set('branch', item.source.branch)
  if (item.source.version) params.set('version', item.source.version)
  return `${base.replace(/\/$/, '')}/?${params}`
}
