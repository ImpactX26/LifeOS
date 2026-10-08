import { Pill, Window } from './ui.jsx'

const SOURCE_COLOR = { live: 'bg-lime', user_entered: 'bg-orange' }

export default function Receipt({ verdict }) {
  return (
    <Window title="// data_receipt.log">
      {!verdict ? (
        <p className="py-12 text-center text-sm">Every number will show where it came from.</p>
      ) : (
        <>
          <h3 className="text-xs font-bold uppercase">// read ({verdict.evidence.length})</h3>
          <ul className="mt-2 space-y-3">
            {verdict.evidence.map((e) => (
              <li key={`${e.server}.${e.tool}`} className="border-l-4 border-ink pl-3">
                <div className="text-xs font-bold uppercase">
                  {e.server} · {e.tool}
                </div>
                <div className="text-sm">{e.finding}</div>
                <div className="mt-1 flex flex-wrap gap-1">
                  <Pill className={SOURCE_COLOR[e.source] ?? 'bg-white'}>{e.source}</Pill>
                  <Pill>as of {e.as_of.slice(0, 16).replace('T', ' ')}</Pill>
                </div>
              </li>
            ))}
          </ul>

          <h3 className="mt-5 text-xs font-bold uppercase">// not read</h3>
          <div className="mt-2 flex flex-wrap gap-2">
            {verdict.not_read.length ? (
              verdict.not_read.map((s) => (
                <Pill key={s} className="bg-ink text-cream">
                  {s} · not read
                </Pill>
              ))
            ) : (
              <span className="text-sm">Nothing. Every source was read.</span>
            )}
          </div>
        </>
      )}
    </Window>
  )
}
