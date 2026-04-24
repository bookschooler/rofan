# Prophet — 미래 트렌드 예측하기

> **이 분석이 하는 일**: ITS로 과거가 왜 바뀌었는지 확인한 뒤, "앞으로 로판 신작은 어떻게 될까?" 예측하기
>
> **프로젝트에서 쓰는 곳**: Phase 4 — 향후 12~24개월 로판 신작 수 예측

**원논문(Tier 1)**: Taylor, S.J., Letham, B. (2018). *Forecasting at scale.* The American Statistician, 72(1), 37–45. https://doi.org/10.1080/00031305.2017.1380080

---

## Prophet이 특별한 이유

시계열 예측의 전통적인 방법인 ARIMA는 전문 지식 없이 쓰기 어려워요. Prophet은 Meta(Facebook)가 "데이터 전문가가 아닌 분석가도 쓸 수 있게" 만든 도구예요.

**Prophet의 접근법**: "트렌드 + 계절성 + 이벤트 효과"를 **각각 따로** 모델링하고 마지막에 더하기

```
예측값 = 트렌드(g) + 계절성(s) + 이벤트 효과(h) + 오차
```

**STL과 비슷해 보이는데?** STL은 과거 데이터를 분해하는 도구. Prophet은 미래를 예측하는 도구. 분해 구조가 비슷하지만 목적이 달라요.

---

## 각 성분을 비유로 이해하기

### 트렌드 g(t) — "대세의 방향"

```
로판 신작 수
│            ↗
│         ↗   ← 2019년 이후 가속 (변동점)
│      ↗
│   ↗   ← 완만한 성장
│ ↗
└──────────────→ 시간
```

Prophet은 트렌드가 쭉 직선이 아니라 **중간에 기울기가 바뀔 수 있다**는 걸 알고 있어요. 이 "기울기가 바뀌는 시점"을 자동으로 찾아줘요.

### 계절성 s(t) — "반복되는 패턴"

```
신작 수
│ 1월 3월   1월 3월   1월 3월
│ ↑  ↑     ↑  ↑     ↑  ↑
│─────────────────────────→ 시간
```

연초에 신작이 집중되는 패턴이 매년 반복되면 → Prophet이 이 패턴을 학습해서 미래에도 적용

### 이벤트 효과 h(t) — "특별한 날"

```python
events = pd.DataFrame({
    'holiday': ['재혼황후_웹툰'],
    'ds': ['2019-10-01'],
    'lower_window': -7,   # 7일 전부터 효과 시작
    'upper_window': 30,   # 30일 후까지 효과 지속
})
```

---

## 가장 중요한 파라미터 1개: `changepoint_prior_scale`

이 값 하나가 예측의 유연함을 결정해요.

**비유**: 젤리처럼 유연하게 구부러지는 선을 그린다고 생각해봐요.
- 값이 크면 → 매우 유연, 데이터에 찰싹 붙음 → 근데 과거 노이즈까지 따라가서 미래 예측이 엉뚱해질 수 있음
- 값이 작으면 → 뻣뻣하게 직선에 가까움 → 큰 변화를 놓칠 수 있음

```python
from prophet import Prophet

# 기본값: 0.05 (약간 뻣뻣)
model = Prophet(changepoint_prior_scale=0.05)

# 더 유연하게 (과적합 위험)
model = Prophet(changepoint_prior_scale=0.5)

# 더 규칙적으로
model = Prophet(changepoint_prior_scale=0.001)
```

---

## 전체 코드 (간단 버전)

```python
from prophet import Prophet
import pandas as pd

# 입력 데이터: 반드시 'ds'(날짜)와 'y'(값) 컬럼
df = monthly_works[['date', 'new_works']].rename(
    columns={'date': 'ds', 'new_works': 'y'}
)

# 모델 생성 및 학습
model = Prophet(
    changepoint_prior_scale=0.05,
    seasonality_mode='additive',   # 계절성 진폭이 일정하면 additive
    yearly_seasonality=True,       # 연간 계절성 켜기
)
model.fit(df)

# 미래 12개월 예측
future = model.make_future_dataframe(periods=12, freq='M')
forecast = model.predict(future)

# 결과 시각화
model.plot(forecast)               # 예측선 + 불확실성 구간
model.plot_components(forecast)    # 트렌드 / 계절성 분리해서 보기
```

---

## 핵심 가정 — "이게 맞아야 Prophet을 쓸 수 있어요"

| 가정 | 쉬운 말 | 깨지면? |
|------|--------|--------|
| 트렌드가 선형 또는 S자 곡선이다 | 꾸준히 증가하거나, 포화점에 수렴한다 | 갑자기 폭락하는 패턴은 예측 어려움 |
| 계절 패턴이 반복된다 | 매년 1월이 많으면 내년 1월도 많을 것이다 | 패턴이 불규칙하면 계절성 과적합 |
| 미래도 과거 패턴을 따른다 | 구조적 변화가 미래에도 없다 | 큰 환경 변화(예: OTT 플랫폼 붕괴)가 예상되면 예측 불가 |
| 최소 2년 이상 데이터가 있다 | 연간 계절성을 학습하려면 2바퀴 이상 | 1년치 데이터로 미래 1년 예측 → 불안정 |

---

## 이럴 때 Prophet이 실패해요

### ❌ 실패 1: 일회성 이벤트를 holidays에 넣었을 때
"선재 업고 튀어 드라마 방영"은 2024년 4월에 딱 한 번 일어난 일이에요.

이걸 holidays에 넣으면 Prophet이 "매년 4월마다 이 드라마가 방영된다"고 학습해버려요.

```python
# 잘못된 사용
model = Prophet(holidays=일회성_이벤트_데이터프레임)
# → 미래 예측에서 매년 4월마다 이벤트 효과가 반복됨

# 올바른 사용: 일회성 이벤트는 holidays에서 제외
# 또는 upper_window를 아주 짧게 설정
```

### ❌ 실패 2: 예측을 너무 멀리 할 때
- 3년치 데이터로 3년 후를 예측하면 불확실성 구간이 매우 넓어져요
- **경험 법칙**: 훈련 데이터 기간의 20% 이내로 예측 지평 제한
  - 3년(36개월) 데이터 → 최대 7개월 예측 정도가 현실적

### ❌ 실패 3: `changepoint_prior_scale`이 너무 클 때
```
훈련 데이터에서: 완벽하게 데이터에 붙어 있음 (좋아보임)
미래 예측에서:  갑자기 말도 안 되는 값으로 튀어오름 (과적합)
```
→ Cross-Validation으로 실제 예측 오차(MAPE) 확인 필수

---

## 예측 성능 검증: Cross-Validation

```python
from prophet.diagnostics import cross_validation, performance_metrics

# 처음 2년(730일)으로 훈련 → 그 후 6개월(180일)씩 이동 → 12개월(365일) 예측
df_cv = cross_validation(
    model,
    initial='730 days',   # 최초 훈련 기간
    period='180 days',    # 윈도우 이동 간격
    horizon='365 days'    # 예측 기간
)

df_metrics = performance_metrics(df_cv)
print(df_metrics[['horizon', 'mape', 'rmse']])
# MAPE: 오차가 실제 값의 몇 %인지 (낮을수록 좋음)
# RMSE: 예측 오차의 크기 (단위가 원본 데이터와 같음)
```

---

## ITS vs Prophet: 어떻게 다른가요?

두 방법 모두 시계열을 다루는데, 완전히 다른 질문에 답해요:

| | ITS | Prophet |
|---|---|---|
| **질문** | "이 이벤트가 효과가 있었나?" | "앞으로 어떻게 될까?" |
| **시간 방향** | 과거 설명 | 미래 예측 |
| **핵심 출력** | 회귀계수 β₂, β₃ + p-value | 예측값 + 불확실성 구간 |
| **인과 추론** | 가능 (준실험적) | 불가 (예측만) |

**이 프로젝트에서 함께 쓰는 스토리**:
1. STL: "로판이 트렌드적으로 성장 중이다"
2. PELT: "2019년 10월에 구조적 변화가 있었다"
3. ITS: "그 시점의 변화는 통계적으로 유의하고, 재혼황후 웹툰 연재와 시기가 일치한다"
4. **Prophet**: "이 트렌드가 앞으로 유지된다면, 2027년까지 신작 수는 이렇게 예측된다"

---

## 면접에서 "예측에 왜 Prophet을 썼나요?" 질문이 나오면

> "ARIMA처럼 전통적인 시계열 모형은 계절성·트렌드·이벤트 효과를 동시에 처리하기 번거롭고, 파라미터 설정도 전문 지식이 필요해요. Prophet은 이 세 가지를 별도로 모델링하고 더하는 구조라서 각 성분을 직관적으로 해석할 수 있어요. 특히 트렌드에서 자동 변동점을 탐지하고, 연간 계절성을 Fourier 급수로 근사하는 방식이 이 데이터에 적합했어요. Taylor & Letham (2018) 논문에서 제안된 방법으로, ITS로 과거 이벤트 효과를 검정한 뒤, 그 트렌드가 미래에도 이어질지 Prophet으로 예측해 분석을 완결했습니다."

---

## 참고 문헌

1. **(Tier 1 — 원논문)** Taylor, S.J., Letham, B. (2018). *Forecasting at scale.* The American Statistician, 72(1), 37–45. https://doi.org/10.1080/00031305.2017.1380080
2. **(Tier 1 — 공식 문서)** Meta Prophet. *Quick Start.* https://facebook.github.io/prophet/docs/quick_start.html
3. **(Tier 1 — 공식 문서)** Meta Prophet. *Uncertainty Intervals.* https://facebook.github.io/prophet/docs/uncertainty_intervals.html
