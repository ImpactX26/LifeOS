// Terminal-window card: black title bar with three dots, white body.
export function Window({ title, children }) {
  return (
    <section className="border-3 border-ink bg-white shadow-hard">
      <div className="flex items-center gap-2 border-b-3 border-ink bg-ink px-3 py-2">
        <span className="size-3 rounded-full bg-orange" />
        <span className="size-3 rounded-full bg-lime" />
        <span className="size-3 rounded-full bg-cream" />
        <span className="ml-2 text-xs text-cream">{title}</span>
      </div>
      <div className="p-4 md:p-5">{children}</div>
    </section>
  )
}

export function Pill({ children, className = 'bg-white' }) {
  return (
    <span className={`inline-block border-2 border-ink px-2 py-0.5 text-[11px] font-bold uppercase ${className}`}>
      {children}
    </span>
  )
}
