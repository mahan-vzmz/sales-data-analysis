# Sales Data Analysis with Python, Pandas & Excel

A beginner-friendly, portfolio-ready mini project for learning practical data analysis with **Python**, **Pandas**, and **Microsoft Excel**.

The goal of this project is not only to learn syntax. The goal is to build a complete workflow similar to a small real-world data analysis task: load raw sales data, inspect it, clean it, analyze it, calculate business KPIs, and create an Excel report/dashboard that can be shown on GitHub and included in a resume.

---

## Project Status

**Current phase:** Project setup and fundamentals

Planned final status:

- [ ] Project environment created
- [ ] Python virtual environment configured
- [ ] Pandas installed
- [ ] Excel support libraries installed
- [ ] Raw sales dataset prepared
- [ ] Dataset inspected with Pandas
- [ ] Data quality issues identified
- [ ] Data cleaned
- [ ] Exploratory analysis completed
- [ ] Business KPIs calculated
- [ ] Excel analysis completed
- [ ] Pivot Tables created
- [ ] Charts created
- [ ] Final Excel report generated
- [ ] Python automation script completed
- [ ] README updated with results
- [ ] Screenshots added
- [ ] Repository prepared for portfolio use

---

## Project Scenario

Imagine that a retail business has provided a sales spreadsheet containing its order history.

The dataset may contain information such as:

| Column | Description |
|---|---|
| `Order_ID` | Unique identifier for each order |
| `Date` | Order date |
| `Customer` | Customer name or ID |
| `Product` | Product name |
| `Category` | Product category |
| `City` | Customer/order city |
| `Quantity` | Number of units sold |
| `Unit_Price` | Price per unit |
| `Discount` | Applied discount |
| `Payment_Method` | Payment method |

The business wants answers to questions such as:

- How much total revenue was generated?
- How many orders were placed?
- Which products sold the most?
- Which products generated the most revenue?
- Which categories performed best?
- Which cities generated the most sales?
- What was the average order value?
- How did sales change over time?
- Which payment methods were used most?
- How much revenue was lost due to discounts?

This project will answer these questions using Python, Pandas, and Excel.

---

## Main Learning Goals

By completing this project, I aim to learn:

### Python for Data Analysis

- Working with Python files and Jupyter notebooks
- Importing libraries
- Variables and basic data types
- Functions
- File paths
- Basic debugging

### Pandas

- `Series`
- `DataFrame`
- `read_excel()`
- `read_csv()`
- `head()`
- `tail()`
- `shape`
- `columns`
- `dtypes`
- `info()`
- `describe()`
- Selecting rows and columns
- Filtering
- Sorting
- Missing values
- Duplicate records
- Type conversion
- Date/time processing
- Creating calculated columns
- `groupby()`
- Aggregation
- `value_counts()`
- `pivot_table()`
- Exporting results to Excel

### Excel

- Tables
- Sorting and filtering
- Basic formulas
- `SUM`
- `AVERAGE`
- `MIN`
- `MAX`
- `COUNT`
- `COUNTIF`
- `SUMIF`
- `SUMIFS`
- `IF`
- `XLOOKUP`
- Pivot Tables
- Charts
- Conditional Formatting
- Basic dashboard design

### Git & GitHub

- Creating a repository
- Project folder organization
- `.gitignore`
- Commits
- Commit messages
- Pushing changes
- Maintaining a clean project history
- Writing portfolio-friendly documentation

---

## Planned Project Structure

```text
sales-data-analysis/
│
├── data/
│   ├── raw/
│   │   └── sales_data.xlsx
│   │
│   └── processed/
│       └── cleaned_sales_data.xlsx
│
├── notebooks/
│   ├── 01_data_inspection.ipynb
│   ├── 02_data_cleaning.ipynb
│   └── 03_sales_analysis.ipynb
│
├── src/
│   └── sales_analysis.py
│
├── reports/
│   └── sales_report.xlsx
│
├── screenshots/
│   └── .gitkeep
│
├── docs/
│   ├── PROJECT_PLAN.md
│   ├── LEARNING_ROADMAP.md
│   ├── SETUP_GUIDE.md
│   └── GIT_GUIDE.md
│
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Project Workflow

The project will follow this pipeline:

```text
Raw Excel Data
      ↓
Data Inspection
      ↓
Data Cleaning
      ↓
Data Transformation
      ↓
Exploratory Data Analysis
      ↓
Business KPI Calculation
      ↓
Excel Reporting
      ↓
Dashboard / Charts
      ↓
Automated Final Report
```

---

## Planned KPIs

The final analysis should include at least:

1. Total Revenue
2. Total Orders
3. Total Units Sold
4. Average Order Value
5. Average Selling Price
6. Total Discount
7. Top-Selling Product
8. Highest-Revenue Product
9. Highest-Revenue Category
10. Highest-Revenue City
11. Monthly Revenue
12. Revenue by Category
13. Revenue by City
14. Revenue by Payment Method

---

## Example Calculated Columns

The dataset may include calculated values such as:

```text
Gross_Sales = Quantity × Unit_Price
```

If `Discount` is represented as a decimal percentage:

```text
Discount_Amount = Gross_Sales × Discount
```

Then:

```text
Net_Revenue = Gross_Sales - Discount_Amount
```

These calculations will first be understood manually and later automated with Pandas.

---

## Technologies

- Python 3
- Pandas
- OpenPyXL
- Jupyter Notebook
- Microsoft Excel
- Git
- GitHub
- Visual Studio Code

Optional later additions:

- Matplotlib
- Plotly
- NumPy

---

## Expected Final Deliverables

At the end of the project, this repository should contain:

- Original raw dataset
- Cleaned dataset
- Data cleaning notebook
- Analysis notebook
- Reusable Python analysis script
- Final Excel report
- Dashboard screenshots
- Complete README
- Requirements file
- Clear Git history

---

## Portfolio Goal

This project is intended to become a small but complete portfolio project demonstrating practical experience with:

**Python • Pandas • Excel • Data Cleaning • Data Analysis • Reporting • Git • GitHub**

Suggested resume title:

> **Sales Data Analysis & Excel Reporting — Python, Pandas, Excel**

Suggested resume description after completion:

> Analyzed and cleaned retail sales data using Python and Pandas, calculated key business metrics, performed exploratory data analysis, and generated an automated Excel reporting workbook with summary tables, Pivot Tables, and charts.

The final resume description should only be used after the corresponding features have actually been implemented.

---

## Important Project Rule

The purpose of this repository is **learning by building**.

Every important line of code should be understood before moving forward.

The project should not become a collection of copied code that cannot be explained during an interview.

For every new concept, the learning process should answer:

1. What is it?
2. Why do we need it?
3. What problem does it solve?
4. How does the syntax work?
5. How are we using it in this project?
6. What common mistakes should we avoid?

---

## Next Step

Start with:

`docs/SETUP_GUIDE.md`

Then continue with:

`docs/LEARNING_ROADMAP.md`
