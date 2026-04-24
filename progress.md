# 로판 IP 파이프라인 분석 — Phase 1 진행 현황

> 마지막 업데이트: 2026-04-24
> 목표: 카카오페이지 / 네이버 시리즈 / 네이버 웹툰 3개 플랫폼의 로판 작품 데이터 수집 및 정제

---

## Phase 1: 데이터 수집

### Step 1-1. 카카오페이지 크롤러

| 버전 | 파일 | 방식 | 결과 | 상태 |
|------|------|------|------|------|
| v1 | `01_kakaopage_crawler.py` | 목록 페이지 `__NEXT_DATA__` + 상세 페이지 개별 호출 | - | 폐기 (속도 느림) |
| v2 | `01_kakaopage_crawler_v2.py` | BFF API `landing/genre` (subcategory_uid=117 로판) | - | 폐기 (start_date 누락) |
| v3 | `01_kakaopage_crawler_v3.py` | BFF API, sort_type UPDATE + PRODUCT_LATEST 2회 수집 후 중복 제거 | **10,770건** 수집 | ✅ 채택 |

**최종 결과물:** `data/raw/kakaopage_works.csv`

| 지표 | 값 |
|------|----|
| 전체 건수 | 10,770건 |
| start_date | 10,770건 (100%) |
| view_count > 0 | 10,559건 (98.0%) |
| content_form | serialized 7,435 / book_edition 3,267 / spinoff 68 |
| rating > 0 | 994건 (9.2%) — 카카오페이지 일부 작품에만 제공 |
| rating 중앙값 (>0) | 9.91 |
| rating_count 중앙값 (>0) | 297명 |
| comment_count 중앙값 (>0) | 129 |

> **주의사항:** BFF API 목록에 rating/episode_count 없음. 별도 상세 페이지 크롤링 필요.

---

### Step 1-2. 카카오페이지 rating 보강

| 버전 | 파일 | 방식 | 결과 | 상태 |
|------|------|------|------|------|
| v1 | `01_kakaopage_enrich_rating.py` | 순차 실행 (sleep=0.35s) | 일부 수집 | 폐기 (rate limit 위험) |
| v2 | `01_kakaopage_enrich_rating_v2.py` | 순차 실행 (sleep=0.8s), 체크포인트 | 실행 오류 발생 | 폐기 |
| chunk | `01_kakaopage_enrich_rating_chunk.py` | **5개 병렬** (sleep=1.5s/프로세스 → 합산 3.3 req/s) | **994건** | ✅ 완료 |

**수집 방법:** 상세 페이지 `page.kakao.com/content/{series_id}` HTML에서 `__NEXT_DATA__` 파싱
→ `serviceProperty.ratingCount`, `ratingSum`, `commentCount` 추출
→ `rating = ratingSum / ratingCount`

**병렬 실행 구조:**
```
kakaopage_works.csv (10,770건)
  ├── kp_chunk_0.csv (2,154건) → kp_rating_chunk_0.csv
  ├── kp_chunk_1.csv (2,154건) → kp_rating_chunk_1.csv
  ├── kp_chunk_2.csv (2,154건) → kp_rating_chunk_2.csv
  ├── kp_chunk_3.csv (2,154건) → kp_rating_chunk_3.csv
  └── kp_chunk_4.csv (2,154건) → kp_rating_chunk_4.csv
```
실행: `python run_parallel_chunks.py` (logs/kp_chunk_{0-4}.log)
예상 완료: 약 54분 (2,154건 × 1.5s ÷ 60)

> **트러블슈팅:** 4 프로세스 × sleep=0.4s = 합산 10 req/s → rate limit 차단. 76분 낭비.
> 1.5s/프로세스(합산 3.3 req/s)로 수정 후 재실행.

---

### Step 1-3. 네이버 시리즈 크롤러

| 파일 | 방식 | 결과 | 상태 |
|------|------|------|------|
| `01_naver_series_crawler.py` | 장르 API `genreCode=207` (로판), orderTypeCode=new, 빈 페이지까지 순회 | **18,778건** | ✅ 완료 |
| `01_naver_series_enrich_startdate.py` | 개별 `volumeList.series?productNo={id}` API로 start_date 역추적 | start_date 73.2% | ✅ 완료 |

**최종 결과물:** `data/raw/naver_series_works.csv`

| 지표 | 값 |
|------|----|
| 전체 건수 | 18,778건 |
| content_form | book_edition 10,113 (53.9%) / serialized 8,653 / spinoff 12 |
| start_date | 13,746건 (73.2%) |
| rating | 수집됨 (목록 API 포함) |

> **인사이트:** 건수가 많은 이유는 단행본(book_edition) 구조 때문 — 동일 IP가 권 단위로 분리 등록됨.
> `content_form` 컬럼으로 serialized / book_edition / spinoff 구분 가능.

---

### Step 1-4. 네이버 웹툰 크롤러

| 버전 | 파일 | 방식 | 결과 | 상태 |
|------|------|------|------|------|
| v1 | `01_naver_webtoon_crawler.py` | 요일별 API + 완결 API, 로판 키워드 필터 | 소수 | 폐기 (정확도 낮음) |
| v2 | `01_naver_webtoon_crawler_v2.py` | 완결 전체 수집 후 info API로 장르 필터링 | 일부 | 폐기 (비효율) |
| v3 | `01_naver_webtoon_crawler_v3.py` | `curationType == 'GENRE_ROMANCE_FANTASY'` 필터 | **0건** | 폐기 (해당 타입 미존재) |
| v4 | `01_naver_webtoon_crawler_v4.py` | **`CUSTOM_TAG id=51` (로판 태그) 직접 수집** | **249건** | ✅ 채택 |

**핵심 발견:** 네이버 웹툰에는 `GENRE_ROMANCE_FANTASY` curationType이 존재하지 않음.
로판 = `CUSTOM_TAG id=51` (tagName='로판') → `/api/curation/list?type=CUSTOM_TAG&id=51`

**최종 결과물:** `data/raw/naver_webtoon_works.csv`

| 지표 | 값 |
|------|----|
| 전체 건수 | 249건 (완결 118 / 연재중 131) |
| start_date | 235건 (94.4%), episode API 역추적 |
| rating | 249건 (100%), 목록 API `averageStarScore` |
| bookmark_count | 249건 (100%), `favoriteCount` — 최대 971,465 (재혼황후) |
| rating_count | 0 (API 미제공) |

---

## 컬럼 설계 결정사항

### content_form 컬럼 (카카오페이지 + 네이버 시리즈)
- `serialized`: 일반 연재 작품
- `book_edition`: 제목에 `[단행본]` 포함 — 동일 IP의 권 단위 재출판
- `spinoff`: 제목에 `[외전]` 포함

**목적:** 분석 시 연재본만 필터링하거나 단행본 전환율을 별도 분석하는 등 선택적 활용 가능.

### primary_metric 설계
| 플랫폼 | 주 지표 | 비고 |
|--------|---------|------|
| 카카오페이지 | `view_count` (누적 조회수) | BFF API에서 직접 제공 |
| 네이버 시리즈 | `episode_count` | 조회수 API 미제공 |
| 네이버 웹툰 | `episode_count` → `rating` (없을 때) | 조회수 API 미제공 |

---

---

### Step 1-6. 3개 플랫폼 통합 데이터셋 생성

**파일:** `analysis/02_integrate_platforms.py`
**결과물:** `data/raw/all_works_integrated.csv`

**DESA 팀 만장일치 결정사항 (4:0):**
- content_form = `serialized` 작품만 분석에 사용 (book_edition / spinoff 제외)
- primary_metric 통합 합산 없음 — 플랫폼별 분리 보관
- start_date 결측 → 유지 후 시계열 집계 시 명시적 제외 (대체 없음)
- tags / bookmark_count 제거 (결측 100%)

**통합 결과:**

| 구분 | 건수 |
|------|------|
| 전체 통합 | 29,797건 |
| serialized (분석 대상) | 16,337건 |
| book_edition (보관) | 13,380건 |
| spinoff (보관) | 80건 |

**start_date 결측률 (serialized 기준, 통합 직후 — 쿠키 재수집 전):**

| 플랫폼 | 결측률 | 비고 |
|--------|--------|------|
| kakaopage | 0.0% | |
| naver_series | 16.3% | 전체 기준 26.8% → book_edition 제거 후 개선 |
| naver_webtoon | 5.6% | |
| **전체** | **8.7%** | |

> **Reviewer 예측 적중:** book_edition에 결측이 몰려 있어서, serialized 필터링 후 네이버 시리즈 결측률이 26.8% → 16.3%로 감소.
> → Step 1-7 쿠키 인증 재수집 후 **전체 결측률 0.0%** 로 개선됨.
> start_date 범위: 2013-01-15 ~ 2026-04-22

---

### Step 1-7. start_date 결측 재수집

통합 후 serialized 기준 결측 현황 재점검 → 원인 파악 후 재수집 시도.

#### 1차 시도 (비인증)

| 플랫폼 | 결측 건수 | 원인 | 1차 결과 |
|--------|----------|------|----------|
| kakaopage | 0건 | — | 없음 |
| naver_series | 1,410건 | 성인 작품 → 로그인 없이 `volumeList` API가 `500` 반환 | 전부 실패 |
| naver_webtoon | 14건 | `401 LOGIN` — 성인 작품, 로그인 세션 필요 | 전부 실패 |

**실패 원인 정밀 분석 (네이버 시리즈):**
- HTTP는 stateless → 서버가 요청자를 식별 못 함
- 비인증 요청 = Cookie 헤더 없음 → 서버가 성인 확인 불가 → `500` 반환
- 해결책: 브라우저의 인증된 세션 쿠키(`NID_SES`, `NID_AUT`)를 Python requests에 수동 주입

#### 2차 시도 (쿠키 인증)

- Chrome DevTools → Network 탭 → 실제 전송 Cookie 헤더값 추출 (성인 인증 완료 상태)
- `.naver_cookie_temp` 파일에 저장 → `01_naver_series_retry_missing.py` v2에서 로드
- `01_naver_series_retry_missing.py` 실행 (serialized 1,410건만 대상)

**재수집 결과:**

| 구분 | 건수 |
|------|------|
| 성공 | 1,403건 |
| 실패 (7건) | `no_episode` — 에피소드 자체 없는 작품 |

**최종 start_date 보유율 (serialized 기준):**

| 플랫폼 | 결측 건수 | 결측률 |
|--------|----------|--------|
| kakaopage | 0건 | 0.0% |
| naver_series | **7건** | **0.1%** (16.3% → 0.1% 개선) |
| naver_webtoon | 14건 | 5.6% |
| **전체** | **21건** | **0.1%** |

> 쿠키 인증 도입으로 네이버 시리즈 serialized 결측률 **16.3% → 0.1%** 로 극적 개선.
> 잔여 7건은 에피소드 자체가 없는 구조적 결측 — 더 이상 재수집 불가.

#### 3차 시도 — 네이버 웹툰 14건 (쿠키 인증)

NID_SES는 naver.com 전체 공통 쿠키 → `comic.naver.com`에서도 동일하게 유효
- `01_naver_webtoon_retry_missing.py` v2 (쿠키 적용) 실행 → **14건 전부 성공**

**최종 start_date 보유율 (serialized 기준):**

| 플랫폼 | 결측 건수 | 결측률 |
|--------|----------|--------|
| kakaopage | 0건 | 0.0% |
| naver_series | 7건 | 0.1% |
| naver_webtoon | **0건** | **0.0%** |
| **전체** | **7건** | **0.0%** |

**`all_works_integrated.csv` 최종 재생성 완료** (2026-04-24)

---

## 다음 단계 (예정)

| 순서 | 작업 | 내용 |
|------|------|------|
| 1 | Phase 2: 시계열 데이터 준비 | `all_works_integrated.csv` → 월별 신작 수 집계 |
| 2 | Phase 2: STL 분해 | 트렌드 + 계절성 + 잔차 분리 |
| 3 | Phase 2: 변동점 감지 | PELT 알고리즘으로 주요 변화점 탐지 |
| 4 | Phase 3: ITS 분석 | 이벤트 전후 인과관계 검정 |

---

## 트러블슈팅 기록

| 날짜 | 문제 | 원인 | 해결 |
|------|------|------|------|
| 2026-04-23 | 네이버 웹툰 v3 → 0건 | `GENRE_ROMANCE_FANTASY` curationType 미존재 | v4: CUSTOM_TAG id=51 사용 |
| 2026-04-23 | 카카오페이지 v2 크롤러가 v3 결과 덮어씀 | start_date 없는 v2를 테스트 실행 | v3 재수집 (30분 소요). 이후 output 파일 확인 의무화 |
| 2026-04-23 | rating 병렬 수집 rate limit 차단 | 4프로세스 × 0.4s = 10 req/s 초과 | 5프로세스 × 1.5s = 3.3 req/s로 수정 |
| 2026-04-24 | 네이버 시리즈 결측 재수집 0건 성공 | 성인 작품 → 비인증 상태로는 API 500 반환 | Chrome 세션 쿠키 추출 후 requests 헤더에 주입 → 1,403건 성공 |
| 2026-04-24 | 쿠키 파일에 줄바꿈 포함돼 InvalidHeader 에러 | `echo` 명령어로 저장 시 개행 포함됨 | Python으로 직접 단일 라인 저장하도록 변경 |
| 2026-04-24 | 네이버 웹툰 14건 401 → 쿠키로 해결 | NID_SES는 naver.com 전체 공통 세션 | 동일 쿠키로 comic.naver.com도 인증 → 전부 성공 |
