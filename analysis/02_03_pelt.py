"""
Phase 2 - Step 2-3: PELT 변동점 감지
입력: data/processed/02_01_timeseries_monthly.csv
      data/processed/02_02_stl_results.csv
출력: data/processed/02_03_changepoints.csv
      charts/02_03_changepoints.png
"""

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import koreanize_matplotlib
import pandas as pd
import numpy as np
from pathlib import Path
import ruptures as rpt
from scipy.stats import ttest_ind

BASE_DIR      = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
CHART_DIR     = BASE_DIR / "charts"

KNOWN_EVENTS = {
    "E001 (재혼황후 웹툰)":      pd.Timestamp("2019-10-25"),
    "E003 (선재업고튀어 드라마)": pd.Timestamp("2024-04-08"),
}

# ── 1. 데이터 로드 ─────────────────────────────────────────────────────────────
print("=" * 60)
print("[1] 데이터 로드")
print("=" * 60)

monthly = pd.read_csv(
    PROCESSED_DIR / "02_01_timeseries_monthly.csv", encoding="utf-8-sig"
)
monthly["month"] = pd.to_datetime(monthly["month"])
monthly = monthly.set_index("month")["new_works"]

stl_df = pd.read_csv(
    PROCESSED_DIR / "02_02_stl_results.csv", encoding="utf-8-sig"
)
stl_df["month"] = pd.to_datetime(stl_df["month"])
stl_df = stl_df.set_index("month")

print(f"  시계열: {len(monthly)}개월")

# ── 2. PELT - beta elbow method ───────────────────────────────────────────────
print("\n[2] PELT 변동점 감지 (model='rbf')")

# 잔차 제거 후 trend+seasonal 신호만 사용 (순수 구조 변화 탐지)
signal = (stl_df["trend"] + stl_df["seasonal"]).values.reshape(-1, 1)

print("\n  [Elbow Method - penalty 1~99 자동 탐색]")
algo_fit = rpt.Pelt(model="rbf", min_size=3, jump=1).fit(signal)
pen_range = range(1, 100)
n_bkps_list = []
for pen in pen_range:
    bkps = algo_fit.predict(pen=pen)[:-1]
    n_bkps_list.append(len(bkps))

# 변동점 수가 3~6개인 구간에서 가장 큰 penalty (가장 보수적) 선택
target_range = [pen for pen, n in zip(pen_range, n_bkps_list) if 3 <= n <= 6]
FINAL_PEN = max(target_range) if target_range else 10
print(f"  변동점 3~6개 구간의 최대 penalty: {FINAL_PEN}")
print(f"  (penalty={FINAL_PEN} -> 변동점 {n_bkps_list[FINAL_PEN-1]}개)")

# Elbow plot 저장
fig_elbow, ax_elbow = plt.subplots(figsize=(10, 4))
ax_elbow.plot(list(pen_range), n_bkps_list, color="steelblue", linewidth=1.5, marker="o", markersize=3)
ax_elbow.axvline(FINAL_PEN, color="tomato", linewidth=1.5, linestyle="--",
                 label=f"선택: penalty={FINAL_PEN} ({n_bkps_list[FINAL_PEN-1]}개)")
ax_elbow.set_xlabel("penalty")
ax_elbow.set_ylabel("변동점 수")
ax_elbow.set_title("PELT Elbow Method - penalty vs 변동점 수")
ax_elbow.legend(fontsize=9)
ax_elbow.grid(True, alpha=0.3)
elbow_path = CHART_DIR / "02_03_pelt_elbow.png"
plt.tight_layout()
plt.savefig(elbow_path, dpi=150, bbox_inches="tight")
plt.close()
print(f"  elbow 차트 저장: {elbow_path}")
print(f"\n  최종 선택: pen={FINAL_PEN}")

algo = rpt.Pelt(model="rbf", min_size=3, jump=1).fit(signal)
breakpoints_idx  = algo.predict(pen=FINAL_PEN)[:-1]
breakpoint_dates = [monthly.index[i] for i in breakpoints_idx]

# ── 3. 변동점 전후 구간 평균 ───────────────────────────────────────────────────
print(f"\n  감지된 변동점 ({len(breakpoint_dates)}개):")
segments = [0] + list(breakpoints_idx) + [len(monthly)]
mean_before_list, mean_after_list = [], []

for i, (idx, dt) in enumerate(zip(breakpoints_idx, breakpoint_dates), 1):
    seg_before = monthly.iloc[segments[i-1]:segments[i]]
    seg_after  = monthly.iloc[segments[i]:segments[i+1]]
    mean_before_list.append(round(seg_before.mean(), 1))
    mean_after_list.append(round(seg_after.mean(), 1))
    change_pct = (seg_after.mean() - seg_before.mean()) / seg_before.mean() * 100
    # Welch's t-test: 전후 구간 평균 차이의 통계적 유의성 검증
    t_stat, p_val = ttest_ind(seg_before.values, seg_after.values, equal_var=False)
    sig_str = "★ 유의미" if p_val < 0.05 else "유의미하지 않음"
    print(f"    CP{i}: {dt.strftime('%Y-%m')}  |  {seg_before.mean():.1f} -> {seg_after.mean():.1f}편  ({change_pct:+.0f}%)  |  t={t_stat:.2f}, p={p_val:.4f} {sig_str}")

# ── 4. 알려진 이벤트 vs 변동점 거리 ───────────────────────────────────────────
print(f"\n  [알려진 이벤트 vs 탐지 변동점]")
print(f"  {'이벤트':<25} {'이벤트 날짜':<13} {'가장 가까운 CP':<13} {'차이(개월)'}")
print(f"  {'-'*62}")
for eid, edate in KNOWN_EVENTS.items():
    diffs     = [abs((dt - edate).days) for dt in breakpoint_dates]
    ci        = int(np.argmin(diffs))
    diff_m    = diffs[ci] / 30.44
    print(f"  {eid:<25} {edate.strftime('%Y-%m-%d'):<13} {breakpoint_dates[ci].strftime('%Y-%m'):<13} {diff_m:.1f}개월")

# ── 5. CSV 저장 ───────────────────────────────────────────────────────────────
cp_df = pd.DataFrame({
    "cp_id":       [f"CP{i+1}" for i in range(len(breakpoint_dates))],
    "date":        [dt.strftime("%Y-%m") for dt in breakpoint_dates],
    "index":       breakpoints_idx,
    "mean_before": mean_before_list,
    "mean_after":  mean_after_list,
    "pen":         FINAL_PEN,
})
csv_path = PROCESSED_DIR / "02_03_changepoints.csv"
cp_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
print(f"\n  저장: {csv_path}")
print(cp_df.to_string(index=False))

# ── 6. 차트 (전체 + 2017 이후 확대) ───────────────────────────────────────────
# 변동점 의미 레이블 (날짜 + 전후 평균 변화)
cp_labels = []
for i, (dt, mb, ma) in enumerate(zip(breakpoint_dates, mean_before_list, mean_after_list), 1):
    pct = (ma - mb) / mb * 100
    cp_labels.append(f"변동점 {i}: {dt.strftime('%Y-%m')}  ({mb:.0f}→{ma:.0f}편, {pct:+.0f}%)")

fig, axes = plt.subplots(2, 1, figsize=(14, 9), sharex=False)
fig.suptitle("로판 월별 신작 수 - PELT 변동점", fontsize=14, fontweight="bold")

for ax, title, xlim in [
    (axes[0], "전체 기간", None),
    (axes[1], "2017 이후 확대", (pd.Timestamp("2017-01-01"), monthly.index[-1])),
]:
    ax.plot(monthly.index, monthly.values, color="steelblue", linewidth=1, label="월별 신작 수")
    ax.plot(stl_df.index, stl_df["trend"].values, color="tomato", linewidth=2,
            linestyle="--", label="추세(Trend)")
    for i, (dt, lbl) in enumerate(zip(breakpoint_dates, cp_labels)):
        ax.axvline(dt, color="darkorange", linewidth=1.5, linestyle=":", label=lbl)
    for eid, edate in KNOWN_EVENTS.items():
        short = eid.split("(")[1].rstrip(")")
        ax.axvline(edate, color="purple", linewidth=1.5, linestyle="--",
                   label=f"{short} ({edate.strftime('%Y-%m')})")
    ax.set_title(title)
    ax.set_ylabel("신작 수")
    ax.legend(fontsize=7.5, loc="upper left", ncol=1)
    if xlim:
        ax.set_xlim(*xlim)

axes[1].set_xlabel("연월")
plt.tight_layout()
chart_path = CHART_DIR / "02_03_changepoints.png"
plt.savefig(chart_path, dpi=150, bbox_inches="tight")
plt.close()
print(f"  저장: {chart_path}")

print("\n" + "=" * 60)
print("[완료] 02_03_pelt.py")
print("=" * 60)
