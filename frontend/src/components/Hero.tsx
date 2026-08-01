import { useState, useRef, useEffect } from 'react'
import { Menu, X } from 'lucide-react'
import type { Tab } from '../App'
import './Hero.css'

const VIDEO_SRC =
  'https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260328_091828_e240eb17-6edc-4129-ad9d-98678e3fd238.mp4'

const NAV_ITEMS: { label: string; tab: Tab }[] = [
  { label: 'Chat',      tab: 'chat' },
  { label: 'Live Map',  tab: 'map' },
  { label: 'Analytics', tab: 'analytics' },
]

export default function Hero({ onEnter }: { onEnter: (tab: Tab) => void }) {
  const [menuOpen, setMenuOpen] = useState(false)
  const videoRef = useRef<HTMLVideoElement>(null)

  // Force muted so browsers honour autoplay (React's `muted` attr is unreliable).
  useEffect(() => {
    if (videoRef.current) videoRef.current.muted = true
  }, [])

  const go = (tab: Tab) => {
    setMenuOpen(false)
    onEnter(tab)
  }

  return (
    <div className="hero">
      <video
        ref={videoRef}
        className="hero-video"
        src={VIDEO_SRC}
        autoPlay
        muted
        loop
        playsInline
        preload="auto"
        aria-hidden="true"
      />
      <div className="hero-scrim" aria-hidden="true" />

      <div className="hero-inner">
        <nav className="hero-nav">
          <span className="hero-brand">AETHER</span>

          <div className="hero-nav-desktop">
            {NAV_ITEMS.map(item => (
              <button key={item.tab} className="hero-nav-link" onClick={() => go(item.tab)}>
                {item.label}
              </button>
            ))}
          </div>

          <button
            className="hero-nav-toggle"
            aria-label={menuOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen(o => !o)}
          >
            {menuOpen ? <X size={22} /> : <Menu size={22} />}
          </button>

          {menuOpen && (
            <div className="hero-nav-mobile">
              {NAV_ITEMS.map(item => (
                <button key={item.tab} className="hero-nav-link" onClick={() => go(item.tab)}>
                  {item.label}
                </button>
              ))}
            </div>
          )}
        </nav>

        <main className="hero-content">
          <span className="hero-label hero-reveal">Aviation Intelligence</span>
          <h1 className="hero-title">
            <span className="hero-title-muted hero-reveal">Real-time.</span>
            <span className="hero-title-bright hero-reveal">Intelligent.</span>
          </h1>
          <p className="hero-subtitle hero-reveal">
            Live aircraft data, decoded by AI — ask anything about what&rsquo;s flying right now.
          </p>
          <div className="hero-actions hero-reveal">
            <button className="hero-btn hero-btn-primary" onClick={() => go('chat')}>
              Enter Console
            </button>
            <button className="hero-btn hero-btn-secondary" onClick={() => go('map')}>
              Explore Live Map
            </button>
          </div>
        </main>
      </div>
    </div>
  )
}
