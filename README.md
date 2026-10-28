# Pulse — Client Meeting-to-Action Tracker

Pulse converts meeting notes into an editable action brief containing decisions, tasks, owners, due dates, risks/dependencies, and unanswered questions. It keeps missing owners/deadlines as **Not stated**, flags relative dates for confirmation, and exports Markdown/TXT briefs, CSV tasks, and full JSON data.

## Run on Windows / VS Code
Open this folder in VS Code. In PowerShell terminal:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Test checklist
1. Click **Load sample meeting**.
2. Click **Extract action brief**.
3. Review Action board and confirm missing owner/date fields remain explicit.
4. Edit a task and its status; add or edit decisions, risks, and questions.
5. Download Markdown brief, task CSV, and JSON. Open the downloads and verify content.
6. Try notes without dates; ensure due date remains **Not stated**.

## Deploy
Push the folder to GitHub, visit https://share.streamlit.io/, sign in with GitHub, create an app, select the repository and `main` branch, set the main file path to `app.py`, and deploy.

## Limitations
This version uses lightweight rule-based extraction rather than a hosted LLM. It proposes likely items based on language patterns, so it may miss or misclassify statements. All results should be reviewed before sharing. It does not guess owners or deadlines.
