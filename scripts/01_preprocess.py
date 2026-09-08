# -*- coding: utf-8 -*-
"""
01_preprocess.py
Maven Roasters (Coffee Shop Sales) 전처리
- 원천: data/raw/coffee_shop_sales_raw.csv (149,116 rows)
- 산출: data/processed/coffee_clean.parquet, data/processed/coffee_clean.csv
"""
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "coffee_shop_sales_raw.csv"
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

pd.set_option("display.width", 140)
pd.set_option("display.max_columns", 30)


def log(msg):
    print(f"[preprocess] {msg}")


# ---------------------------------------------------------------- load
df = pd.read_csv(RAW, dtype={"transaction_id": "int64"})
log(f"raw shape: {df.shape}")
log(f"columns: {list(df.columns)}")
print(df.head(3).to_string())
print()
print(df.dtypes)
print()

# ---------------------------------------------------------------- quality checks (before)
report = {}
report["n_rows_raw"] = len(df)
report["n_dup_full_rows"] = int(df.duplicated().sum())
report["n_dup_transaction_id"] = int(df.duplicated("transaction_id").sum())
report["missing_by_col"] = df.isna().sum().to_dict()
report["unit_price_min"] = float(df["unit_price"].min())
report["unit_price_max"] = float(df["unit_price"].max())
report["qty_min"] = int(df["transaction_qty"].min())
report["qty_max"] = int(df["transaction_qty"].max())
report["n_neg_or_zero_price"] = int((df["unit_price"] <= 0).sum())
report["n_neg_or_zero_qty"] = int((df["transaction_qty"] <= 0).sum())

# ---------------------------------------------------------------- type parsing
# transaction_date: M/D/YY  ; transaction_time: H:MM:SS
df["transaction_date"] = pd.to_datetime(df["transaction_date"], format="%m/%d/%y")
df["transaction_time"] = pd.to_datetime(df["transaction_time"], format="%H:%M:%S").dt.time
df["transaction_dt"] = pd.to_datetime(
    df["transaction_date"].dt.strftime("%Y-%m-%d") + " " + df["transaction_time"].astype(str)
)

# categoricals + trimmed text
for c in ["store_location", "product_category", "product_type", "product_detail"]:
    df[c] = df[c].str.strip()

# ---------------------------------------------------------------- derived fields
df["revenue"] = df["transaction_qty"] * df["unit_price"]

df["date"] = df["transaction_dt"].dt.date
df["year"] = df["transaction_dt"].dt.year
df["month"] = df["transaction_dt"].dt.month
df["month_name"] = df["transaction_dt"].dt.strftime("%Y-%m")
df["iso_week"] = df["transaction_dt"].dt.isocalendar().week.astype(int)
df["year_week"] = df["transaction_dt"].dt.strftime("%G-W%V")
df["dow"] = df["transaction_dt"].dt.dayofweek                 # 0=Mon
df["dow_name"] = df["transaction_dt"].dt.strftime("%a")
df["is_weekend"] = df["dow"].isin([5, 6])
df["hour"] = df["transaction_dt"].dt.hour

def daypart(h):
    if 6 <= h < 11:   return "morning(06-11)"
    if 11 <= h < 14:  return "lunch(11-14)"
    if 14 <= h < 17:  return "afternoon(14-17)"
    if 17 <= h < 21:  return "evening(17-21)"
    return "other"
df["daypart"] = df["hour"].map(daypart)

# ---------------------------------------------------------------- cleaning decisions
# (문서화용) 이상치/결측이 사실상 없어 행 삭제는 하지 않음. 방어적으로 필터만 준비.
mask_valid = (df["unit_price"] > 0) & (df["transaction_qty"] > 0)
n_drop = int((~mask_valid).sum())
df = df[mask_valid].copy()
report["n_rows_dropped_invalid"] = n_drop
report["n_rows_clean"] = len(df)
report["date_min"] = str(df["transaction_dt"].min())
report["date_max"] = str(df["transaction_dt"].max())
report["stores"] = sorted(df["store_location"].unique().tolist())
report["n_products"] = int(df["product_detail"].nunique())
report["n_categories"] = int(df["product_category"].nunique())
report["n_product_types"] = int(df["product_type"].nunique())
report["total_revenue"] = float(df["revenue"].sum())
report["total_units"] = int(df["transaction_qty"].sum())
report["n_transactions"] = int(df["transaction_id"].nunique())

col_order = [
    "transaction_id", "transaction_dt", "date", "year", "month", "month_name",
    "iso_week", "year_week", "dow", "dow_name", "is_weekend", "hour", "daypart",
    "store_id", "store_location",
    "product_id", "product_category", "product_type", "product_detail",
    "transaction_qty", "unit_price", "revenue",
]
df = df[col_order].sort_values("transaction_dt").reset_index(drop=True)

# ---------------------------------------------------------------- save
df.to_parquet(OUT / "coffee_clean.parquet", index=False)
df.to_csv(OUT / "coffee_clean.csv", index=False)
log(f"saved clean data: {df.shape} -> {OUT/'coffee_clean.parquet'}")

# ---------------------------------------------------------------- print report
print("\n================ DATA QUALITY / SUMMARY REPORT ================")
for k, v in report.items():
    print(f"{k:26s}: {v}")

# 저장
pd.Series(report, dtype=object).to_json(OUT / "quality_report.json", force_ascii=False, indent=2)
log("done.")
