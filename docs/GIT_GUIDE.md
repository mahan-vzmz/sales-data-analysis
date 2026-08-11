# Git & GitHub Guide for This Project

This guide contains the Git workflow recommended for the Sales Data Analysis project.

The goal is not to learn every Git command.

The goal is to safely manage the project and create a clean public history.

---

# 1. Core Concepts

## Repository

A Git repository is a project tracked by Git.

---

## Commit

A commit is a saved checkpoint in project history.

A good commit represents a meaningful change.

---

## Branch

A branch is a separate line of development.

For this beginner project, working on `main` is acceptable initially.

Later, feature branches can be introduced.

---

## Remote

A remote is a linked Git repository stored somewhere else, usually GitHub.

Typical name:

```text
origin
```

---

# 2. Initialize the Repository

```powershell
git init
```

Check:

```powershell
git status
```

---

# 3. Basic Daily Workflow

## Step 1 — Check changes

```powershell
git status
```

## Step 2 — Review changes

```powershell
git diff
```

## Step 3 — Stage selected files

All:

```powershell
git add .
```

Or one file:

```powershell
git add README.md
```

## Step 4 — Commit

```powershell
git commit -m "docs: add project setup guide"
```

## Step 5 — Push

```powershell
git push
```

---

# 4. Recommended Commit Style

Use small descriptive commits.

Examples:

```text
chore: initialize project structure
docs: add learning roadmap
data: add initial sales dataset
feat: load Excel dataset with pandas
feat: add missing value inspection
fix: normalize city names
feat: calculate sales metrics
feat: add monthly revenue analysis
feat: export summary to Excel
docs: add dashboard screenshots
```

---

# 5. Commit Prefixes

Suggested prefixes:

| Prefix | Use |
|---|---|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation |
| `data` | Dataset-related change |
| `refactor` | Code improvement without behavior change |
| `test` | Tests |
| `chore` | Setup/maintenance |

This convention is optional, but it creates a more readable history.

---

# 6. What Not to Commit

Do not commit:

```text
.venv/
__pycache__/
.ipynb_checkpoints/
temporary Excel files
passwords
API keys
private datasets
personal information
huge unrelated files
```

---

# 7. Inspect History

Compact history:

```powershell
git log --oneline
```

Example:

```text
a12bc34 feat: add monthly sales analysis
d98ef22 feat: calculate revenue columns
b34ca11 docs: add project roadmap
```

---

# 8. GitHub Repository Description

Suggested description:

> Beginner-friendly sales data analysis project using Python, Pandas, and Excel, covering data cleaning, exploratory analysis, KPI calculation, and automated Excel reporting.

---

# 9. Suggested GitHub Topics

```text
python
pandas
excel
data-analysis
data-cleaning
openpyxl
portfolio-project
```

---

# 10. Recommended Commit Milestones

## Commit 1

```text
chore: initialize project structure and documentation
```

## Commit 2

```text
data: add initial sales dataset
```

## Commit 3

```text
feat: add initial pandas data inspection
```

## Commit 4

```text
feat: add data quality checks
```

## Commit 5

```text
feat: clean and normalize sales data
```

## Commit 6

```text
feat: add calculated revenue fields
```

## Commit 7

```text
feat: add sales KPI analysis
```

## Commit 8

```text
feat: add category and city analysis
```

## Commit 9

```text
feat: add monthly sales analysis
```

## Commit 10

```text
feat: export analysis results to Excel
```

## Commit 11

```text
feat: add final Excel dashboard
```

## Commit 12

```text
docs: finalize portfolio documentation
```

---

# 11. Before Every Push

Run:

```powershell
git status
```

Then ask:

- Do I understand every changed file?
- Did I accidentally add `.venv`?
- Did I add private information?
- Did I add temporary files?
- Does the code currently run?
- Does the commit message explain the change?

---

# 12. Important Rule for Portfolio Projects

GitHub activity is not the goal.

A clean, understandable repository is more valuable than many meaningless commits.

Every important commit should represent a step you can explain.
