# 카페 매출 · 메뉴 구성 데이터 분석 (Maven Roasters)

**질문 (재정의):** 이 카페에서 메뉴 구성이 매출·운영과 어떻게 얽혀 있는가?
(출발 가설 "메뉴 수 → 매출"의 인과 검정은 이 데이터로 불가 — 리포트 4절 참고)

**결론:** 매출은 방문객 수(트래픽)로 결정되고, 메뉴 라인업의 하위 절반은
매출에 거의 기여하지 않는다. 메뉴 수는 매출 확대 수단이 아니라 비용 관리 대상.

## 최종 산출물 (Phase 1 — Maven Roasters)
- **`output/report.html`** — 통합 HTML 리포트 (그림 내장, 단독 실행)
- Artifact: https://claude.ai/code/artifact/1cd19f77-e0c3-489d-bbff-e42ee03b2662
- `output/menu_effect_bounds.md` — 가설을 데이터 한계까지 밀어붙인 추가 분석(07)

## Phase 2 — 국내 프랜차이즈: 메뉴 수 ↔ 매출 (원래 가설 정면 검증)
- **Y (완료):** `scripts/11_fetch_franchise_sales.py` — 공정위 API
  `FftcBrandFrcsStatsService/getBrandFrcsStats` (param `yr`), 2017–2024.
  `data/franchise/coffee_brand_panel.csv` — 944개 커피 브랜드 × 연도,
  가맹점 평균매출액(억원)·매장수·신규개점·계약종료. EDA: `scripts/12_*`, `output/franchise_eda.md`
- **X (완료):** `data/franchise/menusize_panel.csv` — 커피 프랜차이즈 13개
  브랜드별 메뉴 항목 수(음료+푸드), 나무위키 2026 스냅샷, ±20~30% 오차.
- **분석 1차:** `scripts/14_menusize_vs_sales.py` (n=13)
- **분석 심화 (완료):** `scripts/15_menusize_deep.py`, `output/franchise_menusize_deep.md`
  n=20(본분석 19), `menusize_panel_v2.csv`. 8단계: 상관행렬·회귀스위트·LOO·부트스트랩·
  메뉴집계 몬테카를로·검정력·메뉴구성·공정위 8년 3분위 궤적·삼각검증.
  → **총 메뉴 수 ↔ 가맹점 평균매출 r≈0** (부트스트랩 CI −0.47~+0.49), 회귀 계수 전부 유의하지 않음.
  음료 메뉴만 약한 음(−), 8년 궤적은 **중간 규모가 최고인 역U자** 힌트.
  매출을 가르는 건 메뉴 수가 아니라 **가격 포지셔닝·매장 포맷**. 큰 메뉴 = 저가 박리다매 부산물.
  Maven 결과·합리화 시뮬·선택과부하 문헌과 방향 일치. (한계: 단면·n작음·메뉴집계 ±25%)
- (참고) 신메뉴 출시 타임라인: `data/franchise/sbux_promo_phases.csv` (스타벅스, 2017–2026)
  — "신메뉴 빈도" 분석용, 별도 트랙(빅카인즈/DART 필요, 미완).

## 데이터
- 출처: Maven Analytics "Coffee Shop Sales" (가상 카페 체인, NYC 3개 매장)
  미러: `github.com/siglimumuni/Datasets/Coffee Shop Sales.csv`
- `data/raw/coffee_shop_sales_raw.csv` — 149,116행 × 11열, 2023-01-01 ~ 06-30

## 파이프라인
| 스크립트 | 내용 | 주요 산출물 |
|---|---|---|
| `01_preprocess.py` | 정제·파생변수 | `data/processed/coffee_clean.{parquet,csv}`, `quality_report.json` |
| `02_eda.py` | EDA·패널 구성 | `eda_summary.md`, `store_week_panel.csv`, figures 01–08 |
| `03_timeseries_drivers.py` | STL 분해·드라이버 회귀·매출 분해 | `drivers_summary.md`, `drivers_models.txt`, `store_day_panel.csv`, figures 10–14 |
| `04_menu_rationalization.py` | 메뉴 합리화 시뮬레이션 | `menu_rationalization.md`, `menu_item_stats.csv`, `rationalization_grid.csv`, figure 20 |
| `05_report_figures.py` | 리포트용 그림 재생성 | `output/report/r_*.png` |
| `06_build_report.py` | 그림 base64 삽입 → 최종 HTML | `output/report.html` |

## 핵심 수치
- 총매출 $698,812 / 214,470잔 / 6개월 · 메뉴 80종
- 일매출 +111% (1월 $2,635 → 6월 $5,550/일), 성장은 100% 트래픽 (객단가 정체)
- STL: 추세가 분산의 94.6%, 주간계절 1.9% · 요일효과 ±2.8%
- 드라이버 회귀 R² 0.82인데 시간추세 하나가 +73%p, 매장·요일은 ~0
- 파레토: 80개 중 43개(54%)가 매출 80% / 하위 40개 = 23%
- 시뮬레이션: 하위 10개(-12.5% SKU) 단종 → 매출 98% 유지 (대체 0 가정)

## 재현
```bash
pip install pandas numpy matplotlib statsmodels pyarrow tabulate
curl -L -o data/raw/coffee_shop_sales_raw.csv \
  https://raw.githubusercontent.com/siglimumuni/Datasets/master/Coffee%20Shop%20Sales.csv
for s in 01_preprocess 02_eda 03_timeseries_drivers 04_menu_rationalization 05_report_figures 06_build_report; do
  python scripts/$s.py
done
```

## 한계
- 1거래 = 1품목 → 교차판매·연관규칙 불가, 시뮬레이션 유지율은 상한
- 원가·폐기·인건비 없음 → 매출 기준(이익 아님)
- 가상 데이터 · 6개월 · 단일 계절 구간
