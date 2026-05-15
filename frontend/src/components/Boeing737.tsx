/**
 * Boeing 737-800 — full Three.js scene
 *
 * Upgrades vs previous version:
 *  - RoomEnvironment IBL (image-based lighting) → metallic reflections
 *  - MeshPhysicalMaterial + clearcoat on fuselage
 *  - UnrealBloomPass on sky-blue accent emissives
 *  - LatheGeometry fuselage (smooth revolution surface, 52 segments)
 *  - Proper engine nacelles with TorusGeometry inlet lip + fan disc
 *  - Thick wings via ExtrudeGeometry with airfoil profile
 *  - Winglets (angled tip fins)
 *  - Particle contrail (THREE.Points trailing behind engines)
 *  - Full-viewport canvas with cinematic camera
 *  - Slow Y-rotation showcase + gentle idle float
 */

import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js'
import { EffectComposer }  from 'three/examples/jsm/postprocessing/EffectComposer.js'
import { RenderPass }      from 'three/examples/jsm/postprocessing/RenderPass.js'
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js'
import { OutputPass }      from 'three/examples/jsm/postprocessing/OutputPass.js'
import gsap from 'gsap'
import './Boeing737.css'

// ─── Geometry helpers ──────────────────────────────────────────

function buildFuselage(): THREE.BufferGeometry {
  // Profile: (radius, axial-position) — will be revolved around Y then rotated 90° to X
  const pts: [number, number][] = [
    [0,     -2.42],
    [0.03,  -2.34],
    [0.08,  -2.18],
    [0.155, -1.95],
    [0.22,  -1.65],
    [0.264, -1.28],
    [0.286, -0.78],
    [0.296, -0.12],
    [0.298,  0.55],  // widest section (cabin)
    [0.296,  1.18],
    [0.286,  1.62],
    [0.262,  1.95],
    [0.224,  2.12],
    [0.165,  2.26],
    [0.088,  2.36],
    [0.024,  2.42],
    [0,      2.44],
  ]
  const points = pts.map(([r, y]) => new THREE.Vector2(r, y))
  const geo = new THREE.LatheGeometry(points, 52)
  geo.rotateZ(Math.PI / 2)
  return geo
}

function buildAirfoilProfile(chord = 1, thickness = 0.12): THREE.Shape {
  // NACA 2412-inspired upper/lower surface
  const shape = new THREE.Shape()
  const steps  = 24
  const upper: THREE.Vector2[] = []
  const lower: THREE.Vector2[] = []

  for (let i = 0; i <= steps; i++) {
    const x = (i / steps) * chord
    const t = x / chord
    const yt = thickness / 0.2 * (
      0.2969 * Math.sqrt(t) -
      0.126  * t -
      0.3516 * t * t +
      0.2843 * t * t * t -
      0.1036 * t * t * t * t
    )
    upper.push(new THREE.Vector2(x, yt))
    lower.push(new THREE.Vector2(x, -yt * 0.72))
  }

  shape.moveTo(0, 0)
  upper.forEach(p => shape.lineTo(p.x, p.y))
  for (let i = lower.length - 1; i >= 0; i--) shape.lineTo(lower[i].x, lower[i].y)
  shape.closePath()
  return shape
}

function buildWing(side: 1 | -1): THREE.BufferGeometry {
  // Extruded airfoil, tapered via scale manipulation
  const rootChord = 0.78, tipChord = 0.38, span = 2.18
  const sweep = 0.34  // leading-edge sweep offset at tip

  const geo = new THREE.BufferGeometry()
  const verts: number[] = []
  const idx: number[] = []

  // Root section vertices (in XZ plane at z=0)
  const rootPts = buildAirfoilProfile(rootChord, 0.11).getPoints(20)
  // Tip section (offset in Z by span)
  const tipPts  = buildAirfoilProfile(tipChord,  0.07).getPoints(20)

  const n = rootPts.length
  rootPts.forEach(p => { verts.push(-rootChord * 0.28 + p.x, p.y * 0.9, 0) })
  tipPts.forEach(p  => { verts.push(-rootChord * 0.28 + sweep + p.x, p.y, side * span) })

  for (let i = 0; i < n - 1; i++) {
    const a = i, b = i + 1, c = n + i, d = n + i + 1
    idx.push(
      side === 1 ? a : b,
      side === 1 ? b : a,
      side === 1 ? c : d,
      side === 1 ? b : a,
      side === 1 ? d : c,
      side === 1 ? c : d,
    )
  }

  geo.setAttribute('position', new THREE.Float32BufferAttribute(verts, 3))
  geo.setIndex(idx)
  geo.computeVertexNormals()
  return geo
}

function buildEngine(side: 1 | -1, mat: {
  nacelle: THREE.Material
  dark:    THREE.Material
  accent:  THREE.Material
}): THREE.Group {
  const g = new THREE.Group()

  // Outer nacelle — slightly flattened at bottom (CFM56 characteristic)
  const nacelleGeo = new THREE.CylinderGeometry(0.12, 0.135, 0.64, 36, 1, true)
  nacelleGeo.rotateZ(Math.PI / 2)
  g.add(new THREE.Mesh(nacelleGeo, mat.nacelle))

  // Inlet lip — TorusGeometry at the front
  const lipGeo = new THREE.TorusGeometry(0.125, 0.022, 20, 40)
  lipGeo.rotateY(Math.PI / 2)
  const lip = new THREE.Mesh(lipGeo, mat.nacelle)
  lip.position.x = -0.32
  g.add(lip)

  // Fan face — dark disc
  const fanGeo = new THREE.CircleGeometry(0.1, 32)
  fanGeo.rotateY(-Math.PI / 2)
  const fan = new THREE.Mesh(fanGeo, mat.dark)
  fan.position.x = -0.31
  g.add(fan)

  // Fan blades (12 thin rectangles radiating from center)
  const bladeMat = new THREE.MeshPhysicalMaterial({
    color: '#1e3248', metalness: 0.7, roughness: 0.35, side: THREE.DoubleSide,
  })
  for (let i = 0; i < 12; i++) {
    const blade = new THREE.Mesh(
      new THREE.PlaneGeometry(0.088, 0.012),
      bladeMat,
    )
    blade.rotation.x = (i / 12) * Math.PI * 2
    blade.position.set(-0.305, 0, 0)
    g.add(blade)
  }

  // Exhaust nozzle
  const nozzleGeo = new THREE.CylinderGeometry(0.09, 0.102, 0.15, 28)
  nozzleGeo.rotateZ(Math.PI / 2)
  const nozzle = new THREE.Mesh(nozzleGeo, mat.dark)
  nozzle.position.x = 0.395
  g.add(nozzle)

  // Pylon
  const pylonGeo = new THREE.BoxGeometry(0.38, 0.06, 0.04)
  const pylon = new THREE.Mesh(pylonGeo, mat.nacelle)
  pylon.position.set(-0.05, 0.175, 0)
  g.add(pylon)

  g.position.set(-0.22, -0.34, side * 0.82)
  return g
}

function buildWinglet(side: 1 | -1, mat: THREE.Material): THREE.Mesh {
  const shape = new THREE.Shape()
  shape.moveTo(0, 0)
  shape.bezierCurveTo(0.04, 0.22, 0.1, 0.36, 0.08, 0.44)
  shape.bezierCurveTo(0.06, 0.5, 0.02, 0.48, 0, 0.42)
  shape.lineTo(-0.12, 0.04)
  shape.closePath()

  const geo = new THREE.ExtrudeGeometry(shape, {
    depth: 0.018, bevelEnabled: true,
    bevelSize: 0.006, bevelThickness: 0.006, bevelSegments: 2,
  })
  geo.rotateX(side * -0.28)
  const mesh = new THREE.Mesh(geo, mat)
  mesh.position.set(0.12, 0.02, side * 2.18)
  return mesh
}

function buildTailFin(mat: THREE.Material): THREE.Mesh {
  const shape = new THREE.Shape()
  shape.moveTo(0, 0)
  shape.bezierCurveTo(0.05, 0.38, 0.18, 0.72, 0.24, 0.92)
  shape.bezierCurveTo(0.3, 1.08, 0.44, 1.12, 0.52, 0.98)
  shape.bezierCurveTo(0.62, 0.82, 0.72, 0.52, 0.78, 0.12)
  shape.lineTo(0.78, 0)
  shape.closePath()

  const geo = new THREE.ExtrudeGeometry(shape, {
    depth: 0.065, bevelEnabled: true,
    bevelSize: 0.012, bevelThickness: 0.012, bevelSegments: 3,
  })
  geo.translate(-0.06, 0, -0.032)
  return new THREE.Mesh(geo, mat)
}

function buildHStabilizer(side: 1 | -1, mat: THREE.Material): THREE.Mesh {
  const rootC = 0.52, tipC = 0.28, span = 0.88, sweep = 0.22
  const geo   = new THREE.BufferGeometry()
  const verts: number[] = []
  const idx: number[]   = []
  const rootPts = buildAirfoilProfile(rootC, 0.09).getPoints(16)
  const tipPts  = buildAirfoilProfile(tipC,  0.065).getPoints(16)
  const n = rootPts.length

  rootPts.forEach(p => { verts.push(-rootC * 0.32 + p.x, p.y, 0) })
  tipPts.forEach(p  => { verts.push(-rootC * 0.32 + sweep + p.x, p.y, side * span) })

  for (let i = 0; i < n - 1; i++) {
    const a = i, b = i + 1, c = n + i, d = n + i + 1
    idx.push(
      side === 1 ? a : b, side === 1 ? b : a, side === 1 ? c : d,
      side === 1 ? b : a, side === 1 ? d : c, side === 1 ? c : d,
    )
  }
  geo.setAttribute('position', new THREE.Float32BufferAttribute(verts, 3))
  geo.setIndex(idx)
  geo.computeVertexNormals()
  return new THREE.Mesh(geo, mat)
}

function buildContrail(): THREE.Points {
  const count   = 320
  const pos     = new Float32Array(count * 3)
  const opacity = new Float32Array(count)

  for (let i = 0; i < count; i++) {
    const t  = i / count
    pos[i * 3]     = -2.5 - t * 4.2
    pos[i * 3 + 1] = -0.34 + (Math.random() - 0.5) * 0.06
    pos[i * 3 + 2] = (Math.random() - 0.5) * 0.18 + (Math.random() > 0.5 ? 0.82 : -0.82)
    opacity[i]     = (1 - t) * 0.55
  }

  const geo = new THREE.BufferGeometry()
  geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3))
  geo.setAttribute('opacity',  new THREE.Float32BufferAttribute(opacity, 1))

  const mat = new THREE.PointsMaterial({
    color: 0x9ec8e8,
    size: 0.025,
    sizeAttenuation: true,
    transparent: true,
    opacity: 0.7,
    depthWrite: false,
  })

  return new THREE.Points(geo, mat)
}

// ─── Main aircraft assembly ────────────────────────────────────

function buildAircraft(): THREE.Group {
  const root = new THREE.Group()

  // ── Materials ──────────────────────────────────────────────
  const fuselageMat = new THREE.MeshPhysicalMaterial({
    color: '#c8d4e0',
    metalness: 0.72, roughness: 0.22,
    clearcoat: 0.65, clearcoatRoughness: 0.12,
    envMapIntensity: 1.4,
  })
  const wingMat = new THREE.MeshPhysicalMaterial({
    color: '#8090a4', metalness: 0.6, roughness: 0.3,
    clearcoat: 0.3, clearcoatRoughness: 0.2,
    side: THREE.DoubleSide, envMapIntensity: 1.2,
  })
  const nacelleMat = new THREE.MeshPhysicalMaterial({
    color: '#6e8298', metalness: 0.55, roughness: 0.38,
    clearcoat: 0.2, envMapIntensity: 1.0,
  })
  const darkMat = new THREE.MeshStandardMaterial({
    color: '#0d1826', metalness: 0.1, roughness: 0.55,
  })
  const glassMat = new THREE.MeshPhysicalMaterial({
    color: '#0d1827',
    emissive: '#0f3250', emissiveIntensity: 0.22,
    metalness: 0.05, roughness: 0.08,
    transmission: 0.15,
  })
  const accentMat = new THREE.MeshStandardMaterial({
    color: '#38bdf8',
    emissive: '#0a4d72', emissiveIntensity: 0.55,
    metalness: 0.15, roughness: 0.22,
  })
  const bellyMat = new THREE.MeshStandardMaterial({
    color: '#5a7086', metalness: 0.4, roughness: 0.5,
  })

  // ── Fuselage ───────────────────────────────────────────────
  const fuselage = new THREE.Mesh(buildFuselage(), fuselageMat)
  fuselage.castShadow = true
  root.add(fuselage)

  // Belly strip (darker underside)
  const belly = new THREE.Mesh(new THREE.BoxGeometry(4.2, 0.06, 0.28), bellyMat)
  belly.position.set(0, -0.24, 0)
  root.add(belly)

  // Sky-blue livery stripe (both sides)
  ;([-1, 1] as const).forEach(side => {
    const stripe = new THREE.Mesh(new THREE.BoxGeometry(3.9, 0.038, 0.016), accentMat)
    stripe.position.set(-0.12, 0.04, side * 0.298)
    root.add(stripe)
  })

  // Cockpit / radome (dark nose)
  const radome = new THREE.Mesh(
    new THREE.SphereGeometry(0.17, 24, 16, 0, Math.PI * 2, 0, Math.PI * 0.55),
    darkMat,
  )
  radome.rotation.z = -Math.PI / 2
  radome.position.set(-2.3, 0, 0)
  root.add(radome)

  // Cockpit windows
  ;([-1, 1] as const).forEach(side => {
    const win = new THREE.Mesh(new THREE.PlaneGeometry(0.26, 0.09), glassMat)
    win.position.set(-2.08, 0.19, side * 0.14)
    win.rotation.y = side * 0.34
    win.rotation.z = -0.06
    root.add(win)
  })

  // Passenger windows (both sides)
  ;([-1, 1] as const).forEach(side => {
    for (let i = 0; i < 22; i++) {
      const w = new THREE.Mesh(new THREE.PlaneGeometry(0.038, 0.03), glassMat)
      w.position.set(-1.62 + i * 0.155, 0.155, side * 0.3)
      w.rotation.y = side * (Math.PI / 2)
      root.add(w)
    }
  })

  // ── Wings ──────────────────────────────────────────────────
  ;([-1, 1] as const).forEach(side => {
    const wing = new THREE.Mesh(buildWing(side), wingMat)
    wing.position.set(-0.18, -0.04, 0)
    wing.rotation.x = side * -0.05
    wing.castShadow = true
    root.add(wing)

    root.add(buildWinglet(side, wingMat))
    root.add(buildEngine(side, { nacelle: nacelleMat, dark: darkMat, accent: accentMat }))

    const stab = buildHStabilizer(side, wingMat)
    stab.position.set(1.84, 0.06, side * 0.04)
    stab.rotation.x = side * -0.04
    root.add(stab)
  })

  // ── Vertical stabilizer ────────────────────────────────────
  const fin = buildTailFin(wingMat)
  fin.position.set(1.62, 0.18, -0.032)
  root.add(fin)

  // Sky-blue tail stripe
  const tailAccent = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.56, 0.014), accentMat)
  tailAccent.position.set(1.92, 0.56, -0.088)
  tailAccent.rotation.z = -0.18
  root.add(tailAccent)

  // ── Contrail ───────────────────────────────────────────────
  root.add(buildContrail())

  root.rotation.y = 0.32
  root.rotation.x = 0.08
  return root
}

// ─── React component ───────────────────────────────────────────

export default function Boeing737() {
  const mountRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const mount = mountRef.current
    if (!mount) return

    const W = () => mount.clientWidth
    const H = () => mount.clientHeight

    // ── Renderer ──────────────────────────────────────────────
    const renderer = new THREE.WebGLRenderer({
      alpha: true, antialias: true,
      powerPreference: 'high-performance',
    })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setSize(W(), H(), false)
    renderer.setClearColor(0x000000, 0)
    renderer.shadowMap.enabled = true
    renderer.shadowMap.type    = THREE.PCFSoftShadowMap
    renderer.toneMapping       = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.05
    mount.appendChild(renderer.domElement)

    // ── Scene ──────────────────────────────────────────────────
    const scene  = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(40, W() / H(), 0.1, 100)
    camera.position.set(1.2, 0.95, 4.6)
    camera.lookAt(0, 0.06, 0)

    // ── IBL environment (RoomEnvironment) ──────────────────────
    const pmrem = new THREE.PMREMGenerator(renderer)
    pmrem.compileEquirectangularShader()
    scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture
    pmrem.dispose()

    // ── Lighting ───────────────────────────────────────────────
    scene.add(new THREE.AmbientLight(0xdce8ff, 0.55))

    const key = new THREE.DirectionalLight(0xfff5e8, 3.2)
    key.position.set(-4, 5.5, 4)
    key.castShadow = true
    key.shadow.mapSize.set(2048, 2048)
    key.shadow.camera.near = 0.5
    key.shadow.camera.far  = 18
    key.shadow.camera.left = key.shadow.camera.bottom = -4
    key.shadow.camera.right = key.shadow.camera.top   =  4
    scene.add(key)

    const fill = new THREE.DirectionalLight(0xb8d8ff, 1.1)
    fill.position.set(4, 1, 3)
    scene.add(fill)

    const rim = new THREE.DirectionalLight(0x38bdf8, 1.4)
    rim.position.set(3, 0.5, -5)
    scene.add(rim)

    // ── Shadow catcher ─────────────────────────────────────────
    const shadowCatcher = new THREE.Mesh(
      new THREE.PlaneGeometry(7, 3),
      new THREE.ShadowMaterial({ opacity: 0.18 }),
    )
    shadowCatcher.rotation.x = -Math.PI / 2
    shadowCatcher.position.y = -0.82
    shadowCatcher.receiveShadow = true
    scene.add(shadowCatcher)

    // ── Aircraft ───────────────────────────────────────────────
    const aircraft = buildAircraft()
    aircraft.position.x = 6  // starts off-screen right for entry
    aircraft.scale.setScalar(0.001)
    scene.add(aircraft)

    // ── Post-processing: UnrealBloom on accents ────────────────
    const composer = new EffectComposer(renderer)
    composer.addPass(new RenderPass(scene, camera))

    const bloom = new UnrealBloomPass(
      new THREE.Vector2(W(), H()),
      0.38,   // strength
      0.55,   // radius
      0.82,   // threshold (only emissive-bright elements bloom)
    )
    composer.addPass(bloom)
    composer.addPass(new OutputPass())

    // ── GSAP entry ─────────────────────────────────────────────
    gsap.to(aircraft.scale, {
      x: 1, y: 1, z: 1,
      duration: 1.2,
      ease: 'power3.out',
    })
    gsap.to(aircraft.position, {
      x: 0,
      duration: 1.4,
      ease: 'power3.out',
    })

    // ── Resize ─────────────────────────────────────────────────
    const onResize = () => {
      renderer.setSize(W(), H(), false)
      composer.setSize(W(), H())
      camera.aspect = W() / H()
      camera.updateProjectionMatrix()
      bloom.resolution.set(W(), H())
    }
    const ro = new ResizeObserver(onResize)
    ro.observe(mount)

    // ── Animation loop ─────────────────────────────────────────
    const clock  = new THREE.Clock()
    let frameId  = 0
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    const tick = () => {
      frameId = requestAnimationFrame(tick)
      const elapsed = clock.getElapsedTime()

      if (!prefersReduced) {
        // Slow showcase rotation
        aircraft.rotation.y  = 0.32 + elapsed * 0.18
        // Gentle idle: pitch + roll float
        aircraft.position.y  = Math.sin(elapsed * 0.7)  * 0.055
        aircraft.position.z  = Math.sin(elapsed * 0.45) * 0.04
        aircraft.rotation.z  = Math.sin(elapsed * 0.6)  * 0.018
        aircraft.rotation.x  = 0.08 + Math.sin(elapsed * 0.9) * 0.014
      }

      composer.render()
    }
    tick()

    return () => {
      cancelAnimationFrame(frameId)
      ro.disconnect()
      scene.environment?.dispose()
      renderer.dispose()
      composer.dispose()
      mount.removeChild(renderer.domElement)
    }
  }, [])

  return (
    <div className="plane-wrapper" role="img" aria-label="Boeing 737-800 3D">
      <div className="contrail contrail-main" />
      <div className="contrail contrail-soft" />
      <div ref={mountRef} className="b737-canvas" />
    </div>
  )
}
