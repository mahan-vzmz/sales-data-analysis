# Learning Roadmap — Pandas & Excel from Zero

This document defines the learning path for the project.

The rule is simple:

> Learn a concept when the project needs it, then immediately use it.

Avoid trying to memorize the entire Pandas or Excel ecosystem before building anything.

---

# Stage 0 — Understand the Big Picture

Before writing code, understand these terms.

## Data

Data is information stored in a form that can be processed.

Example:

```text
Product: Mouse
Quantity: 3
Price: 25
City: Tehran
```

---

## Dataset

A dataset is a collection of related data.

A spreadsheet with 1,000 sales records is a dataset.

---

## Row

A row usually represents one observation or record.

Example:

```text
ORD-1001 | Mouse | Tehran | 3 | 25
```

---

## Column

A column represents one attribute.

Examples:

```text
Product
City
Quantity
Price
```

---

## Data Analysis

Data analysis means inspecting and transforming data to answer questions.

Example questions:

- Which product sells the most?
- Which month generated the most revenue?
- Which city has the highest average order value?

---

# Stage 1 — Excel Basics

## Learn

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

## Practical Goal

Open the project dataset and be able to:

- understand its structure,
- sort records,
- filter records,
- create basic formulas,
- identify obvious data problems.

---

# Stage 2 — Python Basics Needed for Pandas

You do not need to master Python before learning Pandas.

Learn only what this project needs.

## Topics

### Variables

```python
name = "Laptop"
price = 850
quantity = 2
```

### Strings

```python
city = "Tehran"
```

### Numbers

```python
quantity = 3
price = 25.5
```

### Lists

```python
cities = ["Tehran", "Shiraz", "Tabriz"]
```

### Dictionaries

```python
sale = {
    "product": "Mouse",
    "quantity": 3,
    "price": 25
}
```

### Functions

```python
def calculate_revenue(quantity, price):
    return quantity * price
```

### Imports

```python
import pandas as pd
```

---

# Stage 3 — What Is Pandas?

Pandas is a Python library designed for working with structured/tabular data.

It is especially useful for:

- CSV files
- Excel files
- tables
- business data
- financial data
- logs
- survey data

Main Pandas objects:

1. `Series`
2. `DataFrame`

---

## Series

A Series is similar to one labeled column.

Example conceptually:

```text
0    Tehran
1    Shiraz
2    Tehran
3    Tabriz
```

---

## DataFrame

A DataFrame is a table with rows and columns.

Conceptually:

| Product | Quantity | Price |
|---|---:|---:|
| Mouse | 2 | 25 |
| Laptop | 1 | 900 |
| Keyboard | 3 | 70 |

Most of the project will work with DataFrames.

---

# Stage 4 — Reading Excel with Pandas

Install Excel support through `openpyxl`.

Typical code:

```python
import pandas as pd

df = pd.read_excel("data/raw/sales_data.xlsx")
```

Important questions:

- What is `pd`?
- What does `read_excel()` do?
- What is returned?
- What is stored inside `df`?
- Why should relative paths be used?

---

# Stage 5 — Inspecting Data

Learn these first:

```python
df.head()
df.tail()
df.shape
df.columns
df.dtypes
df.info()
df.describe()
```

## What each means

### `head()`

Shows the first rows.

### `tail()`

Shows the last rows.

### `shape`

Returns:

```text
(rows, columns)
```

### `columns`

Shows column names.

### `dtypes`

Shows data types.

### `info()`

Gives a structural summary.

### `describe()`

Provides descriptive statistics for applicable columns.

---

# Stage 6 — Selecting Data

## Select one column

```python
df["Product"]
```

## Select multiple columns

```python
df[["Product", "Quantity", "Unit_Price"]]
```

## Select rows by condition

```python
df[df["City"] == "Tehran"]
```

## Multiple conditions

```python
df[
    (df["City"] == "Tehran")
    & (df["Quantity"] > 2)
]
```

---

# Stage 7 — Sorting

Example:

```python
df.sort_values("Unit_Price")
```

Descending:

```python
df.sort_values("Unit_Price", ascending=False)
```

---

# Stage 8 — Missing Values

Detect:

```python
df.isna()
```

Count:

```python
df.isna().sum()
```

Possible actions:

```python
df.dropna()
```

or:

```python
df["City"] = df["City"].fillna("Unknown")
```

Important:

Do not automatically use `dropna()` on everything.

The correct action depends on what the missing value means.

---

# Stage 9 — Duplicate Data

Find duplicates:

```python
df.duplicated()
```

Count:

```python
df.duplicated().sum()
```

Remove exact duplicates:

```python
df = df.drop_duplicates()
```

But first determine whether repeated-looking records are actually invalid duplicates.

---

# Stage 10 — Cleaning Text

Common problems:

```text
Tehran
tehran
 Tehran
TEHRAN
```

Useful string operations:

```python
df["City"] = df["City"].str.strip()
df["City"] = df["City"].str.title()
```

---

# Stage 11 — Converting Data Types

Dates:

```python
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
```

Numbers:

```python
df["Quantity"] = pd.to_numeric(
    df["Quantity"],
    errors="coerce"
)
```

Learn what `errors="coerce"` does before using it widely.

---

# Stage 12 — Creating New Columns

Example:

```python
df["Gross_Sales"] = (
    df["Quantity"] * df["Unit_Price"]
)
```

Discount:

```python
df["Discount_Amount"] = (
    df["Gross_Sales"] * df["Discount"]
)
```

Net revenue:

```python
df["Net_Revenue"] = (
    df["Gross_Sales"] - df["Discount_Amount"]
)
```

---

# Stage 13 — Aggregation

Basic functions:

```python
df["Net_Revenue"].sum()
df["Net_Revenue"].mean()
df["Net_Revenue"].min()
df["Net_Revenue"].max()
df["Order_ID"].count()
df["Order_ID"].nunique()
```

Know the difference between:

```text
count
nunique
```

---

# Stage 14 — GroupBy

This is one of the most important Pandas concepts.

Example:

```python
df.groupby("Category")["Net_Revenue"].sum()
```

Interpretation:

> Group all records by category, then calculate total revenue for each category.

Multiple metrics:

```python
df.groupby("Category").agg(
    revenue=("Net_Revenue", "sum"),
    units=("Quantity", "sum"),
    orders=("Order_ID", "nunique"),
)
```

---

# Stage 15 — Value Counts

Example:

```python
df["Payment_Method"].value_counts()
```

Useful for categorical frequency analysis.

---

# Stage 16 — Date Analysis

Extract year:

```python
df["Year"] = df["Date"].dt.year
```

Extract month:

```python
df["Month"] = df["Date"].dt.month
```

Month name:

```python
df["Month_Name"] = df["Date"].dt.month_name()
```

Monthly analysis:

```python
monthly_sales = (
    df.groupby(df["Date"].dt.to_period("M"))
      ["Net_Revenue"]
      .sum()
)
```

---

# Stage 17 — Excel Formulas

Practice these manually:

## SUM

```excel
=SUM(A2:A100)
```

## AVERAGE

```excel
=AVERAGE(A2:A100)
```

## COUNTIF

```excel
=COUNTIF(B:B,"Tehran")
```

## SUMIF

```excel
=SUMIF(B:B,"Tehran",C:C)
```

## SUMIFS

Useful when multiple conditions are needed.

## IF

```excel
=IF(A2>1000,"High","Normal")
```

## XLOOKUP

Use for looking up values from another table.

---

# Stage 18 — Pivot Tables

Understand:

- Rows
- Columns
- Values
- Filters

Example analysis:

```text
Rows: Category
Values: Sum of Net Revenue
```

Then:

```text
Rows: Month
Columns: Category
Values: Sum of Net Revenue
```

---

# Stage 19 — Charts

Recommended charts:

- Line chart for monthly revenue
- Bar chart for categories
- Horizontal bar chart for top products
- Column chart for cities

Avoid adding charts only for decoration.

Every chart should answer a business question.

---

# Stage 20 — Exporting Pandas to Excel

Simple export:

```python
df.to_excel(
    "data/processed/cleaned_sales_data.xlsx",
    index=False
)
```

Multiple sheets:

```python
with pd.ExcelWriter(
    "reports/sales_report.xlsx",
    engine="openpyxl"
) as writer:
    df.to_excel(
        writer,
        sheet_name="Cleaned_Data",
        index=False
    )
```

Later the project can export summary tables to additional sheets.

---

# Stage 21 — Move from Notebook to Script

Notebooks are useful for learning and exploration.

A final reusable script should separate logic into functions.

Possible structure:

```python
def load_data(path):
    ...

def clean_data(df):
    ...

def calculate_metrics(df):
    ...

def build_reports(df):
    ...

def export_report(...):
    ...
```

---

# Stage 22 — Explain the Project Like an Interview

After completing the project, be able to answer:

- What problem did the project solve?
- Why did you use Pandas?
- Why did you use Excel too?
- What is a DataFrame?
- How did you detect missing data?
- How did you handle duplicates?
- What is `groupby()`?
- What KPIs did you calculate?
- What was the most difficult data cleaning problem?
- Why did you use Pivot Tables?
- How is the Excel report generated?
- How could the project be improved?

If you cannot explain a part, revisit it.

---

# Recommended Learning Order

Do not skip around randomly.

Use this order:

```text
Excel Basics
    ↓
Required Python Basics
    ↓
Pandas DataFrame
    ↓
Read Excel
    ↓
Inspect Data
    ↓
Filter / Sort
    ↓
Missing Values
    ↓
Duplicates
    ↓
Cleaning
    ↓
Calculated Columns
    ↓
Aggregation
    ↓
GroupBy
    ↓
Date Analysis
    ↓
Excel Formulas
    ↓
Pivot Tables
    ↓
Excel Charts
    ↓
Export from Python
    ↓
Automated Report
```
