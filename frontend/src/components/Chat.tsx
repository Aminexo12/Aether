import { useEffect, useRef, useState, KeyboardEvent } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Send, ArrowUpRight } from 'lucide-react'
import gsap from 'gsap'
import { useChat } from '../hooks/useChat'
import LiveStatus from './LiveStatus'
import FactTicker from './FactTicker'
import RadarScope from './RadarScope'
import { launchPlane } from './launchPlane'
import './Chat.css'

const INTENT_LABELS: Record<string, string> = {
  REALTIME:  'get_live_flights',
  KNOWLEDGE: 'search_aviation_docs',
  HYBRID:    'get_live_flights + search_aviation_docs',
  ANALYTICS: 'get_traffic_analytics',
  ANOMALY:   'detect_anomalies',
}

const SUGGESTIONS = [
  'How many flights are over France right now?',
  'What are EU 261/2004 compensation rules for delays?',
  'Show me anomalous flights in Europe',
  'Which airlines have the most flights today?',
]

// Role-aware entrance: user slides in from the left, assistant pops in from
// the right with a small scale-up — gives the chat a directional feel
// without going full chat-bubble cliche.
const msgVariants = {
  hidden:  (role: string) => ({
    opacity: 0,
    x: role === 'user' ? -18 : 18,
    scale: role === 'assistant' ? 0.94 : 1,
    filter: 'blur(4px)',
  }),
  visible: {
    opacity: 1,
    x: 0,
    scale: 1,
    filter: 'blur(0px)',
    transition: { duration: 0.32, ease: [0.25, 0, 0, 1] as const },
  },
}

const suggestionContainer = {
  hidden:  {},
  visible: { transition: { staggerChildren: 0.08, delayChildren: 0.2 } },
}

const suggestionItem = {
  hidden:  { opacity: 0, y: 10, filter: 'blur(4px)' },
  visible: {
    opacity: 1, y: 0, filter: 'blur(0px)',
    transition: { duration: 0.3, ease: [0.25, 0, 0, 1] as const },
  },
}

/* GSAP bouncing 3-dot loader */
function DotsLoader() {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!ref.current) return
    const dots = ref.current.querySelectorAll('.bounce-dot')
    const tl = gsap.timeline({ repeat: -1, defaults: { ease: 'power2.out' } })
    dots.forEach((dot, i) => {
      tl.to(dot, { y: -6, duration: 0.22 }, i * 0.13)
        .to(dot, { y: 0,  duration: 0.22, ease: 'power2.in' }, i * 0.13 + 0.22)
    })
    return () => { tl.kill() }
  }, [])
  return (
    <div ref={ref} className="dots-loader" aria-hidden="true">
      <span className="bounce-dot" />
      <span className="bounce-dot" />
      <span className="bounce-dot" />
    </div>
  )
}

export default function Chat() {
  const { messages, streaming, intent, send, clear } = useChat()
  const [input, setInput]       = useState('')
  const [focused, setFocused]   = useState(false)
  const bottomRef  = useRef<HTMLDivElement>(null)
  const inputRef   = useRef<HTMLInputElement>(null)
  const wrapperRef = useRef<HTMLDivElement>(null)
  const sendBtnRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streaming])

  const handleSend = () => {
    const text = input.trim()
    if (!text || streaming) return

    /* Tactile press on wrapper */
    if (wrapperRef.current) {
      gsap.fromTo(wrapperRef.current,
        { scale: 0.985 },
        { scale: 1, duration: 0.25, ease: 'power2.out' }
      )
    }

    /* Launch the mini plane from the send button */
    if (sendBtnRef.current) {
      launchPlane(sendBtnRef.current)
    }

    setInput('')
    send(text)
  }

  const handleKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) handleSend()
  }

  const isEmpty = messages.length === 0

  return (
    <div className="chat-shell">
      <RadarScope />
      <div className="chat">
      <div className="chat-messages">

        {/* ── Empty state ── */}
        {isEmpty && (
          <div className="chat-empty">
            <div className="chat-empty-content">
              <LiveStatus />

              <p className="chat-empty-heading">What's happening in the sky?</p>
              <p className="chat-empty-sub">Real-time data · EU regulations · Anomaly detection</p>

              <motion.div
                className="chat-suggestions"
                variants={suggestionContainer}
                initial="hidden"
                animate="visible"
              >
                {SUGGESTIONS.map(s => (
                  <motion.button
                    key={s}
                    className="suggestion"
                    variants={suggestionItem}
                    whileHover={{ scale: 1.015, transition: { duration: 0.15 } }}
                    whileTap={{ scale: 0.985 }}
                    onClick={() => { setInput(s); inputRef.current?.focus() }}
                  >
                    <span className="suggestion-text">{s}</span>
                    <ArrowUpRight size={13} strokeWidth={1.5} className="suggestion-icon" />
                  </motion.button>
                ))}
              </motion.div>

              <FactTicker />
            </div>
          </div>
        )}

        {/* ── Messages ── */}
        <AnimatePresence initial={false}>
          {messages.map(msg => (
            <motion.div
              key={msg.id}
              className={`msg msg-${msg.role}`}
              variants={msgVariants}
              custom={msg.role}
              initial="hidden"
              animate="visible"
            >
              <span className="msg-label">
                {msg.role === 'user' ? 'YOU' : 'AETHER'}
              </span>
              {msg.role === 'assistant' ? (
                <div className="msg-body prose">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      code: ({ children }) => (
                        <code className="inline-code">{children}</code>
                      ),
                      table: ({ children }) => (
                        <div className="md-table-wrap">
                          <table className="md-table">{children}</table>
                        </div>
                      ),
                    }}
                  >
                    {msg.content || ''}
                  </ReactMarkdown>
                  {streaming && !msg.content && (
                    <span className="stream-cursor" aria-hidden="true" />
                  )}
                </div>
              ) : (
                <p className="msg-body">{msg.content}</p>
              )}
            </motion.div>
          ))}
        </AnimatePresence>

        {/* ── Thinking / tool call row ── */}
        <AnimatePresence>
          {streaming && (
            <motion.div
              className="thinking-row"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.2 }}
            >
              <DotsLoader />
              {intent && (
                <motion.span
                  className="thinking-label"
                  initial={{ opacity: 0, x: -4 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  › {INTENT_LABELS[intent] ?? intent.toLowerCase()}
                </motion.span>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        <div ref={bottomRef} />
      </div>

      {/* ── Input bar ── */}
      <div className="chat-footer">
        <AnimatePresence>
          {messages.length > 0 && (
            <motion.button
              className="clear-btn"
              onClick={clear}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              CLEAR
            </motion.button>
          )}
        </AnimatePresence>

        <motion.div
          ref={wrapperRef}
          className="input-wrapper"
          animate={{ borderColor: focused ? 'var(--sky-blue)' : 'var(--contrail)' }}
          transition={{ duration: 0.15 }}
        >
          <input
            ref={inputRef}
            className="chat-input"
            type="text"
            placeholder="Ask about any flight..."
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            disabled={streaming}
            autoFocus
          />
          <motion.button
            ref={sendBtnRef}
            className="send-btn"
            onClick={handleSend}
            disabled={!input.trim() || streaming}
            whileHover={input.trim() ? { scale: 1.18 } : {}}
            whileTap={input.trim() ? { scale: 0.82 } : {}}
            transition={{ duration: 0.1 }}
            aria-label="Send"
          >
            <Send size={14} strokeWidth={2} />
          </motion.button>
        </motion.div>
      </div>
      </div>
    </div>
  )
}
