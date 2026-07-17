// The emotional hook: a cursor arrow mindlessly auto-moving and clicking on a
// loop, with nobody driving it. Pure SVG + CSS (keyframes in tailwind.config).
// Fully reduced-motion-safe: when motion is reduced, the cursor simply rests.

export default function MindlessCursor({
  className = "",
}: {
  className?: string;
}) {
  return (
    <div
      className={`relative h-40 w-full overflow-hidden rounded-2xl border border-zombie-light/60 bg-white/70 ${className}`}
      aria-hidden="true"
    >
      {/* fake "buttons" the cursor keeps poking at, going nowhere */}
      <div className="absolute inset-0 flex items-center justify-around px-8 opacity-70">
        <div className="h-8 w-20 rounded-md bg-zombie-wash" />
        <div className="h-8 w-16 rounded-md bg-zombie-wash" />
        <div className="h-8 w-24 rounded-md bg-zombie-wash" />
      </div>

      {/* the mindless cursor: loops forever, no human input */}
      <div className="absolute left-10 top-8 motion-safe:animate-cursor-loop">
        {/* click ripple */}
        <span className="absolute -left-1 -top-1 block h-6 w-6 rounded-full border-2 border-zombie-dark motion-safe:animate-click-pulse" />
        <svg width="26" height="26" viewBox="0 0 26 26" className="drop-shadow-sm">
          <path
            d="M4 3 L4 22 L9 17 L13 25 L17 23 L13 15 L20 15 Z"
            fill="#1F1B16"
            stroke="#F7F4EC"
            strokeWidth="1.4"
            strokeLinejoin="round"
          />
        </svg>
      </div>

      <span className="absolute bottom-3 right-4 text-xs font-medium text-dusk">
        running · no operator
      </span>
    </div>
  );
}
