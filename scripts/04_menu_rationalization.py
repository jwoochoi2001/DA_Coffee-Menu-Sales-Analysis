# -*- coding: utf-8 -*-
"""
04_menu_rationalization.py
메뉴 합리화(SKU 축소) 시뮬레이션
- 하위 메뉴를 k개 단종했을 때의 매출 영향을 대체율(substitution rate σ) 시나리오별로 추정
- 대체 로직: 단종품 수요의 σ 비율이 [같은 product_type -> 같은 category] 순으로
  생존 메뉴에 수량비례 재분배, 재분배 매출은 생존 메뉴의 수량가중 평균단가로 평가
- 장바구니(동시구매) 정보 없음(1거래=1품목) → 교차판매 손실 미반영 → 결과는 '매출 유지율의 상한'

입력: data/processed/coffee_clean.parquet
산출: output/figures/2x_*.png, output/menu_rationalization.md,
      data/processed/menu_item_stats.csv, data/processed/rationalization_grid.csv
"""
import re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
FIG = ROOT / "output" / "figures"
plt.rcParams.update({"figure.dpi": 110, "savefig.dpi": 110, "figure.autolayout": True,
                     "axes.grid": True, "grid.alpha": .25,
                     "axes.spines.top": False, "axes.spines.right": False, "font.size": 10})
BLUE, ORANGE, GREEN, RED, GREY = "#2f6f9f", "#e08a2e", "#4f9d69", "#c0392b", "#888"

df = pd.read_parquet(PROC / "coffee_clean.parquet")
N_DAYS = df["date"].nunique()
N_STORES = df["store_location"].nunique()
TOTAL_REV = df["revenue"].sum()
RETAIL_CATS = {"Coffee beans", "Loose Tea", "Branded", "Packaged Chocolate"}

md = ["# Maven Roasters — 메뉴 합리화 시뮬레이션\n"]
def p(x=""): md.append(str(x) + "\n")
def tbl(f): md.append(f.to_markdown() + "\n")

# ============================================================ 1. 아이템 통계
g = (df.groupby(["product_detail", "product_type", "product_category"])
       .agg(revenue=("revenue", "sum"), units=("transaction_qty", "sum"),
            n_tx=("transaction_id", "nunique"), avg_price=("unit_price", "mean"))
       .reset_index())
g["rev_share_%"] = g["revenue"] / TOTAL_REV * 100
g["units_per_store_day"] = g["units"] / (N_DAYS * N_STORES)
g["kind"] = np.where(g["product_category"].isin(RETAIL_CATS), "retail", "prep")

# 매장 편중: 한 매장이 그 아이템 매출에서 차지하는 최대 비중 (균등이면 ~0.33)
si = df.pivot_table(index="product_detail", columns="store_location",
                    values="revenue", aggfunc="sum", fill_value=0)
g["store_conc"] = g["product_detail"].map((si.div(si.sum(1), axis=0)).max(1))
CONC_FLAG = 0.42
g["conc_flag"] = g["store_conc"] > CONC_FLAG

g = g.sort_values("revenue").reset_index(drop=True)
g["rev_rank"] = np.arange(1, len(g) + 1)
g["cum_rev_share_%"] = g["revenue"].cumsum() / TOTAL_REV * 100
g.to_csv(PROC / "menu_item_stats.csv", index=False)

p(f"- 총 SKU(product_detail) **{len(g)}개** · product_type {df.product_type.nunique()}개 · category {df.product_category.nunique()}개")
p(f"- 총매출 ${TOTAL_REV:,.0f} · {N_DAYS}일 · 매장 {N_STORES}곳 · retail {int((g.kind=='retail').sum())} SKU / prep {int((g.kind=='prep').sum())} SKU")
p(f"- 매출 하위 40 SKU(50%)의 매출 합계 비중: **{g.head(40)['revenue'].sum()/TOTAL_REV*100:.1f}%**\n")
p("**매출 하위 18 SKU** (store_conc>0.42 는 특정 매장 편중 → 단종 주의)")
tbl(g.head(18)[["rev_rank", "product_detail", "product_category", "kind", "revenue",
                "units_per_store_day", "avg_price", "rev_share_%", "store_conc", "conc_flag"]]
    .round({"revenue": 0, "units_per_store_day": 2, "avg_price": 2, "rev_share_%": 2, "store_conc": 2}))

# ============================================================ 2. 대체 시뮬레이터
def simulate(cut_items, sigma):
    cut = set(cut_items)
    surv = g[~g.product_detail.isin(cut)]
    kept = surv["revenue"].sum()
    recap = 0.0
    for _, r in g[g.product_detail.isin(cut)].iterrows():
        for level in ("product_type", "product_category"):
            pool = surv[surv[level] == r[level]]
            if len(pool):
                wprice = np.average(pool["avg_price"], weights=pool["units"])
                # 이탈 고객이 원래 지출액보다 더 쓰지는 않는다고 가정(상방 캡)
                recap += sigma * min(r["units"] * wprice, r["revenue"])
                break
    return kept + recap

order = g["product_detail"].tolist()   # 매출 하위 순
sigmas = [0.0, 0.3, 0.5, 0.7]

grid_rows = []
for k in range(0, 41):
    cut = order[:k]
    row = {"k_cut": k, "sku_reduction_%": k / len(g) * 100,
           "gross_rev_dropped_%": g[g.product_detail.isin(cut)]["revenue"].sum() / TOTAL_REV * 100,
           "n_conc_flag": int(g[g.product_detail.isin(cut)]["conc_flag"].sum())}
    for s in sigmas:
        row[f"retain_sig{int(s*100)}"] = simulate(cut, s) / TOTAL_REV * 100
    grid_rows.append(row)
grid = pd.DataFrame(grid_rows)
grid.to_csv(PROC / "rationalization_grid.csv", index=False)

# ============================================================ 3. 프론티어 그림
fig, ax = plt.subplots(1, 2, figsize=(13, 5))
for s, ls, c in zip(sigmas, ["-", "--", "-.", ":"], [RED, ORANGE, GREEN, BLUE]):
    ax[0].plot(grid["k_cut"], grid[f"retain_sig{int(s*100)}"], ls, color=c, lw=1.6,
               label=f"σ={s}")
ax[0].axhline(100, color=GREY, lw=.8); ax[0].axhline(98, color=RED, lw=.8, ls=":")
ax[0].set_xlabel("# SKU cut (bottom-ranked by revenue)")
ax[0].set_ylabel("net revenue retained %")
ax[0].set_title("Revenue retained vs cut depth"); ax[0].legend(fontsize=9)

ax[1].plot(grid["sku_reduction_%"], grid["retain_sig0"], color=RED, label="σ=0 (no substitution, lower bound)")
ax[1].plot(grid["sku_reduction_%"], grid["retain_sig30"], color=ORANGE, label="σ=0.3")
ax[1].plot(grid["sku_reduction_%"], grid["retain_sig50"], color=GREEN, label="σ=0.5")
ax[1].fill_between(grid["sku_reduction_%"], grid["retain_sig0"], grid["retain_sig50"],
                   color=GREEN, alpha=.12)
for xt in (12.5, 25, 37.5):
    ax[1].axvline(xt, color=GREY, lw=.6, ls=":")
ax[1].set_xlabel("SKU reduction %"); ax[1].set_ylabel("net revenue retained %")
ax[1].set_title("Efficient frontier (bottom-k by revenue)"); ax[1].legend(fontsize=8)
fig.savefig(FIG / "20_rationalization_frontier.png"); plt.close(fig)

# ============================================================ 4. 시나리오 표
p("\n## 시나리오별 결과 (매출 하위 순 단종)\n")
p("`retain` = 단종 후 추정 총매출 ÷ 현재 총매출(%). σ=0 = 대체 전혀 없음(하한), σ=0.5 = 수요 절반이 잔여 메뉴로 이동.\n")
sub = grid[grid.k_cut.isin([5, 10, 15, 20, 25, 30])]
tbl(sub[["k_cut", "sku_reduction_%", "gross_rev_dropped_%", "n_conc_flag",
         "retain_sig0", "retain_sig30", "retain_sig50"]].round(2).set_index("k_cut"))
p("- `n_conc_flag` = 그 컷에 포함된 SKU 중 한 매장 편중(>42%)이라 단종 전 매장별 확인이 필요한 개수.")

# ============================================================ 5. 3단 권고안
p("\n## 권고: 3단계 시나리오 (매출 하위 k개 단종)\n")
tiers = [("보수 (Tier 1)", 10), ("중도 (Tier 2)", 20), ("공격 (Tier 3)", 30)]
rows = []
for name, k in tiers:
    items = order[:k]
    kept_types = df[~df.product_detail.isin(items)].product_type.nunique()
    kept_cats = df[~df.product_detail.isin(items)].product_category.nunique()
    rows.append({
        "시나리오": name,
        "단종 SKU": len(items),
        "SKU 감축%": round(len(items) / len(g) * 100, 1),
        "제거 매출%": round(g[g.product_detail.isin(items)].revenue.sum() / TOTAL_REV * 100, 2),
        "유지율 σ=0": round(simulate(items, 0.0) / TOTAL_REV * 100, 1),
        "유지율 σ=0.3": round(simulate(items, 0.3) / TOTAL_REV * 100, 1),
        "유지율 σ=0.5": round(simulate(items, 0.5) / TOTAL_REV * 100, 1),
        "잔여 type/cat": f"{kept_types}/{kept_cats}",
    })
tbl(pd.DataFrame(rows).set_index("시나리오"))

p("\n**Tier 1 (보수) — 단종 대상 10개 SKU**")
t1 = g[g.product_detail.isin(order[:10])].sort_values("revenue")
tbl(t1[["product_detail", "product_category", "kind", "revenue", "units_per_store_day", "avg_price", "conc_flag"]]
    .round({"revenue": 0, "units_per_store_day": 2, "avg_price": 2}).reset_index(drop=True))
p("- 카테고리 분포: " + ", ".join(f"{k} {int(v)}" for k, v in t1.product_category.value_counts().items()))
p("- 대부분 **Loose Tea 낱개 / Packaged Chocolate** — 저회전 포장 SKU. 제조 라인·메뉴판 복잡도와 무관하게 재고만 줄임.")
p("- Tier 2 추가분(11~20위)은 시럽·원두·차 음료로 확장되어 대체율 가정에 더 민감.\n")

# ============================================================ 6. 사이즈 변형 정리
p("## 별도 레버 — 사이즈 변형(Lg/Rg/Sm) 정리\n")
def split_size(s):
    m = re.search(r"\s(Lg|Rg|Sm)$", s)
    return (s[:m.start()], m.group(1)) if m else (s, "NONE")
tmp = df.copy()
tmp[["base", "size"]] = tmp["product_detail"].apply(lambda s: pd.Series(split_size(s)))
multi = tmp[tmp["size"] != "NONE"]
base_rev = multi.groupby("base")["revenue"].sum()
sz = multi.groupby(["base", "size"])["revenue"].sum().reset_index()
sz["share_in_base_%"] = sz["revenue"] / sz["base"].map(base_rev) * 100
n_multi = multi["base"].nunique()
weak = sz[sz["share_in_base_%"] < 30].sort_values("share_in_base_%")
p(f"- 사이즈 옵션이 2개 이상인 음료 base **{n_multi}종**. 그중 base 매출의 30% 미만인 '약한 사이즈' 변형: **{len(weak)}개**")
tbl(weak.assign(revenue=weak.revenue.round(0)).round({"share_in_base_%": 1})
    .set_index(["base", "size"]))
p(f"- 이 약한 변형들을 모두 없애면 SKU **-{len(weak)}개**, 직접 매출 ${weak.revenue.sum():,.0f} ({weak.revenue.sum()/TOTAL_REV*100:.1f}%).")
p("- 다만 가장 약한 변형도 base 매출의 25% 이상 → **뚜렷한 '버릴 사이즈'는 없음**. 2사이즈 음료는 40:60, 3사이즈는 25:35:40 수준으로 고르게 팔림.")
p("- 사이즈 축소는 대체율이 매우 높음(같은 음료·다른 컵, σ≈0.8~0.95) → 없애도 실제 순손실은 위 금액의 5~20%.\n")

# ============================================================ 7. 베이커리 회전율
p("## 참고 — 베이커리 회전율 (폐기 리스크 프록시, COGS 없음)\n")
bak = g[g.product_category == "Bakery"].sort_values("units_per_store_day")
tbl(bak[["product_detail", "units_per_store_day", "revenue", "avg_price"]]
    .round({"units_per_store_day": 2, "revenue": 0, "avg_price": 2}).reset_index(drop=True))
p(f"- 최저 회전 품목도 매장·일 {bak.units_per_store_day.min():.1f}개 → 전 품목이 하루 3개 이상. "
  "폐기 리스크는 낮은 편이며, 베이커리 11종은 **매출 기여(12%) 대비 유지 근거 충분**. "
  "판단은 매출이 아니라 COGS·폐기율 데이터가 있어야 가능.\n")

# ============================================================ 8. 한계
p("## 한계 / 해석 주의\n")
p("- **장바구니 데이터 없음**(1거래=1품목) → 단종 품목 고객이 아예 이탈하는 교차판매 손실 미반영. 모든 수치는 **유지율 상한(낙관)**.")
p("- **COGS·폐기·인건비 없음** → 매출 기준 분석. 저회전·소량 포장 SKU는 이익 개선폭이 매출 수치보다 큼.")
p("- σ(대체율)는 가정. 사이즈 변형 정리 σ≈0.9, 서로 다른 차·시럽 단종 σ≈0.2~0.4.")
p("- 매장 3곳 메뉴가 사실상 동일 → '메뉴 수 축소 실험'을 관측한 게 아니라 시뮬레이션임. 인과 검증엔 메뉴가 다른 다점포/전후 데이터 필요.")

(ROOT / "output" / "menu_rationalization.md").write_text("\n".join(md), encoding="utf-8")
print("done ->", ROOT / "output" / "menu_rationalization.md")
for name, k in tiers:
    it = order[:k]
    print(f"{name}: retain sig0/0.3/0.5 = "
          f"{simulate(it,0)/TOTAL_REV*100:.1f}/{simulate(it,0.3)/TOTAL_REV*100:.1f}/{simulate(it,0.5)/TOTAL_REV*100:.1f}")
print("weak size variants:", len(weak))
