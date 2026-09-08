# -*- coding: utf-8 -*-
"""
05_report_figures.py — 리포트용 통합 스타일 그림 생성
출력: output/report/*.png  (밝은 카드 위에 얹는 전제, 검증된 3색 팔레트)
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from pathlib import Path
from statsmodels.tsa.seasonal import STL
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
OUT = ROOT / "output" / "report"
OUT.mkdir(parents=True, exist_ok=True)

# --- 검증 통과 팔레트 (validate_palette.js, light, ALL PASS)
BLUE, RUST, GREEN = "#2F6F9F", "#B0641A", "#4F9D69"
INK, MUTED, GRID, SURF = "#33302C", "#6B6560", "#E8E4DE", "#FCFCFB"
RED = "#B23B2E"
STORE_C = {"Astoria": BLUE, "Hell's Kitchen": RUST, "Lower Manhattan": GREEN}

plt.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 150, "savefig.bbox": "tight",
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
    "font.family": "Malgun Gothic", "font.sans-serif": ["Malgun Gothic", "Noto Sans KR", "DejaVu Sans"],
    "font.size": 11, "axes.unicode_minus": False,
    "text.color": INK, "axes.labelcolor": INK, "axes.edgecolor": GRID,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": .8, "grid.alpha": .9,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlecolor": INK,
    "axes.titlelocation": "left", "axes.titlepad": 10,
})

df = pd.read_parquet(PROC / "coffee_clean.parquet")
df["date"] = pd.to_datetime(df["date"])
TOTAL = df["revenue"].sum()
daily = df.groupby("date")["revenue"].sum().asfreq("D")


def save(fig, name):
    fig.savefig(OUT / name); plt.close(fig)
    print("  ", name)


# ============================================================ 1. 성장 추이
fig, ax = plt.subplots(figsize=(9, 3.6))
ax.plot(daily.index, daily.values, color=BLUE, lw=.8, alpha=.45)
ax.plot(daily.index, daily.rolling(7, center=True).mean(), color=BLUE, lw=2.2)
ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"${v/1000:.0f}k"))
ax.set_title("일 매출 — 원계열(옅음)과 7일 이동평균")
ax.annotate("1월 평균 $2,635/일", (daily.index[15], 2635), color=MUTED, fontsize=9.5,
            xytext=(daily.index[15], 4600), arrowprops=dict(arrowstyle="-", color=MUTED, lw=.8))
ax.annotate("6월 평균 $5,550/일  (+111%)", (daily.index[-15], 5550), color=INK, fontsize=9.5,
            ha="right", xytext=(daily.index[-8], 3400),
            arrowprops=dict(arrowstyle="-", color=MUTED, lw=.8))
save(fig, "r_growth.png")

# ============================================================ 2. STL 분해
stl = STL(daily, period=7, robust=True).fit()
comp = [("관측값 observed", daily.values, BLUE),
        ("추세 trend  ·  분산의 94.6%", stl.trend.values, INK),
        ("주간 계절 seasonal  ·  분산의 1.9%", stl.seasonal.values, GREEN),
        ("잔차 resid  ·  분산의 5.7%", stl.resid.values, RUST)]
fig, axes = plt.subplots(4, 1, figsize=(9, 8.2), sharex=True)
fig.subplots_adjust(hspace=0.62)
for ax, (t, y, c) in zip(axes, comp):
    ax.plot(daily.index, y, color=c, lw=1.5 if c == INK else .9)
    ax.set_title(t, fontsize=10.5)
    if "resid" in t or "seasonal" in t:
        ax.axhline(0, color=MUTED, lw=.7)
axes[0].yaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"${v/1000:.0f}k"))
axes[1].yaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"${v/1000:.0f}k"))
fig.align_ylabels()
save(fig, "r_stl.png")

# ============================================================ 3. 드라이버 블록별 R²
pan = pd.read_csv(PROC / "store_day_panel.csv")
pan["dow"] = pd.Categorical(pan["dow"], ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"], ordered=True)
pan["log_revenue"] = np.log(pan["revenue"])
blocks = [("매장 고정효과", "C(store)"),
          ("+ 요일", "C(store)+C(dow)"),
          ("+ 시간추세 t, t²", "C(store)+C(dow)+t+t2"),
          ("+ 평균 단가", "C(store)+C(dow)+t+t2+avg_unit_price"),
          ("+ 오전 매출 비중", "C(store)+C(dow)+t+t2+avg_unit_price+morning_share"),
          ("+ 메뉴 폭", "C(store)+C(dow)+t+t2+avg_unit_price+morning_share+menu_breadth")]
r2s = [smf.ols("log_revenue ~ " + f, data=pan).fit().rsquared for _, f in blocks]
labels = [b[0] for b in blocks]
fig, ax = plt.subplots(figsize=(9, 3.8))
prev = 0
for i, (lab, r2) in enumerate(zip(labels, r2s)):
    inc = r2 - prev
    ax.barh(i, inc, left=prev, color=BLUE if lab == "+ 시간추세 t, t²" else MUTED,
            height=.62, edgecolor=SURF, linewidth=1.5)
    ax.text(r2 + .012, i, f"{r2:.2f}", va="center", fontsize=9.5, color=INK)
    prev = r2
ax.set_yticks(range(len(labels))); ax.set_yticklabels(labels)
ax.invert_yaxis(); ax.set_xlim(0, 1.08)
ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"{v:.0%}"))
ax.grid(axis="y", visible=False)
ax.set_title("누적 설명력(R²) — log 일매출 회귀에 변수군 순차 추가\n시간추세 하나가 +73%p, 나머지 변수는 합쳐 +9%p",
             fontsize=11.5)
save(fig, "r_drivers.png")

# ============================================================ 4. 파레토 / 롱테일
prod = df.groupby("product_detail")["revenue"].sum().sort_values(ascending=False)
cum = prod.cumsum() / prod.sum() * 100
n80 = int((cum <= 80).sum()) + 1
fig, ax = plt.subplots(figsize=(9, 3.8))
x = np.arange(1, len(cum) + 1)
ax.fill_between(x, cum.values, color=BLUE, alpha=.12)
ax.plot(x, cum.values, color=BLUE, lw=2)
ax.axhline(80, color=MUTED, lw=.9, ls="--")
ax.axvline(n80, color=RED, lw=1.2)
ax.plot([n80], [80], "o", color=RED, ms=7)
ax.annotate(f"상위 {n80}개 메뉴 = 매출의 80%\n(전체 {len(prod)}개 중 {n80/len(prod):.0%})",
            (n80, 80), xytext=(n80 + 4, 52), color=INK, fontsize=10,
            arrowprops=dict(arrowstyle="-", color=MUTED, lw=.8))
ax.set_xlim(0, len(prod)); ax.set_ylim(0, 101)
ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"{v:.0f}%"))
ax.set_xlabel("메뉴 순위 (매출 상위 → 하위)")
ax.set_title("메뉴별 누적 매출 — 롱테일 구조")
save(fig, "r_pareto.png")

# ============================================================ 5. 카테고리 매출
cat = df.groupby("product_category")["revenue"].sum().sort_values()
fig, ax = plt.subplots(figsize=(9, 3.8))
ax.barh(cat.index, cat.values, color=BLUE, height=.66)
for i, v in enumerate(cat.values):
    ax.text(v + TOTAL * .004, i, f"${v/1000:.0f}k · {v/TOTAL:.0%}", va="center",
            fontsize=9.3, color=INK)
ax.set_xlim(0, cat.max() * 1.18)
ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"${v/1000:.0f}k"))
ax.set_title("카테고리별 매출 — Coffee+Tea가 67%")
ax.grid(axis="y", visible=False)
save(fig, "r_category.png")

# ============================================================ 6. 시간대 × 요일 히트맵
dow_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
piv = df.pivot_table(index="hour", columns="dow_name", values="revenue", aggfunc="sum").reindex(columns=dow_order)
fig, ax = plt.subplots(figsize=(7.6, 5.2))
im = ax.imshow(piv.values, aspect="auto", cmap="BuPu", origin="lower")
ax.set_xticks(range(7)); ax.set_xticklabels(dow_order)
ax.set_yticks(range(len(piv.index))); ax.set_yticklabels([f"{h:02d}" for h in piv.index])
ax.set_ylabel("시각 (hour)")
ax.set_title("매출 히트맵 — 시각 × 요일  (오전이 매출의 49%)")
ax.grid(False)
cb = fig.colorbar(im, ax=ax, fraction=.046, pad=.03)
cb.outline.set_edgecolor(GRID)
cb.ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"${v/1000:.0f}k"))
save(fig, "r_heatmap.png")

# ============================================================ 7. 합리화 프론티어
grid = pd.read_csv(PROC / "rationalization_grid.csv")
fig, ax = plt.subplots(figsize=(9, 4.2))
ramp = {0: RED, 30: "#C67A3C", 50: GREEN}   # σ 증가 = 낙관, 순차 램프
xr = grid["sku_reduction_%"]
xmax = 39
for sig, c in ramp.items():
    ax.plot(xr, grid[f"retain_sig{sig}"], color=c, lw=2, label=f"σ = {sig/100:.1f}")
    row = (xr - xmax).abs().idxmin()
    ax.text(xmax + .5, grid[f"retain_sig{sig}"].iloc[row], f"σ={sig/100:.1f}",
            color=c, fontsize=9.5, va="center", fontweight="bold")
ax.fill_between(xr, grid["retain_sig0"], grid["retain_sig50"], color=GREEN, alpha=.10)
for xt, lab in [(12.5, "보수 · 하위 10"), (25, "중도 · 하위 20"), (37.5, "공격 · 하위 30")]:
    ax.axvline(xt, color=MUTED, lw=.7, ls=":")
    ax.text(xt, 84.4, lab, fontsize=8.5, color=MUTED, ha="center", va="bottom")
ax.set_xlim(0, 43); ax.set_ylim(84, 101)
ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"{v:.0f}%"))
ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"{v:.0f}%"))
ax.set_xlabel("SKU 감축 비율 (하위 매출 순 단종)")
ax.set_ylabel("추정 매출 유지율")
ax.set_title("메뉴 합리화 프론티어 — σ = 이탈 수요의 잔여 메뉴 재포착률")
save(fig, "r_frontier.png")

print("done ->", OUT)
