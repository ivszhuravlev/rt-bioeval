# Developer Documentation

Instructions for developers working on the DVH Analysis Tool.

---

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run Development Server

```bash
python web/app.py
```

Browser opens at `http://127.0.0.1:5000`

---

## Command Line Usage

Process files directly without web interface:

```bash
python -m pipeline.runner
```

Reads from `input/` directory, outputs to `output/`

---

## Testing

Run unit tests:

```bash
pytest tests/ -v
```

Test coverage:
- `test_tcp.py` — TCP model validation
- `test_ntcp.py` — NTCP model validation (critical: NTCP at TD50 = 0.5)
- `test_parser.py` — DVH parsing
- `test_structures.py` — Structure mapping

---

## Configuration

Edit `config/model_params.yaml` to modify model parameters:

```yaml
tcp:
  ptv:
    a: -10           # Tissue parameter (negative for tumors)
    tcd50_gy: 60.0   # Dose for 50% tumor control
    gamma50: 2.0     # Dose-response slope

ntcp:
  lung:
    n: 0.87          # Volume parameter (0=serial, 1=parallel)
    m: 0.18          # Dose-response slope
    td50_gy: 24.5    # Dose for 50% complication
    endpoint: "pneumonitis grade ≥2"
```

See config file for complete parameter descriptions and formulas.

---

## Project Structure

```
rt-bioeval/
├── dvh/                 # DVH parsing and structure mapping
│   ├── parser.py        # Parse TPS DVH text files
│   └── structures.py    # Structure name mapping
├── models/              # Radiobiological models
│   ├── tcp_niemierko.py # TCP calculation (EUD-based)
│   └── ntcp_lkb.py      # NTCP calculation (LKB model)
├── metrics/             # DVH metrics
│   ├── lung.py          # MLD, V5, V20
│   └── cord.py          # Dmax, D0.1cc, D1cc
├── pipeline/            # Main processing pipeline
│   └── runner.py        # Batch processing and export
├── web/                 # Flask web application
│   ├── app.py           # Flask server
│   └── templates/       # HTML templates
├── config/              # Configuration
│   └── model_params.yaml
├── tests/               # Unit tests
├── input/               # Example DVH files (testing only)
└── output/              # Results (JSON, CSV)
```

---

## Building Executable

### Windows

```bash
pyinstaller --onefile --windowed --add-data "web/templates;web/templates" --add-data "config;config" web/app.py -n DVH-Analysis-Tool
```

### macOS

```bash
pyinstaller --onefile --windowed --add-data "web/templates:web/templates" --add-data "config:config" web/app.py -n DVH-Analysis-Tool
```

Executable will be in `dist/` directory.

---

## Key Implementation Details

### DVH Processing

1. **Input**: Cumulative DVH (dose in cGy, volume in %)
2. **Conversion**: cGy → Gy (/100), % → fraction (/100)
3. **Cumulative → Differential**: Required for EUD/Deff calculation
4. **Metrics**: V5/V20 use cumulative directly, MLD uses differential

### Structure Mapping

Priority-based search (config: `structure_mapping`):
- `LUNG_TOTAL` preferred over `LUNGS` for NTCP
- Explicit error if required structure not found
- No silent failures

### Models

**TCP (Niemierko):**
```
EUD = ( Σ vᵢ × Dᵢ^a )^(1/a)
TCP = 1 / ( 1 + (TCD50 / EUD)^(4×γ₅₀) )
```

**NTCP (LKB):**
```
Deff = ( Σ vᵢ × Dᵢ^(1/n) )^n
t = (Deff - TD50) / (m × TD50)
NTCP = Φ(t)
```

### Cord Metrics Note

- `Dmax` always available
- `D0.1cc` / `D1cc` require absolute volumes (cc)
- Current implementation: only Dmax (volume in % not cc)

---

## Adding New Organs

1. Add parameters to `config/model_params.yaml`:
   ```yaml
   ntcp:
     new_organ:
       n: 0.5
       m: 0.15
       td50_gy: 30.0
       endpoint: "complication description"
   ```

2. Add to structure mapping:
   ```yaml
   structure_mapping:
     new_organ:
       - "ORGAN_NAME"
   ```

3. Update `pipeline/runner.py` to process new organ

---

## Code Style

- Type hints for all functions
- Docstrings (Google style)
- Explicit error handling (no silent failures)
- Unit tests for all models

---

## Dependencies

- `numpy` — numerical computations
- `scipy` — normal distribution (ndtr)
- `pyyaml` — config parsing
- `pandas` — CSV export
- `flask` — web interface
- `pytest` — testing

---

## References

1. Niemierko A. (1997). Reporting and analyzing dose distributions: a concept of equivalent uniform dose. Med Phys 24(1):103-110.
2. Lyman JT. (1985). Complication probability as assessed from dose-volume histograms. Radiat Res Suppl 8:S13-19.
3. Kutcher GJ, Burman C. (1989). Calculation of complication probability factors for non-uniform normal tissue irradiation. Int J Radiat Oncol Biol Phys 16(6):1623-1630.
4. Marks LB et al. (2010). Use of normal tissue complication probability models in the clinic. Int J Radiat Oncol Biol Phys 76(3 Suppl):S10-19.
