"""
Phase 4 - Step 4-1: Prophet 예측
입력: data/processed/02_01_timeseries_monthly.csv
출력: data/processed/04_01_prophet_forecast.csv
      charts/04_01_prophet_forecast.png
      charts/04_01_prophet_components.png
"""

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import koreanize_matplotlib
import pandas as pd
import numpy as np
from pathlib import Path
from prophet import Prophet

BASE_DIR      = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
CHART_DIR     = BASE_DIR / "charts"

# ── 1. 데이터 로드 ─────────────────────────────────────────────────────────────
print("=" * 60)
print("[1] 데이터 로드")
print("=" * 60)

monthly = pd.read_csv(
    PROCESSED_DIR / "02_01_timeseries_monthly.csv", encoding="utf-8-sig"
)
monthly["month"] = pd.to_datetime(monthly["month"])
monthly = monthly.set_index("month")["new_works"]

# 2026-04 수집 편향 제외
monthly = monthly[monthly.index < "2026-04-01"]
assert monthly.index.max() < pd.Timestamp("2026-04-01"), "2026-04 제거 확인 필요"
print(f"  학습 데이터: {len(monthly)}개월 ({monthly.index.min().strftime('%Y-%m')} ~ {monthly.index.max().strftime('%Y-%m')})")

# PELT 결과 CSV에서 변동점 동적 로드 (하드코딩 제거 - PELT 결과 바뀌어도 자동 반영)
cp_csv = PROCESSED_DIR / "02_03_changepoints.csv"
if cp_csv.exists():
    cp_df        = pd.read_csv(cp_csv)
    CHANGEPOINTS = (pd.to_datetime(cp_df["date"]).dt.strftime("%Y-%m-01")).tolist()
    print(f"  변동점 (PELT CSV 로드): {CHANGEPOINTS}")
else:
    CHANGEPOINTS = ["2018-01-01", "2021-07-01"]  # fallback
    print(f"  변동점 (fallback 하드코딩): {CHANGEPOINTS}")

# Prophet 입력 형식 (ds, y)
df_prophet = pd.DataFrame({
    "ds": monthly.index,
    "y":  monthly.values,
})

# ── 2. Prophet 모델 학습 ───────────────────────────────────────────────────────
print("\n[2] Prophet 모델 학습")
print(f"  지정 변동점: {CHANGEPOINTS}")

model = Prophet(
    yearly_seasonality=True,
    weekly_seasonality=False,
    daily_seasonality=False,
    changepoints=CHANGEPOINTS,
    changepoint_prior_scale=0.05,   # 변동점 유연성 (기본 0.05)
    seasonality_prior_scale=10,
    interval_width=0.95,
)
model.fit(df_prophet)
print("  학습 완료")

# ── 2-1. Hold-out MAPE 검증 (2025년 제외 후 재학습) ───────────────────────────
print("\n[2-1] Hold-out MAPE 검증")

holdout_start = pd.Timestamp("2025-01-01")
df_train      = df_prophet[df_prophet["ds"] < holdout_start]
df_test       = df_prophet[df_prophet["ds"] >= holdout_start]

model_cv = Prophet(
    yearly_seasonality=True,
    weekly_seasonality=False,
    daily_seasonality=False,
    changepoints=CHANGEPOINTS,
    changepoint_prior_scale=0.05,
    seasonality_prior_scale=10,
    interval_width=0.95,
)
model_cv.fit(df_train)

future_cv   = model_cv.make_future_dataframe(periods=len(df_test), freq="MS")
forecast_cv = model_cv.predict(future_cv)
pred_test   = forecast_cv[forecast_cv["ds"].isin(df_test["ds"])]["yhat"].values
actual_test = df_test["y"].values

mape = np.mean(np.abs((actual_test - pred_test) / actual_test)) * 100
print(f"  Hold-out 기간: {holdout_start.strftime('%Y-%m')} ~ {df_test['ds'].max().strftime('%Y-%m')} ({len(df_test)}개월)")
grade = "PASS (우수)" if mape < 15 else "PASS (양호)" if mape < 40 else "FAIL"
print(f"  MAPE: {mape:.1f}%  (< 15% 우수 / < 40% 양호  -> {grade})")
assert mape < 40, f"MAPE {mape:.1f}% - 예측 신뢰도 검토 필요 (기준 40% 초과)"

# ── 3. 예측 (2026-12까지) ─────────────────────────────────────────────────────
print("\n[3] 2026-12까지 예측")

# 학습 종료(2026-03) 이후 9개월 추가 예측
future = model.make_future_dataframe(periods=9, freq="MS")
forecast = model.predict(future)

# 예측 구간만 추출 (2026-04 이후)
forecast_future = forecast[forecast["ds"] >= "2026-04-01"].copy()
print(f"  예측 기간: {forecast_future['ds'].min().strftime('%Y-%m')} ~ {forecast_future['ds'].max().strftime('%Y-%m')}")
print(f"\n  {'연월':<10} {'예측(yhat)':<12} {'하한(95%)':<12} {'상한(95%)'}")
print(f"  {'-'*45}")
for _, row in forecast_future.iterrows():
    print(f"  {row['ds'].strftime('%Y-%m'):<10} {row['yhat']:>8.1f}편   {row['yhat_lower']:>8.1f}편   {row['yhat_upper']:>8.1f}편")

# ── 4. CSV 저장 ───────────────────────────────────────────────────────────────
save_cols = ["ds", "yhat", "yhat_lower", "yhat_upper", "trend", "yearly"]
forecast_save = forecast[save_cols].copy()
forecast_save.columns = ["month", "yhat", "yhat_lower", "yhat_upper", "trend", "yearly"]
csv_path = PROCESSED_DIR / "04_01_prophet_forecast.csv"
forecast_save.to_csv(csv_path, index=False, encoding="utf-8-sig")
print(f"\n  저장: {csv_path}")

# ── 5. 예측 차트 ───────────────────────────────────────────────────────────────
print("\n[4] 차트 생성")

fig, ax = plt.subplots(figsize=(15, 6))

# 실제 데이터
ax.plot(monthly.index, monthly.values, color="steelblue", linewidth=1,
        label="실제 신작 수", zorder=3)

# 학습 구간 fitted
forecast_train = forecast[forecast["ds"] < "2026-04-01"]
ax.plot(forecast_train["ds"], forecast_train["yhat"],
        color="tomato", linewidth=1.5, linestyle="-", label="Prophet 적합값", zorder=2)

# 예측 구간 (2026-04~)
ax.plot(forecast_future["ds"], forecast_future["yhat"],
        color="darkorange", linewidth=2, linestyle="--", label="예측 (2026-04~)", zorder=3)
ax.fill_between(forecast_future["ds"],
                forecast_future["yhat_lower"], forecast_future["yhat_upper"],
                color="darkorange", alpha=0.2, label="95% 예측 구간")

# 변동점 표시 (PELT CSV에서 동적 로드한 CHANGEPOINTS 사용)
for i, cp in enumerate(CHANGEPOINTS, 1):
    ax.axvline(pd.Timestamp(cp), color="gray", linewidth=1.2,
               linestyle=":", alpha=0.7, label=f"변동점{i} ({cp[:7]})")

# 예측 시작선
ax.axvline(pd.Timestamp("2026-04-01"), color="black", linewidth=1.5,
           linestyle="--", alpha=0.6, label="예측 시작 (2026-04)")

ax.set_title("로판 월별 신작 수 - Prophet 예측 (2026-12까지)", fontsize=13, fontweight="bold")
ax.set_xlabel("연월")
ax.set_ylabel("신작 수 (편)")
ax.legend(fontsize=8, loc="upper left", ncol=2)
plt.tight_layout()

chart_path = CHART_DIR / "04_01_prophet_forecast.png"
plt.savefig(chart_path, dpi=150, bbox_inches="tight")
plt.close()
print(f"  저장: {chart_path}")

# ── 6. 컴포넌트 차트 (추세 + 계절성) ─────────────────────────────────────────
fig2, axes = plt.subplots(2, 1, figsize=(15, 7))
fig2.suptitle("Prophet 컴포넌트 분해 - 추세 & 계절성", fontsize=13, fontweight="bold")

# 추세
axes[0].plot(forecast["ds"], forecast["trend"], color="tomato", linewidth=1.5)
for cp in CHANGEPOINTS:
    axes[0].axvline(pd.Timestamp(cp), color="gray", linewidth=1, linestyle=":", alpha=0.7)
axes[0].axvline(pd.Timestamp("2026-04-01"), color="black", linewidth=1.2, linestyle="--", alpha=0.6)
axes[0].set_ylabel("추세 (편)")
axes[0].set_title("추세 (Trend)")

# 계절성 - 월별 평균 패턴 추출
yearly_df = forecast[["ds", "yearly"]].copy()
yearly_df["month"] = yearly_df["ds"].dt.month
monthly_seasonal = yearly_df.groupby("month")["yearly"].mean()
bar_colors = ["#e74c3c" if v >= 0 else "#3498db" for v in monthly_seasonal.values]
month_kor = ["1월","2월","3월","4월","5월","6월","7월","8월","9월","10월","11월","12월"]
axes[1].bar(monthly_seasonal.index, monthly_seasonal.values, color=bar_colors, alpha=0.8, width=0.6)
axes[1].axhline(0, color="gray", linewidth=0.8, linestyle="--")
y_max = monthly_seasonal.max()
y_min = monthly_seasonal.min()
y_pad = (y_max - y_min) * 0.3
axes[1].set_ylim(y_min - y_pad, y_max + y_pad)
for m, val in monthly_seasonal.items():
    axes[1].text(m, val + (0.3 if val >= 0 else -0.3), f"{val:+.1f}",
                 ha="center", va="bottom" if val >= 0 else "top", fontsize=8)
axes[1].set_xticks(range(1, 13))
axes[1].set_xticklabels(month_kor, fontsize=9)
axes[1].set_ylabel("계절성 효과 (편)")
axes[1].set_title("월별 평균 계절성 (Yearly Seasonality)")

plt.tight_layout()
chart_path2 = CHART_DIR / "04_01_prophet_components.png"
plt.savefig(chart_path2, dpi=150, bbox_inches="tight")
plt.close()
print(f"  저장: {chart_path2}")

print("\n" + "=" * 60)
print("[완료] 04_01_prophet.py")
print("=" * 60)
