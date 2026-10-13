"use strict";
/* Dependency-free cumulative DVH calculations for local browser analysis. */
(function (root) {
  const colors = ["#cf4446", "#3277c3", "#2f946e", "#7958b0", "#c27725",
                  "#c49a1c", "#8a5648", "#c24f98", "#64748b"];
  function splitRow(line, delimiter) {
    const cells = [];
    let cell = "", quoted = false;
    for (let i = 0; i < line.length; i++) {
      const char = line[i];
      if (char === '"') {
        if (quoted && line[i + 1] === '"') { cell += '"'; i++; }
        else { quoted = !quoted; }
      } else if (char === delimiter && !quoted) {
        cells.push(cell.trim()); cell = "";
      } else {
        cell += char;
      }
    }
    if (quoted) throw new Error("Unclosed quoted CSV field.");
    cells.push(cell.trim());
    return cells;
  }
  function parse(text) {
    if (typeof text !== "string") throw new Error("Input must be text.");
    if (text.length > 2 * 1024 * 1024) throw new Error("File exceeds the 2 MB browser limit.");
    const lines = text.replace(/^\uFEFF/, "").split(/\r?\n/).filter(line => line.trim());
    if (!lines.length) throw new Error("The DVH file is empty.");
    const headerIndex = lines.findIndex(line => /^\s*"?Dose_(?:c?Gy)"?\s*[,;\t]/i.test(line));
    if (headerIndex < 0 || headerIndex > 19) {
      throw new Error("Expected a Dose_Gy or Dose_cGy first column.");
    }
    const first = lines[headerIndex];
    const delimiter = first.includes("\t") ? "\t" : first.includes(";") ? ";" : ",";
    const header = splitRow(first, delimiter);
    if (!/^Dose_(?:c?Gy)$/i.test(header[0]) || header.length < 2) {
      throw new Error("DVH header requires a dose column and at least one structure.");
    }
    const names = header.slice(1).map(name => name.replace(/\[[^\]]*\]|\([^)]*\)/g, "").trim());
    if (names.some(name => !name) || new Set(names.map(name => name.toLowerCase())).size !== names.length) {
      throw new Error("Structure names must be distinct and nonempty.");
    }
    const factor = /^Dose_cGy$/i.test(header[0]) ? 0.01 : 1;
    const curves = names.map((name, index) => ({
      name: name,
      target: /ptv|ctv|gtv|target|tumor/i.test(name),
      color: colors[index % colors.length],
      volumes: []
    }));
    const doses = [];
    for (let i = headerIndex + 1; i < lines.length; i++) {
      const columns = splitRow(lines[i], delimiter);
      if (columns.length !== header.length || columns.some(cell => cell === "")) {
        throw new Error("Row " + (i + 1) + ": incorrect number of fields or empty value.");
      }
      const values = columns.map(cell => Number(cell));
      const dose = values[0] * factor;
      if (!Number.isFinite(dose) || dose < 0 || (doses.length && dose <= doses[doses.length - 1])) {
        throw new Error("Row " + (i + 1) + ": doses must be finite and strictly increasing.");
      }
      for (let j = 0; j < curves.length; j++) {
        const volume = values[j + 1], previous = curves[j].volumes;
        if (!Number.isFinite(volume) || volume < 0 || volume > 100) {
          throw new Error("Row " + (i + 1) + ": volumes must be within 0–100%.");
        }
        if (previous.length && volume > previous[previous.length - 1] + 1e-9) {
          throw new Error("Row " + (i + 1) + ": cumulative volume increases with dose.");
        }
        previous.push(volume);
      }
      doses.push(dose);
      if (doses.length > 10000) throw new Error("Dataset exceeds 10,000 dose rows.");
    }
    if (doses.length < 2 || Math.abs(doses[0]) > 1e-8) {
      throw new Error("DVH requires at least two rows beginning at 0 Gy.");
    }
    return { doses: doses, curves: curves };
  }
  function volumeAt(doses, vols, d) {
    if (d <= doses[0]) return vols[0];
    if (d > doses[doses.length - 1]) return 0;
    for (let i = 0; i < doses.length - 1; i++) {
      if (d >= doses[i] && d <= doses[i + 1]) {
        const f = (d - doses[i]) / (doses[i + 1] - doses[i]);
        return vols[i] + f * (vols[i + 1] - vols[i]);
      }
    }
    return vols[vols.length - 1];
  }
  function doseAt(doses, vols, v) {
    if (v >= vols[0]) return doses[0];
    if (v <= vols[vols.length - 1]) return doses[doses.length - 1];
    for (let i = 0; i < vols.length - 1; i++) {
      if (vols[i + 1] <= v && v <= vols[i]) {
        if (vols[i] === vols[i + 1]) return doses[i];
        return doses[i] + (vols[i] - v) / (vols[i] - vols[i + 1]) * (doses[i + 1] - doses[i]);
      }
    }
    return doses[doses.length - 1];
  }
  function meanDose(doses, vols) {
    let total = 0;
    for (let i = 0; i < doses.length - 1; i++) {
      total += (doses[i + 1] - doses[i]) * (vols[i] + vols[i + 1]) / 200;
    }
    return total;
  }
  function metrics(plan, curve, rx) {
    const d = plan.doses, v = curve.volumes;
    const d50 = doseAt(d, v, 50);
    return {
      mean: meanDose(d, v),
      d01: doseAt(d, v, 0.1),
      d2: doseAt(d, v, 2),
      d50: d50,
      d98: doseAt(d, v, 98),
      v20: volumeAt(d, v, 20),
      v95rx: volumeAt(d, v, 0.95 * rx),
      hi: d50 > 0.001 ? (doseAt(d, v, 2) - doseAt(d, v, 98)) / d50 : null
    };
  }
  const api = Object.freeze({ parse: parse, volumeAt: volumeAt, doseAt: doseAt,
                              meanDose: meanDose, metrics: metrics });
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.DVH = api;
})(typeof window !== "undefined" ? window : globalThis);
