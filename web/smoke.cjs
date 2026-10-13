"use strict";
const assert = require("node:assert/strict");
const { chromium } = require("playwright");

(async () => {
  const url = process.env.PAGES_URL;
  if (!url) throw new Error("PAGES_URL is required.");
  const browser = await chromium.launch({ headless: true });
  const errors = [];
  try {
    const page = await browser.newPage({ acceptDownloads: true });
    page.on("pageerror", error => errors.push(error.message));
    const response = await page.goto(url, { waitUntil: "networkidle" });
    assert.equal(response.status(), 200, "Page must load");

    await page.getByRole("button", { name: "Load sample data" }).click();
    await page.waitForFunction(() => document.querySelectorAll("#metricsBody tr").length === 5);
    assert.equal(await page.locator("#chart svg path").count(), 5, "Five DVH curves are plotted");
    assert.equal(await page.locator("#structures").textContent(), "5");
    assert.equal(await page.locator("#status").getAttribute("data-error"), "false");
    assert.equal(await page.locator("#exports").isVisible(), true);

    const [csv] = await Promise.all([
      page.waitForEvent("download"),
      page.getByRole("button", { name: "Export metrics CSV" }).click()
    ]);
    assert.equal(csv.suggestedFilename(), "dvh_metrics.csv");

    const [svg] = await Promise.all([
      page.waitForEvent("download"),
      page.getByRole("button", { name: "Export plot SVG" }).click()
    ]);
    assert.equal(svg.suggestedFilename(), "dvh_plot.svg");

    await page.locator("#file").setInputFiles({
      name: "invalid.csv", mimeType: "text/csv",
      buffer: Buffer.from("Dose_Gy,Lung\n0,100\n10,90\n20,95\n")
    });
    await page.waitForFunction(() => document.querySelector("#status").dataset.error === "true");
    assert.equal(await page.locator("#exports").isVisible(), false, "Invalid data blocks exports");

    await page.locator("#file").setInputFiles({
      name: "valid.csv", mimeType: "text/csv",
      buffer: Buffer.from("Dose_Gy,PTV\n0,100\n10,50\n20,0\n")
    });
    await page.waitForFunction(() => document.querySelector("#status").dataset.error === "false");
    assert.equal(await page.locator("#metricsBody tr").count(), 1, "Local upload analyzes data");

    await page.locator("#rx").fill("0");
    await page.locator("#rx").dispatchEvent("change");
    assert.equal(await page.locator("#exports").isVisible(), false, "Invalid Rx blocks exports");
    assert.deepEqual(errors, [], "No uncaught page JavaScript errors");
    console.log("Live browser DVH upload, plot, validation and exports passed.");
  } finally {
    await browser.close();
  }
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
