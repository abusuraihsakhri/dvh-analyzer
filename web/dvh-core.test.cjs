"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const DVH = require("./dvh-core.js");

test("interpolates Vx and Dx including endpoints", () => {
  const p = DVH.parse("Dose_Gy,PTV,Spinal_Cord\n0,100,100\n10,80,60\n20,50,0\n30,0,0\n");
  assert.equal(DVH.volumeAt(p.doses, p.curves[0].volumes, 15), 65);
  assert.equal(DVH.volumeAt(p.doses, p.curves[0].volumes, 30), 0);
  assert.equal(DVH.doseAt(p.doses, p.curves[0].volumes, 50), 20);
  assert.equal(DVH.meanDose(p.doses, p.curves[1].volumes), 11);
});

test("converts cGy and preserves scientific metrics", () => {
  const p = DVH.parse("Dose_cGy,PTV\n0,100\n1000,50\n2000,0\n");
  assert.deepEqual(p.doses, [0, 10, 20]);
  assert.equal(DVH.metrics(p, p.curves[0], 20).mean, 10);
  assert.equal(DVH.metrics(p, p.curves[0], 20).v95rx, 5);
});

test("rejects invalid and non-monotonic DVHs", () => {
  for (const source of [
    "Dose_Gy,Lung\n0,100\n10,NaN\n20,0\n",
    "Dose_Gy,Lung\n0,100\n10,101\n20,0\n",
    "Dose_Gy,Lung\n0,100\n10,90\n20,95\n",
    "Dose_Gy,Lung\n0,100\n10,90\n9,0\n",
    "Dose_Gy,Lung,Lung\n0,100,100\n10,0,0\n",
    "Dose_Gy,Lung\n10,100\n20,0\n",
  ]) assert.throws(() => DVH.parse(source));
});
