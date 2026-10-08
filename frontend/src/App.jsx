import { useEffect, useState } from 'react'
import before from '../../contracts/verdict.before_finance.json'
import after from '../../contracts/verdict.after_finance.json'
import ServerStrip from './ServerStrip.jsx'
import VerdictCard from './VerdictCard.jsx'
import Receipt from './Receipt.jsx'
import { Pill } from './ui.jsx'

const MOCK_SERVERS = ['calendar', 'gmail', 'travel', 'finance']
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const pluggedOf = (d) => d.servers.filter((s) => s.plugged).map((s) => s.name)

// Backend: Vite proxies /api -> 127.0.0.1:8000 (vite.config.js). Throws if the API is down.
async function api(path, body) {
  const init = body === undefined ? undefined : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }
  const res = await fetch(`/api${path}`, init)
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`)
  return res.json()
}

// Save-the-demo fallback when the API is unreachable: the contract fixtures.
function mockAsk(plugged) {
  const v = plugged.includes('finance') ? after : before
  const evidence = v.evidence.filter((e) => plugged.includes(e.server))
  const not_read = MOCK_SERVERS.filter((s) => !evidence.some((e) => e.server === s))
  return { verdict: { ...v, evidence, not_read }, trace: evidence }
}

export default function App() {
  const [question, setQuestion] = useState(before.question)
  const [servers, setServers] = useState(MOCK_SERVERS)
  const [plugged, setPlugged] = useState(['calendar', 'gmail', 'travel'])
  const [live, setLive] = useState(null) // null = connecting, true = API, false = mock
  const [lit, setLit] = useState([])
  const [reading, setReading] = useState(null)
  const [busy, setBusy] = useState(false)
  const [verdict, setVerdict] = useState(null)

  // Sync with the backend's servers. Re-run whenever the API comes back, so start order doesn't matter.
  const refresh = () =>
    api('/servers').then((d) => {
      setServers(d.servers.map((s) => s.name))
      setPlugged(pluggedOf(d))
      setLive(true)
    })

  useEffect(() => {
    refresh().catch(() => setLive(false))
  }, [])

  async function run(e) {
    e.preventDefault()
    setBusy(true)
    setVerdict(null)
    setLit([])
    let d
    try {
      d = await api('/ask', { question }) // always try the API first, even after a mock answer
      if (!live) await refresh()
    } catch {
      setLive(false)
      d = mockAsk(plugged)
    }
    for (const s of new Set(d.trace.filter((t) => t.ok !== false).map((t) => t.server))) {
      setReading(s)
      await sleep(450)
      setLit((l) => [...l, s])
    }
    setReading(null)
    setVerdict(d.verdict)
    setBusy(false)
  }

  async function toggle(server) {
    setVerdict(null)
    setLit([])
    const action = plugged.includes(server) ? 'unplug' : 'plug'
    try {
      setPlugged(pluggedOf(await api(`/servers/${server}/${action}`, {})))
      return setLive(true)
    } catch {
      setLive(false)
    }
    setPlugged((p) => (action === 'unplug' ? p.filter((s) => s !== server) : [...p, server]))
  }

  const status = { null: ['bg-white', '// connecting…'], true: ['bg-lime', '// live · mcp servers'], false: ['bg-orange', '// api offline · mock data'] }[live]

  return (
    <div className="mx-auto max-w-6xl px-4 py-6 md:py-10">
      <header className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-6xl uppercase leading-none md:text-7xl">
            Life<span className="text-orange">OS</span>
          </h1>
          <p className="mt-2 text-sm">Your everyday AI that decides with you, and shows its evidence.</p>
        </div>
        <Pill className={status[0]}>{status[1]}</Pill>
      </header>

      <form onSubmit={run} className="mb-6 flex gap-3">
        <label htmlFor="q" className="sr-only">Question</label>
        <input
          id="q"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          className="min-w-0 flex-1 border-3 border-ink bg-white px-4 py-3 text-base shadow-hard-sm outline-none focus:shadow-hard md:text-lg"
        />
        <button
          disabled={busy}
          className="border-3 border-ink bg-orange px-6 font-display text-2xl uppercase shadow-hard transition active:translate-x-1 active:translate-y-1 active:shadow-none disabled:opacity-60"
        >
          {busy ? 'Reading…' : 'Ask'}
        </button>
      </form>

      <ServerStrip servers={servers} plugged={plugged} lit={lit} reading={reading} onToggle={toggle} disabled={busy} />

      <main className="mt-6 grid gap-6 lg:grid-cols-5" aria-live="polite">
        <div className="lg:col-span-3">
          <VerdictCard verdict={verdict} busy={busy} />
        </div>
        <div className="lg:col-span-2">
          <Receipt verdict={verdict} />
        </div>
      </main>
    </div>
  )
}
