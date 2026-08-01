import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import './FactTicker.css'

// Each fact is one short sentence — operational aviation knowledge, not trivia.
// Picked so a recruiter scanning the page learns something specific in 4 seconds.
const FACTS: { tag: string; body: string }[] = [
  { tag: 'ADS-B',     body: 'Every aircraft broadcasts position on 1090 MHz — Aether reads that signal.' },
  { tag: 'EU 261',    body: 'Flights over 3,500 km delayed 4+ hours owe passengers €600.' },
  { tag: 'FL360',     body: 'Flight level 360 means 36,000 ft — standard long-haul cruise altitude.' },
  { tag: 'SQUAWK',    body: '7500 means hijack, 7600 radio failure, 7700 general emergency.' },
  { tag: 'ETOPS',     body: 'Extended-range twin operations — how far a 2-engine jet can fly from a runway.' },
  { tag: 'METAR',     body: 'Coded weather observations issued by airports every 30 minutes.' },
  { tag: 'VECTOR',    body: 'Controllers steer aircraft by heading — “turn left, vector 250”.' },
  { tag: 'GO-AROUND', body: 'Aborted landing — pilots climb out and re-enter the approach pattern.' },
]

const ROTATE_MS = 6500

export default function FactTicker() {
  const [i, setI] = useState(0)

  useEffect(() => {
    const id = setInterval(() => setI(p => (p + 1) % FACTS.length), ROTATE_MS)
    return () => clearInterval(id)
  }, [])

  const fact = FACTS[i]

  return (
    <div className="fact-ticker" role="note" aria-live="polite">
      <AnimatePresence mode="wait">
        <motion.div
          key={fact.tag}
          className="fact-line"
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -4 }}
          transition={{ duration: 0.3, ease: [0.25, 0, 0, 1] }}
        >
          <span className="fact-tag">{fact.tag}</span>
          <span className="fact-body">{fact.body}</span>
        </motion.div>
      </AnimatePresence>
    </div>
  )
}
