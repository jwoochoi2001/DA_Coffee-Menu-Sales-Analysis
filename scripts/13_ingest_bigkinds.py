# -*- coding: utf-8 -*-
"""
13_ingest_bigkinds.py
빅카인즈 '기간별 뉴스 추이' 월별 export 들을 읽어 브랜드×기간 X패널 생성,
공정위 커피 브랜드 패널(Y)과 조인.

입력: data/franchise/bigkinds/bk_<브랜드>.xlsx|csv   (컬럼: 날짜/월, 기사건수)
      data/franchise/coffee_brand_panel.csv          (공정위 Y)
산출: data/franchise/brand_news_quarterly.csv
      data/franchise/brand_panel_XY.csv              (연 단위 X+Y 조인)
"""
import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import pandas as pd, numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FR = ROOT / "data" / "franchise"
BK = FR / "bigkinds"

FNAME2BRAND = {   # 파일명 키워드 → 공정위 패널 brand 값
    "스타벅스": "스타벅스", "투썸": "투썸플레이스", "이디야": "이디야",
    "할리스": "할리스", "메가": "메가MGC커피", "컴포즈": "컴포즈커피",
    "빽다방": "빽다방", "파스쿠찌": "파스쿠찌", "엔제리너스": "엔제리너스",
    "폴바셋": "폴바셋", "커피빈": "커피빈", "탐앤탐스": "탐앤탐스",
}


def read_trend(path):
    df = pd.read_excel(path) if path.suffix in (".xlsx", ".xls") else pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]
    # 날짜 컬럼 · 건수 컬럼 자동 탐지
    datecol = next((c for c in df.columns if re.search("날짜|일자|월|date|기간", c, re.I)), df.columns[0])
    cntcol = next((c for c in df.columns if re.search("건수|기사|count|빈도|수$", c, re.I)), df.columns[-1])
    out = pd.DataFrame({
        "date": pd.to_datetime(df[datecol].astype(str).str.replace(r"[^\d]", "-", regex=True)
                               .str.strip("-"), errors="coerce"),
        "n_articles": pd.to_numeric(df[cntcol], errors="coerce"),
    }).dropna()
    return out


def brand_of(fname):
    for k, v in FNAME2BRAND.items():
        if k in fname:
            return v
    return None


def main():
    files = sorted(BK.glob("bk_*.*"))
    if not files:
        print(f"!! {BK} 에 bk_*.xlsx / bk_*.csv 파일이 없습니다.")
        print("   빅카인즈에서 검색→[기간별 뉴스 추이]→월단위→데이터 다운로드 후 이 폴더에 저장.")
        return
    rows = []
    for f in files:
        b = brand_of(f.stem)
        if not b:
            print(f"  (건너뜀: 브랜드 매핑 없음) {f.name}"); continue
        t = read_trend(f)
        wide = "_wide" in f.stem
        t["brand"], t["metric"] = b, ("wide" if wide else "narrow")
        rows.append(t)
        print(f"  {f.name} -> {b}  {t.date.min():%Y-%m}~{t.date.max():%Y-%m}  총 {int(t.n_articles.sum())}건")
    d = pd.concat(rows, ignore_index=True)
    d["year"] = d.date.dt.year
    d["quarter"] = d.date.dt.to_period("Q").astype(str)

    narrow = d[d.metric == "narrow"]
    q = (narrow.groupby(["brand", "quarter"]).n_articles.sum().reset_index()
               .rename(columns={"n_articles": "news_newmenu_q"}))
    q["year"] = q.quarter.str[:4].astype(int)
    q.to_csv(FR / "brand_news_quarterly.csv", index=False, encoding="utf-8-sig")

    yx = (narrow.groupby(["brand", "year"]).n_articles.sum().reset_index()
                .rename(columns={"n_articles": "news_newmenu_y"}))

    # ---- 공정위 Y 와 조인 (연 단위) ----
    Y = pd.read_csv(FR / "coffee_brand_panel.csv")
    xy = Y.merge(yx, left_on=["brand", "yr"], right_on=["brand", "year"], how="left")
    xy["news_newmenu_y"] = xy["news_newmenu_y"].fillna(0)
    xy.to_csv(FR / "brand_panel_XY.csv", index=False, encoding="utf-8-sig")
    print(f"\n조인 완료: {xy.shape} → brand_panel_XY.csv")
    piv = xy[xy.brand.isin(FNAME2BRAND.values())].pivot_table(
        index="brand", columns="yr", values="news_newmenu_y")
    print("\n=== 브랜드 × 연도 '신메뉴' 기사 수 ===")
    print(piv.round(0).to_string())


if __name__ == "__main__":
    main()
