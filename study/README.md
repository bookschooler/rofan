# 방법론 심화 학습 자료

> 이 폴더는 로판 트렌드 분석 프로젝트에서 사용하는 분석 방법론의 수학적 원리, 핵심 가정, 실패 조건을 정리한 학습 자료입니다.
> 코드 사용법은 `RESEARCH_TECH.md`를 참조하세요.

## 목차

| 파일 | 방법론 | 프로젝트 내 역할 |
|------|--------|----------------|
| [01_STL.md](01_STL.md) | STL 분해 (Seasonal-Trend decomposition using LOESS) | Phase 2: 시계열 트렌드 분리 |
| [02_PELT.md](02_PELT.md) | PELT 변동점 감지 (Pruned Exact Linear Time) | Phase 2: 구조적 변화 시점 탐지 |
| [03_ITS.md](03_ITS.md) | ITS 중단 시계열 분석 (Interrupted Time Series) | Phase 3: 이벤트 인과 효과 검정 |
| [04_Prophet.md](04_Prophet.md) | Prophet 시계열 예측 | Phase 4: 미래 트렌드 예측 |
| [05_MannKendall.md](05_MannKendall.md) | Mann-Kendall 검정 | Phase 2: 비선형 추세 방향 검증 |
| [06_Welch_ttest.md](06_Welch_ttest.md) | Welch's t-검정 | Phase 2: 변동점 전후 평균 차이 검증 |
| [07_Holm_Bonferroni.md](07_Holm_Bonferroni.md) | Holm-Bonferroni 다중 검정 보정 | Phase 3: 복수 ITS 모델 동시 검정 보정 |

## 학습 순서 권장

```
STL (트렌드가 뭔지 이해) 
  → Mann-Kendall (그 추세가 비선형이어도 유효한지 검증)
  → PELT (언제 변했는지 찾기)
  → Welch t-검정 (변동점 전후가 진짜 다른지 검증)
  → ITS (왜 변했는지 검정)
  → Holm-Bonferroni (여러 ITS를 동시에 돌릴 때 기준 보정)
  → Prophet (앞으로 어떻게 될지 예측)
```

이 순서가 "과거 기술 → 현재 원인 → 미래 예측"의 분석 스토리와 일치합니다.
