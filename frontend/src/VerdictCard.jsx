import { Window } from './ui.jsx'

const STAMP = {
  yes: ['Yes', 'bg-lime'],
  yes_with_conditions: ['Only if', 'bg-orange'],
  no: ['No', 'bg-danger text-white'],
  insufficient_data: ['Not sure', 'bg-white'],
}

const inr = (n) => (n < 0 ? '−' : '') + '₹' + Math.abs(n).toLocaleString('en-IN')
const range = (r) => (r?.low == null ? null : r.low === r.high ? inr(r.low) : `${inr(r.low)} to ${inr(r.high)}`)

export default function VerdictCard({ verdict, busy }) {
  if (!verdict) {
    return (
      <Window title="// verdict.json">
        <p className="py-12 text-center text-sm">
          {busy ? 'Reading your sources…' : 'Ask a question. LifeOS only reads the sources you plug in.'}
        </p>
      </Window>
    )
  }

  const [label, color] = STAMP[verdict.verdict]
  const n = verdict.numbers
  const stats = [
    ['Balance', n.balance == null ? null : inr(n.balance)],
    ['Trip cost', range(n.trip_cost)],
    ['Monthly commitments', n.monthly_commitments == null ? null : inr(n.monthly_commitments)],
    ['Left after safety floor', range(n.remaining)],
  ]

  return (
    <Window title="// verdict.json">
      <div className="flex flex-wrap items-start gap-4">
        <div
          key={verdict.verdict}
          className={`animate-stamp border-3 border-ink px-4 py-1 font-display text-5xl uppercase shadow-hard ${color}`}
        >
          {label}
        </div>
        <h2 className="min-w-0 flex-1 font-display text-3xl uppercase leading-tight">{verdict.headline}</h2>
      </div>

      <dl className="mt-6 grid grid-cols-2 gap-3">
        {stats.map(([k, v]) => (
          <div key={k} className="border-2 border-ink bg-cream p-3">
            <dt className="text-[11px] font-bold uppercase">// {k}</dt>
            <dd className={`mt-1 font-display text-2xl ${v == null ? 'text-ink/40' : v.startsWith('−') ? 'text-danger' : ''}`}>
              {v ?? 'not read'}
            </dd>
          </div>
        ))}
      </dl>

      {verdict.tradeoffs.length > 0 && (
        <>
          <h3 className="mt-6 text-xs font-bold uppercase">// the plan</h3>
          <ul className="mt-2 space-y-2">
            {verdict.tradeoffs.map((t) => (
              <li key={t} className="flex gap-2 text-sm">
                <span className="font-bold text-orange">→</span>
                {t}
              </li>
            ))}
          </ul>
        </>
      )}
    </Window>
  )
}
