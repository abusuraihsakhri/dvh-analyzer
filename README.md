# DVH Analyzer

### [Open the Live Application →](https://abusuraihsakhri.github.io/dvh-analyzer/)

Cumulative dose–volume histogram (DVH) analysis for radiotherapy research and education. The repository contains a dependency-free Python calculation library and CLI, a separate FastAPI demonstration service, and a static browser viewer.

**Important:** This software is not a validated treatment-planning system or medical device. It does not provide clinical approval of dose constraints. Independently verify results and protocol applicability before clinical use.

## Features

- **Browser viewer:** Upload a tabular cumulative DVH CSV/TSV, inspect dose–volume curves and dose metrics, and export SVG and metrics CSV locally. No account, API key, backend, or network upload is required to analyze an uploaded file.
- **Python library / CLI:** Parse tabular DVH data, interpolate VxGy and Dx%, calculate approximate Dmean, D0.1% (surrogate), ICRU 83 homogeneity index, and gEUD, and export SVG plots.
- **Illustrative constraint screening:** Python CLI includes a fixed set of QUANTEC/RTOG-inspired example thresholds, *not* a validated or exhaustive clinical protocol library.
- **Separate demonstration API:** Generic rule-based supervisor, PHI-pattern filter and HMAC-chained in-memory event log. These utilities do not replace clinical validation or comprehensive PHI de-identification.

## Browser app

When GitHub Pages is enabled and the deployment succeeds, the site is served from the repository's Pages deployment. To run the same interface locally:

```bash
cp sample_thoracic_dvh.csv web/sample_thoracic_dvh.csv
python -m http.server 8000 --directory web
```

Open http://localhost:8000. Use **Load sample data** or choose your own file, edit prescription dose if necessary, inspect the plot and metrics, then use the export buttons. The browser does **not** run the Python modules: the small metric routines are implemented in local JavaScript for fast, dependency-free use. The sample button loads a bundled local file from the same site; all analysis of uploaded DVH files stays on the device.

## Input format

Only **tabular cumulative** DVH CSV/TSV is supported; proprietary vendor export files may need conversion first. The first column must be `Dose_Gy` or `Dose_cGy`, followed by structure columns containing relative cumulative volume percentages (0–100). Doses must start at 0 Gy and increase strictly; cumulative volumes must not increase as dose increases. Invalid values or rows are rejected rather than silently corrected.

```csv
Dose_Gy,PTV_60Gy,Spinal_Cord,Lungs
0,100,100,100
10,100,60,50
20,100,20,25
40,100,0,0
60,0,0,0
```

All structures are treated as relative-volume curves. Absolute-volume metrics such as D0.03cc cannot be calculated without structure volumes. `compute_d_max()` reports D0.1% as a **surrogate**, not a physical maximum. Mean dose relies on the sampled cumulative curve (including its dose-range coverage). The clinical constraints catalog is illustrative and needs protocol- and fractionation-specific review.

## Python installation and CLI

Requires Python 3.9 or newer:

```bash
python -m pip install -e ".[dev]"
python -m pytest -v
python -m dvh_analyzer.cli sample-csv --output sample.csv
python -m dvh_analyzer.cli report --input sample.csv --rx 60
python -m dvh_analyzer.cli plot --input sample.csv --output dvh_plot.svg --rx 60
```

The installed `dvh-analyzer` command exposes the same DVH subcommands. For just the core library, use `python -m pip install -e .` (no runtime third-party dependencies). `.[api]` installs optional FastAPI dependencies.

## Demonstration REST API

```bash
python -m pip install -e ".[api]"
python cli.py serve --host 127.0.0.1 --port 8000
```

Routes: `GET /health`, `GET /metrics` (JSON), `POST /api/audit`, `POST /api/chat`, `GET /api/audit/logs`. The mock chat responder is not a clinical LLM. API audit logs are in-memory and are not durable across restarts. No authentication is included in the demonstration server: do not expose it to untrusted networks or submit patient identifiers.

To use Docker Compose, set a long random `AUDIT_SECRET_KEY` in the environment or an untracked local `.env` first:

```bash
export AUDIT_SECRET_KEY="$(openssl rand -hex 32)"
docker compose up --build
```

The key must remain private. Without a configured key, non-Compose invocations generate a random in-memory signing key that cannot verify log history after a restart. Regex screening is not sufficient to claim HIPAA compliance or zero-PHI safety.

## Tests and technology

Run `python -m pytest -v` for Python tests, and `node --test web/dvh-core.test.cjs` for browser computation tests (Node 22 recommended). GitHub Actions tests Python 3.10, 3.11 and 3.12 and checks browser scripts. The browser viewer uses HTML, CSS, SVG and plain JavaScript with no framework or external runtime dependency; modern versions of Chromium, Firefox and Safari are expected to work. It does not require Pyodide.

## Privacy and limitations

Uploading a file to the **browser viewer** uses only the local File API; nothing is intentionally transmitted to a server, and data is not persisted to browser storage. Exports are downloaded to the user's machine. The separately run API is a different network-connected component. Avoid entering patient-identifying information into the demonstration API or sharing exported data containing identifiers.

The `enrichment.py` classes are threshold-based example scaffolding, not implemented DICOM-RT ingestion, TCP/NTCP modeling, VMAT complexity analysis, or adaptive replanning. The fixed example constraints are not substitutes for institutional standards. The browser and CLI must not be used to make unreviewed treatment decisions.

## License

MIT — see [LICENSE](LICENSE).
