// A cute cartoon zombie — big head, one open eye and one stitched-shut X eye,
// a stitched grin with a little fang, both arms raised and reaching, legs caught
// mid-shuffle. Rendered as inline SVG (no external assets), in the brand violet.
// The idle sway is CSS-driven and disabled under prefers-reduced-motion.
//
// variant="grave" adds a headstone and a mound of earth behind/around it, so on
// the landing page the little guy looks like he's clawing his way out of a grave.
// Everywhere else, use the default plain variant — just the zombie.

type Variant = "plain" | "grave";

export default function ZombieMascot({
  size = 150,
  className = "",
  animate = true,
  variant = "plain",
}: {
  size?: number;
  className?: string;
  animate?: boolean;
  variant?: Variant;
}) {
  const withGrave = variant === "grave";
  const label = withGrave
    ? "A cute violet zombie clawing its way out of a grave, arms raised"
    : "A cute violet zombie with arms raised, shuffling mindlessly";

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 140 150"
      role="img"
      aria-label={label}
      className={className}
    >
      {withGrave && (
        <g aria-hidden="true">
          {/* headstone */}
          <path
            d="M48 138 L48 78 C48 60 64 52 70 52 C76 52 92 60 92 78 L92 138 Z"
            fill="#211D2A"
            stroke="#2A2633"
            strokeWidth="2"
          />
          {/* engraved arc + faint RIP */}
          <path d="M58 82 C58 72 82 72 82 82" fill="none" stroke="#3A3542" strokeWidth="2" />
          <text
            x="70"
            y="98"
            textAnchor="middle"
            fontFamily="var(--font-sans)"
            fontSize="10"
            fontWeight="700"
            fill="#3A3542"
          >
            RIP
          </text>
        </g>
      )}

      {/* the zombie itself — sways as one group */}
      <g className={animate ? "motion-safe:animate-shuffle" : ""} style={{ transformOrigin: "70px 130px" }}>
        {/* ground shadow */}
        <ellipse cx="70" cy="140" rx="30" ry="5" fill="#000000" opacity="0.35" />

        {/* raised arms (drawn behind the body), reaching up and forward */}
        <g stroke="#6D28D9" strokeWidth="12" strokeLinecap="round" fill="none">
          <path d="M56 96 C40 92 34 74 36 60" />
          <path d="M84 96 C100 92 106 74 104 60" />
        </g>
        <g stroke="#8B5CF6" strokeWidth="8" strokeLinecap="round" fill="none">
          <path d="M56 96 C40 92 34 74 36 60" />
          <path d="M84 96 C100 92 106 74 104 60" />
        </g>
        {/* hands */}
        <circle cx="36" cy="58" r="7" fill="#8B5CF6" stroke="#6D28D9" strokeWidth="2.5" />
        <circle cx="104" cy="58" r="7" fill="#8B5CF6" stroke="#6D28D9" strokeWidth="2.5" />

        {/* legs mid-stride */}
        <g stroke="#6D28D9" strokeWidth="13" strokeLinecap="round">
          <path d="M62 116 L58 132" />
          <path d="M80 116 L86 130" />
        </g>
        <g stroke="#8B5CF6" strokeWidth="9" strokeLinecap="round">
          <path d="M62 116 L58 132" />
          <path d="M80 116 L86 130" />
        </g>

        {/* torso */}
        <rect x="52" y="88" width="36" height="34" rx="13" fill="#8B5CF6" stroke="#6D28D9" strokeWidth="3" />
        {/* stitched seam down the belly — the undead detail */}
        <path d="M70 92 L70 118" stroke="#6D28D9" strokeWidth="2" />
        <g stroke="#6D28D9" strokeWidth="1.6" strokeLinecap="round">
          <path d="M66 98 L74 98" />
          <path d="M66 106 L74 106" />
          <path d="M66 114 L74 114" />
        </g>

        {/* head — a soft rounded square, cute and oversized */}
        <rect x="44" y="24" width="52" height="50" rx="20" fill="#8B5CF6" stroke="#6D28D9" strokeWidth="3" />
        {/* upper-left sheen */}
        <ellipse cx="58" cy="38" rx="9" ry="6" fill="#B79CF2" opacity="0.55" />
        {/* a little tuft of hair */}
        <path d="M62 24 L60 16 L66 22 L70 14 L74 22 L80 16 L78 24 Z" fill="#6D28D9" />

        {/* left eye — wide open, half-awake */}
        <circle cx="60" cy="47" r="8" fill="#ECEAE4" stroke="#6D28D9" strokeWidth="1.6" />
        <circle cx="61" cy="48" r="3.4" fill="#0E0D10" />
        {/* drooping lid */}
        <path d="M52 44 Q60 40 68 44" fill="none" stroke="#6D28D9" strokeWidth="2" strokeLinecap="round" />

        {/* right eye — stitched shut with an X */}
        <g stroke="#6D28D9" strokeWidth="2.4" strokeLinecap="round">
          <path d="M77 43 L85 51" />
          <path d="M85 43 L77 51" />
        </g>

        {/* cheeks */}
        <circle cx="53" cy="58" r="3.5" fill="#6D28D9" opacity="0.45" />
        <circle cx="87" cy="58" r="3.5" fill="#6D28D9" opacity="0.45" />

        {/* stitched grin with a tiny fang */}
        <path d="M58 62 Q70 70 82 62" fill="none" stroke="#6D28D9" strokeWidth="2.4" strokeLinecap="round" />
        <g stroke="#6D28D9" strokeWidth="1.6" strokeLinecap="round">
          <path d="M64 63 L64 67" />
          <path d="M70 65 L70 69" />
          <path d="M76 63 L76 67" />
        </g>
        <path d="M66 65 L68 70 L70 65 Z" fill="#ECEAE4" />

        {/* forehead scar */}
        <g stroke="#6D28D9" strokeWidth="1.6" strokeLinecap="round">
          <path d="M82 30 L88 36" />
          <path d="M82 32 L84 30 M85 35 L87 33" />
        </g>
      </g>

      {withGrave && (
        // dirt mound in FRONT of the feet, so he reads as emerging from the earth
        <g aria-hidden="true">
          <path
            d="M20 150 C20 128 44 122 70 122 C96 122 120 128 120 150 Z"
            fill="#1A1720"
            stroke="#2A2633"
            strokeWidth="2"
          />
          {/* a few clods */}
          <circle cx="42" cy="130" r="3" fill="#2A2633" />
          <circle cx="96" cy="132" r="3.5" fill="#2A2633" />
          <circle cx="70" cy="127" r="2.5" fill="#2A2633" />
        </g>
      )}
    </svg>
  );
}
