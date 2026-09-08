# -*- coding: utf-8 -*-
"""
02_eda.py  — Maven Roasters EDA
입력: data/processed/coffee_clean.parquet
산출: output/figures/*.png, output/eda_summary.md, data/processed/store_week_panel.csv
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
FIG = ROOT / "output" / "figures"
FIG.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "figure.dpi": 110, "savefig.dpi": 110, "figure.autolayout": True,
    "axes.grid": True, "grid.alpha": .25, "axes.spines.top": False, "axes.spines.right": False,
    "font.size": 10,
})
BLUE, ORANGE, GREEN = "#2f6f9f", "#e08a2e", "#4f9d69"
STORE_COLORS = {"Astoria": BLUE, "Hell's Kitchen": ORANGE, "Lower Manhattan": GREEN}

df = pd.read_parquet(PROC / "coffee_clean.parquet")
df["date"] = pd.to_datetime(df["date"])
md = []   # markdown lines
def h(x): md.append(f"\n## {x}\n")
def p(x): md.append(x + "\n")
def tbl(frame): md.append(frame.to_markdown() + "\n")

md.append("# Maven Roasters — EDA 요약\n")
p(f"- 기간: **{df['date'].min().date()} ~ {df['date'].max().date()}**")
p(f"- 행 수: **{len(df):,}** — transaction_id가 행마다 유일(= 1행 1품목, 장바구니 결합 없음)")
p(f"- 매장: {', '.join(sorted(df['store_location'].unique()))}")
p(f"- 총매출: **${df['revenue'].sum():,.0f}** / 총판매수량: **{df['transaction_qty'].sum():,}**")
p(f"- 메뉴(product_detail): **{df['product_detail'].nunique()}종** / 카테고리 **{df['product_category'].nunique()}종** / 타입 **{df['product_type'].nunique()}종**")
p(f"- 객단가(거래당 매출): **${df.groupby('transaction_id')['revenue'].sum().mean():.2f}** / 거래당 품목수: **{df.groupby('transaction_id')['product_id'].nunique().mean():.2f}**")

# ---------------------------------------------------------------- 0. 날짜 연속성
h("0. 데이터 커버리지 점검")
daily = df.groupby("date").agg(revenue=("revenue", "sum"), tx=("transaction_id", "nunique"),
                               units=("transaction_qty", "sum")).reset_index()
full_idx = pd.date_range(daily["date"].min(), daily["date"].max(), freq="D")
missing_days = sorted(set(full_idx) - set(daily["date"]))
p(f"- 기대 일수 {len(full_idx)} / 실제 {len(daily)} → 누락일: {len(missing_days)}건 {('없음' if not missing_days else [str(d.date()) for d in missing_days])}")
p(f"- 일매출 범위: ${daily['revenue'].min():,.0f} ~ ${daily['revenue'].max():,.0f} (평균 ${daily['revenue'].mean():,.0f})")

by_store_month = df.assign(m=df["date"].values.astype("datetime64[M]")).pivot_table(
    index="m", columns="store_location", values="revenue", aggfunc="sum")
tbl(by_store_month.round(0).astype(int))

# ---------------------------------------------------------------- 1. 시계열
h("1. 매출 추이")
fig, ax = plt.subplots(2, 1, figsize=(11, 7))
ax[0].plot(daily["date"], daily["revenue"], color=BLUE, lw=.9)
ax[0].plot(daily["date"], daily["revenue"].rolling(7, center=True).mean(), color="black", lw=1.8, label="7d MA")
ax[0].set_title("Daily revenue (all stores)"); ax[0].legend(); ax[0].set_ylabel("$")
for s, g in df.groupby("store_location"):
    gd = g.groupby("date")["revenue"].sum()
    ax[1].plot(gd.index, gd.rolling(7, center=True).mean(), label=s, color=STORE_COLORS[s], lw=1.4)
ax[1].set_title("Daily revenue by store (7d MA)"); ax[1].legend(); ax[1].set_ylabel("$")
fig.savefig(FIG / "01_daily_revenue.png"); plt.close(fig)

mrev = df.groupby([df["date"].values.astype("datetime64[M]"), "store_location"])["revenue"].sum().unstack()
fig, ax = plt.subplots(figsize=(9, 4.5))
mrev.plot(kind="bar", ax=ax, color=[STORE_COLORS[c] for c in mrev.columns], width=.8)
ax.set_title("Monthly revenue by store"); ax.set_xlabel(""); ax.set_ylabel("$")
ax.set_xticklabels([pd.Timestamp(t).strftime("%Y-%m") for t in mrev.index], rotation=0)
fig.savefig(FIG / "02_monthly_revenue.png"); plt.close(fig)

mom = df.groupby(df["date"].values.astype("datetime64[M]"))["revenue"].sum()
p("- 월별 총매출($) 및 전월대비:")
tbl(pd.DataFrame({"revenue": mom.round(0).astype(int), "MoM_%": (mom.pct_change() * 100).round(1)}))

# ---------------------------------------------------------------- 2. 계절/시간 패턴
h("2. 요일 · 시간대 패턴")
dow_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
dow = df.groupby("dow_name")["revenue"].sum().reindex(dow_order)
hour = df.groupby("hour")["revenue"].sum()
fig, ax = plt.subplots(1, 2, figsize=(12, 4))
ax[0].bar(dow.index, dow.values, color=BLUE); ax[0].set_title("Revenue by day of week")
ax[1].bar(hour.index, hour.values, color=ORANGE); ax[1].set_title("Revenue by hour"); ax[1].set_xlabel("hour")
fig.savefig(FIG / "03_dow_hour.png"); plt.close(fig)

piv = df.pivot_table(index="hour", columns="dow_name", values="revenue", aggfunc="sum").reindex(columns=dow_order)
fig, ax = plt.subplots(figsize=(8, 6))
im = ax.imshow(piv.values, aspect="auto", cmap="YlOrRd")
ax.set_xticks(range(7)); ax.set_xticklabels(dow_order); ax.set_yticks(range(len(piv.index)))
ax.set_yticklabels(piv.index); ax.set_title("Revenue heatmap (hour x dow)"); fig.colorbar(im, ax=ax, label="$")
fig.savefig(FIG / "04_heatmap_hour_dow.png"); plt.close(fig)

p(f"- 주중 평균 일매출 ${daily.merge(df[['date','is_weekend']].drop_duplicates())['revenue'][~daily.merge(df[['date','is_weekend']].drop_duplicates())['is_weekend']].mean():,.0f} "
  f"vs 주말 ${daily.merge(df[['date','is_weekend']].drop_duplicates())['revenue'][daily.merge(df[['date','is_weekend']].drop_duplicates())['is_weekend']].mean():,.0f}")
dp = df.groupby("daypart")["revenue"].sum().sort_values(ascending=False)
tbl(dp.to_frame("revenue").assign(**{"share_%": (dp / dp.sum() * 100).round(1)}))

# ---------------------------------------------------------------- 3. 상품/메뉴 구조
h("3. 상품 · 메뉴 구조")
cat = df.groupby("product_category").agg(revenue=("revenue", "sum"), units=("transaction_qty", "sum"),
                                         n_items=("product_detail", "nunique")).sort_values("revenue", ascending=False)
cat["rev_share_%"] = (cat["revenue"] / cat["revenue"].sum() * 100).round(1)
tbl(cat.round(0))

fig, ax = plt.subplots(figsize=(9, 4.5))
ax.barh(cat.index[::-1], cat["revenue"][::-1], color=BLUE)
ax.set_title("Revenue by product category"); ax.set_xlabel("$")
fig.savefig(FIG / "05_category_revenue.png"); plt.close(fig)

prod = df.groupby("product_detail")["revenue"].sum().sort_values(ascending=False)
top10 = prod.head(10); bot10 = prod.tail(10)
p("**매출 상위 10 메뉴**"); tbl(top10.to_frame("revenue").round(0))
p("**매출 하위 10 메뉴**"); tbl(bot10.to_frame("revenue").round(0))

# Pareto (long tail)
cum = prod.cumsum() / prod.sum()
n_for_80 = int((cum <= 0.8).sum()) + 1
fig, ax = plt.subplots(figsize=(9, 4.5))
ax.plot(range(1, len(cum) + 1), cum.values * 100, color=BLUE)
ax.axhline(80, color="red", ls="--", lw=1); ax.axvline(n_for_80, color="red", ls="--", lw=1)
ax.set_title(f"Cumulative revenue by menu rank  (80% reached at {n_for_80} of {len(prod)} items)")
ax.set_xlabel("menu item rank"); ax.set_ylabel("cumulative revenue %")
fig.savefig(FIG / "06_menu_pareto.png"); plt.close(fig)
p(f"- **파레토**: 전체 {len(prod)}개 메뉴 중 상위 **{n_for_80}개({n_for_80/len(prod)*100:.0f}%)**가 매출의 80%를 만든다.")
p(f"- 매출 하위 50% 메뉴({(prod.rank(pct=True) <= .5).sum()}개)의 합산 매출 비중: {prod[prod.rank(pct=True) <= .5].sum()/prod.sum()*100:.1f}%")

# 가격대 분포
fig, ax = plt.subplots(figsize=(8, 4))
ax.hist(df["unit_price"], bins=40, color=ORANGE)
ax.set_title("unit_price distribution"); ax.set_xlabel("$")
fig.savefig(FIG / "07_price_hist.png"); plt.close(fig)

# ---------------------------------------------------------------- 4. 가설용 패널: store × week
h("4. 가설 준비 — store × week 패널 (메뉴 폭 vs 매출)")

def entropy(counts):
    p_ = counts / counts.sum()
    p_ = p_[p_ > 0]
    return float(-(p_ * np.log(p_)).sum())

rows = []
for (store, yw), g in df.groupby(["store_location", "year_week"]):
    cat_units = g.groupby("product_category")["transaction_qty"].sum()
    rows.append({
        "store": store, "year_week": yw,
        "revenue": g["revenue"].sum(),
        "units": g["transaction_qty"].sum(),
        "n_tx": g["transaction_id"].nunique(),
        "menu_breadth": g["product_detail"].nunique(),       # 그 주 실제 팔린 고유 메뉴 수
        "n_categories": g["product_category"].nunique(),
        "n_types": g["product_type"].nunique(),
        "cat_entropy": entropy(cat_units),
        "avg_unit_price": g["unit_price"].mean(),
        "avg_ticket": g.groupby("transaction_id")["revenue"].sum().mean(),
        "days_active": g["date"].nunique(),
    })
panel = pd.DataFrame(rows).sort_values(["store", "year_week"]).reset_index(drop=True)
# 부분 주(첫/마지막 ISO주 등 days_active<7) 표시
panel["full_week"] = panel["days_active"] >= 7
panel.to_csv(PROC / "store_week_panel.csv", index=False)
p(f"- 패널 shape: {panel.shape} (store 3 × 주). full_week=False {int((~panel['full_week']).sum())}건은 부분주.")
tbl(panel.groupby("store")[["revenue", "menu_breadth", "n_categories", "cat_entropy", "avg_unit_price", "avg_ticket"]].mean().round(2))

fw = panel[panel["full_week"]]
corr = fw[["revenue", "menu_breadth", "n_categories", "n_types", "cat_entropy",
           "avg_unit_price", "avg_ticket", "units", "n_tx"]].corr()["revenue"].round(3)
p("**full-week 패널에서 주간매출과의 상관계수(Pearson):**")
tbl(corr.to_frame("corr_with_revenue"))

# 산점도: menu_breadth vs revenue (store별)
fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
for s, g in fw.groupby("store"):
    ax[0].scatter(g["menu_breadth"], g["revenue"], s=22, alpha=.7, color=STORE_COLORS[s], label=s)
ax[0].set_xlabel("menu_breadth (distinct items sold / week)"); ax[0].set_ylabel("weekly revenue $")
ax[0].set_title("Menu breadth vs weekly revenue"); ax[0].legend()
for s, g in fw.groupby("store"):
    ax[1].scatter(g["n_tx"], g["revenue"], s=22, alpha=.7, color=STORE_COLORS[s], label=s)
ax[1].set_xlabel("weekly transactions"); ax[1].set_ylabel("weekly revenue $")
ax[1].set_title("Transactions vs weekly revenue")
fig.savefig(FIG / "08_menu_breadth_vs_revenue.png"); plt.close(fig)

# 간이 OLS (numpy): revenue ~ menu_breadth + n_tx + avg_unit_price + store dummies
d = fw.copy()
d = pd.get_dummies(d, columns=["store"], drop_first=True)
Xcols = ["menu_breadth", "n_tx", "avg_unit_price"] + [c for c in d.columns if c.startswith("store_")]
X = d[Xcols].astype(float).values
X = np.column_stack([np.ones(len(X)), X])
y = d["revenue"].astype(float).values
beta, *_ = np.linalg.lstsq(X, y, rcond=None)
yhat = X @ beta
ss_res = ((y - yhat) ** 2).sum(); ss_tot = ((y - y.mean()) ** 2).sum()
r2 = 1 - ss_res / ss_tot
p("**간이 OLS: weekly revenue ~ menu_breadth + n_tx + avg_unit_price + store dummies**")
ols_tbl = pd.DataFrame({"coef": beta}, index=["intercept"] + Xcols).round(2)
md.append(ols_tbl.to_markdown() + "\n")
p(f"R² = {r2:.3f}  (n={len(y)})")
p("\n> 주의: menu_breadth 와 n_tx(거래수)는 강한 양의 상관 — 거래가 많은 주에 자연히 더 많은 메뉴가 팔린다. "
  "메뉴 '운영 수'가 아니라 '판매된 메뉴 수'라 역인과 가능성이 큼. 이 데이터로는 가설의 '보조 증거'까지가 한계이며, "
  "매장 간 실제 메뉴 구성이 거의 동일해 진짜 검정에는 다점포/패널 외부 데이터가 필요.")

# ---------------------------------------------------------------- write md
(ROOT / "output" / "eda_summary.md").write_text("\n".join(md), encoding="utf-8")
print("EDA done. figures:", sorted(pf.name for pf in FIG.glob("*.png")))
print((ROOT / "output" / "eda_summary.md"))
