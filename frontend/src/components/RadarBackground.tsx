import './RadarBackground.css'

export default function RadarBackground() {
  return (
    <div className="radar-bg" aria-hidden="true">
      <div className="radar-ring radar-ring-1" />
      <div className="radar-ring radar-ring-2" />
      <div className="radar-ring radar-ring-3" />
      <div className="radar-ring radar-ring-4" />
      <div className="radar-origin" />
    </div>
  )
}
