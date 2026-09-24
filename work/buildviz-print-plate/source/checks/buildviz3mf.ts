// ---------------------------------------------------------------------------
// Minimal, dependency-free 3MF (3D Manufacturing Format) writer + binary STL
// writer for the plate exporter (buildviz pack --export).
//
// A 3MF file is an OPC (Open Packaging Conventions) ZIP archive containing at
// least:
//   * [Content_Types].xml  — declares the .rels and .model part content types
//   * _rels/.rels          — the package relationship pointing at the 3D model
//   * 3D/3dmodel.model     — the core 3MF XML (namespace
//                            http://schemas.microsoft.com/3dmanufacturing/core/2015/02)
//                            with <resources> objects (mesh vertices+triangles)
//                            and a <build> of <item>s carrying placement
//                            transforms. unit="millimeter".
//
// This is exactly what Bambu Studio (and most slicers) ingest directly, so a
// plate written here opens with every part already arranged on the bed.
//
// The ZIP is hand-rolled (local file headers + central directory + EOCD, with
// CRC-32 and DEFLATE via node:zlib) so the export depends on nothing beyond the
// Node standard library. This module is THREE-free and Node-only (it uses
// Buffer + zlib); geometry is passed in as plain vertex/triangle arrays by the
// caller (checks/packExport.ts), which already has the loaded meshes.
// ---------------------------------------------------------------------------
import { preparePrintMesh } from './printMeshValidation'
import { deflateRawSync } from 'node:zlib'

// 3MF core namespace (the 2015/02 schema slicers expect).
const CORE_NS = 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'

const CONTENT_TYPES_XML =
  '<?xml version="1.0" encoding="UTF-8"?>\n' +
  '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n' +
  '  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n' +
  '  <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>\n' +
  '</Types>\n'

const RELS_XML =
  '<?xml version="1.0" encoding="UTF-8"?>\n' +
  '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n' +
  '  <Relationship Id="rel0" Target="/3D/3dmodel.model" ' +
  'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n' +
  '</Relationships>\n'

// One mesh resource: a 3MF <object> with raw, untransformed geometry. Vertices
// is a flat [x0,y0,z0, x1,y1,z1, ...]; triangles is a flat [a0,b0,c0, ...] of
// 0-based vertex indices.
export type Mesh3mfObject = {
  name?: string
  id: number
  vertices: number[]
  triangles: number[]
}

// One placed part: references an object id and carries the column-major 16-value
// world transform (THREE.Matrix4.toArray order) that arranges it on the plate.
export type Build3mfItem = {
  objectId: number
  transform: number[]
  name?: string
  partType?: string
}

// Preserve coordinate precision; never turn invalid geometry into zeros.
const fmt = (value: number): string => {
  if (!Number.isFinite(value)) throw new Error('Print check failed: non-finite coordinate or transform.')
  return Object.is(value, -0) ? '0' : String(value)
}

const escapeXml = (value: string): string =>
  value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')

// Convert a column-major 16-value matrix (THREE order) into the 3MF 12-value
// row-vector transform "m00 m01 m02 m10 m11 m12 m20 m21 m22 m30 m31 m32".
// 3MF uses the row-vector convention p' = p · M, so the linear block is the
// transpose of the column-vector 3×3 and the translation is the last column.
// In column-major te, M_ij = te[i + j*4]; dropping the homogeneous row (te[3],
// te[7], te[11], te[15] = 0,0,0,1) yields exactly te indices
// [0,1,2, 4,5,6, 8,9,10, 12,13,14].
const to3mfTransform = (te: number[]): string =>
  [te[0], te[1], te[2], te[4], te[5], te[6], te[8], te[9], te[10], te[12], te[13], te[14]]
    .map(fmt)
    .join(' ')

// Build the core 3D/3dmodel.model XML. Objects become <object>/<mesh>
// resources; items become <build><item>s with their placement transforms.
export const build3mfModelXml = (objects: Mesh3mfObject[], items: Build3mfItem[]): string => {
  const ids = new Set(objects.map(o => o.id))
  if (!objects.length || !items.length || ids.size !== objects.length || objects.some(o => !Number.isInteger(o.id) || o.id <= 0)) throw new Error('Print check failed: missing or duplicate 3MF objects.')
  for (const item of items) {
    const t = item.transform
    const det = t[0]*(t[5]*t[10]-t[9]*t[6])-t[4]*(t[1]*t[10]-t[9]*t[2])+t[8]*(t[1]*t[6]-t[5]*t[2])
    if (!Number.isFinite(det) || det === 0) throw new Error('Print check failed: collapsed object placement.')
    if (!ids.has(item.objectId) || item.transform.length !== 16 || !item.transform.every(Number.isFinite) || item.transform[3] !== 0 || item.transform[7] !== 0 || item.transform[11] !== 0 || item.transform[15] !== 1) throw new Error('Print check failed: invalid object placement.')
  }
  const out: string[] = []
  out.push('<?xml version="1.0" encoding="UTF-8"?>')
  out.push(`<model unit="millimeter" xml:lang="en-US" xmlns="${CORE_NS}">`)
  out.push('  <resources>')
  for (const object of objects) {
    out.push(`    <object id="${object.id}" type="model"${object.name ? ` name="${escapeXml(object.name)}"` : ''}>`)
    out.push('      <mesh>')
    out.push('        <vertices>')
    const { vertices, triangles } = preparePrintMesh(object)
    for (let i = 0; i < vertices.length; i += 3) {
      out.push(
        `          <vertex x="${fmt(vertices[i])}" y="${fmt(vertices[i + 1])}" z="${fmt(vertices[i + 2])}"/>`,
      )
    }
    out.push('        </vertices>')
    out.push('        <triangles>')
    for (let i = 0; i < triangles.length; i += 3) {
      out.push(
        `          <triangle v1="${triangles[i]}" v2="${triangles[i + 1]}" v3="${triangles[i + 2]}"/>`,
      )
    }
    out.push('        </triangles>')
    out.push('      </mesh>')
    out.push('    </object>')
  }
  out.push('  </resources>')
  out.push('  <build>')
  for (const item of items) {
    out.push(`    <item objectid="${item.objectId}" transform="${to3mfTransform(item.transform)}"/>`)
  }
  out.push('  </build>')
  out.push('</model>')
  return `${out.join('\n')}\n`
}

// --- Minimal ZIP writer (CRC-32 + DEFLATE) ---------------------------------

const CRC_TABLE = (() => {
  const table = new Uint32Array(256)
  for (let n = 0; n < 256; n += 1) {
    let c = n
    for (let k = 0; k < 8; k += 1) {
      c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1
    }
    table[n] = c >>> 0
  }
  return table
})()

const crc32 = (data: Buffer): number => {
  let crc = 0xffffffff
  for (let i = 0; i < data.length; i += 1) {
    crc = CRC_TABLE[(crc ^ data[i]) & 0xff] ^ (crc >>> 8)
  }
  return (crc ^ 0xffffffff) >>> 0
}

type ZipEntry = { name: string; data: Buffer }

// Assemble a valid ZIP (no zip64; small parts) from in-memory entries. Each
// entry is DEFLATE-compressed unless that would grow it (then STORED). The CRC
// is always computed over the UNCOMPRESSED bytes, per the ZIP spec.
export const createZip = (entries: ZipEntry[]): Buffer => {
  const parts: Buffer[] = []
  const central: Buffer[] = []
  let offset = 0

  for (const entry of entries) {
    const nameBuf = Buffer.from(entry.name, 'utf8')
    const crc = crc32(entry.data)
    const deflated = deflateRawSync(entry.data)
    const stored = deflated.length >= entry.data.length
    const method = stored ? 0 : 8
    const body = stored ? entry.data : deflated

    const local = Buffer.alloc(30)
    local.writeUInt32LE(0x04034b50, 0) // local file header signature
    local.writeUInt16LE(20, 4) // version needed to extract (2.0)
    local.writeUInt16LE(0, 6) // general purpose flags
    local.writeUInt16LE(method, 8)
    local.writeUInt16LE(0, 10) // mod time
    local.writeUInt16LE(0x21, 12) // mod date (1980-01-01)
    local.writeUInt32LE(crc, 14)
    local.writeUInt32LE(body.length, 18)
    local.writeUInt32LE(entry.data.length, 22)
    local.writeUInt16LE(nameBuf.length, 26)
    local.writeUInt16LE(0, 28) // extra length
    parts.push(local, nameBuf, body)

    const cd = Buffer.alloc(46)
    cd.writeUInt32LE(0x02014b50, 0) // central directory signature
    cd.writeUInt16LE(20, 4) // version made by
    cd.writeUInt16LE(20, 6) // version needed
    cd.writeUInt16LE(0, 8) // flags
    cd.writeUInt16LE(method, 10)
    cd.writeUInt16LE(0, 12) // mod time
    cd.writeUInt16LE(0x21, 14) // mod date
    cd.writeUInt32LE(crc, 16)
    cd.writeUInt32LE(body.length, 20)
    cd.writeUInt32LE(entry.data.length, 24)
    cd.writeUInt16LE(nameBuf.length, 28)
    cd.writeUInt16LE(0, 30) // extra length
    cd.writeUInt16LE(0, 32) // comment length
    cd.writeUInt16LE(0, 34) // disk number start
    cd.writeUInt16LE(0, 36) // internal attrs
    cd.writeUInt32LE(0, 38) // external attrs
    cd.writeUInt32LE(offset, 42) // local header offset
    central.push(cd, nameBuf)

    offset += local.length + nameBuf.length + body.length
  }

  const centralBuf = Buffer.concat(central)
  const eocd = Buffer.alloc(22)
  eocd.writeUInt32LE(0x06054b50, 0) // end of central directory signature
  eocd.writeUInt16LE(0, 4) // disk number
  eocd.writeUInt16LE(0, 6) // disk with central directory
  eocd.writeUInt16LE(entries.length, 8) // entries on this disk
  eocd.writeUInt16LE(entries.length, 10) // total entries
  eocd.writeUInt32LE(centralBuf.length, 12) // central directory size
  eocd.writeUInt32LE(offset, 16) // central directory offset
  eocd.writeUInt16LE(0, 20) // comment length

  return Buffer.concat([...parts, centralBuf, eocd])
}

// Assemble a complete 3MF archive (OPC zip) from mesh objects + build items.
export const create3mf = (objects: Mesh3mfObject[], items: Build3mfItem[]): Buffer => {
  const model = build3mfModelXml(objects, items)
  return createZip([
    { name: '[Content_Types].xml', data: Buffer.from(CONTENT_TYPES_XML, 'utf8') },
    { name: '_rels/.rels', data: Buffer.from(RELS_XML, 'utf8') },
    { name: '3D/3dmodel.model', data: Buffer.from(model, 'utf8') },
  ])
}

// --- Binary STL writer (fallback --format stl) -----------------------------

export type StlTriangle = {
  v1: [number, number, number]
  v2: [number, number, number]
  v3: [number, number, number]
}

const triangleNormal = (t: StlTriangle): [number, number, number] => {
  const ux = t.v2[0] - t.v1[0]
  const uy = t.v2[1] - t.v1[1]
  const uz = t.v2[2] - t.v1[2]
  const vx = t.v3[0] - t.v1[0]
  const vy = t.v3[1] - t.v1[1]
  const vz = t.v3[2] - t.v1[2]
  const nx = uy * vz - uz * vy
  const ny = uz * vx - ux * vz
  const nz = ux * vy - uy * vx
  const len = Math.hypot(nx, ny, nz)
  if (!Number.isFinite(len) || len < 1e-12) return [0, 0, 0]
  return [nx / len, ny / len, nz / len]
}

// Pack a list of world-space triangles into a binary STL (80-byte header,
// uint32 count, then 50 bytes per facet). A merged per-plate STL is the
// fallback format for slicers that prefer STL over 3MF (it loses per-part
// identity and arrangement metadata, but the geometry lands in bed coordinates).
export const createBinaryStl = (triangles: StlTriangle[]): Buffer => {
  const buffer = Buffer.alloc(84 + triangles.length * 50)
  buffer.write('BuildViz plate export', 0, 'ascii')
  buffer.writeUInt32LE(triangles.length, 80)
  let offset = 84
  for (const triangle of triangles) {
    const [nx, ny, nz] = triangleNormal(triangle)
    buffer.writeFloatLE(nx, offset)
    buffer.writeFloatLE(ny, offset + 4)
    buffer.writeFloatLE(nz, offset + 8)
    buffer.writeFloatLE(triangle.v1[0], offset + 12)
    buffer.writeFloatLE(triangle.v1[1], offset + 16)
    buffer.writeFloatLE(triangle.v1[2], offset + 20)
    buffer.writeFloatLE(triangle.v2[0], offset + 24)
    buffer.writeFloatLE(triangle.v2[1], offset + 28)
    buffer.writeFloatLE(triangle.v2[2], offset + 32)
    buffer.writeFloatLE(triangle.v3[0], offset + 36)
    buffer.writeFloatLE(triangle.v3[1], offset + 40)
    buffer.writeFloatLE(triangle.v3[2], offset + 44)
    buffer.writeUInt16LE(0, offset + 48) // attribute byte count
    offset += 50
  }
  return buffer
}
