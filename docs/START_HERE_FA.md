# راهنمای شروع پروژه Pandas و Excel

این فایل نقطه شروع اصلی پروژه است.

هدف پروژه این نیست که صرفاً چند دستور Pandas حفظ کنیم یا چند فرمول Excel یاد بگیریم. هدف این است که از صفر، یک پروژه کوچک ولی واقعی تحلیل داده بسازیم که در پایان بتوان آن را در GitHub منتشر کرد و در رزومه به آن اشاره کرد.

---

# 1. پروژه دقیقاً چیست؟

سناریوی پروژه:

یک فروشگاه اطلاعات فروش خود را در یک فایل Excel ذخیره کرده است.

ما قرار است با استفاده از:

- Python
- Pandas
- Excel
- Git
- GitHub

این داده‌ها را بررسی، تمیز، تحلیل و گزارش کنیم.

در پایان باید بتوانیم به سؤال‌هایی مثل این جواب بدهیم:

- فروش کل چقدر بوده؟
- چند سفارش ثبت شده؟
- کدام محصول بیشترین فروش را داشته؟
- کدام محصول بیشترین درآمد را ساخته؟
- کدام شهر عملکرد بهتری داشته؟
- کدام دسته‌بندی بیشترین درآمد را داشته؟
- فروش در ماه‌های مختلف چه تغییری داشته؟
- میانگین ارزش هر سفارش چقدر است؟
- مجموع تخفیف داده‌شده چقدر بوده؟

---

# 2. چرا این پروژه برای شروع مناسب است؟

چون همزمان چند مهارت کاربردی را در یک پروژه کوچک تمرین می‌کنیم:

## Pandas

برای:

- خواندن Excel
- تمیز کردن داده
- فیلتر کردن
- مرتب‌سازی
- محاسبه
- گروه‌بندی
- تحلیل

## Excel

برای:

- مشاهده و بررسی داده
- فرمول‌ها
- Sort و Filter
- Pivot Table
- نمودار
- ساخت گزارش

## Git و GitHub

برای:

- مدیریت نسخه‌های پروژه
- مستندسازی
- ساخت سابقه پروژه
- ارائه کار در پورتفولیو

---

# 3. قرار نیست چه کاری انجام دهیم؟

در نسخه اول پروژه سراغ موارد زیر نمی‌رویم:

- Machine Learning
- Deep Learning
- SQL Server
- API
- Backend
- Web Development
- Cloud
- Big Data

تمرکز فقط روی پایه‌های تحلیل داده است.

---

# 4. قانون مهم یادگیری

هر چیزی را دقیقاً زمانی یاد می‌گیریم که در پروژه به آن نیاز داریم.

مثلاً وقتی به این کد می‌رسیم:

```python
import pandas as pd
```

قبل از ادامه باید بدانیم:

- `import` چیست؟
- library چیست؟
- Pandas چیست؟
- چرا `as pd` نوشته‌ایم؟

وقتی به این خط برسیم:

```python
df = pd.read_excel("data/raw/sales_data.xlsx")
```

باید بفهمیم:

- `df` چیست؟
- DataFrame چیست؟
- `read_excel` چه کاری می‌کند؟
- مسیر فایل چطور کار می‌کند؟

قرار نیست کدی در پروژه وجود داشته باشد که نتوانیم توضیحش بدهیم.

---

# 5. خروجی نهایی پروژه

در پایان پروژه باید موارد زیر را داشته باشیم:

## Dataset اولیه

```text
data/raw/sales_data.xlsx
```

## Dataset تمیزشده

```text
data/processed/cleaned_sales_data.xlsx
```

## Notebookهای آموزشی

```text
notebooks/01_data_inspection.ipynb
notebooks/02_data_cleaning.ipynb
notebooks/03_sales_analysis.ipynb
```

## اسکریپت Python

```text
src/sales_analysis.py
```

## گزارش Excel

```text
reports/sales_report.xlsx
```

## تصاویر خروجی

```text
screenshots/
```

## مستندات

```text
README.md
docs/
```

---

# 6. مراحل پروژه

## مرحله 0 — ساخت پروژه

یاد می‌گیریم:

- پوشه پروژه چیست
- Git repository چیست
- `.gitignore` چیست
- Virtual Environment چیست
- `requirements.txt` چیست

---

## مرحله 1 — آشنایی با Excel

یاد می‌گیریم:

- Workbook
- Worksheet
- Row
- Column
- Cell
- Table
- Formula
- Sort
- Filter

---

## مرحله 2 — Pandas از صفر

یاد می‌گیریم:

- DataFrame
- Series
- خواندن Excel
- مشاهده داده‌ها

دستورات اولیه:

```python
df.head()
df.tail()
df.shape
df.columns
df.dtypes
df.info()
df.describe()
```

---

## مرحله 3 — پیدا کردن مشکلات داده

بررسی می‌کنیم:

- مقادیر خالی
- داده تکراری
- نوع داده اشتباه
- تاریخ اشتباه
- قیمت نامعتبر
- مقدار فروش نامعتبر
- متن‌های نامنظم

---

## مرحله 4 — Data Cleaning

کارهایی مثل:

```python
df.drop_duplicates()
```

و:

```python
df["City"].str.strip()
```

و:

```python
pd.to_datetime(...)
```

را یاد می‌گیریم.

---

## مرحله 5 — ساخت ستون‌های جدید

مثلاً:

```text
Gross Sales
Discount Amount
Net Revenue
```

فرمول اصلی:

```text
Gross Sales = Quantity × Unit Price
```

بعد:

```text
Discount Amount = Gross Sales × Discount
```

و:

```text
Net Revenue = Gross Sales - Discount Amount
```

---

# 7. مهم‌ترین بخش Pandas: GroupBy

مثلاً می‌خواهیم بدانیم هر دسته‌بندی چقدر درآمد ساخته است.

```python
df.groupby("Category")["Net_Revenue"].sum()
```

معنی ساده:

1. داده‌ها را بر اساس Category دسته‌بندی کن.
2. Net Revenue هر دسته را با هم جمع کن.

این یکی از مهم‌ترین چیزهایی است که در پروژه یاد خواهیم گرفت.

---

# 8. KPI چیست؟

KPI مخفف:

```text
Key Performance Indicator
```

یعنی شاخص مهم عملکرد.

در پروژه ما KPIهایی مثل این خواهیم داشت:

- Total Revenue
- Total Orders
- Units Sold
- Average Order Value
- Total Discount
- Top Product
- Top Category
- Top City

---

# 9. بخش Excel

بعد از اینکه تحلیل را با Pandas انجام دادیم، بخشی از کارها را در Excel هم انجام می‌دهیم تا ابزار را واقعاً یاد بگیریم.

فرمول‌هایی که تمرین می‌کنیم:

```text
SUM
AVERAGE
COUNTIF
SUMIF
SUMIFS
IF
XLOOKUP
```

بعد Pivot Table می‌سازیم.

---

# 10. گزارش نهایی Excel

فایل نهایی بهتر است Sheetهایی شبیه این داشته باشد:

```text
Summary
Cleaned_Data
Monthly_Sales
Product_Analysis
Category_Analysis
City_Analysis
```

در Summary قرار می‌دهیم:

- KPIها
- نمودار فروش ماهانه
- نمودار دسته‌بندی‌ها
- محصولات برتر
- شهرهای برتر

---

# 11. ساختار پیشنهادی پروژه

```text
sales-data-analysis/
│
├── data/
│   ├── raw/
│   └── processed/
│
├── notebooks/
│
├── src/
│
├── reports/
│
├── screenshots/
│
├── docs/
│
├── README.md
├── requirements.txt
└── .gitignore
```

---

# 12. ترتیب دقیق یادگیری

این ترتیب را حفظ می‌کنیم:

```text
راه‌اندازی پروژه
↓
Excel مقدماتی
↓
Python مورد نیاز
↓
Pandas مقدماتی
↓
خواندن Excel
↓
بررسی داده
↓
Data Cleaning
↓
Filter و Sort
↓
محاسبه ستون‌های جدید
↓
GroupBy
↓
KPI
↓
تحلیل زمانی
↓
Pivot Table
↓
Charts
↓
خروجی Excel
↓
Automation
↓
README
↓
GitHub Portfolio
```

---

# 13. نتیجه‌ای که باید به آن برسیم

وقتی پروژه تمام شد باید بتوانیم بدون حفظ کردن جواب بدهیم:

### Pandas چیست؟

یک کتابخانه Python برای کار با داده‌های جدولی و ساختاریافته است.

### DataFrame چیست؟

ساختار جدولی اصلی Pandas است که داده را به شکل سطر و ستون نگهداری می‌کند.

### چرا Pandas استفاده کردیم؟

چون می‌توانیم خواندن، تمیز کردن، فیلتر کردن، محاسبه و تحلیل داده را با کد انجام دهیم.

### چرا Excel هم استفاده کردیم؟

چون Excel هنوز یکی از ابزارهای بسیار رایج برای بررسی، گزارش و ارائه داده‌های تجاری است.

### پروژه چه کاری انجام می‌دهد؟

داده فروش خام را می‌خواند، تمیز می‌کند، KPIها را محاسبه می‌کند، تحلیل فروش انجام می‌دهد و گزارش Excel تولید می‌کند.

---

# 14. ترتیب مطالعه فایل‌های مستندات

ابتدا:

```text
START_HERE_FA.md
```

سپس:

```text
SETUP_GUIDE.md
```

بعد:

```text
LEARNING_ROADMAP.md
```

بعد:

```text
PROJECT_PLAN.md
```

و هنگام کار با Git:

```text
GIT_GUIDE.md
```

---

# 15. اولین کار عملی بعد از این مستندات

قدم بعدی فقط راه‌اندازی محیط است.

تا زمانی که این موارد درست نشده‌اند وارد Pandas نمی‌شویم:

- Python درست نصب شده باشد.
- VS Code آماده باشد.
- پروژه ساخته شده باشد.
- Virtual Environment فعال باشد.
- Pandas نصب شده باشد.
- OpenPyXL نصب شده باشد.
- Git repository ساخته شده باشد.
- اولین commit ثبت شده باشد.

بعد از آن Dataset اولیه را می‌سازیم و وارد اولین Notebook می‌شویم.
