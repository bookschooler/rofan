"""
Phase 5 - Step 5-1: 쇠퇴기 시나리오 분석
입력: data/processed/03_01_its_results.csv
      data/processed/04_01_prophet_forecast.csv
      data/processed/02_01_timeseries_monthly.csv
출력: data/processed/05_01_decline_projection.csv
      charts/05_01_decline_scenarios.png
      charts/05_01_decline_milestones.png
"""

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import koreanize_matplotlib
import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats

BASE_DIR      = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
CHART_DIR     = BASE_DIR / "charts"

# ── 1. 데이터 로드 ─────────────────────────────────────────────────────────────
print("=" * 60)
print("[1] 데이터 로드")
print("=" * 60)

its = pd.read_csv(PROCESSED_DIR / "03_01_its_results.csv", encoding="utf-8-sig")
e003 = its[its["event_id"] == "E003"].iloc[0]
beta1 = e003["beta1"]
beta3 = e003["beta3"]
post_slope = beta1 + beta3

monthly = pd.read_csv(PROCESSED_DIR / "02_01_timeseries_monthly.csv", encoding="utf-8-sig")
monthly["dt"] = pd.to_datetime(monthly["month"])

prophet_fc = pd.read_csv(PROCESSED_DIR / "04_01_prophet_forecast.csv", encoding="utf-8-sig")
prophet_fc["dt"] = pd.to_datetime(prophet_fc["month"])

print(f"  E003 ITS: beta1={beta1:.4f}/월, beta3={beta3:.4f}/월")
print(f"  -> 2024-04 이후 실효 기울기: {post_slope:.4f}편/월 ({post_slope*12:.2f}편/년)")

# ── 2. 기준점 설정 ─────────────────────────────────────────────────────────────
print("\n[2] 기준점 설정")

BASE_DATE  = pd.Timestamp("2026-01-01")
actuals_base = monthly[monthly["dt"] >= "2024-04-01"]
base_level = actuals_base.iloc[0]["new_works"]

# 2024-2025 실측 선형 회귀 (현실 시나리오 기울기)
recent = monthly[(monthly["dt"] >= "2024-04-01") & (monthly["dt"] <= "2025-12-01")].copy()
x_recent = np.arange(len(recent))
realistic_slope, realistic_intercept, *_ = stats.linregress(x_recent, recent["new_works"].values)
print(f"  2024-04~2025-12 실측 기울기: {realistic_slope:.4f}편/월 ({realistic_slope*12:.1f}편/년)")

# 기준점: 2025-12 실제 마지막 값
last_actual = monthly[monthly["dt"] <= "2025-12-01"].iloc[-1]
base_level_2025 = last_actual["new_works"]
base_date_2025  = last_actual["dt"]
print(f"  2025-12 실측 마지막 값: {base_level_2025:.0f}편 ({base_date_2025.strftime('%Y-%m')})")

# ── 3. 3가지 시나리오 미래 투영 ───────────────────────────────────────────────
print("\n[3] 2026~2032 시나리오 투영")

future_months = pd.date_range("2026-01-01", "2032-12-01", freq="MS")
n_future = len(future_months)

# 낙관 시나리오: Prophet 예측 사용
prophet_future = prophet_fc[prophet_fc["dt"] >= "2026-01-01"].copy()
# Prophet이 2026-04~12만 있으므로 2026 Q1은 마지막 실측에서 추세 외삽
prophet_q1_avg = monthly[(monthly["dt"] >= "2025-10-01") & (monthly["dt"] <= "2025-12-01")]["new_works"].mean()

optimistic_vals = []
for m in future_months:
    row = prophet_future[prophet_future["dt"] == m]
    if not row.empty:
        optimistic_vals.append(float(row["yhat"].iloc[0]))
    else:
        optimistic_vals.append(prophet_q1_avg)

# 현실 시나리오: 2024-04 이후 실측 기울기 연장
realistic_vals = [
    base_level_2025 + realistic_slope * (i + 1)
    for i in range(n_future)
]

# 비관 시나리오: ITS post-slope (-1.45편/월) 연장
pessimistic_vals = [
    base_level_2025 + post_slope * (i + 1)
    for i in range(n_future)
]

proj_df = pd.DataFrame({
    "month":      future_months.strftime("%Y-%m"),
    "optimistic": [max(v, 0) for v in optimistic_vals],
    "realistic":  [max(v, 0) for v in realistic_vals],
    "pessimistic":[max(v, 0) for v in pessimistic_vals],
})
print(proj_df[proj_df["month"].isin(["2026-06","2027-01","2028-01","2029-01","2030-01","2031-01","2032-01"])].to_string(index=False))

# ── 4. 마일스톤 계산 (비관 시나리오 기준) ─────────────────────────────────────
print("\n[4] 마일스톤 계산 (비관 시나리오 기준)")

MILESTONES = {
    "PELT CP3 수준 (2022-07: 146편)": 146,
    "월 100편 미만":                   100,
    "PELT CP2 수준 (2020-08: 78편)":   78,
    "PELT CP1 수준 (2017-09: 21편)":   21,
}

milestone_rows = []
print(f"\n  {'마일스톤':<35} {'비관(ITS)':<15} {'현실':<15} {'낙관(Prophet)'}")
print(f"  {'-'*72}")
for label, threshold in MILESTONES.items():
    # 비관
    pess_idx = next((i for i,v in enumerate(pessimistic_vals) if v <= threshold), None)
    pess_str = future_months[pess_idx].strftime("%Y-%m") if pess_idx is not None else "2032년 이후"

    # 현실
    real_idx = next((i for i,v in enumerate(realistic_vals) if v <= threshold), None)
    real_str = future_months[real_idx].strftime("%Y-%m") if real_idx is not None else "2032년 이후"

    # 낙관
    opt_idx = next((i for i,v in enumerate(optimistic_vals) if v <= threshold), None)
    opt_str = future_months[opt_idx].strftime("%Y-%m") if opt_idx is not None else "2032년 이후"

    print(f"  {label:<35} {pess_str:<15} {real_str:<15} {opt_str}")
    milestone_rows.append({
        "milestone": label,
        "threshold": threshold,
        "pessimistic": pess_str,
        "realistic":   real_str,
        "optimistic":  opt_str,
    })

milestone_df = pd.DataFrame(milestone_rows)

# ── 5. CSV 저장 ───────────────────────────────────────────────────────────────
csv_path = PROCESSED_DIR / "05_01_decline_projection.csv"
proj_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
print(f"\n  저장: {csv_path}")

milestone_csv = PROCESSED_DIR / "05_01_decline_milestones.csv"
milestone_df.to_csv(milestone_csv, index=False, encoding="utf-8-sig")
print(f"  저장: {milestone_csv}")

# ── 6. 차트 1: 시나리오별 신작 수 투영 ───────────────────────────────────────
print("\n[5] 차트 생성")

fig, ax = plt.subplots(figsize=(15, 7))

# 실제 데이터
actual_plot = monthly[monthly["dt"] >= "2017-01-01"]
ax.plot(actual_plot["dt"], actual_plot["new_works"],
        color="steelblue", linewidth=1.5, label="실제 신작 수", zorder=3)

# 시나리오
dt_future = pd.to_datetime(proj_df["month"])
ax.plot(dt_future, proj_df["optimistic"],
        color="#16a34a", linewidth=2, linestyle="-", label="낙관 (Prophet: 고원 유지)", zorder=4)
ax.plot(dt_future, proj_df["realistic"],
        color="#d97706", linewidth=2, linestyle="--", label=f"현실 ({realistic_slope*12:.1f}편/년, 2024~2025 실측)", zorder=4)
ax.plot(dt_future, proj_df["pessimistic"],
        color="#dc2626", linewidth=2, linestyle=":", label=f"비관 (ITS -1.45편/월 지속)", zorder=4)

# 예측 시작선
ax.axvline(pd.Timestamp("2026-01-01"), color="black", linewidth=1.5,
           linestyle="--", alpha=0.6, label="예측 시작 (2026-01)")

# 임계값 수평선
threshold_colors = {"146": ("#f59e0b", "PELT CP3 수준 (146편)"),
                    "78":  ("#8b5cf6", "PELT CP2 수준 (78편)")}
ax.axhline(146, color="#f59e0b", linewidth=1, linestyle="--", alpha=0.7,
           label="CP3 기준 (146편, 2022-07 이전)")
ax.axhline(78,  color="#8b5cf6", linewidth=1, linestyle="--", alpha=0.7,
           label="CP2 기준 (78편, 2020-08 이전)")

# PELT CP 표시
pelt_cps = [("2017-09", "CP1"), ("2020-08", "CP2"), ("2022-07", "CP3")]
for cp_date, cp_label in pelt_cps:
    ax.axvline(pd.Timestamp(cp_date), color="darkorange", linewidth=1.2,
               linestyle=":", alpha=0.6)
    ax.text(pd.Timestamp(cp_date), ax.get_ylim()[1] if ax.get_ylim()[1] > 0 else 250,
            f" {cp_label}", fontsize=8, color="darkorange", va="top")

ax.set_title("로판 월별 신작 수 — 쇠퇴기 시나리오 분석 (2026~2032)", fontsize=13, fontweight="bold")
ax.set_xlabel("연월")
ax.set_ylabel("신작 수 (편)")
ax.legend(fontsize=8, loc="upper right", ncol=1)
ax.grid(True, alpha=0.3)
ax.set_ylim(bottom=0)

plt.tight_layout()
chart1 = CHART_DIR / "05_01_decline_scenarios.png"
plt.savefig(chart1, dpi=150, bbox_inches="tight")
plt.close()
print(f"  저장: {chart1}")

# ── 7. 차트 2: 마일스톤 도달 시점 Gantt-style ────────────────────────────────
fig2, ax2 = plt.subplots(figsize=(13, 5))

scenarios = ["optimistic", "realistic", "pessimistic"]
scenario_labels = {"optimistic": "낙관 (Prophet)", "realistic": "현실 (실측)", "pessimistic": "비관 (ITS)"}
scenario_colors = {"optimistic": "#16a34a", "realistic": "#d97706", "pessimistic": "#dc2626"}
y_positions = {"optimistic": 2, "realistic": 1, "pessimistic": 0}

for s in scenarios:
    for row in milestone_rows:
        val = row[s]
        if "이후" not in val:
            x = pd.Timestamp(val + "-01")
            y = y_positions[s]
            ax2.scatter(x, y, s=80, color=scenario_colors[s], zorder=5)
            ax2.annotate(f"{row['threshold']}편\n({val})",
                         xy=(x, y), xytext=(0, 10),
                         textcoords="offset points", fontsize=7,
                         ha="center", color=scenario_colors[s])

ax2.axvline(pd.Timestamp("2026-01-01"), color="black", linewidth=1.5,
            linestyle="--", alpha=0.5, label="현재 (2026-01)")

ax2.set_yticks([0, 1, 2])
ax2.set_yticklabels(["비관 (ITS)", "현실 (실측)", "낙관 (Prophet)"])
ax2.set_xlabel("연도")
ax2.set_title("쇠퇴기 마일스톤 도달 시점 — 시나리오별 비교", fontsize=12, fontweight="bold")
ax2.grid(True, axis="x", alpha=0.3)
ax2.set_xlim(pd.Timestamp("2025-06-01"), pd.Timestamp("2033-01-01"))

plt.tight_layout()
chart2 = CHART_DIR / "05_01_decline_milestones.png"
plt.savefig(chart2, dpi=150, bbox_inches="tight")
plt.close()
print(f"  저장: {chart2}")

print("\n" + "=" * 60)
print("[완료] 05_01_decline_projection.py")
print("=" * 60)
