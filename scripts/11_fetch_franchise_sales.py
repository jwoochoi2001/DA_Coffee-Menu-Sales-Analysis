# -*- coding: utf-8 -*-
"""
11_fetch_franchise_sales.py
공정위 '브랜드별 가맹점 현황 통계' API 수집 → 커피 브랜드 패널
  서비스 : https://apis.data.go.kr/1130000/FftcBrandFrcsStatsService/getBrandFrcsStats
  필수파라미터 : yr (연도), serviceKey
  제공연도 : 2017 ~ 2024
  응답필드 : yr, indutyLclasNm(업종대), indutyMlsfcNm(업종중), corpNm(법인),
             brandNm(브랜드), frcsCnt(가맹점수), newFrcsRgsCnt(신규개점),
             ctrtEndCnt(계약종료), ctrtCncltnCnt(계약해지), nmChgCnt(명의변경),
             avrgSlsAmt(가맹점 평균매출액,원), arUnitAvrgSlsAmt(면적3.3㎡당 평균매출액)
키 : data/franchise/.apikey  (디코딩 키 한 줄)
산출 : data/franchise/franchise_all_raw.csv, coffee_brand_panel.csv
"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import requests, pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FR = ROOT / "data" / "franchise"
KEY = (FR / ".apikey").read_text(encoding="utf-8").strip()
URL = "https://apis.data.go.kr/1130000/FftcBrandFrcsStatsService/getBrandFrcsStats"
YEARS = range(2017, 2025)


def fetch_year(yr, rows_per=1000):
    out, page = [], 1
    while True:
        r = requests.get(URL, params={
            "serviceKey": KEY, "resultType": "json",
            "pageNo": page, "numOfRows": rows_per, "yr": yr,
        }, timeout=40)
        r.raise_for_status()
        j = r.json()
        if j.get("resultCode") not in ("00", None):
            raise RuntimeError(f"{yr} p{page}: {j}")
        items = j.get("items", [])
        out += items
        total = int(j.get("totalCount", 0))
        if not items or page * rows_per >= total:
            break
        page += 1
        time.sleep(0.2)
    print(f"  {yr}: {len(out):>6}건")
    return out


def main():
    allrows = []
    for yr in YEARS:
        allrows += fetch_year(yr)
        time.sleep(0.3)
    raw = pd.DataFrame(allrows)
    num = ["frcsCnt", "newFrcsRgsCnt", "ctrtEndCnt", "ctrtCncltnCnt", "nmChgCnt",
           "avrgSlsAmt", "arUnitAvrgSlsAmt", "yr"]
    for c in num:
        raw[c] = pd.to_numeric(raw[c], errors="coerce")
    raw.to_csv(FR / "franchise_all_raw.csv", index=False, encoding="utf-8-sig")
    print(f"\n전체 {raw.shape} → franchise_all_raw.csv")

    # ── avrgSlsAmt 단위 = 천원 (정보공개서 기준 가맹점당 연 평균매출액) ──
    #    투썸 2017 = 532,698천원 = 5.33억  ← 뉴스치와 일치 확인
    coffee = raw[raw["indutyMlsfcNm"].astype(str).str.contains("커피", na=False)].copy()

    def norm_brand(s):
        s = str(s).split("(")[0].strip()
        for a, b in [("할리스커피", "할리스"), ("할리스/할리스", "할리스"),
                     ("탐앤탐스 커피", "탐앤탐스"), ("탐앤탐스커피", "탐앤탐스"),
                     ("메가엠지씨커피", "메가MGC커피"), ("메가엠지씨 커피", "메가MGC커피"),
                     ("이디야커피", "이디야"), ("엔제리너스커피", "엔제리너스"),
                     ("커피에반하다", "커피에반하다"), ("빽다방", "빽다방")]:
            if s.startswith(a):
                return b
        return s
    coffee["brand"] = coffee["brandNm"].map(norm_brand)
    coffee["avg_sales_eok"] = coffee["avrgSlsAmt"] / 1e5          # 천원 → 억원
    coffee["ar_unit_sales_manwon"] = coffee["arUnitAvrgSlsAmt"] / 10   # 천원 → 만원(3.3㎡당)
    coffee["open_rate"] = coffee["newFrcsRgsCnt"] / coffee["frcsCnt"]
    coffee["close_rate"] = (coffee["ctrtEndCnt"] + coffee["ctrtCncltnCnt"]) / coffee["frcsCnt"]
    coffee = coffee[coffee["frcsCnt"] > 0]

    # 동일 브랜드-연도 중복(영문표기 분리 등)은 매장수 큰 행 채택
    coffee = (coffee.sort_values("frcsCnt", ascending=False)
                    .drop_duplicates(["brand", "yr"])
                    .sort_values(["brand", "yr"]).reset_index(drop=True))
    keep = ["yr", "brand", "brandNm", "corpNm", "frcsCnt", "newFrcsRgsCnt",
            "ctrtEndCnt", "ctrtCncltnCnt", "nmChgCnt", "open_rate", "close_rate",
            "avrgSlsAmt", "avg_sales_eok", "ar_unit_sales_manwon"]
    coffee[keep].to_csv(FR / "coffee_brand_panel.csv", index=False, encoding="utf-8-sig")
    print(f"커피 브랜드-연도 {coffee.shape[0]}행 / 고유 브랜드 {coffee.brand.nunique()}개 "
          f"/ 연도 {sorted(coffee.yr.unique())} → coffee_brand_panel.csv")
    has_sales = coffee[coffee.avg_sales_eok > 0]
    print(f"평균매출 보고 있는 브랜드-연도: {len(has_sales)}")

    big = ["스타벅스", "투썸플레이스", "이디야", "할리스", "메가MGC커피", "컴포즈커피",
           "빽다방", "파스쿠찌", "엔제리너스", "커피빈", "탐앤탐스", "폴바셋",
           "더벤티", "매머드커피", "블루보틀", "토프레소", "요거프레소", "커피베이"]
    view = coffee[coffee.brand.isin(big)]
    print("\n=== 주요 커피 브랜드 · 가맹점 평균매출액 (억원) ===")
    print(view.pivot_table(index="brand", columns="yr", values="avg_sales_eok").round(2).to_string())
    print("\n=== 가맹점 수 ===")
    print(view.pivot_table(index="brand", columns="yr", values="frcsCnt").round(0).to_string())
    print("\n=== 신규 개점 수 ===")
    print(view.pivot_table(index="brand", columns="yr", values="newFrcsRgsCnt").round(0).to_string())


if __name__ == "__main__":
    main()
