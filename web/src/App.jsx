import { useState } from 'react'
import SoundBackground from './SoundBackground.jsx'

// When the frontend is hosted separately (e.g. Render static site), set
// VITE_API_BASE to the backend URL (e.g. https://yourapp.fly.dev). When the
// backend serves the frontend itself, leave it unset — relative /api works.
const API_BASE = import.meta.env.VITE_API_BASE || ''

export default function App() {
  const [song, setSong] = useState('')
  const [artist, setArtist] = useState('')
  const [length, setLength] = useState(20)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [linking, setLinking] = useState(false)
  const [links, setLinks] = useState(null)   // [{name, artist, url}] aligned to tracks
  const [linkError, setLinkError] = useState('')
  const [copied, setCopied] = useState(false)

  async function submit(e) {
    e.preventDefault()
    if (!song.trim() || loading) return
    setLoading(true); setError(''); setResult(null); setLinks(null); setLinkError(''); setCopied(false)
    try {
      const res = await fetch(`${API_BASE}/api/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ song, artist: artist || null, length: Number(length) }),
      })
      const data = await res.json()
      if (data.error) setError(data.error)
      else setResult(data)
    } catch {
      setError('Could not reach the server — is the backend running on :8008?')
    } finally {
      setLoading(false)
    }
  }

  async function findOnSpotify() {
    if (!result || linking) return
    setLinking(true); setLinkError(''); setCopied(false)
    try {
      const res = await fetch(`${API_BASE}/api/links`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: `Same feel as ${result.seed.name}`,
          tracks: result.tracks.map(t => ({ name: t.name, artist: t.artist })),
        }),
      })
      const data = await res.json()
      if (data.error) setLinkError(data.error)
      else setLinks(data.tracks)
    } catch {
      setLinkError('Could not reach the server.')
    } finally {
      setLinking(false)
    }
  }

  async function copyLinks() {
    const urls = (links || []).map(l => l.url).filter(Boolean).join('\n')
    if (!urls) return
    try {
      await navigator.clipboard.writeText(urls)
      setCopied(true)
      setTimeout(() => setCopied(false), 2500)
    } catch { /* clipboard blocked; the links are still clickable below */ }
  }

  // url for a given track row, once links have been fetched (aligned by index)
  const urlFor = i => links && links[i] && links[i].url

  return (
    <>
      <SoundBackground energy={loading ? 1 : 0} />
      <main className="wrap">
        <header className="head">
          <h1>Playlist<span>Maker</span></h1>
          <p>Give me a song — I'll find others with the same feel.</p>
        </header>

        <form className="card" onSubmit={submit}>
          <label className="field">
            <span>Song</span>
            <input value={song} onChange={e => setSong(e.target.value)}
                   placeholder="Mr. Brightside" autoFocus />
          </label>
          <label className="field">
            <span>Artist <em>optional</em></span>
            <input value={artist} onChange={e => setArtist(e.target.value)}
                   placeholder="The Killers" />
          </label>
          <label className="field slider">
            <span>Length <b>{length}</b></span>
            <input type="range" min="5" max="50" value={length}
                   onChange={e => setLength(e.target.value)} />
          </label>
          <button disabled={loading || !song.trim()}>
            {loading ? 'Listening…' : 'Generate playlist'}
          </button>
        </form>

        {error && <div className="error">{error}</div>}

        {result && (
          <section className="results">
            <div className="results-head">
              <div className="seed">
                <span>Same feel as</span>
                <b>{result.seed.name}</b> — {result.seed.artist}
              </div>
              {!links ? (
                <button type="button" className="save" onClick={findOnSpotify} disabled={linking}>
                  {linking ? 'Finding…' : 'Find on Spotify'}
                </button>
              ) : (
                <button type="button" className="save" onClick={copyLinks}>
                  {copied ? '✓ Copied!' : 'Copy Spotify links'}
                </button>
              )}
            </div>

            {linkError && <div className="error small">{linkError}</div>}
            {links && (
              <div className="hint">
                Copy the links, then in the Spotify desktop app make a new playlist and paste — it fills instantly.
                {links.filter(l => !l.url).length ? ` (${links.filter(l => !l.url).length} not found on Spotify)` : ''}
              </div>
            )}

            <ol>
              {result.tracks.map((t, i) => {
                const url = urlFor(i)
                return (
                  <li key={t.uri}>
                    <span className="num">{i + 1}</span>
                    <span className="meta">
                      {url
                        ? <a className="title link" href={url} target="_blank" rel="noreferrer">{t.name}</a>
                        : <span className="title">{t.name}</span>}
                      <span className="by">{t.artist}</span>
                    </span>
                    <span className="bar" title={`similarity ${t.score}`}>
                      <i style={{ width: `${Math.max(4, t.score * 100)}%` }} />
                    </span>
                  </li>
                )
              })}
            </ol>
          </section>
        )}
      </main>
    </>
  )
}
