# DVH Analysis - Simple Instructions

## For First Time Use

### 1. Open Terminal
- Press `Cmd + Space`
- Type "Terminal"
- Press Enter

### 2. Go to Project Folder
```bash
cd /Users/iz/projects/rt-bioeval
```

### 3. Install (First Time Only)
```bash
pip install -r requirements.txt
```
Wait 1-2 minutes. You'll see green "Successfully installed" messages.

### 4. Start the Program
```bash
python3 web/app.py
```

A browser window will open automatically.

---

## Using the Program

### Upload Your Files
1. **Drag and drop** your `.txt` files into the gray upload area
   - Or click to browse and select files
   - You can upload multiple files at once

### Run Analysis
2. Click the green **"Run Analysis"** button
   - Wait ~10-30 seconds
   - Don't close the browser!

### Get Results
3. Click **"Download CSV"** to open results in Excel
   - Or click **"Download JSON"** for detailed data

---

## Next Time

Just repeat steps 1, 2, and 4:
1. Open Terminal
2. Type: `cd /Users/iz/projects/rt-bioeval`
3. Type: `python3 web/app.py`
4. Browser opens → upload files → download results

---

## Stop the Program

In Terminal, press: `Ctrl + C`

---

## Questions?

- Files should be "Cumulative DVH" format (ask TPS operator)
- Check `examples/` folder for correctly formatted files
- See README.md for more details
