import Link from "next/link";
import ZombieMascot from "@/components/ZombieMascot";

export default function NotFound() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-5 px-6 py-12 text-center">
      <ZombieMascot size={110} />
      <p className="font-display text-5xl font-bold text-zombie-dark">404</p>
      <h1 className="font-display text-3xl font-bold sm:text-4xl">
        This grave is empty.
      </h1>
      <p className="max-w-md text-dusk">
        The page you were looking for has wandered off. Let&apos;s get you back to
        solid ground.
      </p>
      <Link
        href="/"
        className="mt-2 rounded-full bg-zombie px-6 py-3 text-sm font-semibold text-white transition hover:bg-zombie-dark"
      >
        Back to home
      </Link>
    </main>
  );
}
