import { useRef, useEffect } from 'react'

// Animated purple "sound" backdrop: layered glowing sine waves + a bottom
// equalizer. Purely decorative (no real audio). `energy` (0..1) swells the
// amplitude — we push it up while a playlist is generating.
export default function SoundBackground({ energy = 0 }) {
  const canvasRef = useRef(null)
  const energyRef = useRef(energy)
  energyRef.current = energy

  useEffect(() => {
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    const dpr = Math.min(window.devicePixelRatio || 1, 2)
    let raf, t = 0
    let eased = 0

    function resize() {
      canvas.width = window.innerWidth * dpr
      canvas.height = window.innerHeight * dpr
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    }
    resize()
    window.addEventListener('resize', resize)

    const waves = [
      { amp: 42, len: 0.006, speed: 0.14, y: 0.62, color: 'rgba(168, 85, 247, 0.55)', w: 2.5 },
      { amp: 30, len: 0.011, speed: 0.22, y: 0.66, color: 'rgba(139, 92, 246, 0.40)', w: 2 },
      { amp: 55, len: 0.004, speed: 0.10, y: 0.70, color: 'rgba(217, 70, 239, 0.30)', w: 3 },
      { amp: 22, len: 0.017, speed: 0.32, y: 0.58, color: 'rgba(124, 58, 237, 0.35)', w: 1.5 },
    ]

    function draw() {
      const W = window.innerWidth, H = window.innerHeight
      eased += (energyRef.current - eased) * 0.06
      const boost = 1 + eased * 1.6

      ctx.clearRect(0, 0, W, H)

      // soft radial glow behind the card
      const g = ctx.createRadialGradient(W / 2, H * 0.42, 0, W / 2, H * 0.42, Math.max(W, H) * 0.6)
      g.addColorStop(0, 'rgba(88, 28, 135, 0.38)')
      g.addColorStop(1, 'rgba(10, 6, 18, 0)')
      ctx.fillStyle = g
      ctx.fillRect(0, 0, W, H)

      ctx.globalCompositeOperation = 'lighter'
      for (const wv of waves) {
        ctx.beginPath()
        for (let x = 0; x <= W; x += 4) {
          const y = H * wv.y
            + Math.sin(x * wv.len + t * wv.speed) * wv.amp * boost
            + Math.sin(x * wv.len * 0.5 + t * wv.speed * 0.5) * wv.amp * 0.4 * boost
          x === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)
        }
        ctx.strokeStyle = wv.color
        ctx.lineWidth = wv.w
        ctx.shadowBlur = 18
        ctx.shadowColor = wv.color
        ctx.stroke()
      }

      // equalizer bars along the bottom
      const bars = 72, bw = W / bars
      ctx.shadowBlur = 0
      for (let i = 0; i < bars; i++) {
        const h = (Math.sin(i * 0.5 + t * 0.09) * 0.5 + 0.5)
          * (Math.sin(i * 0.17 + t * 0.05) * 0.5 + 0.5)
          * (50 + 130 * eased) + 6
        const x = i * bw
        const grad = ctx.createLinearGradient(0, H, 0, H - h)
        grad.addColorStop(0, 'rgba(168,85,247,0.04)')
        grad.addColorStop(1, 'rgba(217,70,239,0.5)')
        ctx.fillStyle = grad
        ctx.fillRect(x + bw * 0.2, H - h, bw * 0.6, h)
      }

      ctx.globalCompositeOperation = 'source-over'
      t += 1
      raf = requestAnimationFrame(draw)
    }
    draw()

    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('resize', resize)
    }
  }, [])

  return <canvas ref={canvasRef} className="sound-bg" aria-hidden="true" />
}
