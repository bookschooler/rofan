"""
Phase 2 - Step 2-1: 월별 신작 수 시계열 집계
입력: data/raw/all_works_integrated.csv
출력: data/processed/02_01_timeseries_monthly.csv
      data/processed/02_01_timeseries_monthly_by_platform.csv
      charts/02_01_platform_monthly.png
"""

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import koreanize_matplotlib
import pandas as pd
from pathlib import Path

BASE_DIR     = Path(__file__).resolve().parent.parent
DATA_DIR     = BASE_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
CHART_DIR    = BASE_DIR / "charts"
PROCESSED_DIR.mkdir(exist_ok=True)
CHART_DIR.mkdir(exist_ok=True)

PLATFORM_LABELS = {
    "kakaopage":     "카카오페이지",
    "naver_series":  "네이버 시리즈",
    "naver_webtoon": "네이버 웹툰",
}

# ── 1. 데이터 로드 ─────────────────────────────────────────────────────────────
print("=" * 60)
print("[1] 데이터 로드")
print("=" * 60)

df = pd.read_csv(DATA_DIR / "raw" / "all_works_integrated.csv", low_memory=False)
print(f"  전체 행 수: {len(df):,}")

# ── 2. 데이터 준비 (serialized 연재작만) ──────────────────────────────────────
print("\n[2] 데이터 준비 (serialized 연재작만 필터링)")

print(f"  content_form 분포:\n{df['content_form'].value_counts().to_string()}")
df = df[df["content_form"] == "serialized"].copy()
print(f"\n  분석 대상: {len(df):,}행")

# ── 3. start_date 전처리 ───────────────────────────────────────────────────────
print("\n[3] start_date 전처리")

df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
n_before = len(df)
df = df.dropna(subset=["start_date"])
print(f"  NaT 제거: {n_before - len(df)}행 제외 → 분석 대상 {len(df):,}행")
print(f"  start_date 범위: {df['start_date'].min().date()} ~ {df['start_date'].max().date()}")

df["month"] = df["start_date"].dt.to_period("M")

# ── 4. 전체 월별 집계 ──────────────────────────────────────────────────────────
print("\n[4] 전체 월별 신작 수 집계")

monthly = df.groupby("month").size().rename("new_works").sort_index()
monthly.index = monthly.index.to_timestamp()

print(f"  시계열 길이: {len(monthly)}개월")
print(f"  월 평균: {monthly.mean():.1f}편  |  최다: {monthly.max()}편 ({monthly.idxmax().strftime('%Y-%m')})")
print(f"  신작 0편 월: {'없음' if (monthly == 0).sum() == 0 else (monthly == 0).sum()}")

yearly = monthly.resample("YE").sum()
print("\n  [연도별 신작 수]")
for year, count in yearly.items():
    print(f"    {year.year}년: {int(count):>4}편")

ts_path = PROCESSED_DIR / "02_01_timeseries_monthly.csv"
monthly.reset_index().rename(columns={"index": "month"}).to_csv(
    ts_path, index=False, encoding="utf-8-sig"
)
print(f"\n  저장: {ts_path}")

# ── 5. 플랫폼별 월별 집계 ──────────────────────────────────────────────────────
print("\n[5] 플랫폼별 월별 신작 수 집계")

platform_monthly = (
    df.groupby(["platform", "month"])
    .size()
    .unstack(level="platform", fill_value=0)
)
platform_monthly.index = platform_monthly.index.to_timestamp()

for col, label in PLATFORM_LABELS.items():
    if col not in platform_monthly.columns:
        continue
    s = platform_monthly[col]
    print(f"\n  [{label}]")
    print(f"    시작월: {s[s > 0].index.min().strftime('%Y-%m')}  |  월 평균: {s.mean():.1f}편  |  최다: {s.max()}편 ({s.idxmax().strftime('%Y-%m')})")
    yearly_p = s.resample("YE").sum()
    for year, cnt in yearly_p.items():
        if cnt > 0:
            print(f"      {year.year}년: {int(cnt):>4}편")

ts_platform_path = PROCESSED_DIR / "02_01_timeseries_monthly_by_platform.csv"
platform_monthly.reset_index().rename(columns={"index": "month"}).to_csv(
    ts_platform_path, index=False, encoding="utf-8-sig"
)
print(f"\n  저장: {ts_platform_path}")

# ── 6. 플랫폼별 차트 ───────────────────────────────────────────────────────────
colors = {"kakaopage": "#FFCD00", "naver_series": "#03C75A", "naver_webtoon": "#1EC800"}

fig, axes = plt.subplots(2, 1, figsize=(14, 10))

bottom = pd.Series(0, index=platform_monthly.index)
for col in ["kakaopage", "naver_series", "naver_webtoon"]:
    if col not in platform_monthly.columns:
        continue
    axes[0].fill_between(
        platform_monthly.index, bottom, bottom + platform_monthly[col],
        label=PLATFORM_LABELS[col], color=colors[col], alpha=0.75
    )
    bottom = bottom + platform_monthly[col]
axes[0].set_title("플랫폼별 로판 신작 수 (누적)", fontsize=13, fontweight="bold")
axes[0].set_ylabel("신작 수")
axes[0].legend(loc="upper left")

for col, label in PLATFORM_LABELS.items():
    if col not in platform_monthly.columns:
        continue
    axes[1].plot(platform_monthly.index, platform_monthly[col],
                 label=label, color=colors[col], linewidth=1.2)
axes[1].set_title("플랫폼별 로판 신작 수 (개별)", fontsize=13, fontweight="bold")
axes[1].set_ylabel("신작 수")
axes[1].set_xlabel("연월")
axes[1].legend(loc="upper left")

plt.tight_layout()
chart_path = CHART_DIR / "02_01_platform_monthly.png"
plt.savefig(chart_path, dpi=150, bbox_inches="tight")
plt.close()
print(f"  저장: {chart_path}")

print("\n" + "=" * 60)
print("[완료] 02_01_timeseries.py")
print("=" * 60)
