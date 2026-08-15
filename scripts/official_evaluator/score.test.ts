/**
 * Headless driver for the official GIS Cup evaluator.
 *
 * Mirrors the sequence the browser worker uses:
 *   parseBuildingDatasetText -> parseSolutionText -> validateSubproblemInput
 *   -> evaluateValidatedSubproblem -> buildEvaluationReport
 *
 * MUST run under vitest, not bare node: src/core/constants.ts does a bare
 * `import packageMetadata from "../../package.json"`, which needs the Vite transform.
 *
 * Environment:
 *   SCORE_DATASET   (required) path to the buildings geojson
 *   SCORE_SOLUTION  (required) path to the three-lines-per-subproblem solution text
 *   SCORE_SUMMARY   (optional) path to write the compact per-block summary JSON
 *   SCORE_REPORT    (optional) path to write the full official EvaluationReport JSON
 *                              (large: one entry per claimed building)
 *   SCORE_BLOCKS    (optional) comma-separated 1-based block indices, e.g. "1,4,7"
 *   SCORE_FULL_DIAGNOSTIC (optional) "1" to force complete perimeter computation.
 *                              Slower. Does NOT change the score.
 */
import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { performance } from "node:perf_hooks";

import { expect, test } from "vitest";

import { parseBuildingDatasetText } from "../src/core/dataset-loader.js";
import { evaluateValidatedSubproblem } from "../src/core/evaluation-engine.js";
import { buildEvaluationReport } from "../src/core/report-builder.js";
import { parseSolutionText } from "../src/core/solution-parser.js";
import { validateSubproblemInput } from "../src/core/submission-validator.js";
import { sha256Hex } from "../src/core/hash.js";
import type { EvaluatedSubproblem, EvaluationVisibilityCache } from "../src/core/evaluation-types.js";

const datasetPath = requireEnv("SCORE_DATASET");
const solutionPath = requireEnv("SCORE_SOLUTION");
const summaryPath = process.env.SCORE_SUMMARY;
const reportPath = process.env.SCORE_REPORT;
const fullDiagnosticCoverage = process.env.SCORE_FULL_DIAGNOSTIC === "1";
const selectedBlocks = parseBlockSelection(process.env.SCORE_BLOCKS);

test("scores a solution with the official evaluator", async () => {
  const datasetBytes = readFileSync(resolve(datasetPath));
  const solutionBytes = readFileSync(resolve(solutionPath));

  const loadStarted = performance.now();
  const dataset = parseBuildingDatasetText(datasetBytes.toString("utf8"));
  const loadMilliseconds = performance.now() - loadStarted;

  const solution = parseSolutionText(solutionBytes.toString("utf8"));

  console.log(`\nOFFICIAL_SCORER_DATASET ${JSON.stringify({
    datasetPath,
    solutionPath,
    spatialReferenceWkid: dataset.spatialReferenceWkid,
    buildingCount: dataset.buildings.length,
    edgeCount: dataset.edgeCount,
    vertexCount: dataset.vertexCount,
    subproblemCount: solution.subproblems.length,
    fullDiagnosticCoverage,
    selectedBlocks: selectedBlocks === undefined ? "all" : [...selectedBlocks],
    datasetLoadMilliseconds: round(loadMilliseconds),
  }, null, 2)}`);

  // The worker shares one cache across subproblems. Its key embeds the antenna set and
  // (outside full-diagnostic mode) tau, so distinct blocks never collide.
  const visibilityCache: EvaluationVisibilityCache = { byConfiguration: new Map() };
  const evaluated: EvaluatedSubproblem[] = [];
  const blockSummaries: BlockSummary[] = [];
  let totalScore = 0;

  for (const subproblem of solution.subproblems) {
    if (selectedBlocks !== undefined && !selectedBlocks.has(subproblem.index)) continue;

    const validated = validateSubproblemInput(subproblem, dataset);
    const started = performance.now();
    const result = evaluateValidatedSubproblem(dataset, validated, {
      fullDiagnosticCoverage,
      visibilityCache,
    });
    const elapsedMilliseconds = performance.now() - started;

    evaluated.push(result);
    totalScore += result.verifiedServiceScore;

    const failedClaimIds = result.buildingResults
      .filter((building) => !building.verified)
      .map((building) => building.buildingId);
    const summary: BlockSummary = {
      index: subproblem.index,
      tau: subproblem.tau,
      k: subproblem.k,
      antennasReported: subproblem.antennas.length,
      antennasRetainedByK: subproblem.retainedAntennas.length,
      antennasValid: validated.validAntennas.length,
      antennasUnique: validated.uniqueAntennas.length,
      antennasInvalid: validated.invalidRetainedAntennaCount,
      claimsReported: validated.claims.reportedIds.length,
      claimsUniqueKnown: validated.claims.uniqueKnownIds.length,
      claimsUnknown: validated.claims.unknownIds.length,
      claimsDuplicate: validated.claims.duplicateIds.length,
      verifiedServiceScore: result.verifiedServiceScore,
      failedClaimCount: failedClaimIds.length,
      failedClaimIds,
      unknownClaimIds: [...validated.claims.unknownIds],
      warningCounts: countWarnings(result.warnings.map((warning) => warning.code)),
      warningSamples: sampleWarnings(result.warnings),
      evaluationMilliseconds: round(elapsedMilliseconds),
    };
    blockSummaries.push(summary);

    // Logged per block so a long background run is observable while it is still going.
    console.log(`OFFICIAL_SCORER_BLOCK ${JSON.stringify({
      ...summary,
      failedClaimIds: `${failedClaimIds.length} ids (in summary json)`,
      unknownClaimIds: `${validated.claims.unknownIds.length} ids (in summary json)`,
    })}`);
  }

  console.log(`\nOFFICIAL_SCORER_TOTAL ${JSON.stringify({
    blocksEvaluated: blockSummaries.length,
    totalVerifiedServiceScore: totalScore,
    totalClaimsUniqueKnown: sum(blockSummaries.map((block) => block.claimsUniqueKnown)),
    totalFailedClaims: sum(blockSummaries.map((block) => block.failedClaimCount)),
  }, null, 2)}`);

  if (summaryPath !== undefined) {
    writeFileSync(resolve(summaryPath), `${JSON.stringify({
      datasetPath,
      solutionPath,
      datasetSha256: await sha256Hex(toArrayBuffer(datasetBytes)),
      solutionSha256: await sha256Hex(toArrayBuffer(solutionBytes)),
      spatialReferenceWkid: dataset.spatialReferenceWkid,
      buildingCount: dataset.buildings.length,
      fullDiagnosticCoverage,
      totalVerifiedServiceScore: totalScore,
      blocks: blockSummaries,
    }, null, 2)}\n`);
  }

  if (reportPath !== undefined) {
    const report = buildEvaluationReport(
      dataset,
      { fileName: datasetPath, sha256: await sha256Hex(toArrayBuffer(datasetBytes)) },
      { fileName: solutionPath, sha256: await sha256Hex(toArrayBuffer(solutionBytes)) },
      evaluated,
      fullDiagnosticCoverage,
    );
    writeFileSync(resolve(reportPath), `${JSON.stringify(report, null, 2)}\n`);
  }

  expect(blockSummaries.length).toBeGreaterThan(0);
});

interface BlockSummary {
  readonly index: number;
  readonly tau?: number;
  readonly k?: number;
  readonly antennasReported: number;
  readonly antennasRetainedByK: number;
  readonly antennasValid: number;
  readonly antennasUnique: number;
  readonly antennasInvalid: number;
  readonly claimsReported: number;
  readonly claimsUniqueKnown: number;
  readonly claimsUnknown: number;
  readonly claimsDuplicate: number;
  readonly verifiedServiceScore: number;
  readonly failedClaimCount: number;
  readonly failedClaimIds: readonly string[];
  readonly unknownClaimIds: readonly string[];
  readonly warningCounts: Record<string, number>;
  readonly warningSamples: Record<string, readonly string[]>;
  readonly evaluationMilliseconds: number;
}

function requireEnv(name: string): string {
  const value = process.env[name];
  if (value === undefined || value === "") {
    throw new Error(`${name} must be set. See the header comment in benchmarks/score.test.ts.`);
  }
  return value;
}

function parseBlockSelection(raw: string | undefined): Set<number> | undefined {
  if (raw === undefined || raw.trim() === "") return undefined;
  const indices = raw.split(",").map((token) => Number(token.trim()));
  if (indices.some((index) => !Number.isSafeInteger(index) || index < 1)) {
    throw new Error(`SCORE_BLOCKS must be comma-separated 1-based indices, got ${JSON.stringify(raw)}.`);
  }
  return new Set(indices);
}

function countWarnings(codes: readonly string[]): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const code of codes) counts[code] = (counts[code] ?? 0) + 1;
  return counts;
}

const WARNING_SAMPLE_LIMIT = 10;

/** Keeps a few full messages per code: the snap distance only appears in the message text. */
function sampleWarnings(
  warnings: readonly { readonly code: string; readonly message: string }[],
): Record<string, readonly string[]> {
  const samples: Record<string, string[]> = {};
  for (const warning of warnings) {
    const bucket = samples[warning.code] ?? (samples[warning.code] = []);
    if (bucket.length < WARNING_SAMPLE_LIMIT) bucket.push(warning.message);
  }
  return samples;
}

function toArrayBuffer(buffer: Buffer): ArrayBuffer {
  return buffer.buffer.slice(buffer.byteOffset, buffer.byteOffset + buffer.byteLength) as ArrayBuffer;
}

function sum(values: readonly number[]): number {
  return values.reduce((total, value) => total + value, 0);
}

function round(value: number): number {
  return Math.round(value * 100) / 100;
}
