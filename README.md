# DVH Analysis Tool

Automated analysis of DVH (Dose-Volume Histogram) data for lung cancer radiotherapy.
Compares **VMAT/VIMA** vs **IMRT** treatment plans.

**Status:** Release Candidate (RC) / Pre-release

**Note:** Executable build is planned. Current version requires Python installation (temporary).

---

## Quick Start Guide

### Step 1: Install Python (one-time setup)

**Check if Python is already installed:**
```bash
python3 --version
```

If you see "Python 3.10" or higher, skip to Step 2.

**If not installed:**
- Download from: https://www.python.org/downloads/
- Install version 3.10 or newer
- On macOS, use `python3` instead of `python`

### Step 2: Install Dependencies (one-time setup)

Open Terminal and run:
```bash
pip install -r requirements.txt
```

Wait for installation to complete (1-2 minutes).

### Step 3: Start the Application

```bash
python3 web/app.py
```

Your browser will automatically open to `http://localhost:5000`

### Step 4: Use the Application

1. **Upload Files**
   - Drag and drop your DVH `.txt` files into the upload area
   - Or click to browse and select files
   - You can upload multiple files at once

2. **Run Analysis**
   - Click the green **"Run Analysis"** button
   - Wait 10-30 seconds for processing

3. **Download Results**
   - Click **"Download JSON"** for detailed data
   - Click **"Download CSV"** to open in Excel

---

## What Files to Upload

**File Format:**
- `.txt` files exported from your Treatment Planning System
- Must be **Cumulative DVH** (not Differential)
- Dose in cGy, Volume in %

**Required Structures in Files:**
Your DVH files must contain these structures:
- `PTV_6000` or `PTV_6600` — tumor target
- `LUNG_TOTAL` — lungs
- `HEART` — heart
- `ESOPHAGUS` — esophagus
- `SPINAL_CORD` — spinal cord

**Example Files:**
See `examples/` folder for correctly formatted files (LCMD2, LCMD3).

---

## Output Files

### JSON Format

Complete results including:
- TCP (Tumor Control Probability) for PTV
- NTCP (Normal Tissue Complication Probability) for organs at risk
- DVH metrics (Mean Lung Dose, V5, V20, Dmax)
- Plan comparison (VMAT vs IMRT deltas)

### CSV Format

One row per treatment plan with columns:
- Patient ID, Plan Name
- TCP values
- NTCP values (lung, heart, esophagus, spinal cord)
- DVH metrics

Import into Excel or any spreadsheet software for further analysis.

---

## Models Used

### TCP (Tumor Control Probability)
- Model: Niemierko (EUD-based)
- Reference: Niemierko A. (1997). Med Phys 24(1):103-110

### NTCP (Normal Tissue Complication Probability)
- Model: Lyman-Kutcher-Burman (LKB)
- References:
  - Lyman JT. (1985). Radiat Res Suppl 8:S13-19
  - Kutcher GJ, Burman C. (1989). Int J Radiat Oncol Biol Phys 16(6):1623-1630
  - Marks LB et al. (2010). Int J Radiat Oncol Biol Phys 76(3 Suppl):S10-19

---

## Common Issues

**Browser doesn't open:**
- Open any browser and type: `http://localhost:5000`

**"Structure not found" error:**
- Your DVH file is missing required structures (see "What Files to Upload")
- Check that structure names match exactly (e.g., `LUNG_TOTAL` not `LUNGS`)

**"Port 5000 already in use":**
- Close other programs that might use port 5000
- Restart your computer if needed

**"Module not found" errors:**
- Run installation again: `pip install -r requirements.txt`
- Make sure you're using Python 3.10 or newer: `python3 --version`

**Files uploaded but no results:**
- Check that files are **Cumulative DVH** format (not Differential)
- Verify dose is in cGy (~6000 for PTV), not Gy (~60)

---

## Support

For technical support or questions about clinical parameters, refer to the model references above or consult with your medical physics team.

---

## Roadmap

### Planned Features

- **Standalone Executable** (high priority)
  - No Python installation required
  - Single-file distribution for Windows/macOS
  - Options being evaluated:
    - Clean build on non-conda environment
    - Windows-specific build
    - Embedded Python launcher

- **Additional Features** (future)
  - Statistical analysis of plan comparisons
  - DVH visualization (matplotlib/plotly)
  - Batch export options

---

## Development Status

**Current Version:** Release Candidate (RC1)

**What Works:**
- ✅ DVH parsing (cumulative, all units)
- ✅ TCP/NTCP calculations (validated)
- ✅ All metrics (MLD, V5, V20, Dmax)
- ✅ Web interface (upload, process, download)
- ✅ JSON + CSV export
- ✅ VMAT vs IMRT comparison

**Known Limitations:**
- ⚠️ Requires Python installation (temporary)
- ⚠️ Cord D0.1cc/D1cc metrics require absolute volumes (currently only Dmax)

---

## License

Research tool for radiotherapy plan evaluation.
