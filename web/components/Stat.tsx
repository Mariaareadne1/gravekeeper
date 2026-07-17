import CountUp from "./CountUp";

// One animated stat card. Numbers are industry findings (see landing copy),
// phrased as findings — never as GraveKeeper's own measurements.
export default function Stat({
  end,
  prefix,
  suffix,
  decimals,
  headline,
  caption,
}: {
  end: number;
  prefix?: string;
  suffix?: string;
  decimals?: number;
  headline: string;
  caption: string;
}) {
  return (
    <div className="rounded-2xl border border-zombie-light/50 bg-white/70 p-6 shadow-sm">
      <div className="font-display text-4xl font-bold text-zombie-dark sm:text-5xl">
        <CountUp end={end} prefix={prefix} suffix={suffix} decimals={decimals} />
      </div>
      <div className="mt-2 font-semibold text-ink">{headline}</div>
      <p className="mt-1 text-sm leading-relaxed text-dusk">{caption}</p>
    </div>
  );
}
