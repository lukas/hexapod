// `buildviz push-stl` — one-command publish of loose STL and/or STEP file(s)
// as a hub build.
//
// Composes a minimal scene.json (one mesh + one identity-transform instance per
// part, combined bbox center) and delegates to the regular `push` pipeline with
// `--upload-assets`, so the pushed build is self-contained in the hub cache and
// immediately gets the whole single-part toolset: the viewer URL, `drawing`,
// `probe`/`slice`/`thickness`, and the printability side of `check`.
//
// STEP (.step/.stp) files are tessellated at ingest via OpenCascade (see
// cli/stepImport.ts): every solid in the assembly becomes its own part, named
// and colored from the STEP assembly tree — one STEP file can yield a whole
// multi-part build. The internal representation stays mesh/STL.
//
// Defaults to `--bump` (accumulate v1, v2, … history) unless the caller passes
// an explicit `--version`. Intended for one-off printables — replacement
// brackets, experimental variants — that would otherwise never make it into
// the hub because writing a scene.json by hand isn't worth it for one part.
import { copyFile, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import {
  CURRENT_SCENE_SCHEMA_VERSION,
  type BuildInstance,
  type BuildMesh,
  type BuildSceneManifest,
} from '../../core/buildScene'
import { parseStl } from '../../core/geometryEngine'
import { pushToHub } from '../../hub/hub'
import { isStepFile, tessellateStepFile } from '../stepImport'
import {
  optionString,
  parseArgs,
  resolveProjectBuild,
  type CliOptions,
} from '../../hub/cliShared'

// Small qualitative palette so multi-file pushes get distinguishable parts.
const PALETTE = ['#4878b0', '#d1605e', '#6aa56e', '#b58fc3', '#c8a552', '#5fa8ad']

const slugify = (value: string) =>
  value
    .toLowerCase()
    .replace(/[^a-z0-9._-]+/g, '_')
    .replace(/^_+|_+$/g, '') || 'part'

// Flags consumed here; everything else recognized by `push` is forwarded.
const FORWARDED_STRING_FLAGS = [
  'version', 'branch', 'message', 'reason', 'keep', 'max-upload-mb', 'design-spec', 'port', 'url',
]
const FORWARDED_BOOLEAN_FLAGS = [
  'bump', 'set-default', 'set-default-branch', 'no-default', 'no-snapshot',
  'no-autostart', 'json',
]

const forwardOptions = (options: CliOptions): string[] => {
  const out: string[] = []
  for (const name of FORWARDED_STRING_FLAGS) {
    const value = optionString(options, name)
    if (value !== undefined) out.push(`--${name}`, value)
  }
  for (const name of FORWARDED_BOOLEAN_FLAGS) {
    if (options[name]) out.push(`--${name}`)
  }
  return out
}

// One part headed for the composed scene: where its STL lives in the staging
// dir, plus naming/color/bounds metadata.
type StagedPart = {
  slug: string
  displayName: string
  relUrl: string
  color?: string
  centroid?: [number, number, number]
  bbox?: { min: [number, number, number]; max: [number, number, number] }
}

const parseDeflection = (options: CliOptions, name: string): number | undefined => {
  const raw = optionString(options, name)
  if (raw === undefined) return undefined
  const value = Number(raw)
  if (!Number.isFinite(value) || value <= 0) throw new Error(`Invalid --${name} "${raw}"`)
  return value
}

export const pushStlCommand = async (args: string[]) => {
  const { positional, options } = parseArgs(args)
  if (positional.length === 0) {
    throw new Error(
      'push-stl requires at least one STL or STEP file:\n' +
        '  buildviz push-stl part.stl assembly.step [more ...] [--project <p>] [--build <b>] ' +
        '[--name "Display name"] [--part-type <type>] [--units mm] ' +
        '[--linear-deflection <mm>] [--angular-deflection <rad>] [-m <note>] [push flags]',
    )
  }

  const files = positional.map((file) => path.resolve(process.cwd(), file))
  for (const file of files) {
    if (!existsSync(file)) throw new Error(`File not found: ${file}`)
    if (path.extname(file).toLowerCase() !== '.stl' && !isStepFile(file)) {
      throw new Error(`push-stl handles .stl and .step/.stp files (got ${path.basename(file)})`)
    }
  }

  const unitsOpt = optionString(options, 'units') ?? 'mm'
  if (unitsOpt !== 'mm' && unitsOpt !== 'cm' && unitsOpt !== 'm') {
    throw new Error(`Invalid --units "${unitsOpt}"; use mm, cm, or m.`)
  }
  const partTypeOpt = optionString(options, 'part-type', 'partType')
  const linearDeflectionMm = parseDeflection(options, 'linear-deflection')
  const angularDeflectionRad = parseDeflection(options, 'angular-deflection')

  // Every part's STL is staged into one temp dir (STEP-derived parts have no
  // on-disk STL to reference in place, so staging everything keeps the asset
  // dir uniform).
  const tempDir = await mkdtemp(path.join(os.tmpdir(), 'buildviz-push-stl-'))
  try {
    const staged: StagedPart[] = []
    const seenSlugs = new Set<string>()
    const uniqueSlug = (base: string) => {
      let slug = base
      let suffix = 2
      while (seenSlugs.has(slug)) slug = `${base}_${suffix++}`
      seenSlugs.add(slug)
      return slug
    }

    for (const file of files) {
      if (isStepFile(file)) {
        const bytes = await readFile(file)
        const parts = await tessellateStepFile(new Uint8Array(bytes), path.basename(file), {
          linearDeflectionMm,
          angularDeflectionRad,
        })
        console.log(`Tessellated ${path.basename(file)}: ${parts.length} solid(s)`)
        for (const part of parts) {
          const slug = uniqueSlug(slugify(part.name))
          const relUrl = `${slug}.stl`
          await writeFile(path.join(tempDir, relUrl), part.stl)
          staged.push({
            slug,
            displayName: part.name,
            relUrl,
            color: part.color,
            bbox: part.bboxMm,
            centroid: [
              (part.bboxMm.min[0] + part.bboxMm.max[0]) / 2,
              (part.bboxMm.min[1] + part.bboxMm.max[1]) / 2,
              (part.bboxMm.min[2] + part.bboxMm.max[2]) / 2,
            ],
          })
        }
      } else {
        const buffer = await readFile(file)
        const data = buffer.buffer.slice(
          buffer.byteOffset,
          buffer.byteOffset + buffer.byteLength,
        ) as ArrayBuffer
        const geometry = parseStl(data)
        const box = geometry.boundingBox
        const slug = uniqueSlug(slugify(path.basename(file, path.extname(file))))
        const relUrl = `${slug}.stl`
        await copyFile(file, path.join(tempDir, relUrl))
        staged.push({
          slug,
          displayName: path.basename(file),
          relUrl,
          ...(box
            ? {
                bbox: {
                  min: [box.min.x, box.min.y, box.min.z],
                  max: [box.max.x, box.max.y, box.max.z],
                },
                centroid: [
                  (box.min.x + box.max.x) / 2,
                  (box.min.y + box.max.y) / 2,
                  (box.min.z + box.max.z) / 2,
                ] as [number, number, number],
              }
            : {}),
        })
        geometry.dispose()
      }
    }

    const meshes: BuildMesh[] = []
    const instances: BuildInstance[] = []
    const min = [Infinity, Infinity, Infinity]
    const max = [-Infinity, -Infinity, -Infinity]
    for (const [index, part] of staged.entries()) {
      if (part.bbox) {
        for (let axis = 0; axis < 3; axis += 1) {
          min[axis] = Math.min(min[axis], part.bbox.min[axis])
          max[axis] = Math.max(max[axis], part.bbox.max[axis])
        }
      }
      meshes.push({ id: `stl:${part.slug}`, name: part.displayName, url: part.relUrl })
      instances.push({
        id: part.slug,
        meshId: `stl:${part.slug}`,
        name: part.displayName,
        partType: partTypeOpt ?? part.slug,
        role: 'extra part',
        color: part.color ?? PALETTE[index % PALETTE.length],
        transform: [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
        // The viewer's camera fit reads per-instance centroids.
        ...(part.centroid ? { centroid: part.centroid } : {}),
      })
    }

    const firstSlug = instances[0].id
    const { buildId } = resolveProjectBuild(options, undefined, firstSlug)
    const displayName = optionString(options, 'name') ?? firstSlug

    const center: [number, number, number] = Number.isFinite(min[0])
      ? [(min[0] + max[0]) / 2, (min[1] + max[1]) / 2, (min[2] + max[2]) / 2]
      : [0, 0, 0]
    const scene: BuildSceneManifest = {
      name: displayName,
      source: `buildviz push-stl (${files.map((file) => path.basename(file)).join(', ')})`,
      schemaVersion: CURRENT_SCENE_SCHEMA_VERSION,
      units: unitsOpt,
      center,
      meshes,
      instances,
    }

    const scenePath = path.join(tempDir, 'scene.json')
    await writeFile(scenePath, JSON.stringify(scene, null, 2))
    const pushArgs = [
      '--scene', scenePath,
      '--assets-dir', tempDir,
      '--upload-assets',
      '--build-id', buildId,
      '--name', displayName,
      ...forwardOptions(options),
    ]
    // Accumulate v1, v2, … by default; an explicit --version opts out.
    if (!optionString(options, 'version') && !options.bump) pushArgs.push('--bump')
    await pushToHub(pushArgs)
  } finally {
    await rm(tempDir, { recursive: true, force: true })
  }
}
