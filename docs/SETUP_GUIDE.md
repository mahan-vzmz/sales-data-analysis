# Setup Guide — Windows + VS Code + Python + Pandas + Excel

This guide describes the recommended beginner setup for the project.

The instructions assume Windows and Visual Studio Code.

---

# 1. Required Software

Install or verify:

1. Python 3
2. Visual Studio Code
3. Microsoft Excel
4. Git
5. A GitHub account

---

# 2. Check Python

Open PowerShell:

```powershell
python --version
```

If that does not work:

```powershell
py --version
```

Expected result:

```text
Python 3.x.x
```

The exact version may be different.

---

# 3. Check Git

```powershell
git --version
```

Expected format:

```text
git version x.x.x
```

---

# 4. Create the Project Folder

Example:

```powershell
cd $HOME\Desktop
mkdir sales-data-analysis
cd sales-data-analysis
```

Open it in VS Code:

```powershell
code .
```

If `code` is not recognized, open VS Code manually and choose:

```text
File → Open Folder
```

---

# 5. Create Initial Folders

From PowerShell inside the project root:

```powershell
mkdir data
mkdir data\raw
mkdir data\processed
mkdir notebooks
mkdir src
mkdir reports
mkdir screenshots
mkdir docs
```

---

# 6. Create a Virtual Environment

Why?

A virtual environment keeps this project's Python packages separated from other Python projects.

Create it:

```powershell
python -m venv .venv
```

If your machine uses `py`:

```powershell
py -m venv .venv
```

---

# 7. Activate the Virtual Environment

PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

After activation, the terminal usually begins with:

```text
(.venv)
```

Example:

```text
(.venv) PS C:\Users\YourName\Desktop\sales-data-analysis>
```

---

# 8. PowerShell Execution Policy Error

If PowerShell blocks activation, you may see a message about scripts being disabled.

A common user-level command is:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then retry:

```powershell
.\.venv\Scripts\Activate.ps1
```

Understand your organization's security policies before changing execution policy on managed systems.

---

# 9. Upgrade pip

With the virtual environment active:

```powershell
python -m pip install --upgrade pip
```

---

# 10. Install Required Packages

Install:

```powershell
pip install pandas openpyxl jupyter
```

Purpose:

- `pandas` → data analysis
- `openpyxl` → read/write modern Excel `.xlsx` files
- `jupyter` → interactive notebooks

---

# 11. Verify Pandas

Run:

```powershell
python
```

Then:

```python
import pandas as pd
print(pd.__version__)
```

Exit Python:

```python
exit()
```

If there is no error, Pandas is installed.

---

# 12. Create requirements.txt

Run:

```powershell
pip freeze > requirements.txt
```

For a small educational project, this records the exact installed package versions.

Later, a fresh environment can install them with:

```powershell
pip install -r requirements.txt
```

---

# 13. VS Code Extensions

Recommended:

- Python
- Jupyter

Optional:

- Excel Viewer
- GitLens

Do not overload VS Code with unnecessary extensions.

---

# 14. Select the Python Interpreter

In VS Code:

```text
Ctrl + Shift + P
```

Search:

```text
Python: Select Interpreter
```

Choose the interpreter inside:

```text
.venv
```

On Windows it usually points to something similar to:

```text
.venv\Scripts\python.exe
```

---

# 15. Create the First Test Script

Create:

```text
src/test_setup.py
```

Add:

```python
import pandas as pd

print("Pandas is working.")
print("Version:", pd.__version__)
```

Run:

```powershell
python src\test_setup.py
```

Expected output:

```text
Pandas is working.
Version: ...
```

---

# 16. Create the First Notebook

Create:

```text
notebooks/01_data_inspection.ipynb
```

First cell:

```python
import pandas as pd

print(pd.__version__)
```

Make sure VS Code selects the `.venv` kernel.

---

# 17. Initial .gitignore

Create:

```text
.gitignore
```

Suggested content:

```gitignore
# Python
__pycache__/
*.py[cod]

# Virtual environment
.venv/
venv/

# Jupyter
.ipynb_checkpoints/

# VS Code
.vscode/

# OS files
.DS_Store
Thumbs.db

# Temporary Excel files
~$*.xlsx
~$*.xls
```

Important:

Do not ignore the actual project `.xlsx` files if they are intended to be part of the portfolio repository and contain no sensitive data.

---

# 18. Initial requirements.txt

A simple manual version can begin as:

```text
pandas
openpyxl
jupyter
```

Or use:

```powershell
pip freeze > requirements.txt
```

The second option pins installed versions.

---

# 19. Initialize Git

Inside the root folder:

```powershell
git init
```

Check:

```powershell
git status
```

Add files:

```powershell
git add .
```

First commit:

```powershell
git commit -m "chore: initialize project structure and documentation"
```

---

# 20. Connect to GitHub

After creating an empty GitHub repository named:

```text
sales-data-analysis
```

GitHub will provide commands similar to:

```powershell
git remote add origin https://github.com/YOUR_USERNAME/sales-data-analysis.git
git branch -M main
git push -u origin main
```

Replace `YOUR_USERNAME` with your actual GitHub username.

Do not copy a placeholder literally.

---

# 21. Verify Project Structure

At this stage:

```text
sales-data-analysis/
│
├── data/
│   ├── raw/
│   └── processed/
│
├── notebooks/
│   └── 01_data_inspection.ipynb
│
├── src/
│   └── test_setup.py
│
├── reports/
├── screenshots/
├── docs/
├── .gitignore
├── requirements.txt
└── README.md
```

---

# 22. Daily Startup Routine

When returning to the project:

```powershell
cd path\to\sales-data-analysis
```

Activate environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Open VS Code:

```powershell
code .
```

Check Git:

```powershell
git status
```

---

# 23. Daily Shutdown Routine

Before finishing:

```powershell
git status
```

Review changed files.

Then:

```powershell
git add .
```

Commit:

```powershell
git commit -m "descriptive message"
```

Push:

```powershell
git push
```

Do not commit broken or unexplained code only to create activity.

---

# 24. Common Beginner Errors

## `ModuleNotFoundError: No module named 'pandas'`

Possible causes:

- Virtual environment not active
- Package installed in another Python environment
- Wrong VS Code interpreter

Check:

```powershell
where python
```

Then:

```powershell
python -m pip show pandas
```

---

## Excel File Not Found

Error may look like:

```text
FileNotFoundError
```

Check:

- file name,
- extension,
- current folder,
- relative path.

Recommended project path:

```python
"data/raw/sales_data.xlsx"
```

Avoid hard-coding paths such as:

```text
C:\Users\Someone\Desktop\...
```

inside portfolio code.

---

## `ImportError` Related to Excel

Make sure:

```powershell
pip install openpyxl
```

---

# 25. Setup Completion Checklist

- [ ] Python works
- [ ] Git works
- [ ] VS Code works
- [ ] Excel available
- [ ] Project folder created
- [ ] `.venv` created
- [ ] `.venv` activated
- [ ] Pandas installed
- [ ] OpenPyXL installed
- [ ] Jupyter installed
- [ ] Correct VS Code interpreter selected
- [ ] Test script runs
- [ ] Notebook runs
- [ ] `.gitignore` created
- [ ] Git initialized
- [ ] First commit created
- [ ] GitHub remote connected
