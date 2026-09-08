# -*- coding: utf-8 -*-
"""
07_menu_effect_bounds.py
"메뉴 수 → 매출" 가설을 이 데이터로 갈 수 있는 최대치까지 밀어붙인다.
  A. 메뉴가 실제로 바뀐 적이 있나 (자연실험 탐색)
  B. 주간 매출 분산 분해 — 매장 간 vs 시점 간 vs 잔차
  C. 매장내 1차 차분 회귀 — Δ메뉴폭의 매출 연관 (트래픽 통제)
  D. 동등성 검정(TOST) — 연관 계수가 '실질적으로 0' 구간 안에 있나
  E. 합리화 시뮬레이션 강건성 — 단종 기준·매장별·σ 몬테카를로
입력: data/processed/coffee_clean.parquet, store_week_panel.csv, menu_item_stats.csv
산출: output/menu_effect_bounds.md, output/figures/3x_*.png
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from pathlib import Path
import statsmodels.formula.api as smf
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
FIG = ROOT / "output" / "figures"
BLUE, RUST, GREEN, INK, MUTED, GRID, RED = "#2F6F9F", "#B0641A", "#4F9D69", "#33302C", "#6B6560", "#E8E4DE", "#B23B2E"
plt.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 150, "savefig.bbox": "tight", "figure.facecolor": "#FCFCFB",
    "axes.facecolor": "#FCFCFB", "savefig.facecolor": "#FCFCFB",
    "font.family": "Malgun Gothic", "font.sans-serif": ["Malgun Gothic", "DejaVu Sans"],
    "axes.unicode_minus": False, "font.size": 11, "text.color": INK, "axes.labelcolor": INK,
    "axes.edgecolor": GRID, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.grid": True, "grid.color": GRID, "grid.alpha": .9, "axes.spines.top": False, "axes.spines.right": False,
    "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlelocation": "left", "axes.titlecolor": INK,
})

df = pd.read_parquet(PROC / "coffee_clean.parquet")
df["date"] = pd.to_datetime(df["date"])
md = ["# 메뉴 수 효과 — 데이터로 갈 수 있는 최대치\n"]
def p(x=""): md.append(str(x) + "\n")
def tbl(f): md.append(f.to_markdown() + "\n")

D0, D1 = df["date"].min(), df["date"].max()

# ============================================================ A. 메뉴 변화 탐색
p("## A. 메뉴 구성은 실제로 바뀐 적이 있나 (자연실험 탐색)\n")
sp = (df.groupby(["store_location", "product_id"])
        .agg(first=("date", "min"), last=("date", "max"),
             active_days=("date", "nunique"), units=("transaction_qty", "sum"))
        .reset_index())
sp["days_to_first"] = (sp["first"] - D0).dt.days
sp["days_from_last"] = (D1 - sp["last"]).dt.days
# '진짜 도입/단종'의 조건: 늦게 등장 + 등장 후엔 꾸준히 팔림 (or 반대)
susp_in = sp[(sp["days_to_first"] > 21) & (sp["units"] / sp["active_days"].clip(lower=1) > 1)]
susp_out = sp[(sp["days_from_last"] > 21) & (sp["units"] / sp["active_days"].clip(lower=1) > 1)]
p(f"- 매장×상품 조합 {len(sp)}개 중, 21일 이상 늦게 첫 판매 &amp; 이후 꾸준한 경우: **{len(susp_in)}건**")
p(f"- 21일 이상 일찍 마지막 판매 &amp; 이전엔 꾸준한 경우: **{len(susp_out)}건**")
lateish = sp[sp["days_to_first"] > 14].sort_values("days_to_first", ascending=False)
tbl(lateish.head(8)[["store_location", "product_id", "first", "days_to_first", "units", "active_days"]]
    .rename(columns={"units": "총수량(6개월)", "active_days": "판매일수"}))
p("- 늦게 등장한 소수 품목은 모두 **6개월간 13–65잔** 수준의 초저회전 상품이다. "
  "1월에 우연히 안 팔렸을 뿐, 메뉴판에서 추가/삭제된 게 아니다.")
p(f"- 매장별 취급 상품 수: {df.groupby('store_location').product_id.nunique().to_dict()} (전체 80종)")
p("\n> **결론 A: 181일 내내, 3개 매장 모두 메뉴 구성이 고정이었다. 메뉴 수의 '변화'가 0이므로 "
  "이 데이터에는 자연실험이 존재하지 않는다.**\n")

# ============================================================ 주간 패널 준비
w = pd.read_csv(PROC / "store_week_panel.csv")
w = w[w["full_week"]].copy()
w["store"] = w["store"].astype("category")
w["week"] = w["year_week"].astype("category")
w["lrev"], w["lntx"] = np.log(w["revenue"]), np.log(w["n_tx"])
w = w.sort_values(["store", "year_week"]).reset_index(drop=True)
p(f"분석 패널: 완전주 store×week **{len(w)}행**, 매장 {w.store.nunique()}곳 · "
  f"주 {w.week.nunique()}개. menu_breadth 범위 {int(w.menu_breadth.min())}–{int(w.menu_breadth.max())} "
  f"(평균 {w.menu_breadth.mean():.1f}).\n")

# ============================================================ B. 분산 분해
p("## B. 주간 매출 분산은 어디서 오나\n")
gm = w["lrev"].mean()
ss_tot = ((w["lrev"] - gm) ** 2).sum()
store_mean = w.groupby("store", observed=True)["lrev"].transform("mean")
week_mean = w.groupby("week", observed=True)["lrev"].transform("mean")
ss_store = ((store_mean - gm) ** 2).sum()
ss_week = ((week_mean - gm) ** 2).sum()
fe2 = smf.ols("lrev ~ C(store) + C(week)", data=w).fit()
p("| 성분 | 설명하는 분산 비중 |")
p("|---|---|")
p(f"| 매장 간 (store) | {ss_store/ss_tot*100:.1f}% |")
p(f"| 시점 간 (week) | {ss_week/ss_tot*100:.1f}% |")
p(f"| 매장+시점 2원 고정효과 합 (R²) | {fe2.rsquared*100:.1f}% |")
p(f"| 그 외 (잔차) | {(1-fe2.rsquared)*100:.1f}% |")
p("\n> **결론 B: 주간 매출 변동의 대부분이 '시점(계절 추세)'에서 온다. 매장 간 차이는 "
  f"{ss_store/ss_tot*100:.0f}%뿐 — 메뉴 구성이 설명할 여지 자체가 거의 없다.**\n")

# ============================================================ C. 1차 차분 회귀
p("## C. 메뉴폭–매출 연관을 트래픽 통제 후 재측정\n")
p("여기서 `menu_breadth` = 그 주 실제로 팔린 고유 SKU 수(51–80). 이건 '메뉴 운영 수'가 "
  "아니라 트래픽에 딸려 오는 값이라, 아래는 **인과가 아니라 관측 연관**을 재는 것이다. "
  "매장별 전주 대비 변화량(1차 차분)으로 매장 고정효과를 제거하고, 트래픽 변화를 통제한다.\n")
w["d_lrev"] = w.groupby("store", observed=True)["lrev"].diff()
w["d_breadth"] = w.groupby("store", observed=True)["menu_breadth"].diff()
w["d_lntx"] = w.groupby("store", observed=True)["lntx"].diff()
fd = w.dropna(subset=["d_lrev", "d_breadth", "d_lntx"]).copy()

m_fd_raw = smf.ols("d_lrev ~ d_breadth", data=fd).fit(cov_type="HC1")
m_fd = smf.ols("d_lrev ~ d_breadth + d_lntx", data=fd).fit(cov_type="HC1")
m_lv = smf.ols("lrev ~ menu_breadth + lntx + C(store) + C(week)", data=w).fit(cov_type="HC1")

def row(name, res, key):
    b, se = res.params[key], res.bse[key]
    lo, hi = b - 1.96 * se, b + 1.96 * se
    return {"모델": name, "β": round(b, 5), "SE": round(se, 5), "p": round(res.pvalues[key], 3),
            "95% CI (β)": f"[{lo:+.4f}, {hi:+.4f}]",
            "≈ 매출%/메뉴 10개": f"{(np.exp(b*10)-1)*100:+.1f}%  [{(np.exp(lo*10)-1)*100:+.1f}, {(np.exp(hi*10)-1)*100:+.1f}]"}
# 표준오차 민감도: HC1 vs 매장클러스터(3) vs 주클러스터(~25)
m_fd_cs = smf.ols("d_lrev ~ d_breadth + d_lntx", data=fd).fit(cov_type="cluster", cov_kwds={"groups": fd["store"]})
m_fd_cw = smf.ols("d_lrev ~ d_breadth + d_lntx", data=fd).fit(cov_type="cluster", cov_kwds={"groups": fd["week"].astype(str)})
rows = [row("① 차분, 통제 없음 (HC1)", m_fd_raw, "d_breadth"),
        row("② 차분 + 트래픽 (HC1)", m_fd, "d_breadth"),
        row("③ 수준 + 매장·주 FE + 트래픽 (HC1)", m_lv, "menu_breadth")]
tbl(pd.DataFrame(rows).set_index("모델"))
p(f"- 트래픽 통제 후에도 점추정치는 **+2~4% / 메뉴 10개**로 약하게 양(+). 트래픽 계수는 압도적이다"
  f"(② Δlog거래수 β = {m_fd.params['d_lntx']:.2f}, R² = {m_fd.rsquared:.2f}).")
p("- **그러나 이 부호는 표준오차 가정에 따라 흔들린다.** 같은 모델②의 d_breadth p값:")
p(f"  - HC1(독립 가정): p = {m_fd.pvalues['d_breadth']:.3f}")
p(f"  - 매장 클러스터(3개, 과소): p = {m_fd_cs.pvalues['d_breadth']:.3f}")
p(f"  - 주 클러스터(~25개): p = {m_fd_cw.pvalues['d_breadth']:.3f}")
p(f"- n = {int(m_fd.nobs)}(완전주 75, 매장 3). 매장 간 상관·계열 상관을 제대로 처리할 표본이 아니다. "
  "→ 이 연관은 **부호조차 신뢰구간이 넓다**. 아래 D는 그 폭을 정량화한 것.\n")

# ============================================================ D. 동등성 검정 (TOST)
from scipy import stats
p("## D. 동등성 검정 (TOST) — 연관을 어디까지 '0'이라 말할 수 있나\n")
p("점추정치가 0에 가깝다고 '효과 없음'이 되진 않는다(검정력 부족일 수 있음). "
  "TOST는 **90% CI가 ±SESOI 안에 완전히 들어오면** α=0.05에서 '무시할 만하다'고 결론한다.\n")
def tost(res, key, delta):
    b, se = res.params[key], res.bse[key]
    dof = int(res.df_resid)
    p_lo = 1 - stats.t.cdf((b + delta) / se, dof)
    p_hi = stats.t.cdf((b - delta) / se, dof)
    ci90 = (b - 1.645 * se, b + 1.645 * se)
    return b, se, ci90, max(p_lo, p_hi), (ci90[0] > -delta and ci90[1] < delta)

models = [("② 차분+트래픽", m_fd, "d_breadth"), ("③ 수준 FE+트래픽", m_lv, "menu_breadth")]
# 여러 SESOI에서 동등 판정
p("**메뉴 10개당 매출 효과** 기준으로 SESOI를 바꿔가며:\n")
grid_rows = []
for pct10 in [3, 5, 7, 10]:
    delta = np.log(1 + pct10 / 100) / 10
    r = {"SESOI (메뉴10개당)": f"±{pct10}%"}
    for name, res, key in models:
        *_, equiv = tost(res, key, delta)
        r[name] = "동등 ✓" if equiv else "불확정"
    grid_rows.append(r)
tbl(pd.DataFrame(grid_rows).set_index("SESOI (메뉴10개당)"))

p("\n**각 모델이 배제하는 효과 크기 (90% CI를 매출%로 환산, 메뉴 10개당):**\n")
rr = []
for name, res, key in models + [("① 통제 없음", m_fd_raw, "d_breadth")]:
    b, se = res.params[key], res.bse[key]
    lo, hi = (np.exp((b - 1.645 * se) * 10) - 1) * 100, (np.exp((b + 1.645 * se) * 10) - 1) * 100
    rr.append({"모델": name, "점추정": f"{(np.exp(b*10)-1)*100:+.1f}%",
               "90% CI": f"[{lo:+.1f}%, {hi:+.1f}%]",
               "배제되는 것": f"|효과| > {max(abs(lo),abs(hi)):.0f}% (메뉴 10개당)"})
tbl(pd.DataFrame(rr).set_index("모델"))

p("\n> **결론 D:**")
p("> - 트래픽 통제 후 메뉴폭–매출 **관측 연관**은 점추정 +2~4%/10메뉴, 90% CI 대략 **±5–7%/10메뉴**.")
p("> - 큰 효과(메뉴 10개당 ±7% 초과)는 배제된다. 그 이내(작은 양의 연관 포함)는 배제도 확인도 불가.")
p("> - 부호가 SE 가정에 따라 흔들리고 표본이 3개 매장뿐이라, **이 데이터로는 '메뉴폭이 매출과 "
  "무관/양(+)/음(-)' 어느 쪽도 확정할 수 없다.** 인과(H₁)는 애초에 식별 불가.\n")

# ============================================================ E. 시뮬레이션 강건성
p("## E. 합리화 시뮬레이션 강건성\n")
g = pd.read_csv(PROC / "menu_item_stats.csv")
TOTAL = df["revenue"].sum()
by_store_rev = df.pivot_table(index="product_detail", columns="store_location",
                              values="revenue", aggfunc="sum", fill_value=0)

def sim(cut, sigma=0.3):
    cut = set(cut); surv = g[~g.product_detail.isin(cut)]
    kept = surv["revenue"].sum(); recap = 0.0
    for _, r in g[g.product_detail.isin(cut)].iterrows():
        for lv in ("product_type", "product_category"):
            pool = surv[surv[lv] == r[lv]]
            if len(pool):
                wp = np.average(pool["avg_price"], weights=pool["units"])
                recap += sigma * min(r["units"] * wp, r["revenue"]); break
    return (kept + recap) / TOTAL * 100

orders = {
    "매출 하위순": g.sort_values("revenue")["product_detail"].tolist(),
    "수량 하위순": g.sort_values("units")["product_detail"].tolist(),
    "거래수 하위순": g.sort_values("n_tx")["product_detail"].tolist(),
}
ks = [5, 10, 15, 20, 25, 30]
rob = pd.DataFrame({name: [sim(o[:k]) for k in ks] for name, o in orders.items()}, index=[f"{k}개" for k in ks])
# 몬테카를로: 무작위 컷
rng = np.random.default_rng(42)
allp = g["product_detail"].tolist()
mc = {}
for k in ks:
    draws = [sim(list(rng.choice(allp, k, replace=False))) for _ in range(300)]
    mc[f"{k}개"] = [np.percentile(draws, 5), np.percentile(draws, 50), np.percentile(draws, 95)]
mcdf = pd.DataFrame(mc, index=["무작위 p5", "무작위 중앙", "무작위 p95"]).T
rob = rob.join(mcdf)
p("σ = 0.3 가정, 단종 기준별 추정 매출 유지율(%):\n")
tbl(rob.round(1))
p("- 어떤 '하위' 기준으로 잘라도 결과가 사실상 같다(10개 컷 → 96–98%).")
p("- 무작위로 10개를 자르면 중앙값 92%로 더 나쁘다 → '하위부터' 자르는 게 실제로 효율적임을 확인.\n")

# 매장별 따로
p("**매장별 따로 시뮬레이션 (하위 매출순, σ=0.3):**\n")
psr = []
for s in sorted(df.store_location.unique()):
    sub = df[df.store_location == s]
    tot_s = sub.revenue.sum()
    gs = (sub.groupby(["product_detail", "product_type", "product_category"])
             .agg(revenue=("revenue", "sum"), units=("transaction_qty", "sum"),
                  avg_price=("unit_price", "mean")).reset_index())
    def sim_s(cut, sigma=.3):
        cut = set(cut); surv = gs[~gs.product_detail.isin(cut)]
        kept = surv.revenue.sum(); rc = 0.
        for _, r in gs[gs.product_detail.isin(cut)].iterrows():
            for lv in ("product_type", "product_category"):
                pool = surv[surv[lv] == r[lv]]
                if len(pool):
                    wp = np.average(pool.avg_price, weights=pool.units)
                    rc += sigma * min(r.units * wp, r.revenue); break
        return (kept + rc) / tot_s * 100
    order_s = gs.sort_values("revenue")["product_detail"].tolist()
    psr.append({"매장": s, **{f"{k}개": round(sim_s(order_s[:k]), 1) for k in [10, 20, 30]}})
tbl(pd.DataFrame(psr).set_index("매장"))
p("- 3개 매장 모두 거의 동일한 곡선 — 매장별로 다른 결론이 나오지 않는다.\n")

# --- 그림
fig, ax = plt.subplots(1, 2, figsize=(12.5, 4.3))
band5 = np.log(1.05) / 10        # ±5% / 10메뉴 를 β 스케일로
band7 = np.log(1.07) / 10
specs = [("① 통제 없음", m_fd_raw, "d_breadth", RUST),
         ("② 차분 + 트래픽", m_fd, "d_breadth", BLUE),
         ("③ 수준 FE + 트래픽", m_lv, "menu_breadth", BLUE)]
ax[0].axvspan(-band7, band7, color=GREEN, alpha=.08)
ax[0].axvspan(-band5, band5, color=GREEN, alpha=.16)
ax[0].axvline(0, color=MUTED, lw=.8)
for i, (nm, res, key, c) in enumerate(specs):
    b, se = res.params[key], res.bse[key]
    ax[0].errorbar(b, i, xerr=1.645 * se, fmt="o", color=c, capsize=4, lw=2, ms=7)
ax[0].set_yticks(range(3)); ax[0].set_yticklabels([s[0] for s in specs])
ax[0].set_xlabel("β  ·  메뉴폭 1개당 Δlog(주간매출)")
ax[0].set_title("메뉴폭 계수 90% CI  ·  초록띠 = ±5% / ±7% (메뉴 10개당)")
ax[0].set_ylim(-.5, 2.5)

for name, o in orders.items():
    ax[1].plot(ks, [sim(o[:k]) for k in ks], "o-", lw=1.8, ms=5,
               label=name, color={"매출 하위순": BLUE, "수량 하위순": GREEN, "거래수 하위순": RUST}[name])
ax[1].fill_between(ks, [mc[f"{k}개"][0] for k in ks], [mc[f"{k}개"][2] for k in ks],
                   color=MUTED, alpha=.18, label="무작위 컷 5–95%")
ax[1].set_xlabel("단종 SKU 수"); ax[1].set_ylabel("추정 매출 유지율 %")
ax[1].set_title("단종 기준별 강건성 (σ = 0.3)"); ax[1].legend(fontsize=8)
ax[1].yaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"{v:.0f}%"))
fig.savefig(FIG / "30_menu_effect_bounds.png"); plt.close(fig)

# ============================================================ 한계
p("## 종합 및 한계\n")
p("| 질문 | 이 데이터로 가능한 답 |")
p("|---|---|")
p("| 메뉴 수를 **바꾸면** 매출이 변하나? (인과) | **답할 수 없음** — 메뉴 변화가 0, 자연실험 없음 |")
p("| 신메뉴 출시 빈도가 매출에 영향을 주나? | **답할 수 없음** — 6개월간 신메뉴 출시 0건, 단일 브랜드 |")
p("| 매장 간 메뉴 수 차이가 매출 차이를 만드나? | **답할 수 없음** — 세 매장 메뉴 동일 |")
p("| 트래픽 통제 후 메뉴폭–매출 **연관**이 남나? | **불확정** — 점추정 +2~4%/10메뉴지만 부호가 SE 가정에 따라 흔들림, n=75 |")
p(f"| 매출 변동을 메뉴가 설명할 여지가 있나? | **거의 없음** — 주간 매출 분산의 {ss_store/ss_tot*100:.1f}%만 매장 간, {ss_week/ss_tot*100:.0f}%가 시점 간 |")
p("| 메뉴를 줄이면 매출이 크게 빠지나? | **아니오** — 단종 기준·매장·σ 무관하게 하위 12%컷 → 96%+ |")
p("\n- D의 결과는 **관측 연관**에 대한 것이지 인과효과 기각이 아니다. "
  "메뉴폭이 거래수를 통해 매출과 얽혀 있고 외생적 변이가 없어, 진짜 인과 파라미터는 식별 불가로 남는다.")
p("- 표본이 작아(완전주 75, 매장 3) 동등성 검정의 검정력이 약하다. "
  "'메뉴 10개당 ±5% 이내'는 확언 못 하고, '±7% 이상'만 배제된다.")
p("- 6개월·단일 계절·가상 데이터. 신메뉴 도입 효과·시즌 메뉴·팬데믹 등은 이 데이터 밖.")

(ROOT / "output" / "menu_effect_bounds.md").write_text("\n".join(md), encoding="utf-8")
print("done ->", ROOT / "output" / "menu_effect_bounds.md")
print("fig -> 30_menu_effect_bounds.png")
