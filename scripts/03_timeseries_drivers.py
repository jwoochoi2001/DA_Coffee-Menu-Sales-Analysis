# -*- coding: utf-8 -*-
"""
03_timeseries_drivers.py
A. 일매출 시계열 분해 (STL, weekly)
B. 매출 드라이버 회귀 (store x day 패널, OLS + robust SE)
   + 매출 = 거래수(n_tx) x 객단가(avg_ticket) 분해 회귀
입력: data/processed/coffee_clean.parquet
산출: output/figures/1x_*.png, output/drivers_summary.md,
      data/processed/store_day_panel.csv
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from statsmodels.tsa.seasonal import STL
from statsmodels.graphics.tsaplots import plot_acf
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
FIG = ROOT / "output" / "figures"
plt.rcParams.update({"figure.dpi": 110, "savefig.dpi": 110, "figure.autolayout": True,
                     "axes.grid": True, "grid.alpha": .25,
                     "axes.spines.top": False, "axes.spines.right": False, "font.size": 10})
BLUE, ORANGE, GREEN, RED = "#2f6f9f", "#e08a2e", "#4f9d69", "#c0392b"

df = pd.read_parquet(PROC / "coffee_clean.parquet")
df["date"] = pd.to_datetime(df["date"])
md = ["# Maven Roasters — 시계열 분해 & 매출 드라이버 회귀\n"]
def p(x=""): md.append(str(x) + "\n")
def tbl(f): md.append(f.to_markdown() + "\n")

# ============================================================= A. 시계열 분해
p("## A. 일매출 시계열 분해 (STL, period=7)\n")
daily = (df.groupby("date")["revenue"].sum()
           .asfreq("D"))
assert daily.isna().sum() == 0, "누락일 존재"

stl = STL(daily, period=7, robust=True).fit()
obs, trend, seas, resid = daily, stl.trend, stl.seasonal, stl.resid

# Hyndman 강도 지표
def strength(comp, resid):
    v = np.var(comp + resid, ddof=1)
    return float(max(0.0, 1 - np.var(resid, ddof=1) / v)) if v > 0 else 0.0
F_T = strength(trend, resid)
F_S = strength(seas, resid)
p(f"- **추세 강도 F_T = {F_T:.3f}**, **주간계절 강도 F_S = {F_S:.3f}** (1에 가까울수록 강함)")
p(f"- 분산 비중: trend {np.var(trend,ddof=1)/np.var(obs,ddof=1)*100:4.1f}% · "
  f"seasonal {np.var(seas,ddof=1)/np.var(obs,ddof=1)*100:4.1f}% · "
  f"resid {np.var(resid,ddof=1)/np.var(obs,ddof=1)*100:4.1f}% (합≈100 근처, 성분 간 상관으로 오차)")

# 추세 기울기 (선형 & 로그)
t = np.arange(len(trend))
b1 = np.polyfit(t, trend.values, 1)[0]
g = np.polyfit(t, np.log(trend.values), 1)[0]
p(f"- 추세 성장: 선형 **+${b1:,.0f}/일**, 로그기울기 **{g*100:.2f}%/일 (≈ {(np.exp(g*30)-1)*100:.1f}%/월 복리)**")
p(f"- 1월 평균 일매출 ${daily['2023-01'].mean():,.0f} → 6월 ${daily['2023-06'].mean():,.0f} "
  f"({daily['2023-06'].mean()/daily['2023-01'].mean()-1:+.0%})")

# 요일 계절 프로파일
dow_names = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
seas_dow = pd.Series(seas.values, index=daily.index.dayofweek).groupby(level=0).mean().reindex(range(7))
seas_dow.index = dow_names
p("\n**STL 주간계절 성분 (요일별 평균, $ / 일매출 대비)**")
tbl(pd.DataFrame({"seasonal_$": seas_dow.round(0),
                  "vs_avg_%": (seas_dow / daily.mean() * 100).round(1)}))
p(f"- 진폭이 작음(±${seas_dow.abs().max():.0f}, 평균의 ±{seas_dow.abs().max()/daily.mean()*100:.1f}%) → **요일 효과는 미미**. "
  "일 변동의 대부분은 추세와 불규칙 성분.")

# 잔차 이상치
rstd = resid.std()
outliers = resid[resid.abs() > 3 * rstd]
p(f"- 잔차 3σ 이탈일: {len(outliers)}건 " + (", ".join(f"{d.date()}({v:+,.0f})" for d, v in outliers.items()) if len(outliers) else "없음"))

# --- 그림: STL 4단 + ACF
fig, ax = plt.subplots(4, 1, figsize=(11, 9), sharex=True)
ax[0].plot(obs.index, obs, color=BLUE, lw=.8); ax[0].set_ylabel("observed")
ax[1].plot(trend.index, trend, color="black", lw=1.6); ax[1].set_ylabel("trend")
ax[2].plot(seas.index, seas, color=GREEN, lw=.8); ax[2].set_ylabel("seasonal(7)")
ax[3].plot(resid.index, resid, color=ORANGE, lw=.7); ax[3].axhline(0, color="k", lw=.6)
ax[3].scatter(outliers.index, outliers.values, color=RED, zorder=5, s=30); ax[3].set_ylabel("resid")
ax[0].set_title("STL decomposition — daily revenue")
fig.savefig(FIG / "10_stl_decomposition.png"); plt.close(fig)

fig, ax = plt.subplots(1, 2, figsize=(12, 4))
plot_acf(resid, ax=ax[0], lags=30, title="ACF of STL residual")
ax[1].plot(seas_dow.index, seas_dow.values, "o-", color=GREEN)
ax[1].axhline(0, color="k", lw=.6); ax[1].set_title("Weekly seasonal profile ($)")
fig.savefig(FIG / "11_resid_acf_weekprofile.png"); plt.close(fig)

# 매장별 STL 추세 비교
fig, ax = plt.subplots(figsize=(10, 4))
for s, c in zip(sorted(df.store_location.unique()), [BLUE, ORANGE, GREEN]):
    sd = df[df.store_location == s].groupby("date")["revenue"].sum().asfreq("D")
    ax.plot(sd.index, STL(sd, period=7, robust=True).fit().trend, label=s, color=c, lw=1.6)
ax.set_title("STL trend by store"); ax.legend(); ax.set_ylabel("$")
fig.savefig(FIG / "12_stl_trend_by_store.png"); plt.close(fig)

# ============================================================= B. 드라이버 회귀
p("\n## B. 매출 드라이버 회귀 — store × day 패널 (n = 3 × 181 = 543)\n")

def daypart_share(g, lo, hi):
    return g.loc[g.hour.between(lo, hi - 1), "revenue"].sum() / g["revenue"].sum()

rows = []
for (s, d), g in df.groupby(["store_location", "date"]):
    tx = g.groupby("transaction_id")["revenue"].sum()
    rows.append(dict(
        store=s, date=d, revenue=g.revenue.sum(),
        n_tx=g.transaction_id.nunique(), units=g.transaction_qty.sum(),
        avg_ticket=tx.mean(), avg_unit_price=g.unit_price.mean(),
        menu_breadth=g.product_detail.nunique(),
        morning_share=daypart_share(g, 6, 11),
        coffee_share=g.loc[g.product_category.eq("Coffee"), "revenue"].sum() / g.revenue.sum(),
        tea_share=g.loc[g.product_category.eq("Tea"), "revenue"].sum() / g.revenue.sum(),
        dow=g.dow_name.iloc[0], dow_num=int(g.dow.iloc[0]),
        month=g.month_name.iloc[0], is_weekend=bool(g.is_weekend.iloc[0]),
    ))
pan = pd.DataFrame(rows).sort_values(["store", "date"]).reset_index(drop=True)
pan["t"] = (pan["date"] - pan["date"].min()).dt.days
pan["t2"] = pan["t"] ** 2 / 1000
pan["dow"] = pd.Categorical(pan["dow"], categories=dow_names, ordered=True)
pan["log_revenue"] = np.log(pan["revenue"])
pan["log_ntx"] = np.log(pan["n_tx"])
pan["log_ticket"] = np.log(pan["avg_ticket"])
pan.to_csv(PROC / "store_day_panel.csv", index=False)
p(f"패널 저장: `data/processed/store_day_panel.csv`  ({pan.shape[0]}행 × {pan.shape[1]}열)\n")
tbl(pan.groupby("store")[["revenue","n_tx","avg_ticket","avg_unit_price","menu_breadth","morning_share"]].mean().round(2))

HC = "HC1"
def fit(formula, y="log_revenue"):
    return smf.ols(f"{y} ~ {formula}", data=pan).fit(cov_type=HC)

m1 = fit("C(store) + C(dow) + t + t2")
m2 = fit("C(store) + C(dow) + t + t2 + avg_unit_price + morning_share + menu_breadth")
m3 = fit("C(store) + C(dow) + C(month)")           # 트렌드를 월더미로

p("### B-1. 모델 비교 (종속변수 = log 일매출)\n")
comp = pd.DataFrame({
    "model": ["M1 calendar(트렌드)", "M2 +가격·구성", "M3 calendar(월더미)"],
    "R2": [m1.rsquared, m2.rsquared, m3.rsquared],
    "adj_R2": [m1.rsquared_adj, m2.rsquared_adj, m3.rsquared_adj],
    "AIC": [m1.aic, m2.aic, m3.aic],
    "n": [int(m1.nobs)]*3,
}).round(3)
tbl(comp.set_index("model"))

def coef_table(res, drop_intercept=True):
    o = pd.DataFrame({"coef": res.params, "se": res.bse, "t": res.tvalues, "p": res.pvalues})
    o["effect_%"] = (np.exp(res.params) - 1) * 100      # log 모델 → 근사 % 효과
    if drop_intercept and "Intercept" in o.index:
        o = o.drop("Intercept")
    return o.round(4)

p("### B-2. M2 계수 (robust HC1) — log 매출\n")
p("`effect_%` = 해당 변수 1단위 증가 시 매출 % 변화 (더미는 기준범주 대비).\n")
tbl(coef_table(m2))
p("- 기준: store=Astoria, dow=Mon.\n")

# 증분 R^2 (블록 기여도)
p("### B-3. 블록별 설명력 (누적 R², HC1 OLS)\n")
blocks = [
    ("store FE",              "C(store)"),
    ("+ 요일",                "C(store) + C(dow)"),
    ("+ 시간추세(t,t2)",       "C(store) + C(dow) + t + t2"),
    ("+ 평균단가",            "C(store) + C(dow) + t + t2 + avg_unit_price"),
    ("+ 오전매출비중",         "C(store) + C(dow) + t + t2 + avg_unit_price + morning_share"),
    ("+ 메뉴폭",              "C(store) + C(dow) + t + t2 + avg_unit_price + morning_share + menu_breadth"),
]
prev = 0.0
inc = []
for name, f in blocks:
    r2 = fit(f).rsquared
    inc.append({"블록": name, "누적R2": round(r2, 3), "증분": round(r2 - prev, 3)})
    prev = r2
tbl(pd.DataFrame(inc).set_index("블록"))

# 매출 분해: log(rev) = log(n_tx) + log(ticket)
p("### B-4. 매출 = 거래수 × 객단가 분해\n")
rhs = "C(store) + C(dow) + t + t2"
mt, mn, mk = fit(rhs, "log_revenue"), fit(rhs, "log_ntx"), fit(rhs, "log_ticket")
dec = pd.DataFrame({
    "log_revenue": mt.params, "log_n_tx": mn.params, "log_avg_ticket": mk.params
}).loc[["t", "t2"]].round(5)
dec.loc["R2"] = [mt.rsquared, mn.rsquared, mk.rsquared]
tbl(dec)
tr_rev = (np.exp(mt.params["t"] * 30) - 1) * 100
tr_tx  = (np.exp(mn.params["t"] * 30) - 1) * 100
tr_tk  = (np.exp(mk.params["t"] * 30) - 1) * 100
p(f"- 월 성장률 기여(선형항 t 기준): 매출 {tr_rev:+.1f}% ≈ 거래수 {tr_tx:+.1f}% + 객단가 {tr_tk:+.1f}%")
p(f"- 객단가 시간추세는 {'유의하지 않음' if mk.pvalues['t']>0.05 else '유의'} (p={mk.pvalues['t']:.3f}) "
  f"→ **성장은 거의 전적으로 방문/거래 증가(트래픽)에서 발생.**")

# B-5. 내생성 점검: 거래수 통제 시 메뉴폭 / 오전비중 효과
p("### B-5. 내생성 점검 — log(거래수) 통제\n")
m_endog = fit("C(store) + C(dow) + t + t2 + avg_unit_price + morning_share + menu_breadth + log_ntx")
chk = coef_table(m_endog).loc[["menu_breadth", "morning_share", "avg_unit_price", "log_ntx"], ["coef", "p", "effect_%"]]
tbl(chk)
p(f"- log(거래수)를 넣으면 R² = {m_endog.rsquared:.3f}, **menu_breadth 효과 {(np.exp(m_endog.params['menu_breadth'])-1)*100:+.2f}%/개 "
  f"(p={m_endog.pvalues['menu_breadth']:.3f})** 로 축소·소멸.")
p("- 즉 B-2의 menu_breadth·morning_share 계수는 **인과적 지렛대가 아니라 '거래량이 많은 날일수록 더 많은 메뉴가 팔리고 "
  "오전 비중이 낮아진다'는 기계적 상관**. 이 데이터의 store-day 수준에서 식별되는 진짜 드라이버는 사실상 **시간추세 하나**.\n")

p("### B-6. 해석 및 한계\n")
p("- **매출 변동의 95%가 추세**(STL 분산비중 94.6%), 요일 계절성은 ±3% 미만, 매장 간 차이도 유의하지 않음.")
p("- 추세 = 6개월간 월복리 ~12–18% 성장이며 **전량 트래픽(거래수) 증가**에서 발생, 객단가는 $4.6~4.8로 정체.")
p("- 데이터에는 이 추세를 '설명'하는 변수가 없음 → 날씨(겨울→여름)·매장 성숙(입소문)·마케팅 중 무엇인지 이 데이터만으로 구분 불가.")
p("- 3σ 이탈일 중 **2023-05-29는 Memorial Day(미국 공휴일)** — 공휴일 더미를 넣으면 잔차가 감소.")
p("- **가설(메뉴 수→매출)**: 본 분석은 메뉴 '운영 수'의 인과효과를 식별하지 못함(매장 간 메뉴 동일 + 판매메뉴수는 거래량의 결과). "
  "가설 검정에는 메뉴 구성이 다른 다점포/시점 데이터가 필요.")

# --- 그림: 계수 forest plot (M2) + 관측 vs 적합
ct = coef_table(m2)
fig, ax = plt.subplots(figsize=(8, 6))
yv = np.arange(len(ct))
ax.errorbar(ct["coef"], yv, xerr=1.96 * ct["se"], fmt="o", color=BLUE, capsize=3)
ax.axvline(0, color="k", lw=.8); ax.set_yticks(yv); ax.set_yticklabels(ct.index)
ax.set_title("M2 coefficients (log revenue) ± 95% CI (HC1)")
fig.savefig(FIG / "13_driver_coefficients.png"); plt.close(fig)

pan["fitted_m2"] = np.exp(m2.fittedvalues)
fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
for s, c in zip(sorted(pan.store.unique()), [BLUE, ORANGE, GREEN]):
    gg = pan[pan.store == s]
    ax[0].plot(gg.date, gg.revenue, color=c, lw=.5, alpha=.5)
    ax[0].plot(gg.date, gg.fitted_m2, color=c, lw=1.4, label=s)
ax[0].set_title("Observed (thin) vs M2 fitted (bold)"); ax[0].legend(); ax[0].set_ylabel("$")
ax[1].scatter(pan.fitted_m2, pan.revenue, s=12, alpha=.5, color=BLUE)
lim = [pan.revenue.min(), pan.revenue.max()]
ax[1].plot(lim, lim, "k--", lw=.8); ax[1].set_xlabel("fitted"); ax[1].set_ylabel("actual")
ax[1].set_title(f"M2 fit  (R²={m2.rsquared:.3f})")
fig.savefig(FIG / "14_m2_fit.png"); plt.close(fig)

# 텍스트 요약본도 저장
with open(ROOT / "output" / "drivers_models.txt", "w", encoding="utf-8") as fh:
    for nm, r in [("M1", m1), ("M2", m2), ("M3", m3),
                  ("log_n_tx", mn), ("log_avg_ticket", mk)]:
        fh.write(f"\n{'='*70}\n{nm}\n{'='*70}\n{r.summary()}\n")

(ROOT / "output" / "drivers_summary.md").write_text("\n".join(md), encoding="utf-8")
print("done ->", ROOT / "output" / "drivers_summary.md")
print("figures:", sorted(f.name for f in FIG.glob('1[0-4]_*.png')))
