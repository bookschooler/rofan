# RESEARCH_TECH: 로맨스 판타지 장르 트렌드 분석 — 기술 실현 가능성 조사
작성일: 2026-04-20
조사자: DESA Researcher

---

## 1. 플랫폼별 크롤링 가능성

### 1-1. 카카오페이지 (page.kakao.com)

**판정: 가능 (단, 연재 시작일 필드 부재가 핵심 제약)**

| 항목 | 내용 |
|------|------|
| robots.txt 제한 | `/viewer`, `/store/kakaopage/webseries/viewer` 만 차단. 작품 목록 페이지는 허용 |
| JavaScript 렌더링 | SPA (Single Page Application). 그러나 내부 GraphQL API를 직접 호출하면 Selenium/Playwright 불필요 |
| 로그인 필요 | 작품 목록, 장르 필터 조회는 비로그인으로 가능. 열람(viewer)은 로그인 필요 (차단됨) |
| 추천 방법 | `requests` + GraphQL POST 요청 (공개 엔드포인트 `https://page.kakao.com/graphql`) |

**획득 가능 필드:**
- `series_id`, 작품명, 장르(subcategory), 작가, 연령등급, 구독자수, 마지막 연재일, 연재상태(연재중/완결)
- 획득 불가 필드: **연재 시작일** — GraphQL 응답에 포함되지 않음. 개별 작품 상세 페이지 별도 요청 필요하며 대규모 수집 시 차단 위험 있음

**근거:**
- robots.txt 직접 확인 (2026-04-20): `Disallow: /viewer`, `Disallow: /store/kakaopage/webseries/viewer` 만 명시
- GraphQL 엔드포인트 및 실제 작동 코드 확인 (출처: 박범준의 일상로그, "python 웹툰 크롤링 시리즈3: 카카오페이지", 2023-03-19, https://95pbj.tistory.com/65) — Tier 2 조건부 인용 (코드 검증 목적)

---

### 1-2. 네이버 시리즈 (series.naver.com)

**판정: 부분 가능 (작품 목록, 장르 태그 획득 가능. 연재 시작일 확인 필요)**

| 항목 | 내용 |
|------|------|
| robots.txt 제한 | `/my/` 하위 전체, `/cart`, `/viewer`, `/search` 차단. 작품 목록(`/novel/`, `/webtoon/`) 허용 |
| JavaScript 렌더링 | 일부 동적. 작품 목록 페이지는 서버사이드 렌더링(SSR) 비율이 높아 requests+BS4 시도 가능. 페이지네이션은 동적일 수 있어 Playwright 권장 |
| 로그인 필요 | 작품 목록 조회는 비로그인 가능. 구매 내역, 개인 서재는 차단 |
| 추천 방법 | requests + BeautifulSoup4 (1차 시도) → 실패 시 Playwright |

**획득 가능 예상 필드:**
- 작품명, 장르 태그, 연재 상태(완결/연재중), 작가, 작품 ID
- 연재 시작일: 작품 상세 페이지에 노출되는 경우가 있으나 플랫폼 정책상 변동 가능. 검증 필요

**근거:**
- robots.txt 직접 확인 (2026-04-20): `Allow: /` 선언 후 개인정보 관련 경로만 Disallow

---

### 1-3. 네이버 웹툰 (webtoons.com / comic.naver.com)

**판정: 가능 (기존 크롤링 사례 다수, Kaggle 데이터셋도 존재)**

| 항목 | 내용 |
|------|------|
| robots.txt 제한 | viewer, challenge 관리 기능, 로그인/로그아웃, 검색, 즐겨찾기, 계정 설정 차단. **작품 목록 및 장르 페이지는 명시적 허용** |
| JavaScript 렌더링 | 부분 동적. 메인 작품 목록은 정적 HTML에서 추출 가능한 사례 다수 확인 |
| 로그인 필요 | 목록 조회 불필요. viewer, 마이페이지 필요 |
| 추천 방법 | requests + BeautifulSoup4 (기본). 페이지네이션이 동적인 경우 Playwright 보완 |

**획득 가능 필드:**
- `id`, 작품명, 작가, 장르, 설명, 평점, 마지막 업데이트 날짜(`date`), 완결 여부(`completed`), 연령 등급, 무료여부
- **주의: `date` 필드는 마지막 업데이트 날짜이지 연재 시작일이 아님**

**근거:**
- robots.txt 직접 확인 (2026-04-20)
- Kaggle 데이터셋 존재 확인 (출처: Kaggle, "Webtoon Dataset in Korean", bmofinnjake, 2022, https://www.kaggle.com/datasets/bmofinnjake/naverwebtoon-datakorean)

---

### 1-4. 연재 시작일 획득 전략 (전 플랫폼 공통 이슈)

**이것이 이 프로젝트의 핵심 데이터 병목이다.**

"신작 수 시계열"을 만들려면 연재 시작일이 필요하다. 각 플랫폼의 목록 API/페이지에서 직접 노출되지 않는 경우가 많으므로 아래 대안을 순서대로 시도할 것을 권장한다.

| 우선순위 | 방법 | 설명 |
|---------|------|------|
| 1순위 | 작품 상세 페이지 개별 요청 | 각 작품 ID로 상세 페이지 접근 → 연재 시작일 파싱. 속도 느리고 차단 위험. `time.sleep(1~2초)` 필수 |
| 2순위 | 카카오페이지: 최초 에피소드 날짜 역추적 | 작품 ID로 에피소드 목록 요청 → 가장 오래된 에피소드 날짜를 연재 시작일로 대용 |
| 3순위 | 나무위키/구글 검색 보완 | 대규모 자동화 불가. 샘플 검증용 |
| 4순위 (권장 우회) | Kaggle 기존 데이터셋 활용 | 네이버 웹툰은 기존 데이터셋(아래 3항 참조)으로 시작 연도 정보 추론 가능 |

---

### 1-5. Kaggle 기존 데이터셋 현황

| 데이터셋 | 플랫폼 | 수록 작품 수 | 포함 필드 | 한계 |
|---------|--------|------------|----------|------|
| [Webtoon Dataset in Korean](https://www.kaggle.com/datasets/bmofinnjake/naverwebtoon-datakorean) | 네이버 웹툰 | 2,100+ | 제목, 장르, 작가, 평점, 날짜, 완결 여부 | 마지막 업데이트일이지 시작일 아님. 2022년 12월 기준 |
| [NAVER Webtoon Dataset with OSMU records](https://www.kaggle.com/datasets/jongbinwon/naver-webtoon-dataset-with-osmu-records) | 네이버 웹툰 | 1,564 | 웹툰 메타 + OSMU(영화/드라마/게임 파생 여부) 레이블 33개 컬럼 | 2023년 9월 기준. 카카오페이지 미포함 |
| [Manhwa Industry Evolution (2000-2026)](https://www.kaggle.com/datasets/artheon/manhwa-industry-evolution-2000-2026) | 복합 | 미확인 | 만화 산업 시계열 포함 가능성 | 직접 확인 필요 |

**카카오페이지 및 네이버 시리즈 전용 Kaggle 데이터셋은 현재 확인되지 않음.** 직접 수집 필요.

---

## 2. 분석 방법별 Python 라이브러리

### 2-1. STL 분해 (Seasonal-Trend decomposition using LOESS)

**판정: 가능, 난이도 하**

| 라이브러리 | 설치 | 핵심 사용법 | 특징 |
|-----------|------|-----------|------|
| `statsmodels.tsa.seasonal.STL` | `pip install statsmodels` | `STL(series, period=12).fit()` | 공식 지원, 문서 충실, 초중급 적합 |
| `stl` (별도 패키지) | `pip install stl` | STL 단독 구현 | statsmodels보다 단순하지만 생태계 작음 |

**권장: `statsmodels` 사용.** GPU 불필요, i7-1260P에서 충분히 실행 가능.

**근거:** statsmodels 공식 문서 (출처: statsmodels.org, "Seasonal-Trend decomposition using LOESS (STL)", https://www.statsmodels.org/dev/examples/notebooks/generated/stl_decomposition.html)

---

### 2-2. 변동점 감지 (Change Point Detection) — ruptures

**판정: 가능, 난이도 하-중**

```python
pip install ruptures

import ruptures as rpt

# 3줄로 변동점 감지 가능
algo = rpt.Pelt(model="rbf").fit(signal)   # 변동점 개수 모를 때
result = algo.predict(pen=10)              # pen: penalty 값

# 또는 변동점 개수를 지정할 때
algo = rpt.Dynp(model="l2").fit(signal)
result = algo.predict(n_bkps=3)
```

- 초중급도 3~5줄로 사용 가능
- GPU 불필요, 순수 NumPy 기반
- 공식 문서에 Jupyter Notebook 예제 포함 (Binder 실행 가능)
- 주요 알고리즘: `Pelt` (변동점 수 미지정 시), `Dynp` (개수 지정 시), `Binseg` (이진 분할)

**근거:** ruptures 공식 문서 (출처: centre-borelli.github.io, "Basic usage - ruptures", https://centre-borelli.github.io/ruptures-docs/getting-started/basic-usage/)
논문: Truong et al., "ruptures: change point detection in Python", 2018, arXiv:1801.00826

---

### 2-3. Interrupted Time Series (중단 시계열 분석) — ITS

**판정: 가능, 난이도 중**

`statsmodels`의 OLS(Ordinary Least Squares, 보통최소제곱법)로 구현.
별도 ITS 전용 패키지는 없으며, 더미 변수를 수동으로 생성하여 회귀식을 구성하는 방식.

```python
import pandas as pd
import statsmodels.formula.api as smf

# 이벤트 발생 시점 기준으로 더미 변수 생성
df['time'] = range(len(df))                        # 시간 인덱스
df['intervention'] = (df['date'] >= event_date).astype(int)   # 이벤트 전후
df['time_after'] = df['time'] * df['intervention']  # 기울기 변화

# OLS 회귀
model = smf.ols('y ~ time + intervention + time_after', data=df).fit()
print(model.summary())  # p-value, 계수 확인
```

- GPU 불필요
- 초중급에게는 더미 변수 설계 개념 이해가 필요하므로 난이도 중으로 분류

**근거:** statsmodels 공식 문서 (출처: statsmodels.org, "Time Series analysis tsa", https://www.statsmodels.org/stable/tsa.html). ITS 구현 패턴 참조: xboard.dev, "Interrupted Time Series (ITS) in Python", https://www.xboard.dev/posts/2020_01_01_interrupted-time-series-python-part-I/

---

### 2-4. Bass Diffusion Model (배스 확산 모형)

**판정: 가능, 난이도 중 (전용 라이브러리 없음, scipy 직접 구현 필요)**

전용 Python 패키지 없음. `scipy.optimize.curve_fit`으로 직접 구현.

```python
import numpy as np
from scipy.optimize import curve_fit

# Bass 모형: dN/dt = (p + q * N/M) * (M - N)
# p: 혁신 계수 (innovation coefficient)
# q: 모방 계수 (imitation coefficient)
# M: 잠재 시장 크기 (market potential)
def bass_model(t, p, q, M):
    return M * (1 - np.exp(-(p + q) * t)) / (1 + (q / p) * np.exp(-(p + q) * t))

params, _ = curve_fit(bass_model, t_data, cumulative_data, p0=[0.03, 0.4, 1000])
p, q, M = params
```

- GPU 불필요. scipy만 설치되면 실행 가능
- **단, 로판 장르의 경우 Bass 모형의 적합성이 낮을 수 있음**: Bass 모형은 신제품 확산 곡선(S-curve) 가정. 장르 신작 수 시계열이 S-curve 형태가 아닐 경우 모형 적합도(R²) 저하. 사용 전 시각적 형태 확인 필요

**근거:** GitHub, "Bass-Diffusion-model-for-short-life-cycle-products-sales-prediction", NForouzandehmehr, https://github.com/NForouzandehmehr/Bass-Diffusion-model-for-short-life-cycle-products-sales-prediction/blob/master/bass.py

---

### 2-5. Prophet (Facebook/Meta Prophet)

**판정: 가능, 난이도 하 (초보자에게 가장 친화적)**

```bash
pip install prophet
```

```python
from prophet import Prophet
import pandas as pd

# 입력 형식: 'ds'(날짜), 'y'(값) 컬럼 필수
df = pd.DataFrame({'ds': dates, 'y': counts})

model = Prophet()
model.fit(df)

future = model.make_future_dataframe(periods=12, freq='M')
forecast = model.predict(future)
model.plot(forecast)
```

- GPU 완전 불필요. i7-1260P에서 월별 시계열(수백 행) 수초 내 완료
- **이벤트 효과 반영**: `add_regressor()` 또는 `add_seasonality()`로 드라마화 이벤트 더미 추가 가능
- Windows 환경에서 설치 시 `pystan` 의존성으로 오류 발생할 수 있음 → `conda install -c conda-forge prophet` 권장

**근거:** Meta Prophet 공식 문서 (출처: facebook.github.io, "Quick Start - Prophet", http://facebook.github.io/prophet/docs/quick_start.html)

---

### 2-6. Event Study (이벤트 스터디)

**판정: 가능, 난이도 중 (전용 패키지 제한적, 수동 구현 권장)**

금융 분야 이벤트 스터디 전용 패키지(`eventstudy`)가 존재하나, 주식 데이터 전용으로 설계됨. 웹소설 시계열에는 수동 구현이 현실적.

```python
# 이벤트 윈도우 전후 평균 비교 방식 (수동 구현)
# CAR: Cumulative Abnormal Return의 장르 버전 = 누적 초과 신작 수

event_window = df[(df['date'] >= event_date - window) & 
                  (df['date'] <= event_date + window)]
baseline = df[df['date'] < event_date - window]['new_works'].mean()
event_study_result = event_window['new_works'] - baseline
```

- ITS와 함께 사용하면 이벤트 전후 수준 변화(level change)와 트렌드 변화(slope change) 모두 포착 가능
- statsmodels OLS 기반 ITS가 사실상 Event Study와 동등한 역할을 함 → 중복 사용은 불필요

---

## 3. 드라마/영화화 데이터

### 3-1. KMDB (한국영화데이터베이스) API

**판정: 가능 (회원가입 및 API 키 발급 필요)**

| 항목 | 내용 |
|------|------|
| 운영 기관 | 한국영상자료원 (공공기관) — Tier 1 출처 |
| 접근 방식 | REST API (JSON 응답) |
| 발급 절차 | 회원가입 → 개발계정 신청 → 심의 → 서비스키 발급 |
| 일일 트래픽 | 개발계정 기준 1,000건/일 |
| 운영계정 | 실서비스 목적 시 별도 신청 |
| 제공 데이터 | 영화 제명, 제작년도, 제작사, 크레딧, 줄거리, 장르, 키워드 등 |

**한계:** KMDB는 영화 중심 DB. **드라마(OTT/방송)** 데이터는 포함이 제한적. 웹소설 원작 드라마 목록은 별도 수집 필요.

**근거:** KMDB 공식 API 가이드 (출처: 한국영상자료원, "Open API 가이드 - KMDb", https://www.kmdb.or.kr/info/api/guide2)

---

### 3-2. 웹소설 원작 드라마 목록 수집

**판정: 부분 가능 (자동화 어려움, 수동 큐레이션 + 보완 데이터 조합 필요)**

| 방법 | 가능 여부 | 비고 |
|------|----------|------|
| KMDB API | 부분 가능 | 영화는 원작 키워드로 검색 가능. 드라마는 제한 |
| Kaggle OSMU 데이터셋 | 가능 | 네이버 웹툰 기준 OSMU 레이블 포함 (1,564건, 2023년 9월 기준). 드라마/영화/게임/애니 파생 여부 표기. URL: https://www.kaggle.com/datasets/jongbinwon/naver-webtoon-dataset-with-osmu-records |
| 위키백과 "소설 원작 드라마 목록" | 출처 불가 (Tier 3) | 직접 인용 금지. 단, URL로 확인 후 1차 출처 교차 검증용 |
| 나무위키 | 출처 불가 (Tier 3) | 동일 |
| 방송통신위원회 / KOCCA | 확인 필요 | 공식 통계 보고서에 원작 유형 분류 포함 가능성 있음 |

**권장 접근법:**
1. Kaggle OSMU 데이터셋으로 네이버 웹툰 원작 목록 확보
2. 카카오페이지 원작은 수동 큐레이션 (규모가 크지 않아 현실적)
3. 드라마 방영일은 KOFIC(영화진흥위원회) 또는 각 방송사 공식 보도자료 기준

---

## 4. 종합 실현 가능성 판정

| 항목 | 판정 | 주요 제약 |
|------|------|----------|
| 카카오페이지 작품 목록 크롤링 | 가능 | GraphQL 직접 호출. requests만으로 충분 |
| 카카오페이지 연재 시작일 | 부분 가능 | 에피소드 목록에서 역추적 필요. 속도 제한 고려 |
| 네이버 시리즈 크롤링 | 부분 가능 | requests+BS4 또는 Playwright. 연재 시작일 확인 필요 |
| 네이버 웹툰 크롤링 | 가능 | 기존 코드/데이터셋 다수. 연재 시작일은 에피소드 역추적 |
| STL 분해 | 가능 | statsmodels, 3줄 코드 |
| 변동점 감지 (ruptures) | 가능 | 5줄 이내. GPU 불필요 |
| ITS (Interrupted Time Series) | 가능 | statsmodels OLS + 더미 변수 수동 생성 |
| Bass Diffusion Model | 가능 | scipy.optimize. 장르 적합성 사전 검증 필요 |
| Prophet | 가능 | 가장 쉬움. Windows 설치 주의 (conda 권장) |
| Event Study | 가능 | ITS와 겹치므로 중복 제거 권장 |
| KMDB API | 가능 | 회원가입 필요. 드라마 데이터 제한 |
| 웹소설 원작 드라마 목록 | 부분 가능 | 자동화 어려움. Kaggle OSMU + 수동 보완 |

---

## 5. Sophie를 위한 핵심 정리

### 왜 이 기술 조사가 중요한가

데이터를 못 구하면 분석이 시작조차 안 된다. 특히 이 프로젝트의 핵심 지표인 "장르별 신작 수 시계열"은 **연재 시작일**이 있어야 만들 수 있는데, 이것이 어떤 플랫폼에서도 목록 API에 바로 노출되지 않는다. 이 제약을 면접에서 설명할 수 있어야 한다.

### 면접에서 "왜 이 방법을 썼냐"에 대한 답변 뼈대

- **변동점 감지에 ruptures를 쓴 이유**: 시계열에서 구조적 변화가 언제 발생했는지를 통계적으로 찾아주는 라이브러리. 사전에 변화 시점을 모를 때 Pelt 알고리즘은 penalty 값 하나로 자동 탐지 가능. 단순 시각화로 "여기서 많아진 것 같다"고 말하는 것보다 훨씬 설득력 있다.
- **ITS를 쓴 이유**: "이 드라마가 방영된 이후 로판 신작이 늘었다"는 인과적 주장을 하려면 단순 상관관계가 아닌 이벤트 전후 추세 변화를 검정해야 한다. ITS는 그것을 회귀계수와 p-value로 보여주는 가장 표준적인 방법이다.
- **Prophet을 추가하는 이유**: ruptures/ITS가 과거 설명이라면 Prophet은 미래 예측이다. 두 가지를 함께 쓰면 "트렌드가 언제 시작됐고(ITS), 앞으로 어떻게 될 것인가(Prophet)"를 한 프로젝트에서 답할 수 있어 스토리가 완결된다.

### 오늘의 개념: GraphQL

REST API는 서버가 정해준 URL로 데이터를 받아오는 방식. GraphQL은 클라이언트가 "나는 이 필드들만 줘"라고 쿼리를 직접 작성해서 보내는 방식. 카카오페이지가 GraphQL을 쓰기 때문에 Selenium 없이 requests만으로 원하는 데이터를 JSON으로 받을 수 있다. 단점은 쿼리 문법을 알아야 하고, 서버가 쿼리 구조를 바꾸면 코드가 깨진다.

---

## 참고 자료

- robots.txt 직접 확인 (page.kakao.com, series.naver.com, webtoons.com), 2026-04-20
- 박범준의 일상로그, "python 웹툰 크롤링 시리즈3: 카카오페이지", 2023-03-19, https://95pbj.tistory.com/65
- Kaggle, "Webtoon Dataset in Korean" (bmofinnjake), 2022, https://www.kaggle.com/datasets/bmofinnjake/naverwebtoon-datakorean
- Kaggle, "NAVER Webtoon Dataset with OSMU records" (jongbinwon), 2023, https://www.kaggle.com/datasets/jongbinwon/naver-webtoon-dataset-with-osmu-records
- statsmodels 공식 문서, "STL decomposition", https://www.statsmodels.org/dev/examples/notebooks/generated/stl_decomposition.html
- ruptures 공식 문서, "Basic usage", https://centre-borelli.github.io/ruptures-docs/getting-started/basic-usage/
- Truong et al., "ruptures: change point detection in Python", arXiv:1801.00826, 2018
- Meta Prophet 공식 문서, "Quick Start", http://facebook.github.io/prophet/docs/quick_start.html
- 한국영상자료원, "Open API 가이드 - KMDb", https://www.kmdb.or.kr/info/api/guide2
