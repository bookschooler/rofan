"""
Phase 2: STL 분해 + PELT 변동점 감지 (통합 실행 파일)
- Step 2-1: 월별 신작 수 시계열 집계 (전체 + 플랫폼별)
- Step 2-2: STL(Seasonal-Trend decomposition using LOESS)로 추세·계절성 분리
- Step 2-3: PELT(Pruned Exact Linear Time) 알고리즘으로 구조 변동점 탐지

각 Step을 독립 실행하려면:
  python analysis/02_01_timeseries.py
  python analysis/02_02_stl.py
  python analysis/02_03_pelt.py
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
import ruptures as rpt

BASE_DIR      = Path(__file__).resolve().parent.parent
DATA_DIR      = BASE_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
CHART_DIR     = BASE_DIR / "charts"
PROCESSED_DIR.mkdir(exist_ok=True)
CHART_DIR.mkdir(exist_ok=True)

PLATFORM_LABELS = {
    "kakaopage":     "카카오페이지",
    "naver_series":  "네이버 시리즈",
    "naver_webtoon": "네이버 웹툰",
}
KNOWN_EVENTS = {
    "E001 (재혼황후 웹툰)":      pd.Timestamp("2019-10-25"),
    "E003 (선재업고튀어 드라마)": pd.Timestamp("2024-04-08"),
}

# ══════════════════════════════════════════════════════════════
# STEP 2-1: 시계열 집계
# ══════════════════════════════════════════════════════════════
print("=" * 60)
print("[Step 2-1] 월별 신작 수 시계열 집계")
print("=" * 60)

df = pd.read_csv(DATA_DIR / "raw" / "all_works_integrated.csv", low_memory=False)
print(f"  전체 행 수: {len(df):,}")

print(f"  content_form 분포:\n{df['content_form'].value_counts().to_string()}")
df = df[df["content_form"] == "serialized"].copy()
print(f"\n  분석 대상 (serialized): {len(df):,}행")

df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
n_before = len(df)
df = df.dropna(subset=["start_date"])
print(f"  NaT 제거: {n_before - len(df)}행 제외 -> 분석 대상 {len(df):,}행")
print(f"  start_date 범위: {df['start_date'].min().date()} ~ {df['start_date'].max().date()}")

df["month"] = df["start_date"].dt.to_period("M")
monthly = df.groupby("month").size().rename("new_works").sort_index()
monthly.index = monthly.index.to_timestamp()

print(f"  시계열 길이: {len(monthly)}개월  |  월 평균: {monthly.mean():.1f}편  |  최다: {monthly.max()}편 ({monthly.idxmax().strftime('%Y-%m')})")

yearly = monthly.resample("YE").sum()
print("\n  [연도별 신작 수]")
for year, count in yearly.items():
    print(f"    {year.year}년: {int(count):>4}편")

monthly.reset_index().rename(columns={"index": "month"}).to_csv(
    PROCESSED_DIR / "02_01_timeseries_monthly.csv", index=False, encoding="utf-8-sig"
)

# 플랫폼별
platform_monthly = (
    df.groupby(["platform", "month"]).size().unstack(level="platform", fill_value=0)
)
platform_monthly.index = platform_monthly.index.to_timestamp()

for col, label in PLATFORM_LABELS.items():
    if col not in platform_monthly.columns:
        continue
    s = platform_monthly[col]
    print(f"\n  [{label}]  시작: {s[s>0].index.min().strftime('%Y-%m')}  월평균: {s.mean():.1f}편  최다: {s.max()}편 ({s.idxmax().strftime('%Y-%m')})")

platform_monthly.reset_index().rename(columns={"index": "month"}).to_csv(
    PROCESSED_DIR / "02_01_timeseries_monthly_by_platform.csv", index=False, encoding="utf-8-sig"
)

colors = {"kakaopage": "#FFCD00", "naver_series": "#03C75A", "naver_webtoon": "#1EC800"}
fig, axes = plt.subplots(2, 1, figsize=(14, 10))
bottom = pd.Series(0, index=platform_monthly.index)
for col in ["kakaopage", "naver_series", "naver_webtoon"]:
    if col not in platform_monthly.columns:
        continue
    axes[0].fill_between(platform_monthly.index, bottom, bottom + platform_monthly[col],
                         label=PLATFORM_LABELS[col], color=colors[col], alpha=0.75)
    bottom = bottom + platform_monthly[col]
axes[0].set_title("플랫폼별 로판 신작 수 (누적)", fontsize=13, fontweight="bold")
axes[0].set_ylabel("신작 수")
axes[0].legend(loc="upper left")
for col, label in PLATFORM_LABELS.items():
    if col not in platform_monthly.columns:
        continue
    axes[1].plot(platform_monthly.index, platform_monthly[col], label=label, color=colors[col], linewidth=1.2)
axes[1].set_title("플랫폼별 로판 신작 수 (개별)", fontsize=13, fontweight="bold")
axes[1].set_ylabel("신작 수")
axes[1].set_xlabel("연월")
axes[1].legend(loc="upper left")
plt.tight_layout()
plt.savefig(CHART_DIR / "02_01_platform_monthly.png", dpi=150, bbox_inches="tight")
plt.close()

print("\n[완료] Step 2-1")

# ══════════════════════════════════════════════════════════════
# STEP 2-2: STL 분해
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("[Step 2-2] STL 분해 (period=12, robust=True)")
print("=" * 60)

stl        = STL(monthly, period=12, robust=True)
stl_result = stl.fit()
trend      = stl_result.trend
seasonal   = stl_result.seasonal
residual   = stl_result.resid

print(f"  추세 범위: {trend.min():.1f} ~ {trend.max():.1f}  |  계절성 진폭: {seasonal.max()-seasonal.min():.1f}  |  잔차 std: {residual.std():.2f}")

x_num = np.arange(len(trend))
slope, intercept, r_val, p_val, _ = stats.linregress(x_num, trend.values)
print(f"  추세 회귀: {slope:.4f}편/월 -> 연간 {slope*12:.1f}편/년  |  R2={r_val**2:.4f}  p={p_val:.6f}")
print(f"  -> 통계적으로 {'유의미한' if p_val < 0.05 else '유의미하지 않은'} {'상승' if slope > 0 else '하락'} 추세")

seasonal_df      = pd.DataFrame({"date": seasonal.index, "seasonal": seasonal.values})
seasonal_df["m"] = seasonal_df["date"].dt.month
monthly_seasonal = seasonal_df.groupby("m")["seasonal"].mean()
peak_month       = int(monthly_seasonal.idxmax())
trough_month     = int(monthly_seasonal.idxmin())
month_kor        = ["1월","2월","3월","4월","5월","6월","7월","8월","9월","10월","11월","12월"]

print("\n  [월별 평균 계절성]")
for m, val in monthly_seasonal.items():
    print(f"    {month_kor[m-1]:>4}: {val:+.1f}")
print(f"  최대 성수기: {month_kor[peak_month-1]}  |  최대 비수기: {month_kor[trough_month-1]}")

resid_s = pd.Series(residual.values, index=residual.index)
print("\n  [잔차 상위 5개월]")
for dt, val in resid_s.nlargest(5).items():
    print(f"    {dt.strftime('%Y-%m')}: {val:+.1f}편")
print("  [잔차 하위 5개월]")
for dt, val in resid_s.nsmallest(5).items():
    print(f"    {dt.strftime('%Y-%m')}: {val:+.1f}편")

stl_csv = pd.DataFrame({
    "month": monthly.index.strftime("%Y-%m"),
    "original": monthly.values, "trend": trend.values,
    "seasonal": seasonal.values, "residual": residual.values,
})
stl_csv.to_csv(PROCESSED_DIR / "02_02_stl_results.csv", index=False, encoding="utf-8-sig")

trend_fit = intercept + slope * x_num
fig, axes = plt.subplots(4, 1, figsize=(14, 11), sharex=True)
fig.suptitle("로판 월별 신작 수 - STL 분해", fontsize=14, fontweight="bold")
axes[0].plot(monthly.index, monthly.values, color="steelblue", linewidth=1)
axes[0].set_ylabel("신작 수"); axes[0].set_title("원본 시계열")
axes[1].plot(trend.index, trend.values, color="tomato", linewidth=1.5)
axes[1].plot(trend.index, trend_fit, color="darkred", linewidth=1, linestyle="--",
             label=f"회귀선 ({slope*12:.1f}편/년, p={p_val:.4f})")
axes[1].legend(fontsize=8); axes[1].set_ylabel("추세"); axes[1].set_title("추세(Trend) + 회귀선")
axes[2].plot(seasonal.index, seasonal.values, color="seagreen", linewidth=1)
axes[2].axhline(0, color="gray", linewidth=0.5, linestyle="--")
axes[2].set_ylabel("계절성")
axes[2].set_title(f"계절성(Seasonal)  성수기:{month_kor[peak_month-1]}  비수기:{month_kor[trough_month-1]}")
axes[3].plot(residual.index, residual.values, color="gray", linewidth=1)
axes[3].axhline(0, color="black", linewidth=0.5, linestyle="--")
for dt, val in resid_s.nlargest(5).items():
    axes[3].annotate(dt.strftime("%Y-%m"), xy=(dt, val), fontsize=7, color="red", ha="center", va="bottom")
axes[3].set_ylabel("잔차"); axes[3].set_title("잔차(Residual)  - 빨간 레이블: 상위 이상치")
plt.tight_layout()
plt.savefig(CHART_DIR / "02_02_stl_decomposition.png", dpi=150, bbox_inches="tight")
plt.close()

print("\n[완료] Step 2-2")

# ══════════════════════════════════════════════════════════════
# STEP 2-3: PELT 변동점 감지
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("[Step 2-3] PELT 변동점 감지 (model='rbf')")
print("=" * 60)

signal = (trend + seasonal).values.reshape(-1, 1)

print("\n  [beta elbow method]")
for pen in [5, 10, 20, 50]:
    algo_tmp  = rpt.Pelt(model="rbf", min_size=3, jump=1).fit(signal)
    bkps_tmp  = algo_tmp.predict(pen=pen)[:-1]
    dates_tmp = [monthly.index[i].strftime("%Y-%m") for i in bkps_tmp]
    print(f"    pen={pen:>3d} -> 변동점 {len(bkps_tmp)}개: {dates_tmp}")

FINAL_PEN = 10
algo = rpt.Pelt(model="rbf", min_size=3, jump=1).fit(signal)
breakpoints_idx  = algo.predict(pen=FINAL_PEN)[:-1]
breakpoint_dates = [monthly.index[i] for i in breakpoints_idx]

print(f"\n  감지된 변동점 ({len(breakpoint_dates)}개):")
segments = [0] + list(breakpoints_idx) + [len(monthly)]
mean_before_list, mean_after_list = [], []
for i, (idx, dt) in enumerate(zip(breakpoints_idx, breakpoint_dates), 1):
    seg_before = monthly.iloc[segments[i-1]:segments[i]]
    seg_after  = monthly.iloc[segments[i]:segments[i+1]]
    mean_before_list.append(round(seg_before.mean(), 1))
    mean_after_list.append(round(seg_after.mean(), 1))
    pct = (seg_after.mean() - seg_before.mean()) / seg_before.mean() * 100
    print(f"    CP{i}: {dt.strftime('%Y-%m')}  |  {seg_before.mean():.1f} -> {seg_after.mean():.1f}편 ({pct:+.0f}%)")

print(f"\n  [알려진 이벤트 vs 탐지 변동점]")
for eid, edate in KNOWN_EVENTS.items():
    diffs  = [abs((dt - edate).days) for dt in breakpoint_dates]
    ci     = int(np.argmin(diffs))
    diff_m = diffs[ci] / 30.44
    print(f"  {eid:<30} {edate.strftime('%Y-%m-%d')}  ->  CP{ci+1} ({breakpoint_dates[ci].strftime('%Y-%m')})  {diff_m:.1f}개월 차이")

cp_df = pd.DataFrame({
    "cp_id": [f"CP{i+1}" for i in range(len(breakpoint_dates))],
    "date":  [dt.strftime("%Y-%m") for dt in breakpoint_dates],
    "index": breakpoints_idx, "mean_before": mean_before_list,
    "mean_after": mean_after_list, "pen": FINAL_PEN,
})
cp_df.to_csv(PROCESSED_DIR / "02_03_changepoints.csv", index=False, encoding="utf-8-sig")

fig, axes = plt.subplots(2, 1, figsize=(14, 9))
fig.suptitle(f"로판 월별 신작 수 - PELT 변동점 (pen={FINAL_PEN})", fontsize=14, fontweight="bold")
for ax, title, xlim in [
    (axes[0], "전체 기간", None),
    (axes[1], "2017 이후 확대", (pd.Timestamp("2017-01-01"), monthly.index[-1])),
]:
    ax.plot(monthly.index, monthly.values, color="steelblue", linewidth=1, label="월별 신작 수")
    ax.plot(trend.index, trend.values, color="tomato", linewidth=2, linestyle="--", label="추세(Trend)")
    for i, dt in enumerate(breakpoint_dates):
        ax.axvline(dt, color="darkorange", linewidth=1.5, linestyle=":", label=f"CP{i+1} {dt.strftime('%Y-%m')}")
    for eid, edate in KNOWN_EVENTS.items():
        ax.axvline(edate, color="purple", linewidth=1.5, linestyle="--", label=eid)
    ax.set_title(title); ax.set_ylabel("신작 수")
    ax.legend(fontsize=7, loc="upper left", ncol=2)
    if xlim:
        ax.set_xlim(*xlim)
axes[1].set_xlabel("연월")
plt.tight_layout()
plt.savefig(CHART_DIR / "02_03_changepoints.png", dpi=150, bbox_inches="tight")
plt.close()

print("\n[완료] Step 2-3")
print("\n" + "=" * 60)
print("[완료] 02_stl_pelt.py - Phase 2 전체 완료")
print("=" * 60)
