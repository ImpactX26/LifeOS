import { Pill } from './ui.jsx'

const LOOK = {
  off: ['border-dashed bg-cream text-ink/50', 'unplugged', 'bg-cream'],
  idle: ['bg-white', 'connected', 'bg-white'],
  reading: ['bg-orange animate-pulse-read', 'reading…', 'bg-white'],
  read: ['bg-lime', '✓ read', 'bg-white'],
}

export default function ServerStrip({ servers, plugged, lit, reading, onToggle, disabled }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
      {servers.map((s) => {
        const on = plugged.includes(s)
        const state = !on ? 'off' : reading === s ? 'reading' : lit.includes(s) ? 'read' : 'idle'
        const [box, label, pill] = LOOK[state]
        return (
          <div key={s} className={`border-3 border-ink p-3 shadow-hard-sm transition-colors ${box}`}>
            <div className="text-[10px] font-bold uppercase">// mcp server</div>
            <div className="font-display text-2xl uppercase">{s}</div>
            <div className="mt-2 flex items-center justify-between gap-2">
              <Pill className={pill}>{label}</Pill>
              <button
                type="button"
                onClick={() => onToggle(s)}
                disabled={disabled}
                aria-pressed={on}
                className="border-2 border-ink bg-white px-2 text-[11px] font-bold uppercase hover:bg-ink hover:text-cream disabled:opacity-50"
              >
                {on ? 'Unplug' : 'Plug in'}
              </button>
            </div>
          </div>
        )
      })}
    </div>
  )
}
