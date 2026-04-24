"""
Phase 2 - Step 2-2: STL 분해
입력: data/processed/02_01_timeseries_monthly.csv
출력: data/processed/02_02_stl_results.csv
      charts/02_02_stl_decomposition.png
"""

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import koreanize_matplotlib
import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats
from statsmodels.tsa.seasonal import STL
import pymannkendall as mk

BASE_DIR      = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
CHART_DIR     = BASE_DIR / "charts"

# ── 1. 시계열 로드 ─────────────────────────────────────────────────────────────
print("=" * 60)
print("[1] 시계열 로드")
print("=" * 60)

monthly = pd.read_csv(
    PROCESSED_DIR / "02_01_timeseries_monthly.csv", encoding="utf-8-sig"
)
monthly["month"] = pd.to_datetime(monthly["month"])
monthly = monthly.set_index("month")["new_works"]
monthly = monthly[monthly.index < "2026-04-01"]  # 수집 편향 제외

print(f"  로드 완료: {len(monthly)}개월 ({monthly.index.min().strftime('%Y-%m')} ~ {monthly.index.max().strftime('%Y-%m')})")

# ── 1-1. 균등 간격 보정 (STL은 내부적으로 균등 간격 가정) ─────────────────────
# 2013년 초반 결측 구간이 있으면 full date_range로 리인덱싱 후 선형 보간
full_idx = pd.date_range(monthly.index.min(), monthly.index.max(), freq="MS")
n_missing = len(full_idx) - len(monthly)
if n_missing > 0:
    monthly = monthly.reindex(full_idx).interpolate(method="linear")
    print(f"  결측 보간: {n_missing}개월 선형 보간 적용 (균등 간격 확보)")
else:
    print(f"  결측 없음 - 균등 간격 확인")

# ── 2. STL 분해 ───────────────────────────────────────────────────────────────
print("\n[2] STL 분해 (period=12, robust=True)")

stl        = STL(monthly, period=12, robust=True)
stl_result = stl.fit()
trend      = stl_result.trend
seasonal   = stl_result.seasonal
residual   = stl_result.resid

print(f"  추세(trend) 범위: {trend.min():.1f} ~ {trend.max():.1f}")
print(f"  계절성(seasonal) 진폭: {seasonal.max() - seasonal.min():.1f}")
print(f"  잔차(residual) 표준편차: {residual.std():.2f}")

# 수용 기준: 잔차 분산이 원본 분산의 30% 미만이어야 STL 분해 의미 있음
resid_ratio = residual.var() / monthly.var()
print(f"  잔차/원본 분산 비율: {resid_ratio:.3f} (기준: < 0.30)")
assert resid_ratio < 0.30, f"STL 분해 품질 불통과: 잔차 분산 비율 {resid_ratio:.3f}"
# 2026-04 제거 수용 기준
assert monthly.index.max() < pd.Timestamp("2026-04-01"), "2026-04 제거 확인 필요"
assert (monthly >= 0).all(), "음수값 없음 확인"

# ── 3. 추세 선형 회귀 + Mann-Kendall 검정 ─────────────────────────────────────
print("\n[3] 추세 분석")

x_num = np.arange(len(trend))
slope, intercept, r_val, p_val, _ = stats.linregress(x_num, trend.values)
direction = "상승" if slope > 0 else "하락"
sig       = "유의미" if p_val < 0.05 else "유의미하지 않음"

print(f"  [OLS 선형 회귀]")
print(f"  기울기: {slope:.4f} 편/월  ->  연간 {slope * 12:.1f} 편/년")
print(f"  R2: {r_val**2:.4f}  |  p-value: {p_val:.6f}")
print(f"  -> 통계적으로 {sig}한 {direction} 추세 (p {'<' if p_val < 0.05 else '>='} 0.05)")

# Mann-Kendall: 선형 가정 없는 단조 추세 검정 (비선형 S자 성장에 더 적합)
mk_result = mk.original_test(monthly.values)
mk_sig    = "유의미" if mk_result.p < 0.05 else "유의미하지 않음"
print(f"\n  [Mann-Kendall 단조 추세 검정 (비모수 - 선형 가정 없음)]")
print(f"  추세 방향: {mk_result.trend}  |  p-value: {mk_result.p:.6f}  |  Tau: {mk_result.Tau:.4f}")
print(f"  -> 통계적으로 {mk_sig}한 단조 {direction} 추세")
assert mk_result.p < 0.05, f"추세 유의성 불통과: p={mk_result.p:.4f}"

# ── 4. 계절성 월별 평균 ────────────────────────────────────────────────────────
print("\n[4] 월별 평균 계절성 효과  (+ : 성수기, - : 비수기)")

seasonal_df       = pd.DataFrame({"date": seasonal.index, "seasonal": seasonal.values})
seasonal_df["m"]  = seasonal_df["date"].dt.month
monthly_seasonal  = seasonal_df.groupby("m")["seasonal"].mean()
peak_month        = int(monthly_seasonal.idxmax())
trough_month      = int(monthly_seasonal.idxmin())
month_kor         = ["1월","2월","3월","4월","5월","6월","7월","8월","9월","10월","11월","12월"]

for m, val in monthly_seasonal.items():
    print(f"  {month_kor[m-1]:>4}: {val:+.1f}")
print(f"\n  최대 성수기: {month_kor[peak_month-1]} ({monthly_seasonal[peak_month]:+.1f}편)")
print(f"  최대 비수기: {month_kor[trough_month-1]} ({monthly_seasonal[trough_month]:+.1f}편)")

# ── 5. 잔차 이상치 ─────────────────────────────────────────────────────────────
print("\n[5] 잔차 이상치 - 상위/하위 5개월")

resid_s    = pd.Series(residual.values, index=residual.index)
sigma      = resid_s.std()
pos_anomaly = resid_s[resid_s >  2 * sigma].sort_values(ascending=False)
neg_anomaly = resid_s[resid_s < -2 * sigma].sort_values()
print(f"  기준: |잔차| > 2sigma ({2*sigma:.1f}편) - 통계적 이상치")
print(f"  [예상보다 신작 많았던 달] ({len(pos_anomaly)}개월)")
for dt, val in pos_anomaly.items():
    print(f"    {dt.strftime('%Y-%m')}: {val:+.1f}편  ({val/sigma:.1f}σ)")
print(f"  [예상보다 신작 적었던 달] ({len(neg_anomaly)}개월)")
for dt, val in neg_anomaly.items():
    print(f"    {dt.strftime('%Y-%m')}: {val:+.1f}편  ({val/sigma:.1f}σ)")

# ── 6. CSV 저장 ───────────────────────────────────────────────────────────────
stl_csv = pd.DataFrame({
    "month":    monthly.index.strftime("%Y-%m"),
    "original": monthly.values,
    "trend":    trend.values,
    "seasonal": seasonal.values,
    "residual": residual.values,
})
csv_path = PROCESSED_DIR / "02_02_stl_results.csv"
stl_csv.to_csv(csv_path, index=False, encoding="utf-8-sig")
print(f"\n  저장: {csv_path}")

# ── 7. 차트 (4패널) ────────────────────────────────────────────────────────────
trend_fit = intercept + slope * x_num

fig, axes = plt.subplots(4, 1, figsize=(14, 13))
fig.suptitle("로판 월별 신작 수 - STL 분해", fontsize=14, fontweight="bold")

# 날짜 기반 3개 패널은 x축 범위 통일
date_xlim = (monthly.index.min(), monthly.index.max())

axes[0].plot(monthly.index, monthly.values, color="steelblue", linewidth=1)
axes[0].set_ylabel("신작 수")
axes[0].set_title("원본 시계열")
axes[0].set_xlim(date_xlim)

axes[1].plot(trend.index, trend.values, color="tomato", linewidth=1.5)
axes[1].plot(trend.index, trend_fit, color="darkred", linewidth=1, linestyle="--",
             label=f"회귀선 ({slope*12:.1f}편/년, p={p_val:.4f})")
axes[1].legend(fontsize=8)
axes[1].set_ylabel("추세")
axes[1].set_title("추세(Trend) + 회귀선")
axes[1].set_xlim(date_xlim)

# 계절성 패널 - 월별 평균 막대 차트 (1~12월)
bar_colors = ["#e74c3c" if v >= 0 else "#3498db" for v in monthly_seasonal.values]
axes[2].bar(monthly_seasonal.index, monthly_seasonal.values, color=bar_colors, alpha=0.8, width=0.6)
axes[2].axhline(0, color="gray", linewidth=0.8, linestyle="--")
# y축 범위를 최대·최솟값 기준으로 위아래 30% 여백 추가
y_max = monthly_seasonal.max()
y_min = monthly_seasonal.min()
y_pad = (y_max - y_min) * 0.3
axes[2].set_ylim(y_min - y_pad, y_max + y_pad)
for m, val in monthly_seasonal.items():
    axes[2].text(m, val + (0.2 if val >= 0 else -0.2), f"{val:+.1f}",
                 ha="center", va="bottom" if val >= 0 else "top", fontsize=8)
axes[2].set_xticks(range(1, 13))
axes[2].set_xticklabels(month_kor, fontsize=9)
axes[2].set_ylabel("평균 계절성 (편)")
axes[2].set_title(f"월별 평균 계절성 효과  |  성수기: {month_kor[peak_month-1]} ({monthly_seasonal[peak_month]:+.1f}편)  비수기: {month_kor[trough_month-1]} ({monthly_seasonal[trough_month]:+.1f}편)")

axes[3].plot(residual.index, residual.values, color="gray", linewidth=1)
axes[3].axhline(0, color="black", linewidth=0.5, linestyle="--")

# 양수 이상치 (빨간색, 위쪽)
used_x_pos = []  # 레이블 겹침 방지용
for dt, val in resid_s.nlargest(5).items():
    # 인접 레이블이 있으면 위아래로 엇갈리게 배치
    offset = 2.5 if any(abs((dt - px).days) < 60 for px in used_x_pos) else 1.0
    axes[3].annotate(dt.strftime("%Y-%m"), xy=(dt, val),
                     xytext=(0, offset * 8), textcoords="offset points",
                     fontsize=7, color="red", ha="center", va="bottom",
                     arrowprops=dict(arrowstyle="-", color="red", lw=0.5))
    used_x_pos.append(dt)

# 음수 이상치 (파란색, 아래쪽)
used_x_neg = []
for dt, val in resid_s.nsmallest(5).items():
    offset = 2.5 if any(abs((dt - px).days) < 60 for px in used_x_neg) else 1.0
    axes[3].annotate(dt.strftime("%Y-%m"), xy=(dt, val),
                     xytext=(0, -offset * 8), textcoords="offset points",
                     fontsize=7, color="steelblue", ha="center", va="top",
                     arrowprops=dict(arrowstyle="-", color="steelblue", lw=0.5))
    used_x_neg.append(dt)

r_max = resid_s.max()
r_min = resid_s.min()
r_pad = (r_max - r_min) * 0.25
axes[3].set_ylim(r_min - r_pad, r_max + r_pad)
axes[3].set_ylabel("잔차")
axes[3].set_title("잔차(Residual)  빨간: 양수 이상치 (+)  파란: 음수 이상치 (-)")
axes[3].set_xlim(date_xlim)

plt.tight_layout()
chart_path = CHART_DIR / "02_02_stl_decomposition.png"
plt.savefig(chart_path, dpi=150, bbox_inches="tight")
plt.close()
print(f"  저장: {chart_path}")

print("\n" + "=" * 60)
print("[완료] 02_02_stl.py")
print("=" * 60)
