import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import gsap from 'gsap'
import Hero from './components/Hero'
import Chat from './components/Chat'
import Map from './components/Map'
import Analytics from './components/Analytics'
import './App.css'

export type Tab = 'chat' | 'map' | 'analytics'

const TABS: { id: Tab; label: string }[] = [
  { id: 'chat',      label: 'CHAT' },
  { id: 'map',       label: 'MAP' },
  { id: 'analytics', label: 'ANALYTICS' },
]

const TAB_INDEX: Record<Tab, number> = { chat: 0, map: 1, analytics: 2 }

export default function App() {
  const [entered, setEntered] = useState(false)
  const [active, setActive] = useState<Tab>('chat')
  const prevRef = useRef<Tab>('chat')

  // GSAP entrance: letters stagger, then subtitle, then tabs, then content
  useEffect(() => {
    if (!entered) return
    const tl = gsap.timeline({ defaults: { ease: 'power3.out' } })

    tl.fromTo('.wordmark-letter',
      { y: -14, opacity: 0, rotateX: -60 },
      { y: 0, opacity: 1, rotateX: 0, stagger: 0.055, duration: 0.45 }
    )
    .fromTo('.wordmark-divider, .wordmark-sub',
      { opacity: 0, x: -6 },
      { opacity: 1, x: 0, duration: 0.35, ease: 'power2.out' },
      '-=0.15'
    )
    .fromTo('.tab',
      { opacity: 0, y: -6 },
      { opacity: 1, y: 0, stagger: 0.07, duration: 0.3, ease: 'power2.out' },
      '-=0.2'
    )
    .fromTo('.shell-main',
      { opacity: 0, y: 10 },
      { opacity: 1, y: 0, duration: 0.4, ease: 'power2.out', clearProps: 'transform' },
      '-=0.15'
    )
  }, [entered])

  const handleEnter = (tab: Tab) => {
    prevRef.current = tab
    setActive(tab)
    setEntered(true)
  }

  const handleTabChange = (tab: Tab) => {
    prevRef.current = active
    setActive(tab)
  }

  const direction = TAB_INDEX[active] >= TAB_INDEX[prevRef.current] ? 1 : -1

  if (!entered) {
    return <Hero onEnter={handleEnter} />
  }

  return (
    <div className="shell">
      <header className="shell-header">
        <div className="shell-header-inner">
          <div className="wordmark">
            <span className="wordmark-name" aria-label="AETHER">
              {'AETHER'.split('').map((ch, i) => (
                <span key={i} className="wordmark-letter">{ch}</span>
              ))}
            </span>
            <span className="wordmark-divider" aria-hidden="true" />
            <span className="wordmark-sub">Aviation Intelligence</span>
          </div>

          <div className="header-right">
            <div className="live-badge">
              <span className="live-dot" />
              <span className="live-label">LIVE</span>
            </div>

            <nav className="tabs" role="tablist">
              {TABS.map(tab => (
                <button
                  key={tab.id}
                  role="tab"
                  aria-selected={active === tab.id}
                  className={`tab ${active === tab.id ? 'tab-active' : ''}`}
                  onClick={() => handleTabChange(tab.id)}
                >
                  {tab.label}
                  {active === tab.id && (
                    <motion.span
                      className="tab-indicator"
                      layoutId="tab-indicator"
                      transition={{ duration: 0.22, ease: [0.25, 0, 0, 1] }}
                    />
                  )}
                </button>
              ))}
            </nav>
          </div>
        </div>
      </header>

      <main className="shell-main">
        <AnimatePresence mode="wait" custom={direction}>
          <motion.div
            key={active}
            custom={direction}
            className="tab-panel"
            variants={{
              enter:  (d: number) => ({ x: d * 28, opacity: 0, filter: 'blur(4px)' }),
              center: { x: 0, opacity: 1, filter: 'blur(0px)' },
              exit:   (d: number) => ({ x: d * -28, opacity: 0, filter: 'blur(4px)' }),
            }}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ duration: 0.24, ease: [0.25, 0, 0, 1] }}
          >
            {active === 'chat'      && <Chat />}
            {active === 'map'       && <Map />}
            {active === 'analytics' && <Analytics />}
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  )
}
