import gsap from 'gsap'

/* Mini plane SVG (top-down view, fits inline) */
const MINI_PLANE_SVG = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 24" fill="none" width="48" height="24">
  <!-- Fuselage -->
  <path d="M 6,10 Q 2,12 2,12 Q 2,12 6,14 L 42,14 Q 46,12 46,12 Q 46,12 42,10 Z"
    fill="#C0CAD8"/>
  <!-- Main wings -->
  <path d="M 16,12 L 22,2 L 30,2 L 26,12 Z" fill="#8899AA"/>
  <path d="M 16,12 L 22,22 L 30,22 L 26,12 Z" fill="#8899AA"/>
  <!-- Tail fins -->
  <path d="M 36,12 L 38,7 L 44,7 L 42,12 Z" fill="#6882A0"/>
  <path d="M 36,12 L 38,17 L 44,17 L 42,12 Z" fill="#6882A0"/>
  <!-- Cockpit -->
  <path d="M 6,10 Q 2,12 6,14 L 12,14 L 12,10 Z" fill="#3C5268"/>
  <!-- Sky-blue stripe -->
  <rect x="12" y="10.5" width="24" height="3" fill="#38BDF8" opacity="0.35" rx="0.5"/>
  <!-- Engine glow hint -->
  <circle cx="22" cy="5" r="2" fill="#38BDF8" opacity="0.25"/>
  <circle cx="22" cy="19" r="2" fill="#38BDF8" opacity="0.25"/>
</svg>
`

export function launchPlane(originEl: HTMLElement) {
  const rect = originEl.getBoundingClientRect()

  /* Container */
  const wrap = document.createElement('div')
  wrap.style.cssText = `
    position: fixed;
    left: ${rect.left + rect.width / 2 - 24}px;
    top:  ${rect.top  + rect.height / 2 - 12}px;
    z-index: 9999;
    pointer-events: none;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
  `

  /* Plane */
  const plane = document.createElement('div')
  plane.innerHTML = MINI_PLANE_SVG

  /* Label */
  const label = document.createElement('span')
  label.textContent = 'AIRBORNE'
  label.style.cssText = `
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 0.12em;
    color: #38BDF8;
    white-space: nowrap;
    opacity: 0;
  `

  wrap.appendChild(plane)
  wrap.appendChild(label)
  document.body.appendChild(wrap)

  const tl = gsap.timeline({
    onComplete: () => wrap.remove(),
  })

  tl
    /* Pop in */
    .fromTo(wrap,
      { scale: 0.4, opacity: 0 },
      { scale: 1, opacity: 1, duration: 0.18, ease: 'back.out(1.4)' }
    )
    /* Label appears */
    .to(label, { opacity: 1, duration: 0.15 }, '-=0.05')
    /* Brief hold */
    .to({}, { duration: 0.12 })
    /* Launch — fly right and up */
    .to(wrap, {
      x: window.innerWidth * 0.7,
      y: -90,
      rotation: -12,
      duration: 0.72,
      ease: 'power2.in',
    })
    /* Fade out near end */
    .to(wrap, {
      opacity: 0,
      duration: 0.22,
    }, '-=0.28')
}
