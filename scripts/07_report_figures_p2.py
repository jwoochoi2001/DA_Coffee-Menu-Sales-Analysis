# -*- coding: utf-8 -*-
"""07_report_figures_p2.py — 리포트 Phase 2(국내 프랜차이즈) 그림, 05와 동일 스타일"""
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.ticker as mtick
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FR = ROOT / "data" / "franchise"; OUT = ROOT / "output" / "report"
BLUE, RUST, GREEN = "#2F6F9F", "#B0641A", "#4F9D69"
INK, MUTED, GRID, SURF, RED, GOLD, PUR = "#33302C", "#6B6560", "#E8E4DE", "#FCFCFB", "#B23B2E", "#C9A227", "#8E5AA8"
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
def save(fig, n): fig.savefig(OUT / n); plt.close(fig); print("  ", n)
eok = mtick.FuncFormatter(lambda v, _: f"{v:.1f}억")

# ---------------------------------------------------------------- 1. 브랜드 매출·매장 추이
d = pd.read_csv(FR / "coffee_brand_panel.csv")
show = ["투썸플레이스","할리스","메가MGC커피","컴포즈커피","이디야","빽다방"]
cols = [BLUE, RUST, GREEN, PUR, MUTED, GOLD]
fig, ax = plt.subplots(1, 2, figsize=(9.2, 3.7))
for br, c in zip(show, cols):
    g = d[(d.brand == br) & (d.avg_sales_eok > 0)].sort_values("yr")
    ax[0].plot(g.yr, g.avg_sales_eok, "o-", label=br, color=c, lw=1.8, ms=3.5)
    g2 = d[d.brand == br].sort_values("yr")
    ax[1].plot(g2.yr, g2.frcsCnt, "o-", label=br, color=c, lw=1.8, ms=3.5)
ax[0].set_title("가맹점 평균매출액"); ax[0].yaxis.set_major_formatter(eok)
ax[0].legend(fontsize=7.5, ncol=2, loc="lower center")
ax[1].set_title("가맹점 수"); ax[1].yaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"{v:,.0f}"))
save(fig, "r_franchise.png")

# ---------------------------------------------------------------- 2. 메뉴 수 × 매출 산점도
m = pd.read_csv(FR / "menusize_panel_v2.csv")
m = m[m.legacy == 0]
tier_c = {"저가": GREEN, "중가": RUST, "고가": BLUE}
m["tier3"] = pd.cut(m.price, [0, 2500, 4000, 9999], labels=["저가","중가","고가"])
fig, ax = plt.subplots(figsize=(9.2, 5))
for t, c in tier_c.items():
    g = m[m.tier3 == t]
    ax.scatter(g.menu_total, g.avg_sales_eok, s=90, alpha=.75, color=c, label=t, edgecolor="white", linewidth=.8)
for _, r in m.iterrows():
    ax.annotate(r.brand, (r.menu_total, r.avg_sales_eok), fontsize=8, color=INK,
                xytext=(4, 3), textcoords="offset points")
b1 = np.polyfit(m.menu_total, m.avg_sales_eok, 1)
xs = np.linspace(m.menu_total.min(), m.menu_total.max(), 20)
ax.plot(xs, np.polyval(b1, xs), color=RED, lw=1.6, ls="--")
ax.text(.5, 1.02, f"회귀 기울기 {b1[0]:+.3f} 억/메뉴   ·   상관 r = {m.menu_total.corr(m.avg_sales_eok):+.2f}   ·   유의하지 않음",
        transform=ax.transAxes, ha="center", fontsize=9.5, color=MUTED)
ax.set_xlabel("총 메뉴 수 (음료 + 푸드, 나무위키 2026 스냅샷)")
ax.set_ylabel("가맹점 평균매출액")
ax.set_title("국내 커피 프랜차이즈 19개 — 메뉴 수 × 매출")
ax.yaxis.set_major_formatter(eok); ax.legend(title="가격대")
save(fig, "r_menuscatter.png")

# ---------------------------------------------------------------- 3. 메뉴 규모 3분위 궤적
raw = pd.read_csv(FR / "franchise_all_raw.csv"); raw = raw[raw.indutyMlsfcNm == "커피"]
def norm(s):
    s = str(s).split("(")[0].strip()
    for k, v in {"할리스커피":"할리스","탐앤탐스커피":"탐앤탐스","탐앤탐스 커피":"탐앤탐스",
                 "메가엠지씨커피":"메가MGC커피","이디야커피":"이디야","THE LITER":"더리터"}.items():
        if s.startswith(k): return v
    return s
raw["brand"] = raw.brandNm.map(norm)
raw["s_eok"] = pd.to_numeric(raw.avrgSlsAmt, errors="coerce") / 1e5
raw = raw[(raw.s_eok > 0) & raw.brand.isin(m.brand)]
terc = pd.qcut(m.set_index("brand").menu_total, 3, labels=["소 (하위 1/3)","중","대 (상위 1/3)"])
raw["mt"] = raw.brand.map(terc)
traj = raw.groupby(["yr","mt"], observed=True).s_eok.mean().unstack()
fig, ax = plt.subplots(figsize=(9.2, 4))
for col, c in zip(traj.columns, [GREEN, RUST, BLUE]):
    ax.plot(traj.index, traj[col], "o-", label=col, color=c, lw=2, ms=4)
ax.set_title("메뉴 규모 3분위별 가맹점 평균매출 (2017–2024)")
ax.yaxis.set_major_formatter(eok); ax.legend(title="메뉴 규모")
save(fig, "r_tercile.png")

print("done ->", OUT)
