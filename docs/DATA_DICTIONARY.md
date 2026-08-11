# Data Dictionary

## Dataset Overview

This dataset represents sales order lines from a fictional electronics retailer.

- Period: January 1, 2025 to December 31, 2025
- Currency: USD
- Expected size: approximately 1,200–1,800 rows
- Row granularity: one product line per order
- An order may contain multiple product lines
- The raw dataset intentionally contains controlled data-quality issues

## Columns

| Column | Expected Type | Description | Validation Rule |
|---|---|---|---|
| `Order_Line_ID` | String | Unique identifier for each order line | Must be unique and non-empty |
| `Order_ID` | String | Identifier shared by all lines of one order | Must be non-empty; duplicates are allowed |
| `Order_Date` | Date | Date on which the order was placed | Must be a valid date in 2025 |
| `Customer_ID` | String | Anonymous customer identifier | Must be non-empty |
| `Product` | String | Product name | Must match the product catalog |
| `Category` | String | Product category | Must match the product's category |
| `City` | String | Customer/order city | Must use a standardized city name |
| `Quantity` | Integer | Number of units sold | Must be greater than zero |
| `Unit_Price_USD` | Float | Price of one unit in US dollars | Must be greater than zero |
| `Discount_Rate` | Float | Discount represented as a decimal | Must be between 0 and 1 |
| `Payment_Method` | String | Payment method used for the order | Must be an allowed method |

## Row Granularity

Each row represents one product line inside an order.

A single order can contain multiple products. Therefore, repeating an
`Order_ID` does not automatically mean that the row is duplicated.

`Order_Line_ID` is the unique identifier for individual rows.

## Allowed Values

### Categories

- Computers
- Accessories
- Audio
- Storage
- Furniture

### Cities

- New York
- Chicago
- Austin
- Seattle
- Boston
- San Francisco

### Payment Methods

- Credit Card
- Debit Card
- PayPal
- Bank Transfer

## Calculated Columns

The following columns do not exist in the raw dataset. They will be
created during data transformation.

### Gross Sales

`Gross_Sales_USD = Quantity × Unit_Price_USD`

### Discount Amount

`Discount_Amount_USD = Gross_Sales_USD × Discount_Rate`

### Net Revenue

`Net_Revenue_USD = Gross_Sales_USD - Discount_Amount_USD`

## KPI Definitions

### Total Revenue

Sum of `Net_Revenue_USD` across all valid order lines.

### Total Orders

Number of unique valid `Order_ID` values.

### Units Sold

Sum of `Quantity` across all valid order lines.

### Average Order Value

`Total Revenue ÷ Number of Unique Orders`

This is not the average revenue per row.

### Top-Selling Product

Product with the highest total quantity sold.

### Highest-Revenue Product

Product with the highest total net revenue.

## Planned Data-Quality Issues

The raw dataset will intentionally include a small, documented number of:

- Exact duplicate rows
- Missing city values
- Missing payment methods
- Extra spaces in text
- Inconsistent capitalization
- Invalid date values
- Invalid quantity values
- Zero or negative unit prices
- Discount rates outside the valid range
- Category/product inconsistencies

The cleaning process must detect and document these issues before
correcting or removing them.