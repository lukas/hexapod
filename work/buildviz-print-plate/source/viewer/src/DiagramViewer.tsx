// DIAGRAM mode: a standalone presentation viewer, entirely separate from the
// build viewer. Mounted by main.tsx when the URL carries ?diagram=<name>; it
// renders a hub diagram document (core/diagramModel.ts) — placed shapes and
// build-part snapshots, arrows, polylines, floating text, and callouts with
// leader lines — plus a side panel with the title, presenter notes, and a
// legend. The page polls diagram.json (ETag/304) so an agent can keep editing
// the diagram over MCP while the human watches it update live.
import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js'
import type {
  DiagramArrow,
  DiagramCylinder,
  DiagramDocument,
  DiagramElement,
  DiagramPart,
} from '../../core/diagramModel'
import './DiagramViewer.css'

const POLL_MS = 2000
const DEFAULT_BACKGROUND = '#0f172a'

// Per-kind default colors, tuned for the dark canvas.
const KIND_COLORS: Record<DiagramElement['kind'], string> = {
  box: '#38bdf8',
  sphere: '#38bdf8',
  cylinder: '#38bdf8',
  line: '#94a3b8',
  arrow: '#f97316',
  text: '#e2e8f0',
  callout: '#e2e8f0',
  part: '#a5b4fc',
}

const elementColor = (element: DiagramElement) =>
  element.color ??
  (element.kind === 'part' ? element.mesh?.sourceColor ?? KIND_COLORS.part : KIND_COLORS[element.kind])

const toVector = (point: [number, number, number]) => new THREE.Vector3(...point)

const degToRad = (deg: [number, number, number]) =>
  new THREE.Euler(
    THREE.MathUtils.degToRad(deg[0]),
    THREE.MathUtils.degToRad(deg[1]),
    THREE.MathUtils.degToRad(deg[2]),
    'XYZ',
  )

// One HTML overlay pinned to a world-space point: a floating label, a text
// element, or a callout bubble (with leader line + anchor dot). Positions are
// updated imperatively every frame — no React churn during orbiting.
type OverlayEntry = {
  element: HTMLDivElement
  point: THREE.Vector3
  offset: [number, number]
  center: boolean
  leader?: SVGLineElement
  dot?: HTMLDivElement
}

const solidMaterial = (element: DiagramElement) =>
  new THREE.MeshStandardMaterial({
    color: elementColor(element),
    roughness: 0.55,
    metalness: 0.1,
    transparent: (element.opacity ?? 1) < 1,
    opacity: element.opacity ?? 1,
  })

// Position `object` so its local +Y axis runs from `from` to `to`; returns the length.
const alignYAxis = (object: THREE.Object3D, from: THREE.Vector3, to: THREE.Vector3) => {
  const direction = to.clone().sub(from)
  const length = direction.length()
  if (length > 0) {
    object.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction.normalize())
  }
  object.position.copy(from)
  return length
}

const buildArrow = (element: DiagramArrow) => {
  const from = toVector(element.from)
  const to = toVector(element.to)
  const group = new THREE.Group()
  const length = alignYAxis(group, from, to)
  if (length === 0) return group

  const shaftRadius = element.shaftMm ?? THREE.MathUtils.clamp(length * 0.015, 0.4, 3)
  const headLength = Math.min(length * 0.35, shaftRadius * 7)
  const shaftLength = Math.max(length - headLength, length * 0.2)
  const material = solidMaterial(element)

  const shaft = new THREE.Mesh(
    new THREE.CylinderGeometry(shaftRadius, shaftRadius, shaftLength, 20),
    material,
  )
  shaft.position.y = shaftLength / 2
  group.add(shaft)

  const head = new THREE.Mesh(new THREE.ConeGeometry(shaftRadius * 2.6, headLength, 24), material)
  head.position.y = shaftLength + headLength / 2
  group.add(head)
  return group
}

const buildCylinder = (element: DiagramCylinder) => {
  const from = toVector(element.from)
  const to = toVector(element.to)
  const holder = new THREE.Group()
  const length = alignYAxis(holder, from, to)
  const mesh = new THREE.Mesh(
    new THREE.CylinderGeometry(element.radiusMm, element.radiusMm, Math.max(length, 0.01), 32),
    solidMaterial(element),
  )
  mesh.position.y = length / 2
  holder.add(mesh)
  return holder
}

const partGeometryCache = new Map<string, Promise<THREE.BufferGeometry>>()

const loadPartGeometry = (part: DiagramPart): Promise<THREE.BufferGeometry> | null => {
  const mesh = part.mesh
  if (!mesh) return null
  if (mesh.url) {
    const cached = partGeometryCache.get(mesh.url)
    if (cached) return cached
    const promise = new STLLoader().loadAsync(mesh.url).then((geometry) => {
      geometry.computeVertexNormals()
      return geometry
    })
    partGeometryCache.set(mesh.url, promise)
    return promise
  }
  if (mesh.primitive?.kind === 'box') {
    return Promise.resolve(new THREE.BoxGeometry(...mesh.primitive.size))
  }
  if (mesh.primitive?.kind === 'cylinder') {
    return Promise.resolve(
      new THREE.CylinderGeometry(
        mesh.primitive.radius,
        mesh.primitive.radius,
        mesh.primitive.depth,
        mesh.primitive.radialSegments ?? 24,
      ),
    )
  }
  return null
}

// World anchor for an element's floating label.
const labelAnchor = (element: DiagramElement): THREE.Vector3 => {
  switch (element.kind) {
    case 'box':
    case 'sphere':
    case 'text':
    case 'callout':
      return toVector(element.at)
    case 'cylinder':
    case 'arrow':
      return toVector(element.from).add(toVector(element.to)).multiplyScalar(0.5)
    case 'line':
      return toVector(element.points[Math.floor(element.points.length / 2)])
    case 'part':
      return toVector(element.at ?? [0, 0, 0])
  }
}

const disposeObject = (object: THREE.Object3D) => {
  object.traverse((child) => {
    if (child instanceof THREE.Mesh || child instanceof THREE.Line || child instanceof THREE.LineSegments) {
      child.geometry.dispose()
      const materials = Array.isArray(child.material) ? child.material : [child.material]
      materials.forEach((material) => material.dispose())
    }
  })
}

type CanvasHandles = {
  scene: THREE.Scene
  camera: THREE.PerspectiveCamera
  controls: OrbitControls
  contentGroup: THREE.Group
  grid: THREE.GridHelper | null
  overlayLayer: HTMLDivElement
  leaderSvg: SVGSVGElement
  overlays: OverlayEntry[]
  userMovedCamera: boolean
  framedOnce: boolean
  appliedCameraJson: string | null
}

const DiagramCanvas = ({ doc }: { doc: DiagramDocument }) => {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const handlesRef = useRef<CanvasHandles | null>(null)

  // Scene setup: renderer, camera, lights, overlay layers, render loop. Runs
  // once per mount; document changes only swap the content group's children.
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 20_000)
    camera.up.set(0, 0, 1)
    camera.position.set(220, -260, 170)

    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    container.appendChild(renderer.domElement)

    const overlayLayer = document.createElement('div')
    overlayLayer.className = 'diagram-overlay-layer'
    const leaderSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
    leaderSvg.classList.add('diagram-leader-svg')
    overlayLayer.appendChild(leaderSvg)
    container.appendChild(overlayLayer)

    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.addEventListener('start', () => {
      if (handlesRef.current) handlesRef.current.userMovedCamera = true
    })

    scene.add(new THREE.HemisphereLight('#f8fafc', '#1e293b', 2.6))
    const keyLight = new THREE.DirectionalLight('#ffffff', 2.2)
    keyLight.position.set(140, -170, 260)
    scene.add(keyLight)

    const contentGroup = new THREE.Group()
    contentGroup.name = 'diagram-content'
    scene.add(contentGroup)

    handlesRef.current = {
      scene,
      camera,
      controls,
      contentGroup,
      grid: null,
      overlayLayer,
      leaderSvg,
      overlays: [],
      userMovedCamera: false,
      framedOnce: false,
      appliedCameraJson: null,
    }

    const resize = () => {
      const width = container.clientWidth
      const height = container.clientHeight
      if (width === 0 || height === 0) return
      renderer.setSize(width, height)
      camera.aspect = width / height
      camera.updateProjectionMatrix()
      leaderSvg.setAttribute('width', String(width))
      leaderSvg.setAttribute('height', String(height))
    }
    resize()
    const observer = new ResizeObserver(resize)
    observer.observe(container)

    const projected = new THREE.Vector3()
    const updateOverlays = () => {
      const width = container.clientWidth
      const height = container.clientHeight
      for (const overlay of handlesRef.current?.overlays ?? []) {
        projected.copy(overlay.point).project(camera)
        const visible = projected.z < 1
        const x = (projected.x * 0.5 + 0.5) * width
        const y = (-projected.y * 0.5 + 0.5) * height
        const bubbleX = x + overlay.offset[0]
        const bubbleY = y + overlay.offset[1]
        overlay.element.style.display = visible ? '' : 'none'
        overlay.element.style.transform = overlay.center
          ? `translate(${bubbleX}px, ${bubbleY}px) translate(-50%, -50%)`
          : `translate(${bubbleX}px, ${bubbleY}px)`
        if (overlay.dot) {
          overlay.dot.style.display = visible ? '' : 'none'
          overlay.dot.style.transform = `translate(${x}px, ${y}px) translate(-50%, -50%)`
        }
        if (overlay.leader) {
          overlay.leader.style.display = visible ? '' : 'none'
          overlay.leader.setAttribute('x1', String(x))
          overlay.leader.setAttribute('y1', String(y))
          overlay.leader.setAttribute('x2', String(bubbleX))
          overlay.leader.setAttribute('y2', String(bubbleY))
        }
      }
    }

    let disposed = false
    const renderLoop = () => {
      if (disposed) return
      controls.update()
      renderer.render(scene, camera)
      updateOverlays()
      requestAnimationFrame(renderLoop)
    }
    renderLoop()

    return () => {
      disposed = true
      observer.disconnect()
      controls.dispose()
      disposeObject(scene)
      renderer.dispose()
      container.replaceChildren()
      handlesRef.current = null
    }
  }, [])

  // Content rebuild on every document change. Part meshes load async, so the
  // build is token-guarded against a newer poll result arriving mid-load.
  useEffect(() => {
    const handles = handlesRef.current
    if (!handles) return
    let stale = false

    const rebuild = async () => {
      const { scene, camera, controls, contentGroup, overlayLayer, leaderSvg } = handles

      scene.background = new THREE.Color(doc.background ?? DEFAULT_BACKGROUND)

      const nextObjects: THREE.Object3D[] = []
      const nextOverlays: OverlayEntry[] = []
      const bubbles: HTMLDivElement[] = []
      const leaders: SVGLineElement[] = []

      const addOverlay = (
        className: string,
        html: string,
        point: THREE.Vector3,
        options: { offset?: [number, number]; center?: boolean; leader?: boolean; color?: string } = {},
      ) => {
        const element = document.createElement('div')
        element.className = className
        element.textContent = html
        if (options.color) element.style.setProperty('--overlay-color', options.color)
        bubbles.push(element)
        const entry: OverlayEntry = {
          element,
          point,
          offset: options.offset ?? [0, 0],
          center: options.center ?? true,
        }
        if (options.leader) {
          const line = document.createElementNS('http://www.w3.org/2000/svg', 'line')
          line.setAttribute('class', 'diagram-leader-line')
          if (options.color) line.style.stroke = options.color
          leaders.push(line)
          entry.leader = line
          const dot = document.createElement('div')
          dot.className = 'diagram-anchor-dot'
          if (options.color) dot.style.background = options.color
          bubbles.push(dot)
          entry.dot = dot
        }
        nextOverlays.push(entry)
        return entry
      }

      for (const element of doc.elements) {
        if (stale) return
        switch (element.kind) {
          case 'box': {
            const mesh = new THREE.Mesh(new THREE.BoxGeometry(...element.size), solidMaterial(element))
            mesh.position.copy(toVector(element.at))
            if (element.rotationDeg) mesh.setRotationFromEuler(degToRad(element.rotationDeg))
            if (element.wireframe) {
              ;(mesh.material as THREE.MeshStandardMaterial).visible = false
            }
            const edges = new THREE.LineSegments(
              new THREE.EdgesGeometry(mesh.geometry),
              new THREE.LineBasicMaterial({
                color: elementColor(element),
                transparent: !element.wireframe,
                opacity: element.wireframe ? 1 : 0.55,
              }),
            )
            mesh.add(edges)
            nextObjects.push(mesh)
            break
          }
          case 'sphere': {
            const mesh = new THREE.Mesh(
              new THREE.SphereGeometry(element.radiusMm, 32, 20),
              solidMaterial(element),
            )
            mesh.position.copy(toVector(element.at))
            nextObjects.push(mesh)
            break
          }
          case 'cylinder':
            nextObjects.push(buildCylinder(element))
            break
          case 'arrow':
            nextObjects.push(buildArrow(element))
            break
          case 'line': {
            const geometry = new THREE.BufferGeometry().setFromPoints(element.points.map(toVector))
            const material = element.dashed
              ? new THREE.LineDashedMaterial({ color: elementColor(element), dashSize: 4, gapSize: 3 })
              : new THREE.LineBasicMaterial({ color: elementColor(element) })
            const line = new THREE.Line(geometry, material)
            if (element.dashed) line.computeLineDistances()
            nextObjects.push(line)
            break
          }
          case 'text':
            addOverlay('diagram-text', element.text, toVector(element.at), {
              color: elementColor(element),
            }).element.style.fontSize = `${element.sizePx ?? 14}px`
            break
          case 'callout':
            addOverlay('diagram-callout', element.text, toVector(element.at), {
              offset: element.offsetPx ?? [28, -28],
              leader: true,
              color: elementColor(element),
            })
            break
          case 'part': {
            const load = loadPartGeometry(element)
            if (!load) break
            const geometry = (await load).clone()
            if (stale) return
            const mesh = new THREE.Mesh(geometry, solidMaterial(element))
            mesh.position.copy(toVector(element.at ?? [0, 0, 0]))
            if (element.rotationDeg) mesh.setRotationFromEuler(degToRad(element.rotationDeg))
            if (element.scale) mesh.scale.setScalar(element.scale)
            nextObjects.push(mesh)
            break
          }
        }
        if (element.label) {
          addOverlay('diagram-label', element.label, labelAnchor(element), {
            offset: [0, -14],
            color: elementColor(element),
          })
        }
      }

      if (stale) return

      // Swap content atomically: old objects/overlays out, new ones in.
      contentGroup.children.forEach(disposeObject)
      contentGroup.clear()
      nextObjects.forEach((object) => contentGroup.add(object))
      handles.overlays = []
      leaderSvg.replaceChildren(...leaders)
      overlayLayer.querySelectorAll('.diagram-text, .diagram-callout, .diagram-label, .diagram-anchor-dot')
        .forEach((node) => node.remove())
      bubbles.forEach((bubble) => overlayLayer.appendChild(bubble))
      handles.overlays = nextOverlays

      // Frame the content: size a ground grid to it and, unless the user has
      // taken over the camera, apply the document camera or auto-frame.
      const bounds = new THREE.Box3().setFromObject(contentGroup)
      nextOverlays.forEach((overlay) => bounds.expandByPoint(overlay.point))
      const hasBounds = !bounds.isEmpty()
      const center = hasBounds ? bounds.getCenter(new THREE.Vector3()) : new THREE.Vector3()
      const radius = hasBounds ? Math.max(bounds.getSize(new THREE.Vector3()).length() / 2, 20) : 120

      if (handles.grid) {
        scene.remove(handles.grid)
        handles.grid.geometry.dispose()
        ;(handles.grid.material as THREE.Material).dispose()
      }
      const gridSize = Math.max(200, Math.ceil((radius * 3) / 100) * 100)
      const grid = new THREE.GridHelper(gridSize, Math.round(gridSize / 10), '#334155', '#1e293b')
      grid.rotation.x = Math.PI / 2
      grid.position.set(center.x, center.y, hasBounds ? bounds.min.z : 0)
      scene.add(grid)
      handles.grid = grid

      const cameraJson = doc.camera ? JSON.stringify(doc.camera) : null
      const cameraChanged = cameraJson !== handles.appliedCameraJson
      if (!handles.userMovedCamera && (!handles.framedOnce || cameraChanged)) {
        if (doc.camera) {
          camera.position.set(...doc.camera.position)
          controls.target.set(...doc.camera.target)
        } else {
          const direction = new THREE.Vector3(1, -1, 0.65).normalize()
          camera.position.copy(center.clone().add(direction.multiplyScalar(radius * 2.4)))
          controls.target.copy(center)
        }
        controls.update()
        handles.framedOnce = true
        handles.appliedCameraJson = cameraJson
      }
    }

    rebuild().catch((error: unknown) => {
      console.warn('BuildViz diagram: could not build content', error)
    })
    return () => {
      stale = true
    }
  }, [doc])

  return <div ref={containerRef} className="diagram-canvas" />
}

// Legend rows: every element that carries a label, plus parts (which are worth
// listing even unlabeled, since they reference real builds).
const legendRows = (doc: DiagramDocument) =>
  doc.elements
    .filter((element) => element.label || element.kind === 'part')
    .map((element) => ({
      id: element.id,
      color: elementColor(element),
      label: element.label ?? (element.kind === 'part' ? element.mesh?.partType ?? element.part : element.id),
      detail:
        element.kind === 'part'
          ? `${element.buildId}${element.version ? `@${element.version}` : ''}`
          : element.kind,
    }))

const DiagramApp = ({ name }: { name: string }) => {
  const [doc, setDoc] = useState<DiagramDocument | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [panelOpen, setPanelOpen] = useState(true)
  const etagRef = useRef<string | null>(null)

  useEffect(() => {
    let cancelled = false
    const url = `/diagrams/${encodeURIComponent(name)}/diagram.json`

    const load = async () => {
      const response = await fetch(url, {
        cache: 'no-cache',
        headers: etagRef.current ? { 'If-None-Match': etagRef.current } : {},
      })
      if (cancelled || response.status === 304) return
      if (!response.ok) {
        const detail = (await response.json().catch(() => null)) as { error?: string } | null
        throw new Error(detail?.error ?? `Diagram request failed (${response.status})`)
      }
      etagRef.current = response.headers.get('ETag')
      const payload = (await response.json()) as DiagramDocument
      if (cancelled) return
      setDoc(payload)
      setError(null)
    }

    const tick = () =>
      void load().catch((loadError: unknown) => {
        if (!cancelled) setError(loadError instanceof Error ? loadError.message : String(loadError))
      })
    tick()
    // Keep polling even while errored: the diagram appears the moment an agent
    // creates it, without the human ever reloading the page.
    const timer = setInterval(tick, POLL_MS)
    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [name])

  useEffect(() => {
    document.title = doc ? `${doc.title} — BuildViz diagram` : `BuildViz diagram — ${name}`
  }, [doc, name])

  if (!doc) {
    return (
      <div className="diagram-app diagram-app-empty">
        <div className="diagram-empty-card">
          <h1>BuildViz diagram</h1>
          <p className="diagram-empty-name">?diagram={name}</p>
          {error ? (
            <>
              <p className="diagram-empty-error">{error}</p>
              <p>
                Waiting for it to appear — an agent can create it with the <code>create_diagram</code> MCP
                tool. This page checks every {Math.round(POLL_MS / 1000)}s.
              </p>
            </>
          ) : (
            <p>Loading…</p>
          )}
          <a href="/">← All builds</a>
        </div>
      </div>
    )
  }

  const legend = legendRows(doc)
  return (
    <div className="diagram-app">
      <header className="diagram-header">
        <span className="diagram-mode-badge">Diagram</span>
        <h1>{doc.title}</h1>
        <span className="diagram-live" title={`Live: refreshes every ${Math.round(POLL_MS / 1000)}s`}>
          <span className="diagram-live-dot" /> live
        </span>
        <div className="diagram-header-spacer" />
        <button type="button" onClick={() => setPanelOpen((open) => !open)}>
          {panelOpen ? 'Hide notes' : 'Show notes'}
        </button>
        <a href="/">All builds</a>
      </header>
      <div className="diagram-body">
        <DiagramCanvas doc={doc} />
        {panelOpen && (doc.notes || legend.length > 0) && (
          <aside className="diagram-panel">
            {doc.notes && <p className="diagram-notes">{doc.notes}</p>}
            {legend.length > 0 && (
              <ul className="diagram-legend">
                {legend.map((row) => (
                  <li key={row.id}>
                    <span className="diagram-legend-swatch" style={{ background: row.color }} />
                    <span className="diagram-legend-label">{row.label}</span>
                    <span className="diagram-legend-detail">{row.detail}</span>
                  </li>
                ))}
              </ul>
            )}
            <p className="diagram-panel-footer">
              {doc.elements.length} element{doc.elements.length === 1 ? '' : 's'} · updates live
            </p>
          </aside>
        )}
      </div>
    </div>
  )
}

export default DiagramApp
