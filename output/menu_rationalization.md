# Maven Roasters — 메뉴 합리화 시뮬레이션

- 총 SKU(product_detail) **80개** · product_type 29개 · category 9개

- 총매출 $698,812 · 181일 · 매장 3곳 · retail 24 SKU / prep 56 SKU

- 매출 하위 40 SKU(50%)의 매출 합계 비중: **23.3%**


**매출 하위 18 SKU** (store_conc>0.42 는 특정 매장 편중 → 단종 주의)

|    |   rev_rank | product_detail               | product_category   | kind   |   revenue |   units_per_store_day |   avg_price |   rev_share_% |   store_conc | conc_flag   |
|---:|-----------:|:-----------------------------|:-------------------|:-------|----------:|----------------------:|------------:|--------------:|-------------:|:------------|
|  0 |          1 | Dark chocolate               | Packaged Chocolate | retail |       755 |                  0.22 |        6.4  |          0.11 |         0.56 | True        |
|  1 |          2 | Earl Grey                    | Loose Tea          | retail |      1271 |                  0.26 |        8.95 |          0.18 |         0.5  | True        |
|  2 |          3 | Spicy Eye Opener Chai        | Loose Tea          | retail |      1336 |                  0.22 |       10.95 |          0.19 |         0.41 | False       |
|  3 |          4 | Guatemalan Sustainably Grown | Coffee beans       | retail |      1340 |                  0.25 |       10    |          0.19 |         0.44 | True        |
|  4 |          5 | Lemon Grass                  | Loose Tea          | retail |      1360 |                  0.28 |        8.95 |          0.19 |         0.53 | True        |
|  5 |          6 | Peppermint                   | Loose Tea          | retail |      1369 |                  0.28 |        8.95 |          0.2  |         0.4  | False       |
|  6 |          7 | Traditional Blend Chai       | Loose Tea          | retail |      1369 |                  0.28 |        8.95 |          0.2  |         0.51 | True        |
|  7 |          8 | English Breakfast            | Loose Tea          | retail |      1441 |                  0.3  |        8.95 |          0.21 |         0.36 | False       |
|  8 |          9 | Serenity Green Tea           | Loose Tea          | retail |      1471 |                  0.29 |        9.25 |          0.21 |         0.46 | True        |
|  9 |         10 | Morning Sunrise Chai         | Loose Tea          | retail |      1596 |                  0.31 |        9.5  |          0.23 |         0.4  | False       |
| 10 |         11 | Sustainably Grown Organic    | Packaged Chocolate | retail |      1680 |                  0.41 |        7.6  |          0.24 |         0.4  | False       |
| 11 |         12 | Hazelnut syrup               | Flavours           | prep   |      1898 |                  4.37 |        0.8  |          0.27 |         0.45 | True        |
| 12 |         13 | Chili Mayan                  | Packaged Chocolate | retail |      1973 |                  0.27 |       13.33 |          0.28 |         0.35 | False       |
| 13 |         14 | Carmel syrup                 | Flavours           | prep   |      2061 |                  4.74 |        0.8  |          0.29 |         0.43 | True        |
| 14 |         15 | Chocolate syrup              | Flavours           | prep   |      2126 |                  4.9  |        0.8  |          0.3  |         0.41 | False       |
| 15 |         16 | Columbian Medium Roast       | Coffee beans       | retail |      2220 |                  0.27 |       15    |          0.32 |         0.39 | False       |
| 16 |         17 | Sugar Free Vanilla syrup     | Flavours           | prep   |      2324 |                  5.35 |        0.8  |          0.33 |         0.5  | True        |
| 17 |         18 | Espresso Roast               | Coffee beans       | retail |      2493 |                  0.31 |       14.75 |          0.36 |         0.43 | True        |


## 시나리오별 결과 (매출 하위 순 단종)


`retain` = 단종 후 추정 총매출 ÷ 현재 총매출(%). σ=0 = 대체 전혀 없음(하한), σ=0.5 = 수요 절반이 잔여 메뉴로 이동.


|   k_cut |   sku_reduction_% |   gross_rev_dropped_% |   n_conc_flag |   retain_sig0 |   retain_sig30 |   retain_sig50 |
|--------:|------------------:|----------------------:|--------------:|--------------:|---------------:|---------------:|
|       5 |              6.25 |                  0.87 |             4 |         99.13 |          99.38 |          99.55 |
|      10 |             12.5  |                  1.9  |             6 |         98.1  |          98.19 |          98.25 |
|      15 |             18.75 |                  3.3  |             8 |         96.7  |          97.02 |          97.23 |
|      20 |             25    |                  5.14 |            11 |         94.86 |          95.37 |          95.71 |
|      25 |             31.25 |                  7.9  |            15 |         92.1  |          93.44 |          94.33 |
|      30 |             37.5  |                 12.1  |            17 |         87.9  |          89.92 |          91.26 |

- `n_conc_flag` = 그 컷에 포함된 SKU 중 한 매장 편중(>42%)이라 단종 전 매장별 확인이 필요한 개수.


## 권고: 3단계 시나리오 (매출 하위 k개 단종)


| 시나리오        |   단종 SKU |   SKU 감축% |   제거 매출% |   유지율 σ=0 |   유지율 σ=0.3 |   유지율 σ=0.5 | 잔여 type/cat   |
|:------------|---------:|----------:|---------:|----------:|------------:|------------:|:--------------|
| 보수 (Tier 1) |       10 |      12.5 |     1.9  |      98.1 |        98.2 |        98.2 | 24/8          |
| 중도 (Tier 2) |       20 |      25   |     5.14 |      94.9 |        95.4 |        95.7 | 20/6          |
| 공격 (Tier 3) |       30 |      37.5 |    12.1  |      87.9 |        89.9 |        91.3 | 14/5          |


**Tier 1 (보수) — 단종 대상 10개 SKU**

|    | product_detail               | product_category   | kind   |   revenue |   units_per_store_day |   avg_price | conc_flag   |
|---:|:-----------------------------|:-------------------|:-------|----------:|----------------------:|------------:|:------------|
|  0 | Dark chocolate               | Packaged Chocolate | retail |       755 |                  0.22 |        6.4  | True        |
|  1 | Earl Grey                    | Loose Tea          | retail |      1271 |                  0.26 |        8.95 | True        |
|  2 | Spicy Eye Opener Chai        | Loose Tea          | retail |      1336 |                  0.22 |       10.95 | False       |
|  3 | Guatemalan Sustainably Grown | Coffee beans       | retail |      1340 |                  0.25 |       10    | True        |
|  4 | Lemon Grass                  | Loose Tea          | retail |      1360 |                  0.28 |        8.95 | True        |
|  5 | Peppermint                   | Loose Tea          | retail |      1369 |                  0.28 |        8.95 | False       |
|  6 | Traditional Blend Chai       | Loose Tea          | retail |      1369 |                  0.28 |        8.95 | True        |
|  7 | English Breakfast            | Loose Tea          | retail |      1441 |                  0.3  |        8.95 | False       |
|  8 | Serenity Green Tea           | Loose Tea          | retail |      1471 |                  0.29 |        9.25 | True        |
|  9 | Morning Sunrise Chai         | Loose Tea          | retail |      1596 |                  0.31 |        9.5  | False       |

- 카테고리 분포: Loose Tea 8, Packaged Chocolate 1, Coffee beans 1

- 대부분 **Loose Tea 낱개 / Packaged Chocolate** — 저회전 포장 SKU. 제조 라인·메뉴판 복잡도와 무관하게 재고만 줄임.

- Tier 2 추가분(11~20위)은 시럽·원두·차 음료로 확장되어 대체율 가정에 더 민감.


## 별도 레버 — 사이즈 변형(Lg/Rg/Sm) 정리


- 사이즈 옵션이 2개 이상인 음료 base **17종**. 그중 base 매출의 30% 미만인 '약한 사이즈' 변형: **5개**

|                                    |   revenue |   share_in_base_% |
|:-----------------------------------|----------:|------------------:|
| ('Brazilian', 'Sm')                |      9482 |              25.1 |
| ('Jamaican Coffee River', 'Sm')    |      9844 |              25.4 |
| ('Ethiopia', 'Sm')                 |      9753 |              25.9 |
| ('Columbian Medium Roast', 'Sm')   |      8356 |              25.9 |
| ('Our Old Time Diner Blend', 'Sm') |      8968 |              28   |

- 이 약한 변형들을 모두 없애면 SKU **-5개**, 직접 매출 $46,403 (6.6%).

- 다만 가장 약한 변형도 base 매출의 25% 이상 → **뚜렷한 '버릴 사이즈'는 없음**. 2사이즈 음료는 40:60, 3사이즈는 25:35:40 수준으로 고르게 팔림.

- 사이즈 축소는 대체율이 매우 높음(같은 음료·다른 컵, σ≈0.8~0.95) → 없애도 실제 순손실은 위 금액의 5~20%.


## 참고 — 베이커리 회전율 (폐기 리스크 프록시, COGS 없음)


|    | product_detail          |   units_per_store_day |   revenue |   avg_price |
|---:|:------------------------|----------------------:|----------:|------------:|
|  0 | Oatmeal Scone           |                  3.35 |      5460 |        3    |
|  1 | Ginger Biscotti         |                  3.38 |      6437 |        3.51 |
|  2 | Almond Croissant        |                  3.52 |      7168 |        3.75 |
|  3 | Chocolate Chip Biscotti |                  3.54 |      6749 |        3.51 |
|  4 | Croissant               |                  3.6  |      6862 |        3.51 |
|  5 | Scottish Cream Scone    |                  3.66 |      8949 |        4.51 |
|  6 | Jumbo Savory Scone      |                  3.73 |      7627 |        3.76 |
|  7 | Hazelnut Biscotti       |                  3.73 |      6608 |        3.26 |
|  8 | Cranberry Scone         |                  3.85 |      6818 |        3.26 |
|  9 | Ginger Scone            |                  4.68 |      8012 |        3.18 |
| 10 | Chocolate Croissant     |                  5.7  |     11626 |        3.76 |

- 최저 회전 품목도 매장·일 3.4개 → 전 품목이 하루 3개 이상. 폐기 리스크는 낮은 편이며, 베이커리 11종은 **매출 기여(12%) 대비 유지 근거 충분**. 판단은 매출이 아니라 COGS·폐기율 데이터가 있어야 가능.


## 한계 / 해석 주의


- **장바구니 데이터 없음**(1거래=1품목) → 단종 품목 고객이 아예 이탈하는 교차판매 손실 미반영. 모든 수치는 **유지율 상한(낙관)**.

- **COGS·폐기·인건비 없음** → 매출 기준 분석. 저회전·소량 포장 SKU는 이익 개선폭이 매출 수치보다 큼.

- σ(대체율)는 가정. 사이즈 변형 정리 σ≈0.9, 서로 다른 차·시럽 단종 σ≈0.2~0.4.

- 매장 3곳 메뉴가 사실상 동일 → '메뉴 수 축소 실험'을 관측한 게 아니라 시뮬레이션임. 인과 검증엔 메뉴가 다른 다점포/전후 데이터 필요.
