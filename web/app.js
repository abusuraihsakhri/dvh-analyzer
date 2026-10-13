"use strict";
(function () {
  const ns = "http://www.w3.org/2000/svg";
  const byId = id => document.getElementById(id);
  let plan = null, currentSvg = null, filename = "dvh";

  function setStatus(message, error) {
    const element = byId("status");
    element.textContent = message;
    element.dataset.error = error ? "true" : "false";
  }

  function svgElement(tag, attrs, content) {
    const element = document.createElementNS(ns, tag);
    for (const key of Object.keys(attrs || {})) element.setAttribute(key, attrs[key]);
    if (content !== undefined) element.textContent = String(content);
    return element;
  }

  function drawChart(data, rx) {
    const width = 900, height = 380, left = 60, right = 24, top = 30, bottom = 52;
    const plotW = width - left - right, plotH = height - top - bottom;
    const maxD = Math.max(10, data.doses[data.doses.length - 1] * 1.04, rx * 1.1);
    const x = dose => left + dose / maxD * plotW;
    const y = volume => top + (1 - volume / 100) * plotH;
    const chart = svgElement("svg", {
      xmlns: ns, viewBox: "0 0 " + width + " " + height,
      role: "img", "aria-label": "Cumulative dose-volume histogram plot"
    });
    chart.appendChild(svgElement("rect", { x: 0, y: 0, width: width, height: height, fill: "#ffffff" }));
    for (let i = 0; i <= 5; i++) {
      const dose = maxD * i / 5, xp = x(dose), volume = 20 * i, yp = y(volume);
      chart.appendChild(svgElement("line", { x1: xp, x2: xp, y1: top, y2: y(0), stroke: "#e3e9f2" }));
      chart.appendChild(svgElement("line", { x1: left, x2: x(maxD), y1: yp, y2: yp, stroke: "#e3e9f2" }));
      chart.appendChild(svgElement("text", { x: xp, y: height - 28, "text-anchor": "middle", fill: "#56627a", "font-size": 13 }, dose.toFixed(0)));
      chart.appendChild(svgElement("text", { x: left - 12, y: yp + 4, "text-anchor": "end", fill: "#56627a", "font-size": 13 }, String(volume)));
    }
    const rxX = x(rx);
    chart.appendChild(svgElement("line", {
      x1: rxX, x2: rxX, y1: top, y2: y(0), stroke: "#c85a36",
      "stroke-width": 1.6, "stroke-dasharray": "5 5"
    }));
    chart.appendChild(svgElement("text", {
      x: Math.min(rxX + 6, width - 100), y: top + 15, fill: "#aa482b", "font-size": 12
    }, "Rx " + rx.toFixed(1) + " Gy"));
    for (const curve of data.curves) {
      const stride = Math.max(1, Math.ceil(data.doses.length / 1500));
      let path = "";
      for (let i = 0; i < data.doses.length; i += stride) {
        path += (path ? " L " : "M ") + x(data.doses[i]).toFixed(2) + " " + y(curve.volumes[i]).toFixed(2);
      }
      const last = data.doses.length - 1;
      if (last % stride !== 0) {
        path += " L " + x(data.doses[last]).toFixed(2) + " " + y(curve.volumes[last]).toFixed(2);
      }
      const line = svgElement("path", {
        d: path, fill: "none", stroke: curve.color, "stroke-width": 2.6,
        "stroke-linejoin": "round", "stroke-linecap": "round"
      });
      line.appendChild(svgElement("title", {}, curve.name));
      chart.appendChild(line);
    }
    chart.appendChild(svgElement("line", { x1: left, x2: left, y1: top, y2: y(0), stroke: "#64748b" }));
    chart.appendChild(svgElement("line", { x1: left, x2: x(maxD), y1: y(0), y2: y(0), stroke: "#64748b" }));
    chart.appendChild(svgElement("text", {
      x: left + plotW / 2, y: height - 5, "text-anchor": "middle", fill: "#334155", "font-size": 14
    }, "Dose (Gy)"));
    chart.appendChild(svgElement("text", {
      x: 17, y: top + plotH / 2, "text-anchor": "middle", fill: "#334155",
      "font-size": 14, transform: "rotate(-90 17 " + (top + plotH / 2) + ")"
    }, "Volume (%)"));
    return chart;
  }

  function value(x, digits) {
    return x === null || !Number.isFinite(x) ? "—" : x.toFixed(digits === undefined ? 2 : digits);
  }

  function addCell(row, text, element) {
    const cell = document.createElement(element || "td");
    cell.textContent = text;
    row.appendChild(cell);
    return cell;
  }

  function render() {
    if (!plan) return;
    const rxInput = byId("rx").value;
    const rx = Number(rxInput);
    if (!rxInput.trim() || !Number.isFinite(rx) || rx <= 0 || rx > 1000) {
      currentSvg = null;
      byId("chart").replaceChildren();
      byId("exports").hidden = true;
      setStatus("Prescription must be a finite dose greater than 0 and at most 1000 Gy.", true);
      return;
    }
    byId("rxBadge").textContent = "Rx " + value(rx, 1) + " Gy";
    byId("structures").textContent = plan.curves.length;
    byId("doseRows").textContent = plan.doses.length;
    byId("maxDose").textContent = value(plan.doses[plan.doses.length - 1], 1) + " Gy";
    const legend = byId("legend"), tbody = byId("metricsBody");
    legend.replaceChildren();
    tbody.replaceChildren();
    for (const curve of plan.curves) {
      const m = DVH.metrics(plan, curve, rx);
      const badge = document.createElement("span");
      badge.className = "legend-item";
      const dot = document.createElement("span");
      dot.className = "legend-dot";
      dot.style.backgroundColor = curve.color;
      badge.append(dot, document.createTextNode(curve.name));
      legend.appendChild(badge);
      const row = document.createElement("tr");
      addCell(row, curve.name, "th").scope = "row";
      [value(m.mean), value(m.d01), value(m.d98), value(m.v20, 1),
       value(m.v95rx, 1), curve.target ? value(m.hi, 3) : "—"].forEach(n => addCell(row, n));
      tbody.appendChild(row);
    }
    currentSvg = drawChart(plan, rx);
    byId("chart").replaceChildren(currentSvg);
    byId("exports").hidden = false;
    setStatus("Analyzed " + filename + " locally. Review data quality and clinical applicability before interpretation.", false);
  }

  function load(text, name) {
    try {
      plan = DVH.parse(text);
      filename = name;
      render();
    } catch (error) {
      plan = null; currentSvg = null;
      byId("chart").replaceChildren();
      byId("legend").replaceChildren();
      byId("metricsBody").replaceChildren();
      byId("exports").hidden = true;
      setStatus(error.message || "Unable to parse the DVH file.", true);
    }
  }

  function download(text, name, mime) {
    const blob = new Blob([text], { type: mime });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url; anchor.download = name;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function csvCell(v) {
    let s = String(v);
    if (/^\s*[=+\-@]/.test(s)) s = "'" + s;
    return '"' + s.replace(/"/g, '""') + '"';
  }

  byId("file").addEventListener("change", async event => {
    const file = event.target.files[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) {
      setStatus("File exceeds the 2 MB limit.", true); return;
    }
    try { load(await file.text(), file.name); }
    catch (error) { setStatus("Could not read file: " + error.message, true); }
  });

  byId("sample").addEventListener("click", async () => {
    try {
      const response = await fetch("./sample_thoracic_dvh.csv", { cache: "no-store" });
      if (!response.ok) throw new Error("HTTP " + response.status);
      load(await response.text(), "sample_thoracic_dvh.csv");
    } catch (error) {
      setStatus("Sample unavailable: " + error.message + ". Upload your own CSV instead.", true);
    }
  });

  byId("rx").addEventListener("change", render);
  byId("csvExport").addEventListener("click", () => {
    if (!plan) return;
    const rx = Number(byId("rx").value);
    const rows = [["Structure", "Dmean_Gy", "D0.1percent_Gy", "D98percent_Gy",
                   "V20Gy_percent", "V95Rx_percent", "ICRU83_HI"]];
    for (const c of plan.curves) {
      const m = DVH.metrics(plan, c, rx);
      rows.push([c.name, m.mean, m.d01, m.d98, m.v20, m.v95rx, c.target ? m.hi : ""]);
    }
    download(rows.map(r => r.map(csvCell).join(",")).join("\r\n") + "\r\n",
             "dvh_metrics.csv", "text/csv;charset=utf-8");
  });

  byId("svgExport").addEventListener("click", () => {
    if (!currentSvg) return;
    const xml = new XMLSerializer().serializeToString(currentSvg);
    download('<?xml version="1.0" encoding="UTF-8"?>\n' + xml,
             "dvh_plot.svg", "image/svg+xml;charset=utf-8");
  });
})();
