from pathlib import Path
root=Path('work/buildviz-print-plate/source')
p=root/'checks/packExport.ts';s=p.read_text().replace('const buildPlate3mf = (','export const buildPlate3mf = (');p.write_text(s)
p=root/'hub/buildWorkflows.ts';s=p.read_text();s="import { packParts, resolvePrinter, type PackInputPart } from '../checks/buildvizPacking'\nimport { buildPlate3mf, type MeshTriData } from '../checks/packExport'\n"+s
s+='''
/** Arrange the exact workflow inventory, preserving authored STL print poses. */
export const downloadWorkflowPlate = async (deps: BuildWorkflowDeps, query: WorkflowQuery, selection: 'all' | 'changed', printer: string = 'x1c') => {
  if (selection !== 'all' && selection !== 'changed') throw new Error('selection must be all or changed')
  const { response, buffers } = await readInternal(deps, query)
  if (response.source.units !== 'mm') throw new Error('Plate export requires millimeter assets.')
  if (response.printed.some(part => part.errors.length || !part.files.length)) throw new Error('Restore missing printable assets before exporting a plate.')
  if (selection === 'changed' && !response.downloads.changed) throw new Error('Changed plate requires a complete baseline revision.')
  const { bed, id } = resolvePrinter(printer)
  const inputs: PackInputPart[] = []
  const meshData = new Map<string, MeshTriData>()
  for (const part of response.printed) for (const file of part.files) {
    const count = selection === 'changed' ? file.quantityToPrint : file.quantity
    if (!count) continue
    if (!Number.isInteger(count) || inputs.length + count > 1000) throw new Error('Plate export supports at most 1000 whole pieces.')
    const bytes = buffers.get(file.id)
    if (!bytes) throw new Error('Printable asset unavailable.')
    const geometry = parseStl(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer)
    try {
      geometry.computeBoundingBox()
      const box = geometry.boundingBox!
      const min = box.min.toArray() as [number, number, number], max = box.max.toArray() as [number, number, number]
      if (![...min, ...max].every(Number.isFinite)) throw new Error('Invalid printable geometry bounds.')
      const position = geometry.getAttribute('position')
      const vertices = Array.from({ length: position.count * 3 }, (_, n) => position.array[n])
      const triangles = geometry.index ? Array.from(geometry.index.array) : Array.from({ length: position.count }, (_, n) => n)
      meshData.set(file.id, { vertices, triangles })
      for (let copy = 0; copy < count; copy++) inputs.push({
        instanceId: `${part.partType}-${file.id}-${copy}`, meshId: file.id, partType: part.partType, name: part.label, color: '#aaaaaa',
        orientation: { rotation: [1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1], rotationEulerDeg: [0,0,0],
          footprint: { x: max[0]-min[0], y: max[1]-min[1] }, heightMm: max[2]-min[2],
          supportAreaMm2: 0, contactAreaMm2: 0, surfaceAreaMm2: 0, score: 0, kind: 'axis', fitsBed: true, box: { min, max } },
      })
    } finally { geometry.dispose() }
  }
  if (!inputs.length) throw new Error('No printable pieces in this selection.')
  const packed = packParts(inputs, { bed, printer: id, marginMm: 8, spacingMm: 8 })
  const entries = Array.from({ length: packed.totals.plateCount }, (_, plate) => ({
    name: `plate-${plate+1}.3mf`, data: buildPlate3mf(packed.parts.filter(part => part.plate === plate), meshData, plate * (bed.x + Math.max(bed.x, bed.y) * .15)),
  }))
  const stem = `${slug(response.source.buildId)}-${slug(response.source.version)}-${selection}`
  if (entries.length === 1) return { fileName: `${stem}-plate.3mf`, bytes: entries[0].data, contentType: 'model/3mf' }
  entries.push({ name: 'README.txt', data: Buffer.from('Open each 3MF in Bambu Studio. Parts are arranged with their STL orientations and requested quantities. Choose your printer, material and supports, then slice. These files contain no printer or filament settings.') })
  return { fileName: `${stem}-plates.zip`, bytes: zip(entries), contentType: 'application/zip' }
}
''';p.write_text(s)
p=root/'hub/hub.ts';s=p.read_text().replace('downloadBuildWorkflows, downloadWorkflowFile,','downloadWorkflowPlate, downloadBuildWorkflows, downloadWorkflowFile,');s=s.replace(": action === 'file' ? await downloadWorkflowFile", ": action === 'plate' ? await downloadWorkflowPlate(deps, query, (params.get('selection') ?? 'all') as 'all' | 'changed', params.get('printer') ?? 'x1c')\n          : action === 'file' ? await downloadWorkflowFile");s=s.replace("action === 'download' ? 'application/zip'", "'contentType' in download ? download.contentType : action === 'download' ? 'application/zip'");p.write_text(s)
p=root/'viewer/src/BuildWorkflows.tsx';s=p.read_text().replace("const [selection, setSelection]", "const [printer, setPrinter] = useState('x1c')\n  const [plateBusy, setPlateBusy] = useState(false)\n  const [plateError, setPlateError] = useState<string | null>(null)\n  const [selection, setSelection]")
s=s.replace('  const changeTab =', '''  const downloadPlate = async () => {
    if (!zipUrl) return
    setPlateBusy(true); setPlateError(null)
    try {
      const url = new URL(zipUrl)
      url.pathname = '/__buildviz/workflows/plate'
      url.searchParams.set('printer', printer)
      const response = await fetch(url)
      if (!response.ok) throw new Error((await response.json()).error || 'Plate export failed.')
      const blobUrl = URL.createObjectURL(await response.blob())
      const a = document.createElement('a'); a.href = blobUrl
      a.download = response.headers.get('Content-Disposition')?.match(/filename="([^"]+)"/)?.[1] ?? 'print-plate.3mf'
      a.click(); setTimeout(() => URL.revokeObjectURL(blobUrl), 1000)
    } catch (reason) { setPlateError(reason instanceof Error ? reason.message : 'Plate export failed.') }
    finally { setPlateBusy(false) }
  }
  const changeTab =''')
s=s.replace('Unzip the download, import the STLs into Bambu Studio, and set the listed quantities.', 'Download a 3MF tray with every selected copy laid out. Keeps STL orientations; choose material and supports in Bambu Studio, then slice. Large selections download as a ZIP of trays.')
s=s.replace('{zipUrl && uniqueFiles > 0 && !busy && millimeterUnits && missingParts.length === 0 ?', '''<label>Tray size <select aria-label="Tray size" value={printer} onChange={e => setPrinter(e.target.value)}><option value="x1c">256 × 256 mm (X1/P1/A1)</option><option value="h2d">350 × 320 mm (H2D)</option></select></label><button type="button" className="workflow-primary" disabled={!zipUrl || !uniqueFiles || busy || plateBusy || !millimeterUnits || missingParts.length > 0} onClick={() => void downloadPlate()}>{plateBusy ? 'Laying out tray…' : 'Download Bambu tray (.3mf)'}</button>{plateError ? <p role="alert">{plateError}</p> : null}{zipUrl && uniqueFiles > 0 && !busy && millimeterUnits && missingParts.length === 0 ?''')
p.write_text(s)
