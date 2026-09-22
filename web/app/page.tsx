export default function Home() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-zinc-50 dark:bg-zinc-950">
      <div className="mx-4 max-w-lg rounded-2xl border border-zinc-200 bg-white p-10 text-center shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <h1 className="text-4xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
          Lectern
        </h1>
        <p className="mt-3 text-lg text-zinc-600 dark:text-zinc-300">
          Read with receipts.
        </p>
        <p className="mt-6 text-sm leading-relaxed text-zinc-500 dark:text-zinc-400">
          A provenance-first reading workspace — every claim shows its source,
          and every document is treated as untrusted input. Building in public,
          week 1 of 8.
        </p>
      </div>
    </main>
  );
}
