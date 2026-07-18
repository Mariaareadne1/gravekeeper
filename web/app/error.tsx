"use client";

import Link from "next/link";
import ZombieMascot from "@/components/ZombieMascot";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-5 px-6 py-12 text-center">
      <ZombieMascot size={110} />
      <h1 className="font-display text-3xl font-bold sm:text-4xl">
        Something came loose in the crypt.
      </h1>
      <p className="max-w-md text-dusk">
        An unexpected error interrupted this page. Nothing in your accounts was touched —
        GraveKeeper only ever reads.
      </p>
      <div className="mt-2 flex flex-wrap items-center justify-center gap-3">
        <button
          onClick={() => reset()}
          className="rounded-full bg-zombie px-6 py-3 text-sm font-semibold text-white transition hover:bg-zombie-dark"
        >
          Try again
        </button>
        <Link
          href="/"
          className="rounded-full border border-zombie-light px-6 py-3 text-sm font-semibold text-dusk hover:bg-zombie-wash"
        >
          Back to home
        </Link>
      </div>
    </main>
  );
}
