# 로맨스판타지 웹소설 시장 분석
### Romance Fantasy Web Novel Market Analysis (2013–2026)

> 카카오페이지·네이버시리즈·네이버웹툰 3개 플랫폼 16,337편을 직접 크롤링해  
> 시계열 통계 분석 4가지 방법론으로 시장 성장 구조와 2032년까지의 전망을 분석한 포트폴리오 프로젝트입니다.

---

## 핵심 발견 (Key Findings)

| 지표 | 결과 |
|---|---|
| 10년 성장 배수 | 월 10편 미만 → **257편** (25배+) |
| 구조적 전환점 | **3회** (2017-09 / 2020-08 / 2022-07), 모두 p<0.0001 |
| 성장 둔화 시작 | **2024년 4월** — ITS 기울기 변화 -3.24편/월 (p<0.001) |
| 2026-12 예측 | **228편** (95% 구간: 197~262편) |
| 쇠퇴기 전망 | 현실 시나리오 기준 **2029년 말** 2022년 이전 수준 회귀 |

---

## 분석 파이프라인

```
[데이터 수집]       [현상 파악]         [원인 파악]         [미래 예측]
크롤러 제작     →   STL 시계열 분해  →  ITS 인과 분석   →  Prophet 예측
3개 플랫폼          PELT 변동점 탐지    재혼황후 / 선재업고튀어   쇠퇴기 시나리오
16,337편            Mann-Kendall 검정   Welch t-test          3가지 시나리오
```

---

## 기술 스택 (Tech Stack)

| 분류 | 사용 기술 |
|---|---|
| **언어** | Python 3.11 |
| **데이터 수집** | Playwright, BeautifulSoup, requests |
| **데이터 처리** | pandas, numpy |
| **통계 분석** | statsmodels (STL, OLS), ruptures (PELT), pymannkendall, scipy |
| **시계열 예측** | Prophet (Meta) |
| **시각화** | matplotlib, koreanize-matplotlib |
| **대시보드** | HTML / CSS / Vanilla JS |

---

## 분석 방법론 (Methodology)

### 1단계 — STL 분해 (Seasonal-Trend decomposition using Loess)
월별 신작 수 시계열을 **추세·계절성·잔차** 3개 성분으로 분리.  
Mann-Kendall 비모수 검정으로 추세 유의성 검증, 2013~2026년 선형 기울기 +1.62편/월 (p<0.001) 확인.

### 2단계 — PELT 변동점 탐지 (Pruned Exact Linear Time)
Elbow Method로 최적 penalty 자동 선택 → **3개 구조적 전환점** 탐지.  
각 전환점 전후 Welch t-test로 유의성 검증 (모두 p<0.0001).

| 전환점 | 전 구간 평균 | 후 구간 평균 | 변화율 |
|---|---|---|---|
| 2017년 9월 | 21편/월 | 79편/월 | **+275%** |
| 2020년 8월 | 79편/월 | 147편/월 | **+86%** |
| 2022년 7월 | 147편/월 | 202편/월 | **+37%** |

### 3단계 — ITS 인과 분석 (Interrupted Time Series)
**재혼황후(2019-10)** 와 **선재업고튀어(2024-04)** 2개 이벤트에 대해  
전체 + 3개 플랫폼 × 2개 이벤트 = **8개 OLS 회귀 모델** 적용.

```
Y = β0 + β1·time + β2·D + β3·time_since + ε
β2: 이벤트 직후 즉각 레벨 변화
β3: 이벤트 이후 기울기(추세) 변화
```

| 이벤트 | β2 (즉각 효과) | β3 (지속 효과) | 해석 |
|---|---|---|---|
| 재혼황후 2019-10 | +35편 ★ (p<0.001) | +0.23편/월 | 공급 신호 → 즉각 시장 확대 |
| 선재업고튀어 2024-04 | +7편 (p=0.418) | **-3.24편/월 ★** (p<0.001) | 구조적 포화의 반영 |

### 4단계 — Prophet 예측 + Hold-out 검증
PELT 변동점을 Prophet changepoints로 주입, 2025년 데이터 Hold-out 검증.  
MAPE (Mean Absolute Percentage Error: 평균 절대 백분율 오차) 23.6% → 방향성 예측 수준.

### 5단계 — 쇠퇴기 시나리오 분석
ITS 결과 + Prophet 예측을 통합해 3가지 시나리오로 2032년까지 투영.

| 시나리오 | 기울기 | 2030년 예상 | 근거 |
|---|---|---|---|
| 낙관 | ±0편/월 | 183편 유지 | Prophet 고원 가정 |
| **현실** | **-1.06편/월** | **145편** | **2024~2025 실측 OLS** |
| 비관 | -1.45편/월 | 126편 | ITS post-slope 지속 |

---

## 주요 산출물

| 파일 | 설명 |
|---|---|
| [`dashboard.html`](dashboard.html) | 전체 분석 결과 인터랙티브 대시보드 |
| [`reports/05_final_report.md`](reports/05_final_report.md) | 최종 종합 보고서 (인사이트·전략 제언 포함) |
| [`reports/slide_deck_spec.md`](reports/slide_deck_spec.md) | 슬라이드 덱 제작 지침서 (DESA Reporter 검토 의견 포함) |
| [`analysis/`](analysis/) | 전체 분석 파이썬 스크립트 |
| [`charts/`](charts/) | 분석 결과 시각화 (PNG) |
| [`data/processed/`](data/processed/) | 정제된 분석 데이터 (CSV) |
| [`study/`](study/) | 분석에 사용된 통계 방법론 학습 노트 |

---

## 전략적 제언 (Business Implications)

### 핵심 메시지: 2026~2028년이 마지막 골든윈도우

> 공급(신작 수)이 줄어드는 구간에서는 IP 계약 단가가 낮고,  
> 살아남는 IP의 희소 가치는 올라간다.  
> **지금이 저비용으로 독점 IP를 확보할 수 있는 마지막 시점이다.**

---

### 플랫폼별 제언

#### 카카오페이지 — 1위 지위를 방어하라
ITS 분석 결과 재혼황후 이후 전체 시장에서 즉각 +35편의 공급 확대가 일어났고,  
그 효과는 네이버시리즈에 집중됐습니다 (+25.6편 vs 카카오 +9.3편).  
성장 둔화기에는 신규 공급보다 **기존 인기 IP의 독점 유지**가 핵심 경쟁력입니다.

- 현재 인기 작품의 **독점 계약 갱신 및 세계관 확장**(외전·시리즈) 우선
- 웹소설 → 웹툰 → 드라마로 이어지는 **자체 IP 파이프라인** 구축
- 공급 감소 국면에서 **독점 콘텐츠 비중**이 플랫폼 락인(Lock-in)의 핵심

#### 네이버시리즈 — 공급 민감도를 강점으로
재혼황후 공급 신호에 가장 빠르게 반응한 플랫폼(β2=+25.6편, p<0.001).  
이는 신인 작가 공급 풀이 넓다는 증거입니다.  
시장 둔화기에 **신인 발굴 채널**을 선점하면 차기 대형 IP 탄생 확률을 높일 수 있습니다.

- **신인 작가 육성 프로그램** 강화 → 공급 안정화
- 월정액·구독 모델 강화로 기존 독자 **리텐션** 확보
- 히트작 기반 **공모전·오디션** 콘텐츠로 팬덤 참여 유도

#### 네이버웹툰 — 국내 포화, 글로벌로 전환
선재업고튀어 분석에서 드라마 방영이 즉각적 공급 확대를 만들지 못했습니다(β2 비유의).  
국내 로판 공급 포화가 가속화되는 시점, **웹툰화·글로벌 수출**이 실질적 성장 채널입니다.

- 로판 IP의 **웹툰화 전환 허브** 역할 강화 (웹소설 → 웹툰 계약 파이프라인)
- 일본·동남아 등 한류 수요 시장을 겨냥한 **글로벌 로판 번역 론칭** 가속
- 로판 전문 레이블 구축으로 **장르 브랜드** 차별화

---

### 공통 타임라인

| 시기 | 권고 행동 |
|---|---|
| **2026~2028** | 저비용 신인 IP 계약 집중, 독점 라인업 확보 (공급 감소 전 마지막 창) |
| **2029~2030** | 확보한 IP의 웹툰화·드라마화 파이프라인 가동, 수익화 전환 |
| **2031 이후** | 희소해진 로판 IP의 고부가가치 활용 (리마스터·글로벌 배급) |

---

## 디렉토리 구조

```
Rofan/
├── README.md
├── dashboard.html              ← 인터랙티브 대시보드
│
├── analysis/
│   ├── 01_*_crawler.py         ← 플랫폼별 크롤러 (Playwright)
│   ├── 02_01_timeseries.py     ← 월별 시계열 집계
│   ├── 02_02_stl.py            ← STL 분해 + Mann-Kendall
│   ├── 02_03_pelt.py           ← PELT 변동점 탐지
│   ├── 03_01_its.py            ← ITS 인과 분석 (전체)
│   ├── 03_02_its_by_platform.py← ITS 인과 분석 (플랫폼별)
│   ├── 04_01_prophet.py        ← Prophet 예측 + Hold-out
│   └── 05_01_decline_projection.py ← 쇠퇴기 시나리오
│
├── charts/                     ← 분석 결과 시각화
├── data/
│   └── processed/              ← 분석용 정제 데이터 (CSV)
│
├── reports/
│   ├── 02_result_and_insights.md   ← STL·PELT 결과 해석
│   ├── 03_result_and_insights.md   ← ITS 결과 해석
│   ├── 04_result_and_insights.md   ← Prophet 결과 해석
│   ├── 05_final_report.md          ← 최종 보고서
│   └── slide_deck_spec.md          ← 슬라이드 덱 제작 지침
│
└── study/                      ← 통계 방법론 학습 노트
    ├── 01_STL.md
    ├── 02_PELT.md
    ├── 03_ITS.md
    ├── 04_Prophet.md
    └── ...
```

---

## 분석 설계 원칙

- **파이프라인 동적 연결**: PELT 결과를 CSV로 저장 → Prophet에 자동 주입 (하드코딩 없음)
- **다중 검정 보정**: 8개 ITS 모델 동시 검정 → Holm-Bonferroni 보정 적용
- **Hold-out 검증**: Prophet 학습 전 2025년 데이터 분리 → MAPE 정량 검증
- **비모수 검정 병행**: OLS와 함께 Mann-Kendall 검정으로 추세 강건성 확인

---

## 로컬 실행 방법

```bash
# 가상환경 설치
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # Mac/Linux

# 패키지 설치
pip install -r requirements.txt   # 또는 uv pip install ...

# 전체 분석 파이프라인 실행
python analysis/05_run_all.py
```

> **참고:** 크롤러(`01_*_crawler.py`)는 별도 실행 불필요.  
> 수집 완료된 데이터가 `data/processed/`에 포함되어 있습니다.

---

*본 프로젝트는 데이터 분석 포트폴리오 목적으로 제작되었습니다.*  
*문의: [GitHub Issues](https://github.com/bookschooler/rofan/issues)*
