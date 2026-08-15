import { defineConfig } from "vitest/config";

// Same shape as vitest.benchmark.config.ts, but with a timeout that can absorb a
// full nine-block scoring run rather than the benchmark suite's 15 minutes.
export default defineConfig({
  test: {
    include: ["benchmarks/score.test.ts"],
    testTimeout: 21_600_000,
    hookTimeout: 21_600_000,
    teardownTimeout: 600_000,
  },
});
