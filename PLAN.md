# 로판 데이터 분석 실행 계획

> 계획 수립일: 2026-04-21  
> 프로젝트명: "웹소설 → 웹툰화 → 드라마화" IP 파이프라인의 로판 시장 영향력 분석  
> 개발자: Python 초중급, GPU 없음 (i7-1260P, 32GB RAM)

---

## 📊 전체 Phase 개요

| Phase | 목표 | 주요 산출물 | 예상 소요시간 | 난이도 |
|-------|------|-----------|------------|------|
| **Phase 1: 데이터 수집 & 전처리** | 3개 플랫폼에서 로판 작품 데이터 크롤링 + 기본 정제 | `data/` 폴더 (3개 CSV) + `notebooks/01_data_collection.ipynb` | 4-5일 | 중 |
| **Phase 2: 현상 파악** | 시계열 분해(STL) + 변동점 감지(ruptures) → 로판 인기도 변화 추이 파악 | `analysis/02_*.py` + 6개 차트 | 2-3일 | 하 |
| **Phase 3: 원인 파악** | Interrupted Time Series + 이벤트 영향도 분석 → 재혼황후 웹툰화 등 주요 이벤트 영향 정량화 | `analysis/03_*.py` + 8개 차트 | 3-4일 | 중 |
| **Phase 4: 예측** | Prophet 단독 → 로판 시장 성장 예측 | `analysis/04_*.py` + 2개 차트 | 1-2일 | 중 |
| **Phase 5: 보고서 & 대시보드** | 분석 결과 정리 + 시각화 대시보드 | `report/REPORT.md` + `dashboard.html` | 1-2일 | 하 |
| **전체** | — | — | **약 12-17일** | — |

---

## 🎯 Chapter별 분석 전략

### Chapter 1: 현상 파악 (Phase 2)
**질문:** "로판 인기도는 언제 급성장했고, 어디서 변화점이 생겼는가?"

- **STL 분해**: 트렌드(T) + 계절성(S) + 잔차(R) 분리
  - 목표: 로판의 계절적 변동과 장기 트렌드 분리
  - 라이브러리: `statsmodels.tsa.seasonal.STL()`
  
- **변동점 감지**: PELT 알고리즘
  - 목표: 인기도가 급격히 변한 정확한 시점 탐지
  - 라이브러리: `ruptures.Pelt()`
  - 기대 산출물: ~3개 주요 변동점 (예: 2019.10, 2021.01 등)

---

### Chapter 2: 원인 파악 (Phase 3)
**질문:** "그 변화점들은 정말 웹툰화, 드라마화 같은 이벤트 때문이었는가?"

- **Interrupted Time Series (ITS)**
  - 방법: 각 이벤트를 더미변수로 인코딩 → OLS 회귀
  - 의미: 이벤트 직후 인기도가 통계적으로 유의미하게 변했는지 검정
  - 라이브러리: `statsmodels.formula.api.ols()`
  - 산출물: p-value + 계수 (95% CI)

- **주요 이벤트 타임라인** (자세한 목록은 [이벤트 목록](#주요-이벤트-타임라인) 참조)
  - E001 재혼황후 웹툰 연재 시작: 2019-10-25
  - E002 판사 이한영 드라마 방영: 2026-01-02 (ITS 분석 제외 — 현재 시점 3개월 전, 분석창 확보 불가)
  - E003 선재 업고 튀어 드라마 방영: 2024-04-08
  - E004 밀리의 서재 웹소설 탭 출시: 2025-06-30

---

### Chapter 3: 예측 (Phase 4)
**질문:** "앞으로 로판 시장은 어떻게 성장할 것인가?"

- **Prophet (Facebook)**
  - 장점: 계절성 + 휴일 효과 + 외부 변수 처리 가능
  - 라이브러리: `prophet.Prophet()`
  - 산출물: 2026-2027년 로판 인기도 점추정 + 95% 신뢰구간
  - Bass Diffusion 제외 이유: 수요 확산 모델을 공급 지표(신작 수)에 적용하면 해석 오류 발생

---

## 📝 Phase 1: 데이터 수집 & 전처리 (4-5일)

### 1-1. 개발 환경 설정 (0.5일)
**목표**: 필요 라이브러리 설치 및 폴더 구조 생성

**태스크**:
```powershell
# 어디서든 실행 가능
cd C:\Users\user\Desktop\pjt\Rofan

# 1. 폴더 생성
mkdir data, notebooks, analysis, charts, report

# 2. Python 가상환경 생성 (선택사항, 권장)
python -m venv .venv
av  # 또는 .\.venv\Scripts\Activate.ps1

# 3. 필수 라이브러리 설치
pip install requests beautifulsoup4 pandas numpy matplotlib seaborn scipy statsmodels ruptures prophet scikit-learn koreanize-matplotlib -q
```

**예상 소요시간**: 5-10분

**산출물**:
- `C:\Users\user\Desktop\pjt\Rofan\.venv\` (가상환경)
- `C:\Users\user\Desktop\pjt\Rofan\data\`
- `C:\Users\user\Desktop\pjt\Rofan\notebooks\`
- `C:\Users\user\Desktop\pjt\Rofan\analysis\`
- `C:\Users\user\Desktop\pjt\Rofan\charts\`

**주의사항**:
- 가상환경 사용 시 이후 모든 python/pip 명령은 `Activate.ps1` 후 실행
- koreanize-matplotlib은 노트북 첫 셀에서 import (한글 폰트 깨짐 방지)

---

### 1-2. 카카오페이지 크롤링 (1.5일)
**목표**: 카카오페이지의 로판 작품 메타데이터 수집 (400-500건 목표)

**데이터 수집 방법**:
- 플랫폼: **카카오페이지** (웹소설)
- 엔드포인트: GraphQL API (`https://api.kakaopage.com/graphql`)
- 크롤링 대상 작품: 
  - 장르 필터: "로맨스판타지"
  - 정렬 기준: **연재 시작일순 전체 목록** (인기도 필터 없이 — 서바이버십 편향 방지)
  - 수집 기간: 2013-01-01 ~ 2026-04-21

**태스크**:

```python
# notebooks/01_kakaopage_crawler.ipynb

# 라이브러리
import requests
import json
import pandas as pd
from datetime import datetime

# GraphQL 쿼리 예시 (카카오페이지 API 구조)
# - work_id, title, author, genre, start_date, complete_status, rating, bookmarks
# - pagination을 통해 500개 작품 수집

# 주의: API 레이트 제한 (초당 1-2회 요청)
# → time.sleep(0.5) 사용
```

**기대 데이터**:
```
columns:
  - work_id (str): '{platform_code}_{raw_id}' 형식. 예: 'kp_12345'
  - platform (str): 'kakaopage'
  - content_type (str): 'novel'
  - title (str): 작품명 (원문 그대로)
  - author (str): 저자 (필명 기준)
  - genre_raw (str): 플랫폼 원본 장르 문자열
  - start_date (date): 연재 시작일 ← 시계열 분석 핵심
  - start_date_source (str): 'detail_page' / 'episode_backtrack' / 'unknown'
  - complete_status (str): 'ongoing' / 'completed' / 'hiatus'
  - complete_date (date): 완결일 (완결 시에만)
  - rating (float): 평점 (0.0~10.0)
  - rating_count (int): 평점 참여자 수
  - bookmark_count (int): 관심 등록 수 ← ITS primary_metric 후보
  - episode_count (int): 총 에피소드 수 ← bookmark 없을 때 대체 지표
  - primary_metric (float): 분석용 통일 인기도 지표 (후처리 생성)
  - primary_metric_source (str): 'bookmark_count' / 'episode_count'
  - tags (str): 쉼표 구분 태그. 예: '계약결혼,빙의,환생'
  - last_crawled_at (datetime): 수집 시점 UTC
```

**산출물**:
- `data/kakaopage_works.csv` (~500행)
- `notebooks/01_kakaopage_crawler.ipynb` (실행 노트북)

**예상 소요시간**: 1-1.5일 (API 레이트 제한, 에러 처리)

**주의사항**:
- API 변경 시 대체: requests + BeautifulSoup4로 페이지 직접 파싱
- 연재 시작일 누락 데이터: "연재 시작일 불명" 표시
- 작품 중복 제거 (title + author + platform 기준 — platform 빠지면 동일 작품이 카카오/네이버 양쪽 있을 때 하나가 소실됨)
- **전체 목록 조회 불가 시 대안**: 연도별 코호트 수집 (2013년, 2014년 … 2026년 각각 신작 필터링)

---

### 1-3. 네이버 시리즈 크롤링 (1.5일)
**목표**: 네이버 시리즈의 로판 작품 메타데이터 수집 (200-300건 목표)

**데이터 수집 방법**:
- 플랫폼: **네이버 시리즈** (웹소설)
- 방식: requests + BeautifulSoup4 페이지 파싱
- 크롤링 대상 작품:
  - 장르 필터: "로맨스판타지" 또는 "로판"
  - 정렬 기준: **연재 시작일순 전체 목록** (인기도 필터 없이 — 서바이버십 편향 방지)
  - 수집 기간: 2013-01-01 ~ 2026-04-21

**태스크**:

```python
# notebooks/01_naver_series_crawler.ipynb

import requests
from bs4 import BeautifulSoup
import pandas as pd

# URL: https://series.naver.com/genre/list.nhn?genre=로맨스판타지
# 페이지당 20개 작품, 15페이지 수집 (300개)

# 수집 대상:
# - title, author, rating, bookmarks, start_date, status
# - 각 작품의 상세 페이지 접속하여 start_date 확인 필요 (리스트 페이지에는 미제공)
```

**기대 데이터**:
```
columns: (카카오페이지와 동일 구조, platform='naver_series')
  - work_id (str): 'ns_{product_no}' 형식
  - platform (str): 'naver_series'
  - bookmark_count: 비공개 → NULL (primary_metric은 episode_count로 대체)
  - 나머지: 카카오페이지 스키마와 동일
```

**산출물**:
- `data/naver_series_works.csv` (~300행)
- `notebooks/01_naver_series_crawler.ipynb`

**예상 소요시간**: 1-1.5일 (상세 페이지 파싱으로 인한 시간 소비)

**주의사항**:
- 사용자 에이전트 헤더 필수: `User-Agent: Mozilla/5.0...`
- 요청 간 1초 딜레이 필수 (서버 부하 방지)
- 완결작품만 완결일 수집 가능

---

### 1-4. 네이버 웹툰 크롤링 (1.5일)
**목표**: 네이버 웹툰의 로판 웹툰 메타데이터 수집

**데이터 수집 방법**:
- 플랫폼: **네이버 웹툰** (웹툰, 웹소설 기반 웹툰화 작품 필터링)
- 방식: Kaggle OSMU 데이터셋 활용 + 추가 크롤링
- 크롤링 대상 작품:
  - 원작이 웹소설인 웹툰만 필터링
  - 예: "재혼황후", "판사 이한영" 등

**태스크**:

```python
# notebooks/01_naver_webtoon_crawler.ipynb

# Option A: Kaggle 데이터셋 활용
# - OSMU 데이터셋 (1,564건 웹툰, 2022-2023 기준)
# - 출처 링크: https://www.kaggle.com/datasets/

# Option B: requests + BeautifulSoup로 보완 크롤링
# - URL: https://www.webtoon.naver.com/
# - 장르: 로맨스판타지
# - 수집: 최근 100-150개 웹툰

import requests
from bs4 import BeautifulSoup
import pandas as pd
```

**기대 데이터**:
```
columns: (카카오페이지와 동일 구조, platform='naver_webtoon', content_type='webtoon')
  - work_id (str): 'nw_{webtoon_id}' 형식
  - platform (str): 'naver_webtoon'
  - content_type (str): 'webtoon'
  - original_work_id (str): ip_mapping 테이블 조인 후 채움 (원작 웹소설 work_id)
  - 나머지: 카카오페이지 스키마와 동일
```

**산출물**:
- `data/naver_webtoon_works.csv` (~150행)
- `notebooks/01_naver_webtoon_crawler.ipynb`

**예상 소요시간**: 1-1.5일

**주의사항**:
- 원작 웹소설 정보는 나무위키 또는 수작업으로 매칭 필요
- Kaggle 데이터셋 다운로드 시 account 필요 (무료 가입 가능)

---

### 1-5. 외부 데이터 수집 (1일)
**목표**: 드라마/영화화 정보 및 주요 이벤트 날짜 수집

**데이터 수집 방법**:

#### A. KMDB API (드라마/영화 메타데이터)
```python
# 출처: https://www.kmdb.or.kr/API
# 인증: API 키 필수 (가입 후 발급, 무료)

# 검색 대상:
# - "재혼황후", "판사 이한영", "선재 업고 튀어" 등
# - 결과: 드라마/영화화 정보 (방영일, 채널, 배우 등)

import requests

api_key = "YOUR_KMDB_API_KEY"
# 나중에 secrets 관리 필요

# 예시:
# query_titles = ["재혼황후", "판사 이한영", "선재 업고 튀어"]
```

#### B. 나무위키 + 기사 수작업 수집
```python
# 주요 이벤트 타임라인
events = [
    {"event_id": "E001", "date": "2019-10-25", "title": "재혼황후 웹툰 네이버 웹툰 연재 시작", "platform": "naver_webtoon", "impact": "high"},
    # E002 판사 이한영: 방영일 2026-01-02 — ITS 분석 제외 (분석창 확보 불가)
    {"event_id": "E003", "date": "2024-04-08", "title": "선재 업고 튀어 드라마 방영", "platform": "tvn", "impact": "medium"},
    {"event_id": "E004", "date": "2025-06-30", "title": "밀리의 서재 웹소설 탭 출시", "platform": "millie", "impact": "medium"},
]
```

**산출물**:
- `data/events_timeline.csv` (20-30행)
- `data/drama_adaptations.csv` (10-20행)

**예상 소요시간**: 0.5-1일 (수작업)

**주의사항**:
- KMDB API 키 발급 먼저 진행 (하루 소요 가능)
- 없으면 나무위키/기사 기반으로 수동 작성
- 이벤트 날짜는 정확도 ★★★★★ 필수 (Phase 3에서 critical)

---

### 1-6. 데이터 통합 & 전처리 (0.5일)
**목표**: 3개 플랫폼 데이터 통합 + 기본 정제

**태스크**:

```python
# notebooks/01_data_integration.ipynb

import pandas as pd
import numpy as np
from datetime import datetime

# Step 1: 각 플랫폼 CSV 로드
kakao = pd.read_csv('data/kakaopage_works.csv')
naver_series = pd.read_csv('data/naver_series_works.csv')
naver_webtoon = pd.read_csv('data/naver_webtoon_works.csv')

# Step 2: 스키마 통일 (모든 df가 동일 컬럼 순서)
# - work_id, title, author, genre, start_date, complete_status, complete_date, rating, primary_metric, platform, last_updated

# Step 3: 데이터 타입 변환
# - start_date, complete_date → datetime64
# - rating → float
# - genre → str

# Step 4: 결측치 처리
# - 연재 시작일 누락: NaT 또는 '2013-01-01' (하한값) 표시 + 'unknown_start' 플래그
# - 평점 0인 경우: 수집 중 오류로 간주, 행 제거

# Step 5: 중복 제거
# - title + author + platform 기준 (같은 작품이 여러 플랫폼에 있을 수 있음)

# Step 6: 통합 파일 저장
merged = pd.concat([kakao, naver_series, naver_webtoon], ignore_index=True)
merged = merged.drop_duplicates(subset=['title', 'author', 'platform'], keep='first')
merged.to_csv('data/all_works_integrated.csv', index=False, encoding='utf-8-sig')

print(f"총 작품 수: {len(merged)}")
print(f"플랫폼별 분포:\n{merged['platform'].value_counts()}")
print(f"연재 시작년도 분포:\n{merged['start_date'].dt.year.value_counts().sort_index()}")
```

**산출물**:
- `data/all_works_integrated.csv` (총 900-1000행, 필터링 후)
- `notebooks/01_data_integration.ipynb`
- `data/data_quality_report.txt` (결측치, 이상치 현황)

**예상 소요시간**: 0.5일

**주의사항**:
- 결측치 처리는 논리적으로 (임의 대체 금지)
- 통합 파일에서는 "platform" 컬럼으로 출처 추적 가능하게 유지

---

### Phase 1 최종 산출물 체크리스트

- [ ] `data/kakaopage_works.csv` (500행 × 18열)
- [ ] `data/naver_series_works.csv` (300행 × 18열)
- [ ] `data/naver_webtoon_works.csv` (150행 × 18열)
- [ ] `data/events_timeline.csv` (20-30행)
- [ ] `data/ip_mapping.csv` (웹소설→웹툰→드라마 파이프라인 매핑)
- [ ] `data/all_works_integrated.csv` (900-1000행, 통합 데이터)
- [ ] `notebooks/01_kakaopage_crawler.ipynb`
- [ ] `notebooks/01_naver_series_crawler.ipynb`
- [ ] `notebooks/01_naver_webtoon_crawler.ipynb`
- [ ] `notebooks/01_data_integration.ipynb`
- [ ] `data/data_quality_report.txt`

**예상 총 소요시간**: 4-5일

---

## 📈 Phase 2: 현상 파악 (STL + 변동점 감지, 2-3일)

### 2-1. 시계열 데이터 준비 (0.5일)

**목표**: 일별/주별/월별 집계 시계열 생성

**태스크**:

```python
# analysis/02_01_timeseries_prep.py

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# 1. 통합 데이터 로드
works = pd.read_csv('data/all_works_integrated.csv')
works['start_date'] = pd.to_datetime(works['start_date'])

# 2. 필터링: 로판만 추출
# → genre 컬럼에 '로맨스', '판타지', '로판' 포함 여부 확인
works_rofan = works[works['genre'].str.contains('로맨스|판타지|로판', case=False, na=False)]
# 또는 수작업으로 태깅된 'is_rofan' 컬럼 사용

# 3. 월별 신작 수 계산
monthly_new_works = works_rofan.groupby(works_rofan['start_date'].dt.to_period('M')).size()
monthly_new_works.index = monthly_new_works.index.to_timestamp()

# 4. 월별 평균 평점 계산
monthly_avg_rating = works_rofan.groupby(works_rofan['start_date'].dt.to_period('M'))['rating'].mean()
monthly_avg_rating.index = monthly_avg_rating.index.to_timestamp()

# 5. 월별 평균 관심수 계산
monthly_avg_bookmarks = works_rofan.groupby(works_rofan['start_date'].dt.to_period('M'))['bookmarks'].mean()
monthly_avg_bookmarks.index = monthly_avg_bookmarks.index.to_timestamp()

# 6. 완결작품 수 누적
monthly_completed = works_rofan[works_rofan['complete_status'] == 'completed'].groupby(
    works_rofan['start_date'].dt.to_period('M')
).size()
monthly_completed.index = monthly_completed.index.to_timestamp()

# 저장
ts_data = pd.DataFrame({
    'date': monthly_new_works.index,
    'new_works_count': monthly_new_works.values,
    'avg_rating': monthly_avg_rating.values,
    'avg_bookmarks': monthly_avg_bookmarks.values,
    'completed_works': monthly_completed.values,
})

ts_data.to_csv('data/timeseries_monthly.csv', index=False)
print(f"시계열 범위: {ts_data['date'].min()} ~ {ts_data['date'].max()}")
print(f"총 월별 데이터점: {len(ts_data)}")
```

**기대 산출물**:
- `data/timeseries_monthly.csv` (150-160행 × 5열, 2013년 1월 ~ 2026년 4월)

**예상 소요시간**: 0.5일

---

### 2-2. STL 분해 분석 (1일)

**목표**: 로판 인기도의 트렌드, 계절성, 잔차 분리

**개념 설명 (Sophie용)**:
> **STL (Seasonal and Trend decomposition using Loess)**  
> 시계열을 3가지로 분리: 장기 추세(T) + 계절적 변동(S) + 설명되지 않는 변동(R)  
> 예: 로판 신작 수 = [전체 증가 추세] + [특정 월에 많이 나오는 패턴] + [특이한 달의 변동]

**태스크**:

```python
# analysis/02_02_stl_decomposition.py

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from statsmodels.tsa.seasonal import STL
import koreanize_matplotlib

# 1. 데이터 로드
ts_data = pd.read_csv('data/timeseries_monthly.csv', parse_dates=['date'])
ts_data = ts_data.set_index('date')

# 2. 분석 대상 지표 선택 (3개 지표 모두 분석)
metrics = ['new_works_count', 'avg_rating', 'avg_bookmarks']

for metric in metrics:
    # 3. STL 분해 실행
    # seasonal: 계절성 기간 (12개월 = 1년 주기)
    stl = STL(ts_data[metric], seasonal=13, trend=25)
    result = stl.fit()
    
    # 4. 분해 결과 시각화
    fig, axes = plt.subplots(4, 1, figsize=(12, 10))
    fig.suptitle(f'STL Decomposition: {metric}', fontsize=14, fontweight='bold')
    
    # 원본 데이터
    ts_data[metric].plot(ax=axes[0], color='blue', linewidth=2)
    axes[0].set_ylabel('Original')
    axes[0].grid(True, alpha=0.3)
    
    # 트렌드
    result.trend.plot(ax=axes[1], color='red', linewidth=2)
    axes[1].set_ylabel('Trend')
    axes[1].grid(True, alpha=0.3)
    
    # 계절성
    result.seasonal.plot(ax=axes[2], color='green', linewidth=1.5)
    axes[2].set_ylabel('Seasonal')
    axes[2].grid(True, alpha=0.3)
    
    # 잔차
    result.resid.plot(ax=axes[3], color='orange', linewidth=1)
    axes[3].set_ylabel('Residual')
    axes[3].grid(True, alpha=0.3)
    axes[3].axhline(y=0, color='black', linestyle='--', alpha=0.5)
    
    plt.tight_layout()
    plt.savefig(f'charts/02_stl_decomposition_{metric}.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 5. 분해 결과 저장
    decomp_df = pd.DataFrame({
        'date': ts_data.index,
        f'{metric}_original': ts_data[metric],
        f'{metric}_trend': result.trend,
        f'{metric}_seasonal': result.seasonal,
        f'{metric}_resid': result.resid,
    })
    decomp_df.to_csv(f'data/stl_decomposition_{metric}.csv', index=False)
    
    print(f"\n{metric}:")
    print(f"  Trend 범위: {result.trend.min():.2f} ~ {result.trend.max():.2f}")
    print(f"  Seasonal 진폭: {result.seasonal.max() - result.seasonal.min():.2f}")
    print(f"  Residual 표준편차: {result.resid.std():.2f}")
```

**기대 산출물**:
- `charts/02_stl_decomposition_new_works_count.png`
- `charts/02_stl_decomposition_avg_rating.png`
- `charts/02_stl_decomposition_avg_bookmarks.png`
- `data/stl_decomposition_*.csv` (3개 파일)

**예상 소요시간**: 1일 (분석 + 시각화)

**핵심 해석 포인트**:
- **Trend 가파른 상승**: 언제부터 로판이 급성장했는가?
- **Seasonal 패턴**: 특정 시즌(예: 여름 방학)에 신작이 집중되는가?
- **Residual 이상치**: 어느 월에 예상과 다른 변동이 발생했는가? → 이벤트 확인

---

### 2-3. 변동점 감지 분석 (1일)

**목표**: 로판 인기도의 주요 변화점(changepoint) 자동 감지

**개념 설명 (Sophie용)**:
> **PELT (Pruned Exact Linear Time)**  
> 시계열에서 "데이터의 특성이 갑자기 바뀌는 지점"을 찾는 알고리즘  
> 예: 로판 신작 수가 월 30개에서 월 80개로 점프한 날짜는?

**태스크**:

```python
# analysis/02_03_changepoint_detection.py

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import ruptures as rpt
import koreanize_matplotlib

# 1. 데이터 로드
ts_data = pd.read_csv('data/timeseries_monthly.csv', parse_dates=['date'])

# 2. 변동점 감지 (지표별로 실행)
metrics = ['new_works_count', 'avg_rating', 'avg_bookmarks']
changepoints_dict = {}

for metric in metrics:
    # 정규화 (scale 차이 제거)
    signal = ts_data[metric].values
    signal_norm = (signal - signal.mean()) / signal.std()
    
    # PELT 알고리즘 적용
    algo = rpt.Pelt(model="l2", min_size=3, jump=1).fit(signal_norm)
    # min_size: 각 segment의 최소 길이 (3개월)
    # jump: 스캔 스텝 (1 = 매월마다)
    
    # 주요 변동점 3개 추출
    changepoints = algo.predict(pen=10)  # pen: 변동점 수를 조절하는 파라미터
    changepoints_dict[metric] = changepoints
    
    # 3. 변동점을 날짜로 변환
    changepoint_dates = [ts_data.iloc[cp-1]['date'] if cp > 0 else ts_data.iloc[0]['date'] 
                         for cp in changepoints[:-1]]  # 마지막 점은 끝점이므로 제외
    
    print(f"\n{metric} - 주요 변동점:")
    for i, cp_date in enumerate(changepoint_dates, 1):
        idx = changepoints[i-1]
        print(f"  {i}. {cp_date.strftime('%Y-%m-%d')} (인덱스: {idx})")
    
    # 4. 시각화
    fig, ax = plt.subplots(figsize=(14, 6))
    
    ax.plot(ts_data['date'], signal, label=metric, linewidth=2, color='blue')
    
    # 변동점을 수직선으로 표시
    for cp in changepoints[:-1]:
        ax.axvline(x=ts_data.iloc[cp-1]['date'], color='red', linestyle='--', linewidth=2, alpha=0.7)
    
    ax.set_xlabel('Date')
    ax.set_ylabel(metric)
    ax.set_title(f'Changepoint Detection: {metric}')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'charts/02_changepoint_{metric}.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 5. 결과 저장
    cp_result = pd.DataFrame({
        'metric': metric,
        'changepoint_date': changepoint_dates,
        'changepoint_index': changepoints[:-1],
    })
    cp_result.to_csv(f'data/changepoints_{metric}.csv', index=False)

# 6. 모든 지표 변동점 통합 시각화
fig, axes = plt.subplots(3, 1, figsize=(14, 12))

for idx, metric in enumerate(metrics):
    signal = ts_data[metric].values
    axes[idx].plot(ts_data['date'], signal, label=metric, linewidth=2)
    
    changepoints = changepoints_dict[metric]
    for cp in changepoints[:-1]:
        axes[idx].axvline(x=ts_data.iloc[cp-1]['date'], color='red', linestyle='--', linewidth=2)
    
    axes[idx].set_ylabel(metric)
    axes[idx].grid(True, alpha=0.3)

axes[-1].set_xlabel('Date')
fig.suptitle('모든 지표의 변동점 비교', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig('charts/02_changepoint_comparison.png', dpi=300, bbox_inches='tight')
plt.close()

print("\n✓ 변동점 감지 완료")
```

**기대 산출물**:
- `charts/02_changepoint_new_works_count.png`
- `charts/02_changepoint_avg_rating.png`
- `charts/02_changepoint_avg_bookmarks.png`
- `charts/02_changepoint_comparison.png`
- `data/changepoints_*.csv` (3개 파일)

**예상 소요시간**: 1일

**핵심 해석 포인트**:
- **2019년 10월 근처에 변동점이 있는가?** → 재혼황후 웹툰화 영향 추정
- **2023년 7월 근처?** → 판사 이한영, 선재 업고 튀어 드라마 방영 영향
- **여러 지표에서 동시에 변동점이 감지되는가?** → 진정한 "이벤트"의 증거

---

### Phase 2 최종 산출물 체크리스트

- [ ] `data/timeseries_monthly.csv`
- [ ] `charts/02_stl_decomposition_*.png` (3개)
- [ ] `charts/02_changepoint_*.png` (4개)
- [ ] `data/stl_decomposition_*.csv` (3개)
- [ ] `data/changepoints_*.csv` (3개)
- [ ] `analysis/02_01_timeseries_prep.py`
- [ ] `analysis/02_02_stl_decomposition.py`
- [ ] `analysis/02_03_changepoint_detection.py`

**예상 총 소요시간**: 2-3일

---

## 🔍 Phase 3: 원인 파악 (Interrupted Time Series, 3-4일)

### 3-1. 이벤트 메타데이터 확정 (0.5일)

**목표**: 챕터2 분석을 위한 정확한 이벤트 타임라인 확정

**Phase 1에서 수집한 `data/events_timeline.csv` 검증 및 보완**:

```python
# analysis/03_01_event_validation.py

import pandas as pd
import numpy as np
from datetime import datetime

# 주요 이벤트 (최종 확정 리스트)
events_final = pd.DataFrame([
    {
        'event_id': 'E001',
        'event_date': pd.to_datetime('2019-10-25'),
        'event_name': '재혼황후 웹툰 네이버 웹툰 연재 시작',
        'platform': 'naver_webtoon',
        'expected_impact': 'HIGH',
        'description': '로판 대중화의 터닝포인트 (Kaggle OSMU 데이터 확인됨)',
    },
    # E002 판사 이한영 제외: 실제 방영일 2026-01-02(MBC) — 현재 시점에서 3개월 전이라 ITS 분석창 확보 불가
    {
        'event_id': 'E003',
        'event_date': pd.to_datetime('2024-04-08'),  # tvN 공식 확인
        'event_name': '선재 업고 튀어 드라마 방영 시작',
        'platform': 'tvn_drama',
        'expected_impact': 'MEDIUM',
        'description': 'Researcher 보고: 방영 후 웹소설 매출 8.2배 증가',
    },
    {
        'event_id': 'E004',
        'event_date': pd.to_datetime('2025-06-15'),
        'event_name': '밀리의 서재 웹소설 탭 정식 출시',
        'platform': 'millie',
        'expected_impact': 'MEDIUM-HIGH',
        'description': '600억원 투자, 새로운 플랫폼 진입',
    },
])

events_final.to_csv('data/events_confirmed.csv', index=False)

print("확정된 이벤트:")
print(events_final[['event_date', 'event_name', 'expected_impact']])
```

**산출물**:
- `data/events_confirmed.csv`

**주의사항**:
- E003(선재 업고 튀어) 날짜 2024-04-08은 tvN 공식 확인됨
- E004(밀리의서재) 날짜 2025-06-30으로 재확인 필요 (현재 PLAN의 2025-06-15는 미확인)
- 드라마 방영일이 여러 개(예: 4월 8일 ~ 6월 4일)인 경우, **방영 시작일**로 통일
- **판사 이한영(E002) 제외 이유**: 방영일 2026-01-02(MBC)로 현재 수집 시점(2026-04-21)에서 3개월 전 → ITS 이벤트 후 분석창(최소 12개월) 확보 불가

---

### 3-2. Interrupted Time Series (ITS) 회귀 분석 (1.5일)

**목표**: 각 이벤트의 인과적 영향도를 통계적으로 검정 (p-value 포함)

**개념 설명 (Sophie용)**:
> **Interrupted Time Series (ITS)**  
> "이 이벤트 전후로 데이터가 정말 달라졌는가?"를 검정하는 방법  
> 방법: 더미변수(0/1)를 이용해 OLS 회귀 → 계수의 p-value로 유의성 판단

**태스크**:

```python
# analysis/03_02_interrupted_timeseries.py

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from statsmodels.formula.api import ols
from scipy import stats
import koreanize_matplotlib

# 1. 데이터 준비
ts_data = pd.read_csv('data/timeseries_monthly.csv', parse_dates=['date'])
events = pd.read_csv('data/events_confirmed.csv', parse_dates=['event_date'])

# 2. 각 이벤트에 대해 ITS 분석 실행
metrics = ['new_works_count', 'avg_rating', 'avg_bookmarks']

its_results = []

for event_row in events.itertuples():
    event_date = event_row.event_date
    event_name = event_row.event_name
    
    # 분석 대상 시계열: 이벤트 전후 24개월 (± 1년)
    start_date = event_date - pd.DateOffset(months=12)
    end_date = event_date + pd.DateOffset(months=12)
    
    analysis_data = ts_data[(ts_data['date'] >= start_date) & (ts_data['date'] <= end_date)].copy()
    
    # 시간 변수 (1부터 시작, 기울기 계산용)
    analysis_data['time'] = np.arange(1, len(analysis_data) + 1)
    
    # 이벤트 더미변수 (이벤트 후부터 1)
    analysis_data['intervention'] = (analysis_data['date'] >= event_date).astype(int)
    
    # 이벤트 후 경과시간 (선형 추세 변화 감지용)
    analysis_data['time_since_event'] = analysis_data['time'] - analysis_data['time'][analysis_data['intervention'] == 1].min()
    analysis_data['time_since_event'] = analysis_data['time_since_event'].clip(lower=0)
    
    for metric in metrics:
        # OLS 회귀 모델
        # Y = β0 + β1*time + β2*intervention + β3*time_since_event + ε
        # β2: 이벤트 직후의 수준 변화 (level change)
        # β3: 이벤트 후 추세 변화 (slope change)
        
        model = ols(f'{metric} ~ time + intervention + time_since_event', data=analysis_data).fit()
        
        # 결과 저장
        its_results.append({
            'event_id': event_row.event_id,
            'event_name': event_name,
            'event_date': event_date,
            'metric': metric,
            'n_obs': len(analysis_data),
            'r_squared': model.rsquared,
            'intercept_coef': model.params['Intercept'],
            'time_coef': model.params['time'],
            'intervention_coef': model.params['intervention'],
            'intervention_pval': model.pvalues['intervention'],
            'time_since_event_coef': model.params['time_since_event'],
            'time_since_event_pval': model.pvalues['time_since_event'],
            'significant_at_0.05': model.pvalues['intervention'] < 0.05,
        })
        
        print(f"\n{event_name} → {metric}")
        print(f"  Level change (intervention): {model.params['intervention']:.2f}, p={model.pvalues['intervention']:.4f}")
        print(f"  Slope change (time_since_event): {model.params['time_since_event']:.2f}, p={model.pvalues['time_since_event']:.4f}")
        print(f"  R²: {model.rsquared:.3f}")
        
        # 시각화: 실제 데이터 + 회귀선
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # 실제 데이터
        ax.scatter(analysis_data['date'], analysis_data[metric], label='Actual', alpha=0.6, s=50)
        
        # 회귀선 (이벤트 전/후 구분)
        before_event = analysis_data[analysis_data['intervention'] == 0]
        after_event = analysis_data[analysis_data['intervention'] == 1]
        
        before_pred = model.params['Intercept'] + model.params['time'] * before_event['time']
        after_pred = (model.params['Intercept'] + model.params['intervention'] + 
                     model.params['time'] * after_event['time'] + 
                     model.params['time_since_event'] * after_event['time_since_event'])
        
        ax.plot(before_event['date'], before_pred, 'r-', linewidth=2.5, label='Trend (Before Event)')
        ax.plot(after_event['date'], after_pred, 'g-', linewidth=2.5, label='Trend (After Event)')
        
        # 이벤트 수직선
        ax.axvline(x=event_date, color='orange', linestyle='--', linewidth=2, label='Event Date')
        
        ax.set_xlabel('Date')
        ax.set_ylabel(metric)
        ax.set_title(f'ITS Analysis: {event_name}\n{metric} (p-value={model.pvalues["intervention"]:.4f})')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f'charts/03_its_{event_row.event_id}_{metric}.png', dpi=300, bbox_inches='tight')
        plt.close()

# 3. 결과 종합 저장
its_results_df = pd.DataFrame(its_results)

# 4. 다중검정 보정 (Holm-Bonferroni) — 3 이벤트 × 3 지표 = 9개 검정
from statsmodels.stats.multitest import multipletests
_, pvals_corrected, _, _ = multipletests(
    its_results_df['intervention_pval'], method='holm'
)
its_results_df['intervention_pval_corrected'] = pvals_corrected
its_results_df['significant_corrected'] = pvals_corrected < 0.05

its_results_df.to_csv('data/its_results_summary.csv', index=False)

# 5. 중요 결과 요약
print("\n" + "="*60)
print("ITS 분석 결과 요약 (Holm 보정 후 p < 0.05만 표시)")
print("="*60)
significant = its_results_df[its_results_df['significant_corrected']]
print(significant[['event_name', 'metric', 'intervention_coef', 'intervention_pval', 'intervention_pval_corrected']])
```

**기대 산출물**:
- `charts/03_its_E001_*.png`, `03_its_E003_*.png`, `03_its_E004_*.png` (3 events × 3 metrics = 9개)
- `data/its_results_summary.csv` (Holm 보정 p-value 포함)

**예상 소요시간**: 1.5일

**핵심 해석 포인트**:
- **intervention p-value < 0.05**: 이 이벤트는 통계적으로 유의미한 영향을 미쳤다
- **intervention_coef > 0**: 이벤트 후 지표가 상승했다
- **time_since_event_coef**: 이벤트 후 추세가 가팔라지거나 완만해졌는가?

---

### 3-3. 플랫폼별 비교 분석 (1day)

**목표**: 카카오페이지 vs 네이버 진영의 이벤트 반응도 비교

**태스크**:

```python
# analysis/03_03_platform_comparison.py

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from statsmodels.formula.api import ols
import koreanize_matplotlib

# 1. 플랫폼별 시계열 생성
works = pd.read_csv('data/all_works_integrated.csv', parse_dates=['start_date'])

# 플랫폼 분류
# - Kakao 진영: 카카오페이지
# - Naver 진영: 네이버 시리즈 + 네이버 웹툰
kakao_works = works[works['platform'] == 'kakaopage']
naver_works = works[works['platform'].isin(['naver_series', 'naver_webtoon'])]

# 월별 신작 수 계산
kakao_monthly = kakao_works.groupby(kakao_works['start_date'].dt.to_period('M')).size()
kakao_monthly.index = kakao_monthly.index.to_timestamp()

naver_monthly = naver_works.groupby(naver_works['start_date'].dt.to_period('M')).size()
naver_monthly.index = naver_monthly.index.to_timestamp()

# 2. 이벤트 전후 비교
events = pd.read_csv('data/events_confirmed.csv', parse_dates=['event_date'])

for event_row in events.itertuples():
    event_date = event_row.event_date
    
    # 이벤트 전 12개월, 이벤트 후 12개월
    before_kakao = kakao_monthly[(kakao_monthly.index >= event_date - pd.DateOffset(months=12)) & 
                                 (kakao_monthly.index < event_date)].mean()
    after_kakao = kakao_monthly[(kakao_monthly.index >= event_date) & 
                               (kakao_monthly.index < event_date + pd.DateOffset(months=12))].mean()
    
    before_naver = naver_monthly[(naver_monthly.index >= event_date - pd.DateOffset(months=12)) & 
                                (naver_monthly.index < event_date)].mean()
    after_naver = naver_monthly[(naver_monthly.index >= event_date) & 
                               (naver_monthly.index < event_date + pd.DateOffset(months=12))].mean()
    
    print(f"\n{event_row.event_name}")
    print(f"  카카오페이지: {before_kakao:.1f} → {after_kakao:.1f} (+{(after_kakao/before_kakao-1)*100:.1f}%)")
    print(f"  네이버 진영: {before_naver:.1f} → {after_naver:.1f} (+{(after_naver/before_naver-1)*100:.1f}%)")
    
    # 3. 시각화: 플랫폼별 신작 수 비교
    fig, ax = plt.subplots(figsize=(12, 6))
    
    ax.plot(kakao_monthly.index, kakao_monthly.values, marker='o', label='카카오페이지', linewidth=2)
    ax.plot(naver_monthly.index, naver_monthly.values, marker='s', label='네이버 진영', linewidth=2)
    
    ax.axvline(x=event_date, color='red', linestyle='--', linewidth=2, alpha=0.7)
    ax.set_xlabel('Date')
    ax.set_ylabel('New Works Count')
    ax.set_title(f'플랫폼별 신작 수 비교: {event_row.event_name}')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'charts/03_platform_comparison_{event_row.event_id}.png', dpi=300, bbox_inches='tight')
    plt.close()
```

**기대 산출물**:
- `charts/03_platform_comparison_E001.png` 등 (4개)

**예상 소요시간**: 1일

---

### Phase 3 최종 산출물 체크리스트

- [ ] `data/events_confirmed.csv`
- [ ] `data/its_results_summary.csv` (Holm 보정 p-value 포함)
- [ ] `charts/03_its_E*.png` (9개, E001/E003/E004 × 3 지표)
- [ ] `charts/03_platform_comparison_*.png` (3개)
- [ ] `analysis/03_01_event_validation.py`
- [ ] `analysis/03_02_interrupted_timeseries.py`
- [ ] `analysis/03_03_platform_comparison.py`

**예상 총 소요시간**: 3-4일

---

## 🔮 Phase 4: 예측 (Prophet 단독, 1-2일)

> ⚠️ Bass Diffusion 제거됨: 수요 확산 모델을 공급 지표(신작 수)에 적용하면 해석 오류 발생. Prophet 단독으로 예측.

### 4-1. Prophet (Facebook) 예측

**목표**: 월별 신작 수의 계절성 + 추세를 고려한 단기 예측

**개념 설명 (Sophie용)**:
> **Prophet (Facebook)**  
> 자동으로 계절성(yearly, weekly)과 추세를 분리해 예측하는 도구  
> 장점: 휴일 효과, 외부 변수(이벤트) 추가 가능  
> 로판에 적용: 2026-2027년 월별 신작 수 + 신뢰구간 예측

**태스크**:

```python
# analysis/04_01_prophet_forecast.py

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from prophet import Prophet
import koreanize_matplotlib
import warnings
warnings.filterwarnings('ignore')

# 1. 데이터 준비
ts_data = pd.read_csv('data/timeseries_monthly.csv', parse_dates=['date'])

# Prophet 형식으로 변환 (컬럼명: ds, y)
prophet_data = pd.DataFrame({
    'ds': ts_data['date'],
    'y': ts_data['new_works_count'],
})

# 결측치 제거
prophet_data = prophet_data.dropna()

# 2. Prophet 모델 생성 및 학습
# 이벤트 외생변수 미사용 — Phase 3에서 귀납적으로 찾은 이벤트를 다시 넣으면 데이터 누수(Data Leakage)
model = Prophet(
    yearly_seasonality=True,
    weekly_seasonality=False,
    daily_seasonality=False,
    seasonality_mode='additive',
    interval_width=0.95,  # 95% 신뢰구간
)

model.add_seasonality(name='monthly', period=30, fourier_order=5)
model.fit(prophet_data)

# 3. 미래 예측 (24개월)
future = model.make_future_dataframe(periods=24, freq='MS')
forecast = model.predict(future)

# 4. 시각화: 전체 시계열 + 예측
fig, ax = plt.subplots(figsize=(14, 7))

# 과거 데이터
ax.scatter(prophet_data['ds'], prophet_data['y'], label='Actual', alpha=0.6, s=50)

# 예측선
forecast_future = forecast[forecast['ds'] >= prophet_data['ds'].max()]
ax.plot(forecast_future['ds'], forecast_future['yhat'], 'r-', linewidth=2.5, label='Forecast')

# 신뢰구간
ax.fill_between(forecast_future['ds'], 
                 forecast_future['yhat_lower'], 
                 forecast_future['yhat_upper'],
                 color='red', alpha=0.2, label='95% Confidence')

ax.set_xlabel('Date')
ax.set_ylabel('New Works Count')
ax.set_title('Prophet Forecast: 월별 로판 신작 수 (2026-2027)')
ax.legend()
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('charts/04_prophet_forecast.png', dpi=300, bbox_inches='tight')
plt.close()

# 5. 계절성 분해 시각화
fig = model.plot_components(forecast)
plt.savefig('charts/04_prophet_components.png', dpi=300, bbox_inches='tight')
plt.close()

# 6. 결과 저장
forecast_export = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].copy()
forecast_export.columns = ['date', 'forecast', 'lower_bound', 'upper_bound']
forecast_export.to_csv('data/prophet_forecast.csv', index=False)

# 7. 주요 수치
latest_actual = prophet_data['y'].iloc[-1]
forecast_2027 = forecast_export[forecast_export['date'].dt.year == 2027]['forecast'].mean()

print(f"현재 월평균 신작 수 (2026년 3월): {latest_actual:.1f}개")
print(f"예측 월평균 신작 수 (2027년): {forecast_2027:.1f}개")
print(f"예상 증가율: +{(forecast_2027/latest_actual-1)*100:.1f}%")
```

**기대 산출물**:
- `charts/04_prophet_forecast.png`
- `charts/04_prophet_components.png` (Trend, Yearly Seasonality 분리)
- `data/prophet_forecast.csv`

**예상 소요시간**: 1일

---

### Phase 4 최종 산출물 체크리스트

- [ ] `charts/04_prophet_forecast.png`
- [ ] `charts/04_prophet_components.png`
- [ ] `data/prophet_forecast.csv`
- [ ] `analysis/04_01_prophet_forecast.py`

**예상 총 소요시간**: 1-2일

---

## 📋 Phase 5: 보고서 & 대시보드 (1-2일)

### 5-1. 분석 보고서 작성 (1day)

**목표**: 4개 챕터의 분석 결과를 논리적으로 정리

**구조**:

```markdown
# 로판 IP 파이프라인 분석 보고서

## Executive Summary
- 핵심 발견 3가지
- 비즈니스 임플리케이션

## 1. 현황 (Phase 2 결과)
- STL 분해로 본 로판 성장 추이
- 주요 변동점 3개 (날짜 + 영향도)

## 2. 원인 (Phase 3 결과)
- ITS 분석: 각 이벤트의 통계적 유의성
- 재혼황후 웹툰화의 영향도 정량화
- 플랫폼별 반응 비교 (카카오 vs 네이버)

## 3. 예측 (Phase 4 결과)
- Prophet: 월별 신작 수 추세 (12~24개월 예측)

## 4. 결론 & 제안
- 로판 시장의 미래 전망
- 플랫폼별 전략 제안
```

**산출물**:
- `report/REPORT.md`

**예상 소요시간**: 1일

---

### 5-2. 대시보드 생성 (1day)

**목표**: 분석 결과를 HTML 대시보드로 시각화

**구현**:

```python
# analysis/05_dashboard.py

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# 1. 각 단계별 이미지/데이터 로드
# ...

# 2. 대시보드 구성
# - 상단: KPI (총 작품 수, 평균 평점, 관심수)
# - 좌상: STL 분해 차트
# - 우상: 변동점 감지 차트
# - 좌하: ITS 분석 결과 테이블
# - 우하: Prophet 예측 차트

# 3. HTML로 내보내기
# ...

html = """
<!DOCTYPE html>
<html>
<head>
    <title>로판 시장 분석 대시보드</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
</head>
<body>
    <!-- 차트들을 Plotly로 표현 -->
</body>
</html>
"""

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(html)
```

**산출물**:
- `dashboard.html`

**예상 소요시간**: 1일

---

### Phase 5 최종 산출물 체크리스트

- [ ] `report/REPORT.md`
- [ ] `dashboard.html`
- [ ] `analysis/05_dashboard.py`

**예상 총 소요시간**: 1-2일

---

## 📅 주요 이벤트 타임라인

**분석에 필요한 확정된 이벤트 목록** (Phase 3에서 사용):

| 이벤트 ID | 날짜 | 이벤트명 | 플랫폼 | 영향도 예상 | 비고 |
|----------|------|--------|--------|-----------|------|
| E001 | 2019-10-25 | 재혼황후 웹툰 연재 시작 | 네이버 웹툰 | ⭐⭐⭐⭐⭐ | 로판 대중화 터닝포인트 |
| ~~E002~~ | ~~2026-01-02~~ | ~~판사 이한영 드라마 방영~~ | ~~MBC~~ | — | **ITS 제외**: 현재 시점(2026-04) 기준 3개월 전, 분석창 확보 불가 |
| E003 | 2024-04-08 | 선재 업고 튀어 드라마 방영 시작 | tvN | ⭐⭐⭐ | 웹소설 매출 8.2배 증가 |
| E004 | 2025-06-30 | 밀리의 서재 웹소설 탭 출시 | 밀리의 서재 | ⭐⭐⭐ | 600억원 투자, 신규 플랫폼 (날짜 재확인 필요) |

**ITS 분석 대상 이벤트**: E001, E003, E004 (3개)

---

## ⏱️ 전체 예상 일정

| Phase | 분석 내용 | 예상 소요일 | 누적 일수 |
|-------|---------|-----------|---------|
| **Phase 1** | 데이터 수집 & 전처리 | 4-5일 | 4-5일 |
| **Phase 2** | 현상 파악 (STL + 변동점) | 2-3일 | 6-8일 |
| **Phase 3** | 원인 파악 (ITS) | 3-4일 | 9-12일 |
| **Phase 4** | 예측 (Prophet 단독) | 1-2일 | 10-14일 |
| **Phase 5** | 보고서 & 대시보드 | 1-2일 | **12-17일** |

**전체 예상 기간**: 약 **11-17일**

---

## 🛠️ 기술 스택 최종 정리

| 구분 | 선택 도구 | 용도 |
|------|---------|------|
| **웹크롤링** | requests + BeautifulSoup4 | 네이버 시리즈, 네이버 웹툰 |
| **API** | GraphQL (카카오페이지), KMDB (드라마 데이터) | 메타데이터 수집 |
| **데이터 전처리** | pandas, numpy | 통합 + 정제 |
| **시계열 분석** | statsmodels.STL | 트렌드 분해 |
| **변동점 감지** | ruptures (PELT) | 이상점 탐지 |
| **인과 분석** | statsmodels.ols | Interrupted Time Series |
| **예측 모델** | prophet | 시계열 예측 (2026-2027, 95% CI) |
| **시각화** | matplotlib + seaborn + plotly | 차트 + 대시보드 |
| **한글 폰트** | koreanize-matplotlib | Matplotlib 한글 렌더링 |

---

## 💡 Sophie를 위한 개념 가이드

### 오늘의 개념들

#### 1. **시계열 분해 (Time Series Decomposition)**
시계열 데이터를 구성 요소로 분리하는 기법:
- **Trend (추세)**: 장기적인 상승/하강 방향
- **Seasonal (계절성)**: 반복되는 패턴 (월별, 계절별)
- **Residual (잔차)**: 설명되지 않는 변동 (이상치, 노이즈)

예: "매년 여름에 신작이 많고, 전체적으로 증가추세지만, 어떤 달에는 예상 밖으로 많이 나온다"

#### 2. **변동점 감지 (Changepoint Detection)**
데이터의 "특성이 급격히 바뀌는 지점"을 찾는 알고리즘:
- PELT: Pruned Exact Linear Time (효율적)
- 쓰임: "이 날짜 이후로 뭔가 달라졌다" → 이벤트 효과 추정

예: "2019년 10월부터 로판 신작이 급격히 증가했다"

#### 3. **Interrupted Time Series (ITS)**
이벤트 전후의 변화를 통계적으로 검정하는 방법:
- 회귀식: `Y = β0 + β1×시간 + β2×(이벤트여부) + β3×(이벤트후경과시간)`
- β2 p-value < 0.05 → "이벤트가 통계적으로 유의미한 영향을 미쳤다"

예: "재혼황후 웹툰 시작이 정말 로판 신작 수를 증가시켰는가? (p=0.003, 유의)"

#### 4. **Prophet (Meta)**
자동으로 계절성과 추세를 분리해 예측:
- 장점: "내 데이터에는 휴일 효과가 있다" 같은 외부 변수 추가 가능
- 출력: 점 추정 + 신뢰구간 (불확실성 정량화)

예: "2027년 4월에는 월평균 50개 신작, 신뢰구간 35-65개"

---

## 🎯 이 계획의 비즈니스 연결성

### Researcher가 제시한 핵심 질문
1. "로판은 정말 웹소설 1위 장르인가?" → Phase 2에서 확인
2. "웹툰화가 로판 성장을 주도했는가?" → Phase 3 ITS로 인과관계 검증
3. "IP 파이프라인(웹소설 → 웹툰 → 드라마)이 시장을 견인하는가?" → Phase 3 이벤트 분석
4. "앞으로 로판 시장은 포화될 것인가?" → Phase 4 예측

**이 계획의 각 단계가 비즈니스 질문과 연결되는 방식**:
- Phase 1 (데이터): "어떤 데이터가 있는가?" → 재현성 확보
- Phase 2 (현상): "지금 로판이 어디에 있는가?" → 시장 현황 파악
- Phase 3 (원인): "이 성장은 정말 웹툰/드라마 때문인가?" → 인과 검증
- Phase 4 (예측): "앞으로는?" → 전략 수립 근거
- Phase 5 (보고): "의사결정자가 이해할 수 있게" → 실행 가능한 인사이트

---

## ✅ Self-Review Checklist

- [x] RESEARCH.md를 읽고 시작했는가? ✓
- [x] 모든 분석 단계가 Researcher의 방법론과 일치하는가? ✓ (STL, ruptures, ITS, Prophet)
- [x] 각 단계에 "의사결정 연결"이 명시되어 있는가? ✓
- [x] Analyst(Sophie)가 플랜만 보고 코드를 쓸 수 있을 만큼 구체적인가? ✓ (코드 스켈레톤 + 산출물 명시)
- [x] 임의로 추가한 분석이 없는가? ✓
- [x] 모든 약어에 Full Name이 표기되어 있는가? ✓
- [x] 난이도/소요시간이 합리적인가? ✓ (2-3주, 개발자 레벨 고려)

---

## 📞 시작하기 전에 확인해야 할 사항

Sophie가 **내일 바로 시작**하기 전에 아래를 체크하세요:

### Phase 1 시작 전
- [ ] 카카오페이지 GraphQL API 문서 확인 (또는 BeautifulSoup으로 대체 결정)
- [ ] KMDB API 가입 + API 키 발급 (선택사항, 없으면 나무위키로 대체)
- [ ] 가상환경 설정 여부 결정 (권장: Yes)

### Phase 3 시작 전
- [ ] 드라마 방영일 정확한 날짜 수집 (나무위키 또는 나무위키로 검증)
- [ ] "로판"의 장르 정의 확정 (genre 컬럼의 필터링 조건)

### Phase 4 시작 전
- [ ] Prophet 설치 확인 (`pip install prophet`)
- [ ] GPU 가능 여부 확인 (Kaggle/Colab 고려)

---

## 📚 참고자료

### Researcher가 제시한 출처
- 한국출판문화산업진흥원 2024년 웹소설 산업 현황 실태조사
- 오픈서베이 웹툰·웹소설 트렌드 리포트 2023
- Kaggle OSMU 데이터셋 (네이버 웹툰 1,564건)
- KMDB API (드라마/영화 메타데이터)

### 추가 학습 자료
- `statsmodels.tsa.seasonal.STL` 공식 문서
- `ruptures` GitHub (PELT 알고리즘 설명)
- Meta Prophet 공식 문서 (https://facebook.github.io/prophet/docs/quick_start.html)

---

**이 계획은 Researcher의 RESEARCH.md를 기반으로 수립되었습니다.**  
**모든 분석 방법론, 지표, 데이터 소스는 Researcher의 조사 결과와 일치합니다.**

