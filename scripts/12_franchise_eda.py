# -*- coding: utf-8 -*-
"""
12_franchise_eda.py — 공정위 커피 프랜차이즈 패널 EDA (2017~2024)
입력: data/franchise/coffee_brand_panel.csv
산출: output/figures/41_franchise_*.png, output/franchise_eda.md
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import pandas as pd, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.ticker as mtick
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FR = ROOT / "data" / "franchise"; FIG = ROOT / "output" / "figures"
BLUE, RUST, GREEN, INK, MUT, GRD = "#2F6F9F", "#B0641A", "#4F9D69", "#33302C", "#6B6560", "#E8E4DE"
plt.rcParams.update({"figure.dpi":150,"savefig.dpi":150,"savefig.bbox":"tight","font.family":"Malgun Gothic",
    "axes.unicode_minus":False,"figure.facecolor":"#FCFCFB","axes.facecolor":"#FCFCFB","savefig.facecolor":"#FCFCFB",
    "axes.spines.top":False,"axes.spines.right":False,"axes.grid":True,"grid.color":GRD,"grid.alpha":.9,
    "axes.titleweight":"bold","axes.titlelocation":"left","font.size":10})

d = pd.read_csv(FR / "coffee_brand_panel.csv")
md = ["# 공정위 커피 프랜차이즈 패널 — EDA (2017–2024)\n"]
def p(x=""): md.append(str(x)+"\n")
def tbl(f): md.append(f.to_markdown()+"\n")

p(f"- 출처: 공정거래위원회 `FftcBrandFrcsStatsService/getBrandFrcsStats` (정보공개서 기준)")
p(f"- 커버리지: **{d.brand.nunique()}개 커피 브랜드 · {len(d)} 브랜드-연도 · 2017–2024**")
p(f"- 평균매출액(avg_sales_eok) 보고: {(d.avg_sales_eok>0).sum()} 브랜드-연도")
p(f"- 필드: 가맹점수 frcsCnt · 신규개점 newFrcsRgsCnt · 계약종료 ctrtEndCnt · 계약해지 ctrtCncltnCnt · "
  "가맹점 평균매출액(억원) · 3.3㎡당 매출(만원) · 개점률 · 폐점률\n")

BIG = ["스타벅스","투썸플레이스","이디야","할리스","메가MGC커피","컴포즈커피","빽다방",
       "파스쿠찌","엔제리너스","커피베이","탐앤탐스","더벤티","매머드커피","요거프레소","토프레소"]
b = d[d.brand.isin(BIG)].copy()

# 저가/고가 태그
LOWCOST = {"메가MGC커피","컴포즈커피","빽다방","더벤티","매머드커피","커피베이","요거프레소","토프레소"}
b["tier"] = np.where(b.brand.isin(LOWCOST), "저가", "중고가")

p("## 1. 가맹점 평균매출액 추이 (억원)\n")
piv = b.pivot_table(index="brand", columns="yr", values="avg_sales_eok")
tbl(piv.round(2))
p("- **투썸 5.2억 내외로 독보적 유지.** 할리스·파스쿠찌는 2017 3.7~4.0억 → 2022 2.7~2.9억으로 하락 후 소폭 반등.")
p("- 저가 3사(메가·컴포즈·빽다방) 2.5~3.6억 — 출점 폭증에도 가맹점당 매출이 **희석되지 않음**. 오히려 메가는 상승(2.5→3.6억).")
p("- 이디야는 완만한 하락(2.3→1.9억) + 출점 둔화.\n")

p("## 2. 출점 속도 (가맹점 수)\n")
tbl(b.pivot_table(index="brand", columns="yr", values="frcsCnt").round(0).astype("Int64"))
p("- 컴포즈 93→2,360 (25배), 메가 40→2,681 (67배), 더벤티 187→1,129. "
  "이디야는 1,865→3,005(2022) 정점 후 2,805로 첫 순감.\n")

p("## 3. 개점률 vs 폐점률 (당해 신규·종료 ÷ 가맹점수)\n")
rate = (b.groupby("brand")[["open_rate","close_rate"]].mean()*100).round(1)
rate["순증률"] = (rate.open_rate - rate.close_rate).round(1)
tbl(rate.sort_values("순증률", ascending=False))
p("- 저가 브랜드는 개점률 20~40%로 공격적, 폐점률은 낮음(<3%). 성숙 브랜드(이디야·엔제리너스·요거프레소)는 개점률이 폐점률에 근접하거나 역전.\n")

# ---- 그림 ----
fig, ax = plt.subplots(1, 2, figsize=(13, 4.6))
show = ["투썸플레이스","할리스","메가MGC커피","컴포즈커피","이디야","빽다방"]
colors = [BLUE, RUST, GREEN, "#8E5AA8", MUT, "#C9A227"]
for brand, c in zip(show, colors):
    g = b[b.brand == brand].sort_values("yr")
    g = g[g.avg_sales_eok > 0]
    ax[0].plot(g.yr, g.avg_sales_eok, "o-", label=brand, color=c, lw=1.8, ms=4)
ax[0].set_title("가맹점 평균매출액 (억원)"); ax[0].legend(fontsize=8, ncol=2)
ax[0].yaxis.set_major_formatter(mtick.FuncFormatter(lambda v,_:f"{v:.0f}억"))
for brand, c in zip(show, colors):
    g = b[b.brand == brand].sort_values("yr")
    ax[1].plot(g.yr, g.frcsCnt, "o-", label=brand, color=c, lw=1.8, ms=4)
ax[1].set_title("가맹점 수"); ax[1].legend(fontsize=8, ncol=2)
fig.savefig(FIG / "41_franchise_sales_stores.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(8.5, 5))
agg = b.groupby("brand").agg(open_rate=("open_rate","mean"), close_rate=("close_rate","mean"),
                             sales=("avg_sales_eok", lambda s: s[s>0].mean()),
                             size=("frcsCnt","max"), tier=("tier","first")).dropna()
for tier, c in [("저가", GREEN), ("중고가", BLUE)]:
    s = agg[agg.tier == tier]
    ax.scatter(s.open_rate*100, s.sales, s=s["size"]/6+30, alpha=.65, color=c, label=tier, edgecolor="white")
    for nm, r in s.iterrows():
        ax.annotate(nm, (r.open_rate*100, r.sales), fontsize=8, color=INK,
                    xytext=(4,3), textcoords="offset points")
ax.set_xlabel("평균 개점률 (신규개점 ÷ 가맹점수, %)"); ax.set_ylabel("가맹점 평균매출액 (억원)")
ax.set_title("출점 공격성 × 가맹점당 매출  (원 크기 = 최대 가맹점수)")
ax.legend(); ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda v,_:f"{v:.0f}억"))
fig.savefig(FIG / "42_franchise_openrate_sales.png"); plt.close(fig)

p("## 4. 한계\n")
p("- 정보공개서 기준 = **가맹점만** 집계. 스타벅스·폴바셋 등 직영 브랜드는 미포함(→ DART 필요).")
p("- 평균매출액은 연 1회, 브랜드 단위. 동일점 성장률·계절성은 없음.")
p("- 2023년 일부 브랜드 결측(법인 합병·보고 지연). 브랜드명 영문표기 분리 등은 정규화했으나 완벽하지 않음.")
p("- **신메뉴 출시 데이터는 이 API에 없음** — 별도 수집 필요(스타벅스는 완료, 나머지는 미완).\n")

(ROOT/"output"/"franchise_eda.md").write_text("\n".join(md), encoding="utf-8")
print("done. figs: 41_franchise_sales_stores.png, 42_franchise_openrate_sales.png")
print(rate.sort_values("순증률", ascending=False).to_string())
