# Maven Roasters — EDA 요약

- 기간: **2023-01-01 ~ 2023-06-30**

- 행 수: **149,116** — transaction_id가 행마다 유일(= 1행 1품목, 장바구니 결합 없음)

- 매장: Astoria, Hell's Kitchen, Lower Manhattan

- 총매출: **$698,812** / 총판매수량: **214,470**

- 메뉴(product_detail): **80종** / 카테고리 **9종** / 타입 **29종**

- 객단가(거래당 매출): **$4.69** / 거래당 품목수: **1.00**


## 0. 데이터 커버리지 점검

- 기대 일수 181 / 실제 181 → 누락일: 0건 없음

- 일매출 범위: $2,037 ~ $6,404 (평균 $3,861)

| m                   |   Astoria |   Hell's Kitchen |   Lower Manhattan |
|:--------------------|----------:|-----------------:|------------------:|
| 2023-01-01 00:00:00 |     27314 |            27821 |             26543 |
| 2023-02-01 00:00:00 |     25105 |            25720 |             25320 |
| 2023-03-01 00:00:00 |     32835 |            33111 |             32889 |
| 2023-04-01 00:00:00 |     39478 |            40304 |             39159 |
| 2023-05-01 00:00:00 |     52429 |            52599 |             51700 |
| 2023-06-01 00:00:00 |     55083 |            56957 |             54446 |


## 1. 매출 추이

- 월별 총매출($) 및 전월대비:

|                     |   revenue |   MoM_% |
|:--------------------|----------:|--------:|
| 2023-01-01 00:00:00 |     81678 |   nan   |
| 2023-02-01 00:00:00 |     76145 |    -6.8 |
| 2023-03-01 00:00:00 |     98835 |    29.8 |
| 2023-04-01 00:00:00 |    118941 |    20.3 |
| 2023-05-01 00:00:00 |    156728 |    31.8 |
| 2023-06-01 00:00:00 |    166486 |     6.2 |


## 2. 요일 · 시간대 패턴

- 주중 평균 일매출 $3,874 vs 주말 $3,828

| daypart          |   revenue |   share_% |
|:-----------------|----------:|----------:|
| morning(06-11)   |    341970 |      48.9 |
| lunch(11-14)     |    126879 |      18.2 |
| afternoon(14-17) |    124161 |      17.8 |
| evening(17-21)   |    105803 |      15.1 |


## 3. 상품 · 메뉴 구조

| product_category   |   revenue |   units |   n_items |   rev_share_% |
|:-------------------|----------:|--------:|----------:|--------------:|
| Coffee             |    269952 |   89250 |        21 |            39 |
| Tea                |    196406 |   69737 |        16 |            28 |
| Bakery             |     82316 |   23214 |        11 |            12 |
| Drinking Chocolate |     72416 |   17457 |         4 |            10 |
| Coffee beans       |     40085 |    1828 |        10 |             6 |
| Branded            |     13607 |     776 |         3 |             2 |
| Loose Tea          |     11214 |    1210 |         8 |             2 |
| Flavours           |      8409 |   10511 |         4 |             1 |
| Packaged Chocolate |      4408 |     487 |         3 |             1 |

**매출 상위 10 메뉴**

| product_detail               |   revenue |
|:-----------------------------|----------:|
| Sustainably Grown Organic Lg |     21152 |
| Dark chocolate Lg            |     21006 |
| Latte Rg                     |     19112 |
| Cappuccino Lg                |     17642 |
| Morning Sunrise Chai Lg      |     17384 |
| Latte                        |     17258 |
| Jamaican Coffee River Lg     |     16481 |
| Sustainably Grown Organic Rg |     16234 |
| Cappuccino                   |     15998 |
| Brazilian Lg                 |     15110 |

**매출 하위 10 메뉴**

| product_detail               |   revenue |
|:-----------------------------|----------:|
| Morning Sunrise Chai         |      1596 |
| Serenity Green Tea           |      1471 |
| English Breakfast            |      1441 |
| Traditional Blend Chai       |      1369 |
| Peppermint                   |      1369 |
| Lemon Grass                  |      1360 |
| Guatemalan Sustainably Grown |      1340 |
| Spicy Eye Opener Chai        |      1336 |
| Earl Grey                    |      1271 |
| Dark chocolate               |       755 |

- **파레토**: 전체 80개 메뉴 중 상위 **43개(54%)**가 매출의 80%를 만든다.

- 매출 하위 50% 메뉴(40개)의 합산 매출 비중: 23.3%


## 4. 가설 준비 — store × week 패널 (메뉴 폭 vs 매출)

- 패널 shape: (81, 13) (store 3 × 주). full_week=False 6건은 부분주.

| store           |   revenue |   menu_breadth |   n_categories |   cat_entropy |   avg_unit_price |   avg_ticket |
|:----------------|----------:|---------------:|---------------:|--------------:|-----------------:|-------------:|
| Astoria         |   8601.63 |          69.04 |           7.85 |          1.36 |             3.38 |         4.59 |
| Hell's Kitchen  |   8759.67 |          73.41 |           8.3  |          1.4  |             3.38 |         4.65 |
| Lower Manhattan |   8520.64 |          74.11 |           8.78 |          1.43 |             3.36 |         4.8  |

**full-week 패널에서 주간매출과의 상관계수(Pearson):**

|                |   corr_with_revenue |
|:---------------|--------------------:|
| revenue        |               1     |
| menu_breadth   |               0.266 |
| n_categories   |               0.086 |
| n_types        |               0.176 |
| cat_entropy    |               0.166 |
| avg_unit_price |               0.17  |
| avg_ticket     |               0.2   |
| units          |               0.989 |
| n_tx           |               0.983 |

**간이 OLS: weekly revenue ~ menu_breadth + n_tx + avg_unit_price + store dummies**

|                       |     coef |
|:----------------------|---------:|
| intercept             | -4922.7  |
| menu_breadth          |     1    |
| n_tx                  |     4.71 |
| avg_unit_price        |  1363.4  |
| store_Hell's Kitchen  |   136.11 |
| store_Lower Manhattan |   432.8  |

R² = 0.977  (n=75)


> 주의: menu_breadth 와 n_tx(거래수)는 강한 양의 상관 — 거래가 많은 주에 자연히 더 많은 메뉴가 팔린다. 메뉴 '운영 수'가 아니라 '판매된 메뉴 수'라 역인과 가능성이 큼. 이 데이터로는 가설의 '보조 증거'까지가 한계이며, 매장 간 실제 메뉴 구성이 거의 동일해 진짜 검정에는 다점포/패널 외부 데이터가 필요.
