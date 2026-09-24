import type { BuildVersionEntry } from './buildModel'
import type { CatalogRevision, CatalogSource } from './catalogModel'

export type WorkflowPartKind = 'printed' | 'purchased' | 'other'
export type WorkflowPartMetadata = {
  kind: WorkflowPartKind
  label?: string
  material?: string
  url?: string
  notes?: string
  evidence?: string
}
export type WorkflowBomItem = {
  id: string; label: string; quantity: number; unit?: string; url?: string; notes?: string; partTypes?: string[]
}
export type WorkflowInstruction = {
  id: string; title: string; url?: string; text?: string; partTypes?: string[]
}
export type WorkflowRun = {
  id: string; title: string; url: string; videoUrl?: string
  kind?: 'mujoco' | 'training' | 'evaluation' | 'other'
  status?: string; summary?: string; model?: string; partTypes?: string[]
  association?: 'exact-revision' | 'robot-family' | 'unverified'
  source?: CatalogSource
}
/** Authored metadata. A mesh's existence alone never establishes printability. */
export type WorkflowMetadata = {
  schema: 1
  parts: Record<string, WorkflowPartMetadata>
  bom?: { notes?: string; items?: WorkflowBomItem[] }
  instructions?: WorkflowInstruction[]
  runs?: WorkflowRun[]
}
export type WorkflowQuery = { build: string; branch?: string; version?: string; compare?: string; catalog?: string }
export type WorkflowProvenance = {
  level: 'exact-revision' | 'branch-fallback' | 'build-fallback' | 'missing'
  file: 'workflow.json' | 'design_spec.yaml'
  note: string
}
export type WorkflowChange = 'new' | 'changed' | 'quantity' | 'unchanged' | 'unavailable' | 'not-compared'
export type WorkflowFile = {
  id: string; fileName: string; meshIds: string[]; sha256: string; geometrySha256: string; bytes: number
  quantity: number; previousQuantity: number | null; quantityToPrint: number
  change: WorkflowChange; downloadUrl: string
}
export type WorkflowPart = {
  partType: string; label: string; kind: WorkflowPartKind | 'unknown'; quantity: number
  instanceIds: string[]; material?: string; url?: string; notes?: string; evidence?: string
  classificationSource: 'workflow' | 'design-spec' | 'unclassified'
  files: WorkflowFile[]; errors: string[]
}
export type BuildWorkflows = {
  schema: 1
  source: CatalogRevision & { name: string; units: string; storage: 'snapshot' | 'working-copy' }
  scope: { catalogId?: string; name?: string; selectedInstances: number; totalInstances: number }
  metadata: { workflow: WorkflowProvenance; designSpec: WorkflowProvenance }
  printed: WorkflowPart[]; purchased: WorkflowPart[]; other: WorkflowPart[]; unknown: WorkflowPart[]
  bom: { notes?: string; items: WorkflowBomItem[] }
  instructions: WorkflowInstruction[]; runs: WorkflowRun[]
  baselines: BuildVersionEntry[]
  comparison: { version: string | null; automatic: boolean; note: string; removed: Array<{ partType: string; quantity: number }> }
  downloads: { all: string; changed: string | null; quantities: string }
  warnings: string[]
}
