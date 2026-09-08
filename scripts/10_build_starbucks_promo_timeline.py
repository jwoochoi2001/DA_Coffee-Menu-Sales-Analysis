# -*- coding: utf-8 -*-
"""
10_build_starbucks_promo_timeline.py
스타벅스 코리아 프로모션(시즌·한정) 음료 출시 타임라인 — X변수 원천
출처: 나무위키 「스타벅스/메뉴/프로모션 음료」 및 연도별 하위문서 (2017~2026)
      웹 조회로 수집, 날짜는 발표된 프로모션 시작일 기준(일부 근사).
산출: data/franchise/sbux_promo_phases.csv         (프로모션 단계별)
      data/franchise/sbux_promo_quarterly.csv      (분기 집계 — 매출 패널과 조인용)
      output/figures/40_sbux_promo_cadence.png
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTD = ROOT / "data" / "franchise"; OUTD.mkdir(parents=True, exist_ok=True)
FIG = ROOT / "output" / "figures"

# phase: (start_date, season, theme_short, collab, n_items_listed, n_new, date_precision)
#  n_new = 신규로 판단되는 음료 수 (returning/continued/reissue 제외). 근사치.
P = [
 # ---- 2017 (2016은 나무위키 미기록) ----
 ("2017-01-01","winter","New Year","",2,2,"exact"),
 ("2017-02-15","spring","Spring Wonderland","",2,2,"exact"),
 ("2017-03-21","spring","Cherry Blossom","",3,3,"exact"),
 ("2017-04-18","summer","Show Your Flavor 1","",3,3,"exact"),
 ("2017-06-08","summer","Show Your Flavor 2","",4,4,"exact"),
 ("2017-07-25","summer","Show Your Flavor 3","",3,3,"exact"),
 ("2017-09-05","fall","Autumn 1","",2,2,"exact"),
 ("2017-09-29","fall","Autumn 2","",2,2,"exact"),
 ("2017-10-27","christmas","Give Good 1","",3,3,"exact"),
 ("2017-11-29","christmas","Give Good 2","",2,2,"exact"),
 # ---- 2018 ----
 ("2018-01-01","winter","New Year","",3,3,"exact"),
 ("2018-02-20","spring","Capture Spring","",3,3,"exact"),
 ("2018-03-20","spring","Cherry Blossom","",3,3,"exact"),
 ("2018-04-17","summer","Show Your Flavor 1","",3,3,"exact"),
 ("2018-06-08","summer","Show Your Flavor 2","",3,3,"exact"),
 ("2018-07-24","summer","Sweet & Bold","",3,3,"exact"),
 ("2018-09-04","fall","Latte Truly Yours 1","",2,2,"exact"),
 ("2018-09-28","fall","Latte Truly Yours 2","",2,2,"exact"),
 ("2018-10-05","halloween","Happy Halloween","",2,2,"approx"),
 ("2018-10-26","christmas","Blend is Magic","",5,5,"exact"),
 # ---- 2019 ----
 ("2019-01-01","winter","Teavana New Year","",4,4,"exact"),
 ("2019-02-08","winter","Valentine","",2,2,"exact"),
 ("2019-02-19","spring","Craft Your Coffee","",3,3,"exact"),
 ("2019-03-05","spring","Would You Berry Me","",3,3,"exact"),
 ("2019-03-19","spring","Cherry Blossom","",3,3,"exact"),
 ("2019-04-16","summer","15-Minute Vacation 1","",3,3,"exact"),
 ("2019-05-02","spring","Gratitude Month","",5,3,"exact"),
 ("2019-06-11","summer","15-Minute Vacation 2","",3,3,"exact"),
 ("2019-07-16","summer","Korea 20th Anniversary","anniv",2,2,"exact"),
 ("2019-07-30","summer","Teavolution","",4,2,"exact"),
 ("2019-09-03","fall","Autumn 1","",2,2,"exact"),
 ("2019-09-27","fall","Autumn 2","",4,2,"exact"),
 ("2019-10-15","halloween","Trick or Treat","",3,3,"exact"),
 ("2019-10-29","christmas","Merry Coffee 1","",5,5,"exact"),
 ("2019-11-28","christmas","Merry Coffee 2","",5,4,"exact"),
 # ---- 2020 ----
 ("2020-01-02","winter","Be The Brightest Stars","",3,3,"approx"),
 ("2020-01-21","winter","BTS x Starbucks","idol",1,1,"exact"),
 ("2020-02-07","winter","Berry Loves Chocolate","",3,3,"exact"),
 ("2020-02-25","spring","Spring Choux","",3,3,"exact"),
 ("2020-03-24","spring","Cherry Blossom","",3,3,"exact"),
 ("2020-04-14","summer","Stay Chill Peaceful 1","",3,3,"exact"),
 ("2020-05-01","summer","Stay Chill (May adds)","",6,6,"exact"),
 ("2020-06-09","summer","Stay Chill Playful 2","",3,3,"exact"),
 ("2020-07-02","summer","Playful (July adds)","",2,2,"exact"),
 ("2020-07-14","summer","Stay Chill Playful 3","",3,3,"exact"),
 ("2020-09-08","fall","Give Thanks All Around","",3,3,"exact"),
 ("2020-10-13","halloween","Spooky Friends","",2,2,"exact"),
 ("2020-10-30","christmas","Carry the Merry 1","",3,3,"exact"),
 ("2020-12-02","christmas","Carry the Merry 2 + Delivers","",7,7,"exact"),
 # ---- 2021 ----
 ("2021-01-01","winter","BOOST my day","",4,4,"exact"),
 ("2021-01-25","winter","Strawberry / Cupid","",3,3,"exact"),
 ("2021-02-14","spring","Dream Away","",3,2,"exact"),
 ("2021-03-16","spring","Find Your Blooming","",3,3,"exact"),
 ("2021-04-13","summer","One with the Sun 1","",3,3,"exact"),
 ("2021-05-01","summer","Mother's Day adds","",4,4,"exact"),
 ("2021-06-15","summer","Hello Summer 2","",4,4,"exact"),
 ("2021-07-15","summer","Found Happy Place 3","",3,3,"approx"),
 ("2021-09-07","fall","Black Glazed Season","",3,3,"exact"),
 ("2021-10-12","halloween","Halloween","",3,3,"exact"),
 ("2021-10-28","christmas","Carry the Merry 1","",3,3,"exact"),
 ("2021-12-02","christmas","Carry the Merry 2","",3,3,"exact"),
 # ---- 2022 ----
 ("2022-01-01","winter","New Year","",3,3,"exact"),
 ("2022-02-22","spring","Spring 1","",3,3,"exact"),
 ("2022-03-22","spring","Spring 2","",3,3,"exact"),
 ("2022-04-12","summer","Summer 1","",3,3,"exact"),
 ("2022-06-13","summer","Summer 2","",3,3,"exact"),
 ("2022-07-26","summer","Summer 3","",3,3,"exact"),
 ("2022-09-02","fall","Fall","",3,3,"exact"),
 ("2022-10-11","halloween","Halloween","",2,2,"exact"),
 ("2022-11-09","christmas","Christmas 1","",4,4,"exact"),
 ("2022-12-02","christmas","Christmas 2","",2,2,"exact"),
 # ---- 2023 ----
 ("2023-01-01","winter","New Year","",3,3,"exact"),
 ("2023-02-15","spring","Spring 1","",3,3,"exact"),
 ("2023-03-21","spring","Spring 2","",4,3,"exact"),
 ("2023-05-03","summer","Summer 1","",4,4,"exact"),
 ("2023-07-11","summer","Summer 2","",3,3,"exact"),
 ("2023-08-29","fall","Fall / Disney 100","disney",4,4,"exact"),
 ("2023-10-05","fall","Fall 2 / Disney","disney",2,2,"exact"),
 ("2023-11-02","christmas","Christmas 1","",3,3,"exact"),
 ("2023-11-29","christmas","Christmas 2","",2,2,"exact"),
 # ---- 2024 ----
 ("2024-01-01","winter","New Year Blue Dragon","",3,3,"exact"),
 ("2024-02-01","winter","February","",3,3,"exact"),
 ("2024-02-29","spring","March","",3,3,"exact"),
 ("2024-03-28","spring","April","",2,2,"exact"),
 ("2024-05-01","summer","Summer 1","",3,3,"exact"),
 ("2024-07-05","summer","25th Anniversary 1","anniv",4,4,"exact"),
 ("2024-08-02","summer","25th Anniversary 2","anniv",3,3,"exact"),
 ("2024-08-30","fall","September","",3,3,"exact"),
 ("2024-09-27","fall","October / Playmobil","toy",2,2,"exact"),
 ("2024-11-01","christmas","Holiday 1","",4,4,"exact"),
 ("2024-12-02","christmas","Holiday 2","",1,1,"exact"),
 # ---- 2025 ----
 ("2025-01-01","winter","New Year / Harry Potter","ip",3,3,"exact"),
 ("2025-02-06","winter","Valentine","",3,3,"exact"),
 ("2025-03-05","spring","Spring 1 Choux","",4,4,"exact"),
 ("2025-04-15","spring","Spring 2","",3,3,"exact"),
 ("2025-05-22","summer","Summer 1","",3,3,"exact"),
 ("2025-06-18","summer","Summer New Releases","",4,4,"exact"),
 ("2025-07-21","summer","Summer 2","",4,4,"exact"),
 ("2025-09-19","fall","Pre-Fall","",6,6,"exact"),
 ("2025-10-30","christmas","Christmas 1 / Where's Wally","ip",5,5,"exact"),
 ("2025-11-28","christmas","Christmas 2","",3,3,"exact"),
 # ---- 2026 (부분) ----
 ("2026-01-01","winter","New Year / Friends","ip",4,4,"exact"),
 ("2026-02-04","winter","New Year 2","",5,3,"exact"),
 ("2026-03-04","spring","Spring 1 Choux","",4,4,"exact"),
 ("2026-03-27","spring","KBO Collab","sports",1,1,"exact"),
 ("2026-04-15","spring","Spring 2 / Toy Story 5","toy",5,3,"exact"),
 ("2026-06-23","summer","Summer 1","",6,6,"exact"),
 ("2026-07-27","summer","Summer 2","",6,3,"exact"),
 ("2026-08-28","fall","Pre-Autumn","",6,6,"exact"),
]

df = pd.DataFrame(P, columns=["start_date","season","theme","collab","n_items_listed","n_new","date_precision"])
df["start_date"] = pd.to_datetime(df["start_date"])
df["brand"] = "스타벅스"
df["year"] = df.start_date.dt.year
df["quarter"] = df.start_date.dt.to_period("Q").astype(str)
df["month"] = df.start_date.dt.to_period("M").astype(str)
df["is_collab"] = (df.collab != "").astype(int)
df = df.sort_values("start_date").reset_index(drop=True)
df.to_csv(OUTD / "sbux_promo_phases.csv", index=False, encoding="utf-8-sig")

# ---- 분기 집계 (매출 패널 조인용) ----
q = (df.groupby("quarter")
       .agg(promo_phases=("theme","count"),
            new_drinks=("n_new","sum"),
            items_listed=("n_items_listed","sum"),
            collab_phases=("is_collab","sum"))
       .reset_index())
q["year"] = q.quarter.str[:4].astype(int)
q = q[q.year.between(2017, 2025)]
q.to_csv(OUTD / "sbux_promo_quarterly.csv", index=False, encoding="utf-8-sig")

# ---- 연 집계 ----
y = df[df.year.between(2017,2025)].groupby("year").agg(
    promo_phases=("theme","count"), new_drinks=("n_new","sum"),
    collab_phases=("is_collab","sum")).reset_index()

print("=== 프로모션 단계 수 / 연도 ===")
print(y.to_string(index=False))
print(f"\n총 프로모션 단계: {len(df)}  ·  총 신규 음료(근사): {df.n_new.sum()}")
print(f"기간: {df.start_date.min().date()} ~ {df.start_date.max().date()}")

# ---- 그림 ----
plt.rcParams.update({"figure.dpi":150,"savefig.dpi":150,"savefig.bbox":"tight",
    "font.family":"Malgun Gothic","axes.unicode_minus":False,
    "figure.facecolor":"#FCFCFB","axes.facecolor":"#FCFCFB","savefig.facecolor":"#FCFCFB",
    "axes.spines.top":False,"axes.spines.right":False,"axes.grid":True,
    "grid.color":"#E8E4DE","grid.alpha":.9,"axes.titleweight":"bold","axes.titlelocation":"left"})
qq = q.copy(); qq["qi"] = range(len(qq))
fig, ax = plt.subplots(2,1,figsize=(11,6.2),sharex=True)
ax[0].bar(qq.qi, qq.new_drinks, color="#2F6F9F", width=.7)
ax[0].bar(qq.qi, qq.collab_phases, color="#B0641A", width=.7, label="콜라보 단계 수")
ax[0].set_title("스타벅스 코리아 — 분기별 신규 프로모션 음료 수 (X 변수 후보)")
ax[0].legend(fontsize=8)
ax[1].plot(qq.qi, qq.promo_phases, "o-", color="#4F9D69")
ax[1].set_title("분기별 프로모션 '단계' 수")
ax[1].set_xticks(qq.qi[::2]); ax[1].set_xticklabels(qq.quarter[::2], rotation=45, ha="right", fontsize=8)
for a in ax: a.yaxis.set_major_locator(mtick.MaxNLocator(integer=True))
fig.savefig(FIG / "40_sbux_promo_cadence.png"); plt.close(fig)
print("\nsaved -> data/franchise/sbux_promo_phases.csv, sbux_promo_quarterly.csv")
print("fig   -> output/figures/40_sbux_promo_cadence.png")
