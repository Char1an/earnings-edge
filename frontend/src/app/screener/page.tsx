import { Suspense } from "react";

import ScreenerClient from "./ScreenerClient";

// useSearchParams is client-only and forces the whole subtree out of static
// prerendering; wrapping in Suspense is Next 14's escape hatch during build.
export const dynamic = "force-dynamic";

export default function ScreenerPage() {
  return (
    <Suspense fallback={null}>
      <ScreenerClient />
    </Suspense>
  );
}
