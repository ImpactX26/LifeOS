import { useState } from 'react'
import before from '../../contracts/verdict.before_finance.json'
import after from '../../contracts/verdict.after_finance.json'
import ServerStrip from './ServerStrip.jsx'
import VerdictCard from './VerdictCard.jsx'
import Receipt from './Receipt.jsx'
import { Pill } from './ui.jsx'

const SERVERS = ['calendar', 'gmail', 'travel', 'finance', 'price']
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

// Mock backend until B ships POST /ask: Finance plugged in => the "after" contract.
// ponytail: mock ignores the question text; swap this one function for fetch('/ask') at integration (H6).
async function ask(_question, plugged) {
  const v = plugged.includes('finance') ? after : before
  const evidence = v.evidence.filter((e) => plugged.includes(e.server))
  const not_read = SERVERS.filter((s) => !evidence.some((e) => e.server === s))
  return { ...v, evidence, not_read }
}

export default function App() {
  const [question, setQuestion] = useState(before.question)
  const [plugged, setPlugged] = useState(['calendar', 'gmail', 'travel'])
  const [lit, setLit] = useState([])
  const [reading, setReading] = useState(null)
  const [busy, setBusy] = useState(false)
  const [verdict, setVerdict] = useState(null)

  async function run(e) {
    e.preventDefault()
    setBusy(true)
    setVerdict(null)
    setLit([])
    const v = await ask(question, plugged)
    for (const s of new Set(v.evidence.map((x) => x.server))) {
      setReading(s)
      await sleep(500)
      setLit((l) => [...l, s])
    }
    setReading(null)
    setVerdict(v)
    setBusy(false)
  }

  function toggle(server) {
    setPlugged((p) => (p.includes(server) ? p.filter((s) => s !== server) : [...p, server]))
    setVerdict(null)
    setLit([])
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-6 md:py-10">
      <header className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-6xl uppercase leading-none md:text-7xl">
            Life<span className="text-orange">OS</span>
          </h1>
          <p className="mt-2 text-sm">Your everyday AI that decides with you, and shows its evidence.</p>
        </div>
        <Pill className="bg-lime">// mock data · contracts/*.json</Pill>
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

      <ServerStrip servers={SERVERS} plugged={plugged} lit={lit} reading={reading} onToggle={toggle} disabled={busy} />

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
