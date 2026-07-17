// A cute cartoon "zombie agent" — a little blob ghost holding a cursor arrow,
// eyes half-closed, drifting. Rendered as inline SVG (no external assets).
// The gentle idle bob is CSS-driven and disabled under prefers-reduced-motion.

export default function ZombieMascot({
  size = 140,
  className = "",
  animate = true,
}: {
  size?: number;
  className?: string;
  animate?: boolean;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 120 120"
      role="img"
      aria-label="A small green zombie agent, half asleep, drifting while holding a cursor"
      className={`${animate ? "motion-safe:animate-drift" : ""} ${className}`}
    >
      {/* soft shadow */}
      <ellipse cx="58" cy="108" rx="30" ry="6" fill="#1F1B16" opacity="0.08" />

      {/* body — a rounded blob with a wavy ghost hem */}
      <path
        d="M30 54
           C30 30 44 18 60 18
           C76 18 90 30 90 54
           L90 92
           C90 96 86 96 84 92
           C82 88 78 88 76 92
           C74 96 70 96 68 92
           C66 88 62 88 60 92
           C58 96 54 96 52 92
           C50 88 46 88 44 92
           C42 96 38 96 36 92
           L30 82 Z"
        fill="#A8C48A"
        stroke="#5C7B41"
        strokeWidth="2.5"
      />

      {/* a stitched patch — the "abandoned/undead" detail */}
      <path d="M40 44 L52 44" stroke="#5C7B41" strokeWidth="2" strokeLinecap="round" />
      <path d="M43 40 L43 48 M47 40 L47 48" stroke="#5C7B41" strokeWidth="1.6" strokeLinecap="round" />

      {/* half-closed eyes */}
      <g>
        <circle cx="50" cy="58" r="7" fill="#F7F4EC" stroke="#5C7B41" strokeWidth="1.6" />
        <circle cx="72" cy="58" r="7" fill="#F7F4EC" stroke="#5C7B41" strokeWidth="1.6" />
        <circle cx="50" cy="60" r="2.6" fill="#1F1B16" />
        <circle cx="72" cy="60" r="2.6" fill="#1F1B16" />
        {/* drooping lids */}
        <path d="M43 56 Q50 52 57 56" fill="#A8C48A" />
        <path d="M65 56 Q72 52 79 56" fill="#A8C48A" />
      </g>

      {/* sleepy mouth */}
      <path d="M55 74 Q61 78 67 74" stroke="#5C7B41" strokeWidth="2" fill="none" strokeLinecap="round" />

      {/* little arm holding a cursor it keeps mindlessly clicking */}
      <path d="M88 66 Q100 68 102 80" stroke="#5C7B41" strokeWidth="2.5" fill="none" strokeLinecap="round" />
      <g transform="translate(96 78)">
        <path
          d="M0 0 L0 16 L4 12 L7 19 L10 17 L7 10 L13 10 Z"
          fill="#F7F4EC"
          stroke="#1F1B16"
          strokeWidth="1.4"
          strokeLinejoin="round"
        />
      </g>

      {/* a "zzz" to say it's running but asleep at the wheel */}
      <g fill="#5C7B41" opacity="0.75" fontFamily="var(--font-sans)" fontWeight="700">
        <text x="94" y="40" fontSize="9">z</text>
        <text x="100" y="32" fontSize="11">z</text>
        <text x="107" y="22" fontSize="13">z</text>
      </g>
    </svg>
  );
}
