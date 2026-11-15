import assert from "node:assert/strict";
import fs from "node:fs/promises";
import { syncBuiltinESMExports } from "node:module";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import { acquireChartAlertLock } from "../src/server/chart-alert-store.ts";

test("concurrent stale-lock recovery does not remove a new owner", async () => {
  const folder = await fs.mkdtemp(path.join(os.tmpdir(), "chart-alert-stale-race-"));
  const lockPath = path.join(folder, "monitor.lock");
  await fs.writeFile(lockPath, JSON.stringify({ protocol: 2, pid: 2_147_483_647, token: "stale" }));
  const originalReadFile = fs.readFile;
  const originalUnlink = fs.unlink;
  let staleReads = 0;
  let targetUnlinks = 0;
  let releaseStaleReads;
  let signalFirstRead;
  let signalSecondRead;
  let signalStaleRemoved;
  let signalNewOwner;
  const staleReadsGate = new Promise((resolve) => { releaseStaleReads = resolve; });
  const firstRead = new Promise((resolve) => { signalFirstRead = resolve; });
  const secondRead = new Promise((resolve) => { signalSecondRead = resolve; });
  const staleRemoved = new Promise((resolve) => { signalStaleRemoved = resolve; });
  const newOwnerCreated = new Promise((resolve) => { signalNewOwner = resolve; });
  fs.readFile = async (filePath, ...args) => {
    const contents = await originalReadFile(filePath, ...args);
    if (path.resolve(String(filePath)) !== lockPath) return contents;
    staleReads += 1;
    if (staleReads === 1) signalFirstRead();
    if (staleReads === 2) signalSecondRead();
    if (staleReads <= 2) await staleReadsGate;
    return contents;
  };
  fs.unlink = async (filePath, ...args) => {
    if (path.resolve(String(filePath)) !== lockPath) return originalUnlink(filePath, ...args);
    targetUnlinks += 1;
    if (targetUnlinks === 1) {
      await originalUnlink(filePath, ...args);
      signalStaleRemoved();
      await newOwnerCreated;
      return;
    }
    if (targetUnlinks === 2) await newOwnerCreated;
    return originalUnlink(filePath, ...args);
  };
  syncBuiltinESMExports();

  let firstRecovery;
  let secondRecovery;
  let replacementOwner;
  try {
    firstRecovery = acquireChartAlertLock(lockPath);
    await firstRead;
    secondRecovery = acquireChartAlertLock(lockPath);
    const secondOutcome = await Promise.race([
      secondRead.then(() => "second-stale-read"),
      secondRecovery.then(() => "second-finished", () => "second-finished"),
    ]);
    releaseStaleReads();
    await staleRemoved;
    replacementOwner = await acquireChartAlertLock(lockPath);
    assert.ok(replacementOwner);
    const replacementToken = JSON.parse(String(await originalReadFile(lockPath, "utf8"))).token;
    signalNewOwner();

    const [first, second] = await Promise.all([firstRecovery, secondRecovery]);
    const currentToken = JSON.parse(String(await originalReadFile(lockPath, "utf8"))).token;
    assert.equal(currentToken, replacementToken, `new owner was displaced after ${secondOutcome}`);
    await first?.();
    await second?.();
  } finally {
    releaseStaleReads();
    signalNewOwner();
    await Promise.allSettled([firstRecovery, secondRecovery].filter(Boolean));
    await replacementOwner?.();
    fs.readFile = originalReadFile;
    fs.unlink = originalUnlink;
    syncBuiltinESMExports();
    await fs.rm(folder, { recursive: true, force: true });
  }
});

test("orphan recovery guards fail closed without deleting either lock file", async () => {
  const folder = await fs.mkdtemp(path.join(os.tmpdir(), "chart-alert-recovery-guard-"));
  const lockPath = path.join(folder, "monitor.lock");
  const recoveryPath = `${lockPath}.recovery`;
  const stale = JSON.stringify({ protocol: 2, pid: 2_147_483_647, token: "stale" });
  const orphan = JSON.stringify({ pid: 2_147_483_647, token: "orphan-recovery" });
  try {
    await fs.writeFile(lockPath, stale);
    await fs.writeFile(recoveryPath, orphan);
    assert.equal(await acquireChartAlertLock(lockPath), null);
    assert.equal(await fs.readFile(lockPath, "utf8"), stale);
    assert.equal(await fs.readFile(recoveryPath, "utf8"), orphan);
  } finally { await fs.rm(folder, { recursive: true, force: true }); }
});
