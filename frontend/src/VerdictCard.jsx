import { Window } from './ui.jsx'

const STAMP = {
  yes: ['Yes', 'bg-lime'],
  yes_with_conditions: ['Only if', 'bg-orange'],
  risky: ['Risky', 'bg-amber'],
  info: ['Info', 'bg-white'],
  no: ['Not yet', 'bg-danger text-white'],
  insufficient_data: ['Not sure', 'bg-white'],
}

const inr = (n) => (n < 0 ? '−' : '') + '₹' + Math.abs(n).toLocaleString('en-IN')
const range = (r) => (r?.low == null ? null : r.low === r.high ? inr(r.low) : `${inr(r.low)} to ${inr(r.high)}`)

export default function VerdictCard({ verdict, busy, explanation }) {
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
  const belowFloor = n.safety_floor != null && n.remaining?.low != null && n.remaining.low < n.safety_floor
  const costLabel = { purchase: 'Price', savings_goal: 'Price', expense: 'Cost' }[verdict.kind] || 'Trip cost'
  const day = (iso) => new Date(`${iso}T00:00:00`).toLocaleDateString('en-IN', { weekday: 'short', day: '2-digit', month: 'short' })
  const stats = [
    ['Balance', n.balance == null ? null : inr(n.balance)],
    [costLabel, range(n.trip_cost)],
    // the engine's cash-flow projection: salary in, bills and everyday spending out, day by day
    n.cash_on_day == null
      ? ['Cash on the day (est.)', null]
      : [`Cash on ${day(n.pay_day)} (est., before paying)`, inr(n.cash_on_day), n.cash_on_day < 0],
    [n.next_salary ? `Lowest before payday, ${day(n.next_salary)} (floor ${inr(n.safety_floor)})` : 'Lowest before payday',
      range(n.remaining), belowFloor],
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

      {explanation && (
        <p className="mt-4 border-l-4 border-orange bg-cream p-3 text-sm">
          <span className="font-bold">// gemini explains: </span>
          {explanation}
        </p>
      )}

      <dl className="mt-6 grid grid-cols-2 gap-3">
        {stats.map(([k, v, bad]) => (
          <div key={k} className="border-2 border-ink bg-cream p-3">
            <dt className="text-[11px] font-bold uppercase">// {k}</dt>
            <dd className={`mt-1 font-display text-2xl ${v == null ? 'text-ink/40' : bad ? 'text-danger' : ''}`}>
              {v ?? 'not read'}
            </dd>
          </div>
        ))}
      </dl>

      {n.math?.length > 0 && (
        <>
          {/* the lowest-point number above, as a receipt: every row is from the engine and they add up exactly */}
          <h3 className="mt-6 text-xs font-bold uppercase">// the math</h3>
          <table className="mt-2 w-full border-2 border-ink bg-cream text-sm">
            <tbody>
              {n.math.map((r, i) => {
                const total = i === n.math.length - 1
                return (
                  <tr key={i} className={total ? 'border-t-2 border-ink font-bold' : ''}>
                    <td className="w-6 py-1 pl-3 font-bold">{total ? '=' : r.amount < 0 ? '−' : '+'}</td>
                    <td className="py-1">{r.label}</td>
                    <td className={`py-1 pr-3 text-right tabular-nums ${total && r.amount < n.safety_floor ? 'text-danger' : ''}`}>
                      {total ? inr(r.amount) : inr(Math.abs(r.amount))}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </>
      )}

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
