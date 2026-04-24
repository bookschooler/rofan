# Holm-Bonferroni 보정 — "검정을 여러 번 할수록 기준을 엄격하게"

> **이 방법이 하는 일**: 여러 모델을 동시에 검정할 때 "운 좋게 통과"하는 가짜 결과를 걸러내기
>
> **프로젝트에서 쓰는 곳**: Phase 3 (ITS) — 이벤트×플랫폼 조합 12개를 동시에 검정할 때 적용

**원논문(Tier 1)**: Holm, S. (1979). *A simple sequentially rejective multiple test procedure.* Scandinavian Journal of Statistics, 6(2), 65–70.

---

## 왜 이게 필요한가 — 핵심 직관

**주사위를 한 번 던져서 6이 나올 확률**: 1/6 ≈ 17%

**주사위를 10번 던져서 적어도 한 번 6이 나올 확률**: 1 - (5/6)^10 ≈ **84%**

검정도 똑같아요.

> 검정 1번: 효과 없는데 "있다"고 잘못 판단할 확률 5%  
> 검정 12번: 12번 중 적어도 1번은 잘못 판단할 확률 → **1 - (0.95)^12 ≈ 46%**

즉, 12번 검정하면 거의 절반 확률로 가짜 결과가 섞여요. 아무 보정 없이 각각 p<0.05로 판단하면 안 돼요.

---

## 쏘피가 말한 직관 — 정확히 맞아요!

> "각 검정 확률도 20분의 1이니까 그걸 반영하면 오류가 안 생기지 않아?"

맞아요. 그게 바로 **Bonferroni 보정**의 핵심이에요.

12번 검정한다면, 각 검정의 기준을 이렇게 조정해요:

$$\text{개별 기준} = \frac{0.05}{12} \approx 0.004$$

즉, p < 0.004를 통과해야만 "유의미하다"고 인정해요. 이렇게 하면 전체적으로 "우연히 통과할 확률"이 다시 5% 수준으로 내려와요.

**핵심**: 보정은 자동으로 안 돼요. 명시적으로 기준을 나눠줘야 오류가 사라져요.

---

## Bonferroni vs Holm-Bonferroni — 뭐가 다른가?

**Bonferroni (기본형)**: 모든 검정에 같은 기준(0.05/n) 적용. 단순하지만 너무 엄격해서 진짜 효과도 놓칠 수 있어요.

**Holm-Bonferroni (개선형)**: p-value를 작은 것부터 순서대로 평가해서, 작을수록 더 엄격하게, 클수록 덜 엄격하게 적용.

| 검정 순위 | p-value | Bonferroni 기준 | Holm 기준 |
|---------|---------|----------------|----------|
| 1번째 (가장 작음) | 0.001 | 0.05/12 = 0.004 | 0.05/12 = 0.004 |
| 2번째 | 0.008 | 0.004 | 0.05/11 = 0.0045 |
| 3번째 | 0.02 | 0.004 | 0.05/10 = 0.005 |
| ... | ... | ... | ... |

**결론**: Holm은 Bonferroni보다 덜 보수적(더 유연)하지만, 안전성은 동일해요. 그래서 Holm-Bonferroni를 더 많이 써요.

---

## Holm 순서대로 판단하는 방법

1. 모든 검정의 p-value를 작은 순서로 정렬
2. 가장 작은 p-value부터 차례로 확인:
   - k번째 검정의 기준: `0.05 / (전체 개수 - k + 1)`
   - p-value < 기준 → 통과 (계속 진행)
   - p-value ≥ 기준 → **여기서 멈추고, 이후는 모두 기각**
3. 통과한 것만 "유의미하다"고 결론

---

## 코드로 보기

```python
from statsmodels.stats.multitest import multipletests

# ITS 결과에서 p-value 모으기 (β2: 레벨변화, β3: 기울기변화)
all_pvals = results_df["p_beta2"].tolist() + results_df["p_beta3"].tolist()

# Holm-Bonferroni 보정 적용
reject, pvals_corrected, _, _ = multipletests(all_pvals, method="holm")

# 보정된 p-value 저장
n = len(results_df)
results_df["p_beta2_holm"] = pvals_corrected[:n]
results_df["p_beta3_holm"] = pvals_corrected[n:]
results_df["sig_beta2_holm"] = results_df["p_beta2_holm"] < 0.05
```

**결과 읽는 법**:
```
보정 전: E001 β2 p=0.031 → 유의미
보정 후: E001 β2 p=0.062 → 유의미하지 않음
→ 이 결과는 다중 검정 오류였음. 보정 후 실제 효과 없음으로 판정.
```

---

## 로판 프로젝트에서는 어떤 결과가 나왔나?

```
ITS Phase 3-1: 2개 이벤트 × β2/β3 = 4개 검정
ITS Phase 3-2: 6개 모델(3플랫폼×2이벤트) × β2/β3 = 12개 검정
```

**결과**: 보정 전후 유의성 판정이 동일했어요.

이게 좋은 신호예요. "12번 검정했는데도 기준이 엄격해진 후에도 살아남았다" = 효과가 충분히 강하다는 뜻.

---

## 언제 다중 검정 보정이 필요한가?

| 상황 | 필요 여부 |
|------|---------|
| 하나의 연구 질문에 대해 검정 1번 | 불필요 |
| 플랫폼 3개 × 이벤트 2개 = 6개 동시 검정 | **필요** |
| 같은 데이터로 여러 가설을 탐색적으로 검정 | **필요** |
| 사전에 정한 1개의 가설만 검정 | 불필요 |

> **경험 법칙**: 검정 횟수가 3개 이상이거나, 같은 데이터를 여러 각도로 분석하면 보정을 고려해요.

---

## 면접에서 "왜 Holm-Bonferroni를 썼나요?" 질문이 나오면

> "3개 플랫폼 × 2개 이벤트 = 6개 모델에서 각각 β2, β3를 검정하면 총 12번 검정이 됩니다. 보정 없이 각각 p<0.05로 판단하면 46% 확률로 가짜 유의미한 결과가 생겨요. Bonferroni보다 통계적 검증력을 잃지 않으면서도 안전한 Holm 방법을 적용했고, 보정 전후 결과가 동일해서 분석 결론의 강건성을 확인했습니다."

---

## 참고 문헌

1. **(Tier 1 — 원논문)** Holm, S. (1979). *A simple sequentially rejective multiple test procedure.* Scandinavian Journal of Statistics, 6(2), 65–70.
2. **(Tier 1 — 공식 문서)** statsmodels.stats.multitest. https://www.statsmodels.org/dev/generated/statsmodels.stats.multitest.multipletests.html
