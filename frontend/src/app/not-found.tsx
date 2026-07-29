import Link from "next/link";

import { StockSearch } from "@/components/StockSearch";

export default function NotFound() {
  return (
    <div className="max-w-xl mx-auto py-16 space-y-6">
      <div>
        <h1 className="text-3xl font-semibold">Not found</h1>
        <p className="text-muted mt-2">
          That page doesn&apos;t exist — or the symbol isn&apos;t in the Nifty 500 (or its
          ticker differs from what you typed). Try searching:
        </p>
      </div>

      <StockSearch />

      <div className="text-sm text-muted">
        or go back to the{" "}
        <Link href="/" className="text-accent hover:underline">
          home page
        </Link>{" "}
        ·{" "}
        <Link href="/screener" className="text-accent hover:underline">
          screener
        </Link>
      </div>
    </div>
  );
}
