# Google Forms Automation & Response Manager

A Streamlit-based tool to automate Google Form submissions with weighted probabilities and synthetic data generation.

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Launch the App
```bash
streamlit run app.py
```

### 3. Use the 4-Tab Workflow

| Tab | Purpose |
|-----|---------|
| **1. Form URL & Parsing** | Paste a public Google Form URL → extracts questions, entry IDs, choices |
| **2. Question Probabilities** | Set weights for multiple-choice; configure mock generators for text fields |
| **3. Multi-Submission Engine** | Run N submissions with configurable delay; view live logs + export CSV |
| **4. Standalone Script** | Export a portable `.py` file to run anywhere without Streamlit |

---

## Tab 1: Parse a Form
- Paste any public Google Form URL (e.g., `https://docs.google.com/forms/d/e/.../viewform` or `forms.gle/...`)
- Click **Fetch & Parse**
- Or use **Load Sample Demo Form** in sidebar for instant testing

---

## Tab 2: Configure Answers

### Choice Questions (Radio, Dropdown, Checkbox, Scale)
- Each option gets a **weight slider** (0–100)
- Probability = weight / total_weight
- Toolbar buttons: **Equalize All** / **Randomize All**

### Text Questions (Short Answer, Paragraph)
| Mode | Use Case |
|------|----------|
| **Mock Generator** | Name, Email, Phone, Date, Feedback, Rating, Number |
| **Custom List** | One value per line → random pick per submission |
| **Fixed String** | Same value every time |
| **Blank** | Submit empty (optional fields only) |

---

## Tab 3: Run Submissions
- Set **Total Responses** (1–1000)
- Set **Delay Between Requests** (0.05–5 sec)
- **Preview Single Payload** → dry-run JSON
- **Test 1 Live Submission** → verify endpoint works
- **Start Multi-Submission** → progress bar + live metrics
- **Download Submission Logs (CSV)** after completion

---

## Tab 4: Export Standalone Script
- Click **Download Standalone Python Script**
- Runs with just `python google_form_submitter.py`
- No Streamlit dependency

---

## Sidebar Features
- **Preset Profiles** → Save/Load/Delete configurations to SQLite (`form_presets.db`)
- **User-Agent** → Customize HTTP header
- **Clear Logs** → Reset execution history

---

## Running the Standalone Script
```bash
python google_form_submitter.py
```
Edit `run_submissions(total_count=10, delay_sec=0.5)` at the bottom to change volume/speed.

---

## Requirements
- Python 3.9+
- Public Google Form (no login required)
- Network access to `docs.google.com`

---

## Tips
- Use **forms.gle** short links — auto-resolved
- For checkboxes: weight = independent inclusion probability (%)
- For required fields left blank: generator picks a fallback
- Save presets before closing — survives restarts

---

## File Structure
```
Google Form Filler/
├── app.py              # Streamlit UI (main entry)
├── form_parser.py      # HTML → structured questions
├── generator.py        # Weighted pick + mock data
├── database.py         # SQLite preset storage
├── requirements.txt
├── test_*.py           # Unit tests
└── form_presets.db     # Created on first save
```