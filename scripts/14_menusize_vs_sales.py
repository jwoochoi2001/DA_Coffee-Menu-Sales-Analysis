# -*- coding: utf-8 -*-
"""
14_menusize_vs_sales.py
원래 가설 정면 검증(단면) — 브랜드별 '메뉴 수' ↔ 가맹점 평균매출

X (메뉴 수): 나무위키 브랜드 문서(2026년 스냅샷) 기준 상시 메뉴 항목 수.
             HOT/ICED·사이즈 변형 제외, 시즌·단종 제외. 오차 ±20~30% (menu_conf).
Y (매출)  : 공정위 FftcBrandFrcsStatsService, 브랜드별 최근연도 가맹점 평균매출액(억원).
통제      : 매장 수, 가격대(저가/중가/고가), 업력(년).

산출: data/franchise/menusize_panel.csv, output/franchise_menusize.md,
      output/figures/43_menusize_vs_sales.png
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import pandas as pd, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.ticker as mtick
import statsmodels.formula.api as smf
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FR = ROOT / "data" / "franchise"; FIG = ROOT / "output" / "figures"
BLUE, RUST, GREEN, INK, MUT, GRD, RED = "#2F6F9F","#B0641A","#4F9D69","#33302C","#6B6560","#E8E4DE","#B23B2E"
plt.rcParams.update({"figure.dpi":150,"savefig.dpi":150,"savefig.bbox":"tight","font.family":"Malgun Gothic",
  "axes.unicode_minus":False,"figure.facecolor":"#FCFCFB","axes.facecolor":"#FCFCFB","savefig.facecolor":"#FCFCFB",
  "axes.spines.top":False,"axes.spines.right":False,"axes.grid":True,"grid.color":GRD,"grid.alpha":.9,
  "axes.titleweight":"bold","axes.titlelocation":"left","font.size":10})

# 브랜드: (음료수, 푸드수, menu_conf, 가격대, 창업년)  — 나무위키 2026 스냅샷 수집치
M = {
 "투썸플레이스": (43, 55, .70, "고가", 2002),
 "할리스":       (36, 18, .70, "중가", 1998),
 "파스쿠찌":     (57, 85, .60, "중가", 2002),
 "엔제리너스":   (27, 34, .70, "중가", 2000),
 "탐앤탐스":     (34, 14, .80, "중가", 1999),
 "이디야":       (80, 60, .75, "중가", 2001),
 "메가MGC커피":  (74, 29, .65, "저가", 2015),
 "컴포즈커피":   (82, 19, .80, "저가", 2014),
 "빽다방":       (62, 35, .75, "저가", 2006),
 "더벤티":       (89, 45, .65, "저가", 2014),
 "커피베이":     (89, 50, .75, "저가", 2011),
 "요거프레소":   (32, 15, .60, "저가", 2010),
 "매머드커피":   (60, 30, .55, "저가", 2015),  # 매머드익스프레스 포함 근사
}
mx = pd.DataFrame([(k, *v) for k, v in M.items()],
                  columns=["brand", "menu_drinks", "menu_food", "menu_conf", "tier", "founded"])
mx["menu_total"] = mx.menu_drinks + mx.menu_food

# ---- 공정위 Y (브랜드별 최근 유효연도) ----
Y = pd.read_csv(FR / "coffee_brand_panel.csv")
Y = Y[Y.avg_sales_eok > 0].sort_values("yr")
ylast = Y.groupby("brand").tail(1)[["brand", "yr", "avg_sales_eok", "frcsCnt",
                                    "newFrcsRgsCnt", "open_rate", "close_rate"]]
d = mx.merge(ylast, on="brand", how="inner").rename(columns={"yr": "sales_yr"})
d["age"] = d["sales_yr"] - d["founded"]
d["low"] = (d.tier == "저가").astype(int)
d["log_total"] = np.log(d.menu_total)
d["log_drinks"] = np.log(d.menu_drinks)
d["log_stores"] = np.log(d.frcsCnt)
d = d.sort_values("avg_sales_eok", ascending=False).reset_index(drop=True)
d.to_csv(FR / "menusize_panel.csv", index=False, encoding="utf-8-sig")

md = ["# 브랜드 메뉴 수 ↔ 가맹점 평균매출 (단면 분석)\n"]
def p(x=""): md.append(str(x) + "\n")
def tbl(f): md.append(f.to_markdown(index=False) + "\n")

p(f"- 표본: 국내 커피 프랜차이즈 **{len(d)}개** (X·Y 모두 확보). 단면(cross-section), 매출은 브랜드별 최근연도.")
p(f"- X(메뉴 수): 나무위키 2026 스냅샷, HOT/ICED·사이즈 제외, 시즌·단종 제외. **오차 ±20~30%.**")
p(f"- Y(매출): 공정위 정보공개서 기준 가맹점 평균매출액(억원).\n")
tbl(d[["brand", "tier", "menu_drinks", "menu_food", "menu_total", "frcsCnt",
       "avg_sales_eok", "sales_yr", "age"]].round(2))

# ---- 상관 ----
p("\n## 상관계수 (Pearson / Spearman)\n")
cr = []
for xcol in ["menu_total", "menu_drinks", "menu_food"]:
    cr.append({"X": xcol,
               "pearson r": round(d[xcol].corr(d.avg_sales_eok), 3),
               "spearman ρ": round(d[xcol].corr(d.avg_sales_eok, method="spearman"), 3)})
tbl(pd.DataFrame(cr))
p("- 저가 브랜드만 / 중고가만 부분집합 상관:")
for grp, sub in [("저가", d[d.low == 1]), ("중고가", d[d.low == 0])]:
    if len(sub) >= 4:
        p(f"  - {grp}(n={len(sub)}): menu_total ↔ 매출 r = {sub.menu_total.corr(sub.avg_sales_eok):.2f}")

# ---- OLS ----
p("\n## OLS (종속: 가맹점 평균매출액, 억원)\n")
models = {
 "M1 메뉴만":        "avg_sales_eok ~ log_total",
 "M2 +저가더미":     "avg_sales_eok ~ log_total + low",
 "M3 +매장수+업력":  "avg_sales_eok ~ log_total + low + log_stores + age",
 "M4 음료수만(M3형)": "avg_sales_eok ~ log_drinks + low + log_stores + age",
}
rowsm = []
for name, f in models.items():
    r = smf.ols(f, data=d).fit(cov_type="HC3")
    key = "log_total" if "log_total" in f else "log_drinks"
    b, se, pv = r.params[key], r.bse[key], r.pvalues[key]
    rowsm.append({"모델": name, "메뉴 계수 β": round(b, 3), "SE": round(se, 3),
                  "p": round(pv, 3), "R²": round(r.rsquared, 3), "n": int(r.nobs),
                  "해석": f"메뉴 2배 → 매출 {b*np.log(2):+.2f}억"})
tbl(pd.DataFrame(rowsm))
mfull = smf.ols(models["M3 +매장수+업력"], data=d).fit(cov_type="HC3")
p("\n**M3 전체 계수:**")
p("| 항 | β | p |")
p("|---|---|---|")
for k in mfull.params.index:
    p(f"| {k} | {mfull.params[k]:+.3f} | {mfull.pvalues[k]:.3f} |")

# ---- 그림 ----
fig, ax = plt.subplots(1, 2, figsize=(13, 5))
cmap = {"고가": BLUE, "중가": RUST, "저가": GREEN}
for tier, g in d.groupby("tier"):
    ax[0].scatter(g.menu_total, g.avg_sales_eok, s=g.frcsCnt/12+50, alpha=.7,
                  color=cmap[tier], label=tier, edgecolor="white")
for _, r in d.iterrows():
    ax[0].annotate(r.brand, (r.menu_total, r.avg_sales_eok), fontsize=8,
                   xytext=(4, 3), textcoords="offset points", color=INK)
ax[0].set_xlabel("총 메뉴 수 (음료+푸드)"); ax[0].set_ylabel("가맹점 평균매출액 (억원)")
ax[0].set_title("메뉴 수 × 매출  (원 크기 = 매장 수)"); ax[0].legend(title="가격대")
ax[0].yaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"{v:.0f}억"))

# 저가더미 통제 후 부분잔차
d["_yresid"] = smf.ols("avg_sales_eok ~ low + log_stores + age", data=d).fit().resid
d["_xresid"] = smf.ols("log_total ~ low + log_stores + age", data=d).fit().resid
ax[1].scatter(d._xresid, d._yresid, s=60, color=BLUE, alpha=.7, edgecolor="white")
for _, r in d.iterrows():
    ax[1].annotate(r.brand, (r._xresid, r._yresid), fontsize=8, xytext=(4, 3),
                   textcoords="offset points", color=INK)
bx = np.polyfit(d._xresid, d._yresid, 1)
xs = np.linspace(d._xresid.min(), d._xresid.max(), 20)
ax[1].plot(xs, np.polyval(bx, xs), color=RED, lw=1.5)
ax[1].axhline(0, color=MUT, lw=.6); ax[1].axvline(0, color=MUT, lw=.6)
ax[1].set_xlabel("log(메뉴수) | 가격대·매장수·업력 통제 후 잔차")
ax[1].set_ylabel("평균매출 | 통제 후 잔차")
ax[1].set_title(f"부분회귀 (partial regression)  ·  기울기 {bx[0]:+.2f}")
fig.savefig(FIG / "43_menusize_vs_sales.png"); plt.close(fig)

p("\n## 한계\n")
p("- **n=13, 단면.** 인과 아님. 메뉴 수는 브랜드 전략(저가 다품목 vs 고가 집중)의 결과이기도 함.")
p("- 메뉴 수 집계는 나무위키 2026 스냅샷 기반 ±20~30% 오차. 시점이 Y(2023~24)와 어긋남.")
p("- 스타벅스·폴바셋(직영)은 공정위 매출이 없어 제외. 표본이 가맹 브랜드에 치우침.")
p("- 매출은 브랜드 단위 연 1회 평균 — 매장별·계절 변이 없음.\n")

(ROOT / "output" / "franchise_menusize.md").write_text("\n".join(md), encoding="utf-8")
print(d[["brand","tier","menu_total","frcsCnt","avg_sales_eok"]].to_string(index=False))
print("\n" + pd.DataFrame(cr).to_string(index=False))
print("\ndone -> output/franchise_menusize.md, figures/43_menusize_vs_sales.png")
