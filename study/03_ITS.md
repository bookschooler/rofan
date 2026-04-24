# ITS — Interrupted Time Series (중단 시계열 분석)

> **이 분석이 하는 일**: "재혼황후 웹툰이 연재된 이후 로판 신작이 늘었다 — 이게 진짜 이벤트 때문인가, 원래 늘고 있던 거 아닌가?" 구분하기
>
> **프로젝트에서 쓰는 곳**: Phase 3 — 드라마화 이벤트의 인과적 효과를 회귀계수와 p-value로 수치화

**핵심 논문(Tier 1)**: Bernal, J.L., Cummins, S., Gasparrini, A. (2017). *Interrupted time series regression for the evaluation of public health interventions: a tutorial.* International Journal of Epidemiology, 46(1), 348–355. https://doi.org/10.1093/ije/dyw098

---

## 왜 단순 전후 비교가 안 되나요?

"이벤트 전 평균 vs 이벤트 후 평균"을 비교하면 되지 않냐고 생각할 수 있어요. 안 되는 이유:

```
신작 수
│                    ↗ 이벤트 후 실제 (더 가파름)
│               ↗↗↗
│          ↗↗↗
│     ↗↗↗  ← 이벤트 전에도 이미 증가 중
│ ↗↗↗
└────────────────────→ 시간
         ↑ 이벤트

단순 비교: "이벤트 후 평균이 높다" = 맞지만 이미 늘고 있었기 때문에 당연한 거 아닌가?
```

ITS가 하는 일: "이벤트가 없었다면 이 증가 속도가 그대로 계속됐을 것이다(반사실)"를 추정하고, 실제로 그것보다 더 많이 늘었는지 검정.

---

## 핵심 수식 — 딱 1개만 외우기

$$Y_t = \beta_0 + \beta_1 T + \beta_2 X_t + \beta_3 (T \times X_t) + \varepsilon_t$$

한국어로 풀면:

```
이번 달 신작 수 
= (기본값)
+ (이벤트 전 매달 증가분) × 시간
+ (이벤트 발생 직후 즉각 변화)
+ (이벤트 이후 매달 증가분 변화) × 이벤트 후 경과 월수
+ 오차
```

각 β가 뭘 의미하는지 로판 예시로:

| β | 이름 | 로판 예시 |
|---|------|---------|
| β₀ | 기준값 | 2013년 1월 기준 신작 수 |
| β₁ | 이벤트 전 기울기 | 재혼황후 전, 매월 신작 +0.5편씩 증가했음 |
| **β₂** | **즉각적 수준 변화** | 재혼황후 웹툰 연재 직후 갑자기 신작 +5편 |
| **β₃** | **기울기 변화** | 이벤트 이후 매월 증가폭이 +0.5 → +1.2로 가속됨 |

**β₂와 β₃이 0보다 크고 p-value < 0.05 면 → "이 이벤트는 통계적으로 유의한 효과가 있었다"**

---

## 반사실(Counterfactual)을 그림으로 이해하기

```
신작 수
│
│                         ●●● 실제 데이터 (이벤트 후)
│                    ●●●●
│               ●●●●
│──────────────●
│         ╱╱╱╱  ← 이벤트 없었을 때 예상 트렌드 (반사실)
│    ╱╱╱╱╱
│╱╱╱╱
└──────────────────────────→ 시간
              ↑ 이벤트 발생

β₂ = 이벤트 발생 시점에서 실제 - 반사실 (즉각 점프)
β₃ = 이후 기울기가 더 가팔라진 정도
```

---

## 더미 변수 만들기

```python
import pandas as pd
import statsmodels.formula.api as smf

# 재혼황후 웹툰 연재 시작: 2019-10-01
event_date = pd.Timestamp('2019-10-01')

df['T'] = range(1, len(df) + 1)                           # 시간 인덱스 (1, 2, 3, ...)
df['X'] = (df['date'] >= event_date).astype(int)           # 이벤트 더미: 이전=0, 이후=1
df['TX'] = df['T'] * df['X']                               # 기울기 변화 항

# OLS 회귀 (HAC: 시계열 자기상관 보정)
model = smf.ols('new_works ~ T + X + TX', data=df).fit(
    cov_type='HAC', cov_kwds={'maxlags': 3}
)

print(model.summary())
```

결과에서 봐야 할 것:
```
                 coef    std err    t      P>|t|
T (β₁)          0.51      0.12   4.25    0.000  ← 이벤트 전 매달 +0.51편
X (β₂)          4.83      1.45   3.33    0.001  ← 이벤트 직후 +4.83편 (유의!)
TX (β₃)         0.89      0.23   3.87    0.000  ← 이후 증가속도 +0.89/월 (유의!)
```

---

## 핵심 가정 — "이게 맞아야 ITS를 쓸 수 있어요"

| 가정 | 쉬운 말 | 깨지면? |
|------|--------|--------|
| 이벤트 전 트렌드가 이벤트 없었어도 계속됐을 것이다 | 반사실이 선형 연장선이다 | 이벤트와 무관한 다른 이유로 바뀌었으면 β₂, β₃가 오염됨 |
| 이벤트 시점이 명확하게 하나다 | "2019년 10월부터" 딱 잘라 말할 수 있다 | 점진적으로 바이럴된 경우 시점 설정이 어려움 |
| 이벤트 전에 충분한 데이터가 있다 | 이벤트 전 최소 8~12개월 이상 | 이전 트렌드 추정이 불안정해짐 |
| 잔차(오차)에 자기상관이 없다 (또는 보정) | 시계열 특성상 이전 달이 이번 달에 영향 | 무시하면 p-value가 실제보다 작게 나옴 (가짜 유의) |

---

## 이럴 때 ITS가 실패해요

### ❌ 실패 1: 자기상관을 무시했을 때
"이번 달 신작이 많으면 다음 달도 많다" — 시계열은 이런 특성이 있어요. 일반 OLS로 분석하면 이 상관관계를 오차로 보지 않아서 표준 오차가 과소 추정됩니다. 결과: p-value가 실제보다 낮게 나와서 효과가 있는 것처럼 보임.

**해결**: `cov_type='HAC'` 반드시 적용

### ❌ 실패 2: 이벤트와 동시에 다른 변화도 있을 때
- "재혼황후 웹툰 연재" 시작과 같은 달에 "카카오페이지 대규모 할인 이벤트"가 있었다면?
- β₂가 두 이벤트의 합산 효과가 되어서 재혼황후만의 효과라고 말할 수 없어요
- **보고서에 이 한계를 명시해야 함**

### ❌ 실패 3: 이벤트 전 데이터가 너무 짧을 때
- 2019년 9월에 연재 시작인데 데이터가 2019년 1월부터밖에 없다면 → 8개월치로 트렌드 추정
- 기준: 이벤트 전후 각각 최소 8개 관측값 (Bernal et al., 2017 권장)

### ❌ 실패 4: "통계적으로 유의하다 = 이 이벤트가 원인이다"로 단정
- ITS는 준실험 설계(Quasi-experimental design)예요. 무작위 대조 실험(RCT)이 아니에요.
- β₃이 유의하다 = "이벤트 이후 트렌드가 통계적으로 의미 있게 변했다"
- ≠ "재혼황후가 유일한 원인이다"
- **보고서에서 반드시 "인과 주장의 한계" 명시**

---

## 여러 이벤트를 분석할 때: 다중 검정 보정

이 프로젝트는 이벤트가 여러 개예요 (E001, E003, E004). 이벤트별로 검정을 3번 하면 우연히 p < 0.05가 나올 확률이 14%로 올라가요. 이걸 막으려면 Holm-Bonferroni를 써요.

```python
from statsmodels.stats.multitest import multipletests

# 각 이벤트별 ITS에서 얻은 β₃의 p-value
pvals = [0.03, 0.08, 0.01]   # E001, E003, E004의 p-value

reject, pvals_corrected, _, _ = multipletests(pvals, method='holm')

for i, (event, p_orig, p_corr, sig) in enumerate(zip(
    ['E001', 'E003', 'E004'], pvals, pvals_corrected, reject
)):
    print(f"{event}: 원래 p={p_orig:.3f} → 보정 p={p_corr:.3f} → {'유의' if sig else '비유의'}")
```

**왜 Holm-Bonferroni인가**: 가장 단순한 Bonferroni 보정보다 검정력이 높으면서도 거짓 양성을 잘 통제해요. 이벤트가 3~5개인 이 프로젝트에 딱 맞아요.

---

## ITS와 PELT를 함께 쓰는 이유

```
PELT:  "2019년 10월에 뭔가 바뀌었다" (탐지)
ITS:   "2019년 10월 이후 β₃=+0.89, p<0.001 → 재혼황후 연재와 타이밍이 일치하고 효과가 유의하다" (검정)
```

PELT 없이 ITS만 써도 되지만, PELT로 먼저 변동점을 찾으면 "이 이벤트 시점에서 ITS를 해야 한다"는 데이터 기반 근거가 생겨요.

---

## 면접에서 "이벤트 효과를 어떻게 측정했나요?" 질문이 나오면

> "단순히 이벤트 전후 평균을 비교하면 이미 증가하고 있던 트렌드가 반영돼서 이벤트의 순수한 효과를 측정할 수 없어요. ITS는 이벤트 전 트렌드를 반사실로 설정하고, 이벤트 이후 실제 데이터가 그 반사실에서 얼마나 이탈했는지를 β₂(즉각 수준 변화)와 β₃(기울기 변화)로 측정합니다. 시계열 자기상관 보정을 위해 HAC 표준 오차를 사용했고, 여러 이벤트를 동시에 검정할 때는 거짓 양성을 통제하기 위해 Holm-Bonferroni 보정을 적용했습니다."

---

## 참고 문헌

1. **(Tier 1 — 방법론 튜토리얼)** Bernal, J.L., Cummins, S., Gasparrini, A. (2017). *Interrupted time series regression for the evaluation of public health interventions: a tutorial.* International Journal of Epidemiology, 46(1), 348–355. https://doi.org/10.1093/ije/dyw098
2. **(Tier 1 — 준실험 설계 고전)** Shadish, W.R., Cook, T.D., Campbell, D.T. (2002). *Experimental and Quasi-experimental Designs for Generalized Causal Inference.* Houghton Mifflin.
3. **(Tier 1 — 공식 문서)** statsmodels. *OLS Regression.* https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.OLS.html
