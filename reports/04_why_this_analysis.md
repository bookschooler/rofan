# Phase 4 - Why This Analysis

## Step 4-1: Prophet 예측

### 무엇을 하나요?
Phase 2-3에서 파악한 로판 신작 수의 과거 패턴(추세, 계절성, 변동점, 이벤트 효과)을 바탕으로
**2026년 4월~12월의 신작 수를 예측**합니다.

### 왜 필요한가요?
Phase 3에서 2024-04 이후 월 -3.33편씩 감속 중이라는 통계적 증거를 발견했습니다.
이 감속이 지속된다면 언제, 어느 수준까지 신작 수가 떨어질지 — "2026년 하반기에
2022년 수준으로 되돌아간다"는 가설을 수치로 검증하기 위해 예측을 추가합니다.

### 어떻게 하나요?
**Prophet** (Meta/Facebook 오픈소스)은 추세 + 계절성 + 이벤트를 자동 분리해 예측하는 라이브러리입니다.

- PELT에서 탐지한 변동점을 `02_03_changepoints.csv`에서 동적 로드해 `changepoints`로 지정 (현재: 2017-09, 2020-08, 2022-07)
- `yearly_seasonality=True`: 월별 계절성 자동 학습
- `interval_width=0.95`: 95% 예측 구간 생성

### 산출물
| 파일 | 내용 |
|------|------|
| `data/processed/04_01_prophet_forecast.csv` | 월별 예측값 + 95% 상하한 |
| `charts/04_01_prophet_forecast.png` | 실제값 + 예측 차트 |
| `charts/04_01_prophet_components.png` | 추세/계절성 분해 차트 |
