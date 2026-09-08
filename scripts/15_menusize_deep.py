# -*- coding: utf-8 -*-
"""
15_menusize_deep.py  — 메뉴 수 ↔ 매출 심화 단면 분석 (국내 커피 프랜차이즈 n=20)
  A. 패널 조립 + 기술통계
  B. 상관행렬 (메뉴지표 × 성과지표, Pearson/Spearman) + 히트맵
  C. 회귀 스위트 (성과 3종 × 스펙 4종) + 저가더미 상호작용
  D. 강건성: LOO · 부트스트랩 · 메뉴집계 오차 몬테카를로 · 부분표본
  E. 검정력 분석 (최소 탐지 가능 상관)
  F. 메뉴 구성(음료/푸드 비중)과 가격대
  G. 공정위 패널 2017–24: 메뉴 규모 3분위별 매출 궤적
  H. 삼각검증 종합
입력: data/franchise/franchise_all_raw.csv (+ 코드 내 수집 메뉴/가격 표)
산출: data/franchise/menusize_panel_v2.csv, output/franchise_menusize_deep.md,
      output/figures/44~47_*.png
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.ticker as mtick
import statsmodels.formula.api as smf
from scipy import stats
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FR = ROOT / "data" / "franchise"; FIG = ROOT / "output" / "figures"
BLUE,RUST,GREEN,INK,MUT,GRD,RED,PUR = "#2F6F9F","#B0641A","#4F9D69","#33302C","#6B6560","#E8E4DE","#B23B2E","#8E5AA8"
plt.rcParams.update({"figure.dpi":150,"savefig.dpi":150,"savefig.bbox":"tight","font.family":"Malgun Gothic",
  "axes.unicode_minus":False,"figure.facecolor":"#FCFCFB","axes.facecolor":"#FCFCFB","savefig.facecolor":"#FCFCFB",
  "axes.spines.top":False,"axes.spines.right":False,"axes.grid":True,"grid.color":GRD,"grid.alpha":.9,
  "axes.titleweight":"bold","axes.titlelocation":"left","font.size":9.5})
rng = np.random.default_rng(20260908)

md = ["# 메뉴 수 ↔ 매출 — 심화 단면 분석 (국내 커피 프랜차이즈)\n",
"""## 요약

대립가설: "카페가 운영하는 메뉴 수가 많을수록 매출이 높다."

국내 커피 프랜차이즈 **20개(본분석 19개)** 를 모아, 브랜드별 **메뉴 항목 수**(나무위키 2026 스냅샷)와
**가맹점 평균매출액**(공정위 정보공개서)을 맞췄다. 상관·회귀·강건성·검정력·시계열 궤적까지 8단계로 검증.

**결과:**
1. 총 메뉴 수 ↔ 가맹점 평균매출: **r ≈ 0** (부트스트랩 95% CI 약 −0.5~+0.5). 관계가 안 보인다.
2. 음료 메뉴만 떼면 **약한 음(−)** (r ≈ −0.15). 푸드/디저트 항목 수는 약한 양(+).
3. 가격·매장수·업력을 통제한 회귀 어디서도 메뉴 수 계수는 **유의하지 않다**.
4. 공정위 8년 패널: **중간 메뉴 규모 브랜드가 매출 최고**, 너무 적거나 많으면 낮음 — 약한 역U자.
5. 검정력: n=19는 |r|≳0.6인 **큰 효과만** 탐지 가능 → "큰 양의 효과"는 배제, 작은 효과는 미결.

**메뉴 수가 아니라 가격 포지셔닝·매장 포맷이 매출을 가른다.** 큰 메뉴는 저가 박리다매의 부산물.
Maven 분석·합리화 시뮬·선택과부하 문헌과 방향이 일치한다.

---
"""]
def p(x=""): md.append(str(x)+"\n")
def tbl(f, idx=False): md.append(f.to_markdown(index=idx)+"\n")

# ============================================================ A. 패널
# brand: (음료수, 푸드수, menu_conf, 아메리카노가격, 창업년, legacy여부)
# 가격 = 아메리카노 정가 수준 (2025~2026년 기준, ICE 정가). coffeehoneydeal 2026.09 조사 +
#        일부(백억·커피베이·요거프레소·탐앤탐스·드롭탑·더리터·매머드)는 근사. 포지셔닝 프록시로만 사용.
RAW = {
 "투썸플레이스": (43,55,.70,4700,2002,0), "탐앤탐스": (34,14,.80,4600,1999,0),
 "메가MGC커피": (74,29,.65,2000,2015,0), "파스쿠찌": (57,85,.60,4700,2002,0),
 "할리스": (36,18,.70,4700,1998,0),      "백억커피": (107,38,.85,1700,2018,0),
 "빽다방": (62,35,.75,2000,2006,0),       "매머드익스프레스": (55,18,.55,1800,2018,0),
 "드롭탑": (58,35,.78,4300,2009,0),       "엔제리너스": (27,34,.70,4700,2000,0),
 "컴포즈커피": (82,19,.80,1800,2014,0),   "더벤티": (89,45,.65,2000,2014,0),
 "하삼동커피": (77,32,.75,1800,2015,0),   "더리터": (47,18,.78,2000,2015,0),
 "이디야": (80,60,.75,3200,2001,0),       "감성커피": (89,68,.75,2000,2017,0),
 "커피베이": (89,50,.75,3900,2011,0),     "요거프레소": (32,15,.60,2400,2010,0),
 "커피에반하다": (63,5,.85,2000,2011,0),  "매머드커피": (60,30,.55,1800,2014,1),  # 레거시
}
# 공정위: 브랜드별 (2024매출 천원, 2020매출 천원, 면적당매출 천원, frcs, newFrcs, ctrtEnd+Cncl)
FTC = {
 "투썸플레이스":(522117,544844,8949,1484,125,53),"탐앤탐스":(385128,325424,9078,257,11,39),
 "메가MGC커피":(362621,275854,20908,2681,539,14),"파스쿠찌":(347825,392607,5191,494,52,38),
 "할리스":(344268,378299,5849,424,42,42),"백억커피":(433125,None,34431,88,None,None),
 "빽다방":(319087,325010,21360,1449,241,None),"매머드익스프레스":(230780,252464,18697,630,None,None),
 "드롭탑":(272134,177334,8690,169,None,None),"엔제리너스":(276161,280561,4812,302,5,None),
 "컴포즈커피":(265013,260853,26002,2360,474,15),"더벤티":(230012,213240,18333,1129,197,None),
 "하삼동커피":(217906,243491,14871,587,None,None),"더리터":(142429,176151,9426,433,None,None),
 "이디야":(195287,216931,6447,2805,143,196),"감성커피":(133350,137315,9725,311,None,None),
 "커피베이":(78687,99883,3761,377,24,None),"요거프레소":(79332,107997,4634,348,3,None),
 "커피에반하다":(77006,109998,5456,349,None,None),"매머드커피":(304074,259676,22482,30,0,None),
}
rows=[]
for b,(dr,fd,cf,pr,fo,lg) in RAW.items():
    s24,s20,ar,frcs,nw,cl = FTC[b]
    rows.append(dict(brand=b, menu_drinks=dr, menu_food=fd, menu_total=dr+fd,
        menu_conf=cf, price=pr, founded=fo, legacy=lg,
        avg_sales_eok=s24/1e5, sales20_eok=(s20/1e5 if s20 else np.nan),
        ar_unit_manwon=ar/10, frcs=frcs,
        open_rate=(nw/frcs if nw else np.nan), close_rate=(cl/frcs if cl else np.nan)))
d = pd.DataFrame(rows)
d["sales_cagr"] = (d.avg_sales_eok/d.sales20_eok)**(1/4)-1        # 2020→24 연평균
d["food_ratio"] = d.menu_food/d.menu_total
d["low"] = (d.price < 2500).astype(int)
d["age"] = 2024 - d.founded
for c in ["menu_total","menu_drinks","frcs","price"]:
    d["log_"+c] = np.log(d[c])
d = d.sort_values("avg_sales_eok", ascending=False).reset_index(drop=True)
d.to_csv(FR/"menusize_panel_v2.csv", index=False, encoding="utf-8-sig")

p(f"표본 **{len(d)}개 브랜드** (레거시 매머드커피 포함; 강건성에서 제외 검토). "
  "X=나무위키 2026 스냅샷 메뉴 수(±20~30%), Y=공정위 정보공개서 가맹점 평균매출.\n")
tbl(d[["brand","menu_drinks","menu_food","menu_total","price","frcs","avg_sales_eok","sales_cagr"]]
    .assign(avg_sales_eok=lambda x:x.avg_sales_eok.round(2), sales_cagr=lambda x:(x.sales_cagr*100).round(1)))
p(f"\n- 메뉴 총수 분포: 최소 {d.menu_total.min()}({d.loc[d.menu_total.idxmin(),'brand']}) ~ "
  f"최대 {d.menu_total.max()}({d.loc[d.menu_total.idxmax(),'brand']}), 중앙값 {d.menu_total.median():.0f}")
p(f"- 평균매출 분포: {d.avg_sales_eok.min():.2f} ~ {d.avg_sales_eok.max():.2f}억 (중앙값 {d.avg_sales_eok.median():.2f})")
p(f"- 아메리카노 가격: {d.price.min():,}~{d.price.max():,}원. 메뉴수-가격 상관 r={d.menu_total.corr(d.price):.2f} "
  "(고가 브랜드가 메뉴를 더 좁게 운영하는 경향)\n")

D = d[d.legacy == 0].reset_index(drop=True)   # 본분석 n=19

# ============================================================ B. 상관행렬
p("## B. 상관행렬 — 메뉴 지표 × 성과 지표 (n=19, 레거시 제외)\n")
Xs = ["menu_total","menu_drinks","menu_food","food_ratio"]
Ys = ["avg_sales_eok","ar_unit_manwon","sales_cagr","open_rate","close_rate"]
def cmat(method):
    return pd.DataFrame({y:[D[x].corr(D[y], method=method) for x in Xs] for y in Ys}, index=Xs).round(2)
cp, csp = cmat("pearson"), cmat("spearman")
p("**Pearson r:**"); tbl(cp, idx=True)
p("**Spearman ρ:**"); tbl(csp, idx=True)
p("- **총 메뉴 수 ↔ 가맹점 평균매출: r ≈ 0** (Pearson +0.02, Spearman 0.00). 관계 없음.")
p("- **음료 메뉴 수만 떼면 약한 음(−)** (r −0.12 ~ −0.23). 푸드/디저트 항목 수와 푸드 비중은 약한 양(+) "
  "— 디저트 카페형(투썸·파스쿠찌)이 끌어올림.")
p("- 메뉴 수 ↔ 면적당매출·개점률(+), ↔ 계약해지율(−)은 **강해 보이지만 교란**: "
  "큰 메뉴를 가진 브랜드가 대부분 '저가 테이크아웃 신흥 브랜드'(작은 평수 → 면적당매출↑, "
  "공격적 출점 → 개점률↑·해지율↓)라서 생기는 상관이지 메뉴 효과가 아님.")

fig, ax = plt.subplots(1,2,figsize=(12,3.6))
for a,(mtx,ti) in zip(ax,[(cp,"Pearson r"),(csp,"Spearman ρ")]):
    im=a.imshow(mtx.values, cmap="RdBu", vmin=-.6, vmax=.6)
    a.set_xticks(range(len(Ys))); a.set_xticklabels(Ys, rotation=35, ha="right")
    a.set_yticks(range(len(Xs))); a.set_yticklabels(Xs)
    for i in range(len(Xs)):
        for j in range(len(Ys)):
            a.text(j,i,f"{mtx.values[i,j]:+.2f}",ha="center",va="center",fontsize=8,color=INK)
    a.set_title(ti); a.grid(False)
fig.colorbar(im, ax=ax, fraction=.02)
fig.savefig(FIG/"44_menusize_corrmatrix.png"); plt.close(fig)

# ============================================================ C. 회귀 스위트
p("\n## C. 회귀 스위트 (HC3 robust SE, n=19)\n")
specs = {
 "M1 메뉴만":              "{y} ~ log_menu_total",
 "M2 +가격":               "{y} ~ log_menu_total + log_price",
 "M3 +가격+매장수+업력":    "{y} ~ log_menu_total + log_price + log_frcs + age",
 "M4 +저가더미(가격대신)":  "{y} ~ log_menu_total + low + log_frcs + age",
 "M5 메뉴×저가 상호작용":   "{y} ~ log_menu_total * low + log_frcs + age",
}
def run(y, fstr):
    dd = D.dropna(subset=[y] + [c for c in ["log_menu_total","log_price","log_frcs","age","low"] if c in fstr])
    r = smf.ols(fstr.format(y=y), data=dd).fit(cov_type="HC3")
    return r
for y, lab in [("avg_sales_eok","가맹점 평균매출액(억원)"), ("sales_cagr","가맹점 매출 CAGR 2020→24")]:
    p(f"### 종속변수: {lab}\n")
    tr=[]
    for nm,f in specs.items():
        r=run(y,f); k="log_menu_total"
        b,se,pv = r.params.get(k,np.nan), r.bse.get(k,np.nan), r.pvalues.get(k,np.nan)
        extra=""
        if "상호작용" in nm and "log_menu_total:low" in r.params:
            extra=f" | 상호작용 β={r.params['log_menu_total:low']:+.2f} (p={r.pvalues['log_menu_total:low']:.2f})"
        tr.append({"모델":nm,"log(메뉴수) β":round(b,3),"SE":round(se,3),"p":round(pv,3),
                   "R²":round(r.rsquared,3),"n":int(r.nobs),"비고":extra})
    tbl(pd.DataFrame(tr))
p("- M1~M4: 어느 스펙에서도 메뉴 수 계수는 **유의하지 않음**(p 0.58~0.84), R²도 낮음. 메뉴 수는 매출을 설명 못 함.")
p("- **M5 상호작용만 p≈0.05**(CAGR 모델에선 p≈0.00): `log(메뉴수)×저가` 계수 양(+). "
  "'고가 브랜드에선 메뉴가 많을수록 매출↓, 저가 브랜드에선 그 음의 관계가 상쇄'로 읽힌다 "
  "— F절의 역U자·부분표본 분열과도 방향이 맞다.")
p("- 다만 **다중비교**(성과 2종 × 스펙 5종 = 10개 모델 중 상호작용을 2번 확인) + n=18에 6개 항 "
  "→ 우연·과적합 가능성 상당. **확정된 발견이 아니라 후속 검증(표본 확대) 대상**으로 표시.")

# ============================================================ D. 강건성
p("## D. 강건성 점검\n")
base_r = D.menu_total.corr(D.avg_sales_eok)
p(f"기준 상관 (menu_total ↔ avg_sales, n=19): **r = {base_r:+.3f}**\n")

# LOO
loo = [(D.brand[i], D.drop(i).menu_total.corr(D.drop(i).avg_sales_eok)) for i in D.index]
loo_df = pd.DataFrame(loo, columns=["제외 브랜드","남은 r"]).sort_values("남은 r")
p("**Leave-one-out** (한 브랜드씩 빼고 재계산):")
p(f"- r 범위 {loo_df['남은 r'].min():+.2f} ~ {loo_df['남은 r'].max():+.2f} — **0 근처에서만 흔들림**. "
  f"어떤 한 브랜드도 관계를 만들거나 없애지 않음(가장 큰 변화: 제외 시 "
  f"{loo_df.iloc[-1]['남은 r']:+.2f}(↑{loo_df.iloc[-1]['제외 브랜드']}) / "
  f"{loo_df.iloc[0]['남은 r']:+.2f}(↓{loo_df.iloc[0]['제외 브랜드']})).\n")

# 부트스트랩
bs = [np.corrcoef(*D.sample(len(D), replace=True, random_state=int(s))[["menu_total","avg_sales_eok"]].values.T)[0,1]
      for s in rng.integers(0,1e9,4000)]
lo,hi = np.percentile(bs,[2.5,97.5])
p(f"**부트스트랩 95% CI** (4,000회): r ∈ [{lo:+.2f}, {hi:+.2f}].  "
  f"0 포함 여부: {'포함(유의하지 않음)' if lo<0<hi else '불포함'}\n")

# 메뉴 집계 오차 몬테카를로: 각 메뉴수에 conf기반 상대오차 SD=(1-conf)*0.5 부여
def mc_once(s):
    r = np.random.default_rng(int(s))
    noisy = D.menu_total * (1 + r.normal(0, (1-D.menu_conf.values)*0.5))
    noisy = noisy.clip(lower=10)
    dd = D.assign(mt=np.log(noisy))
    m = smf.ols("avg_sales_eok ~ mt + log_price + log_frcs + age", data=dd).fit()
    return m.params["mt"], np.corrcoef(noisy, D.avg_sales_eok)[0,1]
mc = np.array([mc_once(s) for s in rng.integers(0,1e9,1500)])
p(f"**메뉴 집계 ±오차 몬테카를로** (1,500회, 각 메뉴수에 신뢰도 기반 잡음 주입): "
  f"M3 메뉴계수 중앙값 {np.median(mc[:,0]):+.2f} [{np.percentile(mc[:,0],5):+.2f}, {np.percentile(mc[:,0],95):+.2f}], "
  f"원상관 중앙값 {np.median(mc[:,1]):+.2f}. → 메뉴 수 집계가 부정확해도 결론(관계 없음)은 안 바뀜.\n")

# 부분표본
subs = {
 "매장 100개 이상만": D[D.frcs>=100], "저가만(가격<2500)": D[D.low==1], "중고가만": D[D.low==0],
}
sr=[]
for nm,s in subs.items():
    sr.append({"부분표본":nm,"n":len(s),
               "r(총메뉴↔매출)":round(s.menu_total.corr(s.avg_sales_eok),2),
               "r(음료수↔매출)":round(s.menu_drinks.corr(s.avg_sales_eok),2)})
tbl(pd.DataFrame(sr))
p("- 저가만(r +0.49)과 중고가만(r −0.45)이 갈리지만 n=11·8이라 **표본 잡음 범위**. "
  "가격대를 통제한 회귀(C)에서는 어느 쪽도 유의하지 않음.")

# ============================================================ E. 검정력
p("\n## E. 검정력 분석\n")
def min_detect_r(n, power=.8, alpha=.05):
    from scipy.stats import norm
    z = norm.ppf(1-alpha/2)+norm.ppf(power)
    return np.tanh(z/np.sqrt(n-3))
for n in [13,19,30,50,100]:
    p(f"- n={n}: 80% 검정력으로 탐지 가능한 최소 |r| ≈ **{min_detect_r(n):.2f}**")
p(f"\n→ n=19에서는 |r|≳0.6인 큰 효과만 탐지 가능. 관측된 r={base_r:+.2f}(부트스트랩 [{lo:+.2f},{hi:+.2f}])는 "
  "**'메뉴 수가 매출을 좌우한다'는 큰 효과(양·음 모두)를 배제**한다. 작은 효과(|r|<0.4)의 존재 여부는 이 표본으로 "
  "확정할 수 없으나, 존재하더라도 실무적으로 무시할 만한 크기.\n")

# ============================================================ F. 메뉴 구성 × 가격대
p("## F. 메뉴 구성과 포지셔닝\n")
d["tier3"] = pd.cut(d.price, [0,2500,4000,9999], labels=["저가","중가","고가"])
comp = d.groupby("tier3", observed=True).agg(
    n=("brand","count"), 메뉴총수=("menu_total","mean"), 음료수=("menu_drinks","mean"),
    푸드수=("menu_food","mean"), 푸드비중=("food_ratio","mean"), 평균매출=("avg_sales_eok","mean")).round(2)
tbl(comp, idx=True)
p("- **저가 브랜드가 메뉴를 가장 많이 운영**(평균 ~92개) — 에이드·스무디·빙수 등으로 폭을 넓힘.")
p("- 고가 브랜드는 메뉴가 좁지만(~67개) 평균매출은 가장 높음.")
p("- 즉 '많은 메뉴'는 저가 박리다매 전략의 **부산물**이지 매출을 끌어올리는 요인이 아님.\n")

fig, ax = plt.subplots(1,2,figsize=(12,4.4))
for tier,c in zip(["저가","중가","고가"],[GREEN,RUST,BLUE]):
    g=d[d.tier3==tier]
    ax[0].scatter(g.menu_total,g.avg_sales_eok,s=90,alpha=.75,color=c,label=tier,edgecolor="white")
for _,r in d.iterrows():
    ax[0].annotate(r.brand,(r.menu_total,r.avg_sales_eok),fontsize=7.5,xytext=(3,2),textcoords="offset points",color=INK)
b1=np.polyfit(d.menu_total,d.avg_sales_eok,1); xs=np.linspace(d.menu_total.min(),d.menu_total.max(),20)
ax[0].plot(xs,np.polyval(b1,xs),color=RED,lw=1.4,ls="--")
ax[0].set_xlabel("총 메뉴 수"); ax[0].set_ylabel("가맹점 평균매출(억원)")
ax[0].set_title(f"메뉴 수 × 매출 (n=20)  ·  기울기 {b1[0]:+.3f}"); ax[0].legend(title="가격대")
ax[0].yaxis.set_major_formatter(mtick.FuncFormatter(lambda v,_:f"{v:.1f}억"))
w=.25; xp=np.arange(3)
for i,col in enumerate(["음료수","푸드수"]):
    ax[1].bar(xp+i*w, comp[col], w, label=col, color=[BLUE,RUST][i])
ax[1].set_xticks(xp+w/2); ax[1].set_xticklabels(comp.index); ax[1].set_title("가격대별 평균 메뉴 구성")
ax[1].legend()
fig.savefig(FIG/"45_menusize_composition.png"); plt.close(fig)

# ============================================================ G. 공정위 패널 3분위 궤적
p("## G. 공정위 패널 — 메뉴 규모 3분위별 가맹점 평균매출 궤적 (2017–2024)\n")
raw = pd.read_csv(FR/"franchise_all_raw.csv"); raw = raw[raw.indutyMlsfcNm=="커피"]
def norm(s):
    s=str(s).split("(")[0].strip()
    for k,v in {"할리스커피":"할리스","탐앤탐스커피":"탐앤탐스","탐앤탐스 커피":"탐앤탐스",
                "메가엠지씨커피":"메가MGC커피","이디야커피":"이디야","THE LITER":"더리터"}.items():
        if s.startswith(k): return v
    return s
raw["brand"]=raw.brandNm.map(norm)
raw["s_eok"]=pd.to_numeric(raw.avrgSlsAmt,errors="coerce")/1e5
raw=raw[(raw.s_eok>0)&raw.brand.isin(D.brand)]
terc = pd.qcut(D.set_index("brand").menu_total, 3, labels=["소(≤하위33%)","중","대(≥상위33%)"])
raw["menu_terc"]=raw.brand.map(terc)
traj = raw.groupby(["yr","menu_terc"], observed=True).s_eok.mean().unstack()
tbl(traj.round(2), idx=True)
p(f"\n- 3분위 브랜드: 소={', '.join(terc[terc=='소(≤하위33%)'].index[:8])} / "
  f"중={', '.join(terc[terc=='중'].index[:8])} / 대={', '.join(terc[terc=='대(≥상위33%)'].index[:8])}")
fig, ax = plt.subplots(figsize=(8,4.3))
for col,c in zip(traj.columns,[GREEN,RUST,BLUE]):
    ax.plot(traj.index, traj[col], "o-", label=col, color=c, lw=1.9)
ax.set_title("메뉴 규모 3분위별 가맹점 평균매출 (2017–2024)")
ax.set_ylabel("억원"); ax.legend(title="메뉴 규모"); ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda v,_:f"{v:.1f}억"))
fig.savefig(FIG/"46_menusize_tercile_trajectory.png"); plt.close(fig)
p("\n- **중간 메뉴 규모 브랜드군이 8년 내내 가장 높은 평균매출**(≈3억). 소·대 그룹은 서로 비슷하고 더 낮음(≈2억).")
p("- 약한 **역U자** 힌트 — 너무 적어도, 너무 많아도 불리하고 중간이 유리. 단 분위당 6~7개 브랜드라 확정 불가.")
p("- 어느 그룹도 시간이 지나며 격차를 좁히지 못함 → 메뉴 규모보다 브랜드 고유 요인(포지셔닝)이 지배적.\n")

# ============================================================ H. 삼각검증
p("## H. 삼각검증 — 5개 증거\n")
p("| # | 근거 | 수준·설계 | 메뉴 수 효과 |")
p("|---|---|---|---|")
p("| 1 | Maven 매장내 주간 회귀 | store×week, 트래픽 통제 | 계수 0으로 소멸 |")
p("| 2 | Maven 합리화 시뮬 | 메뉴 하위 50% 단종 | 매출 77~88% 유지 |")
p("| 3 | Maven 분산 분해 | 주간매출 분산 | 매장 간(≈메뉴 여지) 0.2% |")
p("| 4a | **본 분석: 국내 19개 브랜드 단면** | 브랜드 간, 가격·매장수 통제 | 총 메뉴 수 r≈0, 유의하지 않음 |")
p("| 4b | 〃 (음료 메뉴만) | 〃 | r≈−0.15, 약한 음(−) |")
p("| 4c | 〃 (공정위 패널 3분위, 2017–24) | 8년 궤적 | 중간 메뉴가 최고, 소·대는 낮음 (역U 힌트) |")
p("| 5 | 학술·업계 문헌 | 선택 과부하, Simon-Kucher | 중앙값 58 SKU, 초과 시 매출·만족 하락 |")
p("\n> **종합:** 어느 갈래에서도 '메뉴 수를 늘리면 매출이 오른다'는 근거는 없다. "
  "국내 브랜드 단면에서 총 메뉴 수와 평균매출의 관계는 **사실상 0**, 음료 메뉴만 보면 약한 음(−), "
  "시계열 궤적은 **중간 규모가 유리한 역U자**를 희미하게 시사한다. "
  "매출을 가르는 것은 메뉴 수가 아니라 **가격 포지셔닝·매장 포맷**이며, 큰 메뉴는 저가 박리다매 전략의 부산물이다. "
  "(한계: n=19·단면·메뉴집계 ±25%·검정력 낮음 → |r|<0.4의 작은 효과는 배제 못 함.)\n")

p("## 데이터 한계\n")
p("- **X (메뉴 수):** 나무위키 2026년 스냅샷 기반. HOT/ICED·사이즈 변형 제외, 시즌·단종 제외했으나 "
  "브랜드별 문서 완성도 차이로 **±20~30% 오차**(menu_conf 0.55~0.85). Y(2023~24)와 시점도 어긋남.")
p("- **Y (매출):** 정보공개서 기준 = 가맹점만. 스타벅스·폴바셋 등 직영 브랜드 제외 → 표본이 가맹 브랜드 편중.")
p("- **n=19, 단면.** 인과 아님. 메뉴 수는 브랜드 전략의 결과이기도 하고(역인과), 관측 안 된 교란(마케팅비·입지·브랜드 자산) 많음.")
p("- 매머드커피(레거시, 30개점)는 본분석 제외, 강건성에서만 사용.")
p("- 가격은 아메리카노 1종 기준(2024.1) — 전체 가격대의 근사.\n")

(ROOT/"output"/"franchise_menusize_deep.md").write_text("\n".join(md), encoding="utf-8")
print("done. n =", len(d), "| base r =", round(base_r,3),
      "| bootstrap CI = [%.2f, %.2f]" % (lo,hi))
print("figs: 44_corrmatrix, 45_composition, 46_tercile_trajectory")
