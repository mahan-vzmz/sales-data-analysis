# Project Plan — Sales Data Analysis with Pandas & Excel

## 1. Project Purpose

This mini project is designed as a first practical data analysis project.

It has two equally important goals:

1. Learn the fundamentals of Pandas and Excel through hands-on work.
2. Produce a clean GitHub repository that can later be referenced in a resume or portfolio.

The project should remain small enough for a beginner to understand completely, but complete enough to demonstrate an end-to-end data analysis workflow.

---

# 2. Business Problem

A fictional retail company has sales transaction data stored in an Excel workbook.

The company wants to turn raw transaction data into useful business information.

The analyst must:

- validate the data,
- clean incorrect or incomplete records,
- calculate relevant business fields,
- analyze sales performance,
- identify trends,
- summarize important KPIs,
- and prepare an Excel report.

---

# 3. Scope

## In Scope

The project will include:

- Excel data import
- Data inspection
- Data cleaning
- Missing-value handling
- Duplicate detection
- Data type correction
- Date processing
- Calculated columns
- Filtering
- Sorting
- Grouping
- Aggregations
- KPI calculation
- Trend analysis
- Excel formulas
- Pivot Tables
- Charts
- Exporting Pandas results to Excel
- Final Excel report
- GitHub documentation

## Out of Scope for Version 1

The first version will not require:

- Machine Learning
- Deep Learning
- Databases
- SQL servers
- Cloud deployment
- Web applications
- APIs
- Big Data frameworks
- Advanced statistics

These can be added in future projects.

---

# 4. Dataset Design

The initial dataset should have enough records to make analysis meaningful.

Recommended size for the beginner version:

- 500 to 3,000 rows
- 8 to 12 useful columns

Recommended columns:

| Column | Type | Example |
|---|---|---|
| Order_ID | String / Integer | ORD-1001 |
| Date | Date | 2026-01-15 |
| Customer | String | Customer_021 |
| Product | String | Wireless Mouse |
| Category | String | Accessories |
| City | String | Tehran |
| Quantity | Integer | 3 |
| Unit_Price | Float | 25.50 |
| Discount | Float | 0.10 |
| Payment_Method | String | Card |

---

# 5. Data Quality Problems to Practice

The dataset should intentionally contain a small number of realistic issues.

Examples:

- Empty city values
- Missing payment methods
- Duplicate rows
- Incorrect capitalization
- Extra spaces
- Invalid quantities
- Incorrect data types
- Dates stored as text
- Duplicate order IDs
- Zero or negative prices
- Discount values outside expected range

These problems are useful because real-world datasets are rarely perfectly clean.

---

# 6. Analysis Questions

The project should answer the following questions.

## General Performance

- What is total net revenue?
- How many unique orders exist?
- How many total units were sold?
- What is the average order value?
- What is the average discount?

## Product Performance

- Which product sold the highest quantity?
- Which product generated the highest revenue?
- What are the top 10 products by revenue?
- Which products perform poorly?

## Category Performance

- Which category generated the most revenue?
- Which category sold the most units?
- What percentage of total revenue comes from each category?

## Geographic Analysis

- Which city generated the most revenue?
- Which city had the most orders?
- What is average order value by city?

## Time Analysis

- What is monthly revenue?
- Which month performed best?
- Are sales increasing or decreasing?
- What is average daily revenue?

## Payment Analysis

- Which payment method is most common?
- Which payment method generates the most revenue?

## Discount Analysis

- How much total discount was given?
- Which category received the most discount?
- Is higher discount associated with higher sales volume?

---

# 7. Required Calculations

## Gross Sales

```text
Gross_Sales = Quantity × Unit_Price
```

## Discount Amount

```text
Discount_Amount = Gross_Sales × Discount
```

## Net Revenue

```text
Net_Revenue = Gross_Sales - Discount_Amount
```

## Average Order Value

```text
Average_Order_Value = Total_Revenue / Number_of_Orders
```

---

# 8. Project Milestones

## Milestone 0 — Repository Initialization

Deliverables:

- Project folder
- Git repository
- README
- `.gitignore`
- `requirements.txt`
- Documentation folder

Success condition:

The repository structure is clean and committed.

---

## Milestone 1 — Environment Setup

Tasks:

- Confirm Python installation
- Create virtual environment
- Install Pandas
- Install OpenPyXL
- Install Jupyter
- Configure VS Code
- Test imports

Success condition:

The following code runs without error:

```python
import pandas as pd

print(pd.__version__)
```

---

## Milestone 2 — Excel Fundamentals

Learn:

- Workbook
- Worksheet
- Cell
- Row
- Column
- Range
- Table
- Formula
- Sort
- Filter

Practice:

- Open dataset manually
- Format it as a table
- Sort by revenue
- Filter by city
- Create simple formulas

---

## Milestone 3 — Pandas Fundamentals

Learn:

- Series
- DataFrame
- Index
- Columns
- Rows
- Data types

Required commands:

```python
pd.read_excel()
df.head()
df.tail()
df.shape
df.columns
df.dtypes
df.info()
df.describe()
```

Success condition:

The student can explain what each command does without memorizing a definition.

---

## Milestone 4 — Data Inspection

Tasks:

- Count rows and columns
- Inspect data types
- Find null values
- Find duplicates
- Find invalid values
- Check unique categories
- Check date range

Useful operations:

```python
df.isna().sum()
df.duplicated().sum()
df["Category"].unique()
df["City"].value_counts()
```

---

## Milestone 5 — Data Cleaning

Tasks:

- Remove exact duplicates
- Standardize text
- Trim spaces
- Convert dates
- Convert numeric fields
- Handle missing values
- Validate quantity
- Validate prices
- Validate discounts

Important rule:

Never delete or replace data without understanding why.

Document every cleaning decision.

---

## Milestone 6 — Data Transformation

Create:

- `Gross_Sales`
- `Discount_Amount`
- `Net_Revenue`
- `Year`
- `Month`
- `Month_Name`

Possible example:

```python
df["Gross_Sales"] = df["Quantity"] * df["Unit_Price"]
```

---

## Milestone 7 — Exploratory Analysis

Learn:

- Filtering
- Sorting
- `groupby`
- Aggregation
- `value_counts`
- Pivot tables in Pandas

Examples:

```python
df.groupby("Category")["Net_Revenue"].sum()

df.groupby("City")["Order_ID"].nunique()

df.sort_values("Net_Revenue", ascending=False)
```

---

## Milestone 8 — KPI Calculation

Create a summary object/table containing:

- Total Revenue
- Total Orders
- Units Sold
- Average Order Value
- Total Discounts
- Top Product
- Top Category
- Top City

All KPI definitions should be documented.

---

## Milestone 9 — Excel Analysis

Use Excel to reproduce selected calculations manually.

Required practice:

- SUM
- AVERAGE
- COUNTIF
- SUMIF
- SUMIFS
- IF
- XLOOKUP
- Pivot Table

Purpose:

Understand both manual spreadsheet analysis and automated Python analysis.

---

## Milestone 10 — Excel Report

Create a final workbook with sheets such as:

```text
Summary
Cleaned_Data
Monthly_Sales
Product_Analysis
Category_Analysis
City_Analysis
```

Recommended `Summary` sheet:

- KPI cards
- Monthly revenue chart
- Category chart
- Top products table
- City performance table

---

## Milestone 11 — Automation

Create:

```text
src/sales_analysis.py
```

The script should:

1. Read raw data.
2. Validate it.
3. Clean it.
4. Calculate new columns.
5. Generate analysis tables.
6. Export final results.
7. Save an Excel report.

The final goal is for one command to rebuild the report.

Example future command:

```bash
python src/sales_analysis.py
```

---

## Milestone 12 — Portfolio Polish

Final tasks:

- Clean README
- Add screenshots
- Explain project architecture
- Add project results
- Add learning outcomes
- Add installation instructions
- Add usage instructions
- Check spelling
- Remove temporary files
- Check `.gitignore`
- Verify project works from a fresh environment

---

# 9. Definition of Done

Version 1 is complete when:

- Raw data exists.
- Cleaning process is documented.
- Pandas analysis runs successfully.
- KPIs are correct.
- Excel workbook is generated.
- Dashboard/report is understandable.
- Repository is clean.
- README explains how to run the project.
- A new user can clone the repository and reproduce the analysis.

---

# 10. Portfolio Quality Checklist

Before publishing:

- [ ] No passwords or private information
- [ ] No absolute local file paths
- [ ] No unnecessary large files
- [ ] No temporary Excel files
- [ ] No `.venv` folder committed
- [ ] No `__pycache__`
- [ ] Clear variable names
- [ ] Clear comments
- [ ] Small understandable functions
- [ ] Correct spelling
- [ ] Reproducible instructions
- [ ] Screenshots of final output
- [ ] Professional repository description
- [ ] Relevant GitHub topics/tags

Suggested GitHub topics:

```text
python
pandas
excel
data-analysis
data-cleaning
openpyxl
portfolio-project
beginner-project
```
