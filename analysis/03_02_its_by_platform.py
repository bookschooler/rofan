"""
Phase 3 - Step 3-2: 플랫폼별 ITS 분석
입력: data/processed/02_01_timeseries_monthly_by_platform.csv
출력: data/processed/03_02_its_by_platform.csv
      charts/03_02_its_{platform}_{event}.png (6개)
"""

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import koreanize_matplotlib
import pandas as pd
import numpy as np
from pathlib import Path
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests

BASE_DIR      = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
CHART_DIR     = BASE_DIR / "charts"

EVENTS = {
    "E001": {"date": "2019-10", "label": "재혼황후 웹툰 연재"},
    "E003": {"date": "2024-04", "label": "선재업고튀어 드라마"},
}
PLATFORM_LABELS = {
    "kakaopage":     "카카오페이지",
    "naver_series":  "네이버 시리즈",
    "naver_webtoon": "네이버 웹툰",
}

# ── 1. 플랫폼별 시계열 로드 ────────────────────────────────────────────────────
print("=" * 60)
print("[1] 플랫폼별 시계열 로드")
print("=" * 60)

df_raw = pd.read_csv(
    PROCESSED_DIR / "02_01_timeseries_monthly_by_platform.csv", encoding="utf-8-sig"
)
df_raw["month"] = pd.to_datetime(df_raw["month"])
df_raw = df_raw.set_index("month")

# 2026-04 수집 편향 제외
df_raw = df_raw[df_raw.index < "2026-04-01"]
print(f"  시계열: {len(df_raw)}개월 ({df_raw.index.min().strftime('%Y-%m')} ~ {df_raw.index.max().strftime('%Y-%m')})")
print(f"  플랫폼: {list(df_raw.columns)}")

# ── 2. ITS 함수 ────────────────────────────────────────────────────────────────
def run_its(series, event_date_str, event_label, event_id, platform, platform_label):
    event_date = pd.Timestamp(event_date_str)

    # 이벤트 이후 데이터가 6개월 미만이면 분석 불가
    post_n = (series.index >= event_date).sum()
    pre_n  = (series.index < event_date).sum()
    if post_n < 6:
        print(f"    [{platform_label} x {event_id}] 스킵 - 이벤트 후 {post_n}개월 (최소 6개월 필요)")
        return None

    df = pd.DataFrame({"new_works": series})
    df["time"]         = np.arange(1, len(df) + 1)
    df["intervention"] = (df.index >= event_date).astype(int)
    df["time_since"]   = np.where(
        df.index >= event_date,
        np.arange(1, len(df) + 1) - pre_n,
        0
    )

    model = smf.ols("new_works ~ time + intervention + time_since", data=df).fit()

    b2 = model.params["intervention"]
    b3 = model.params["time_since"]
    p2 = model.pvalues["intervention"]
    p3 = model.pvalues["time_since"]
    r2 = model.rsquared

    df["fitted"]         = model.fittedvalues
    cf                   = df.copy()
    cf["intervention"]   = 0
    cf["time_since"]     = 0
    df["counterfactual"] = model.predict(cf)

    # 차트
    fig, ax = plt.subplots(figsize=(13, 4))
    ax.plot(df.index, df["new_works"],      color="steelblue", linewidth=1,   label="실제 신작 수")
    ax.plot(df.index, df["fitted"],         color="tomato",    linewidth=1.5, label="ITS 회귀선")
    ax.plot(df.index, df["counterfactual"], color="gray",      linewidth=1.2,
            linestyle="--", label="반사실선")
    ax.axvline(event_date, color="purple", linewidth=2, linestyle="--",
               label=f"{event_label}")

    ax.set_title(f"[{platform_label}] ITS: {event_label} ({event_date_str})",
                 fontsize=10, fontweight="bold")

    stats_text = (
        f"레벨 변화  β2 = {b2:+.1f}편   p = {p2:.3f} {'★' if p2 < 0.05 else ''}\n"
        f"기울기 변화  β3 = {b3:+.3f}편/월   p = {p3:.3f} {'★' if p3 < 0.05 else ''}\n"
        f"R² = {r2:.4f}"
    )
    ax.text(0.98, 0.05, stats_text, transform=ax.transAxes,
            fontsize=8.5, verticalalignment="bottom", horizontalalignment="right",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="lightyellow", alpha=0.85))
    ax.set_xlabel("연월")
    ax.set_ylabel("신작 수")
    ax.legend(fontsize=7, loc="upper left")
    plt.tight_layout()

    chart_path = CHART_DIR / f"03_02_its_{platform}_{event_id}.png"
    plt.savefig(chart_path, dpi=150, bbox_inches="tight")
    plt.close()

    return {
        "platform":    platform,
        "platform_label": platform_label,
        "event_id":    event_id,
        "event_label": event_label,
        "event_date":  event_date_str,
        "pre_n":       pre_n,
        "post_n":      post_n,
        "beta2":       round(b2, 3),
        "beta3":       round(b3, 4),
        "p_beta2":     round(p2, 4),
        "p_beta3":     round(p3, 4),
        "sig_beta2":   p2 < 0.05,
        "sig_beta3":   p3 < 0.05,
        "r2":          round(r2, 4),
    }

# ── 3. 플랫폼 × 이벤트 ITS 실행 ──────────────────────────────────────────────
print("\n[2] 플랫폼 x 이벤트 ITS 실행 (3 x 2 = 6개)")

results = []
for platform, platform_label in PLATFORM_LABELS.items():
    if platform not in df_raw.columns:
        continue
    series = df_raw[platform]
    print(f"\n  [{platform_label}]")
    for eid, meta in EVENTS.items():
        row = run_its(series, meta["date"], meta["label"], eid, platform, platform_label)
        if row:
            results.append(row)
            print(f"    {eid} | β2={row['beta2']:+.1f}편 (p={row['p_beta2']:.4f}) {'★' if row['sig_beta2'] else ''}"
                  f"  β3={row['beta3']:+.4f}편/월 (p={row['p_beta3']:.4f}) {'★' if row['sig_beta3'] else ''}"
                  f"  R²={row['r2']:.3f}")

# ── 4. 비교표 출력 및 CSV 저장 ────────────────────────────────────────────────
print("\n" + "=" * 60)
print("[3] 플랫폼별 결과 비교표")
print("=" * 60)

results_df = pd.DataFrame(results)

for eid in EVENTS:
    subset = results_df[results_df["event_id"] == eid]
    print(f"\n  [{eid}: {EVENTS[eid]['label']}]")
    print(f"  {'플랫폼':<12} {'β2(레벨)':<12} {'p(β2)':<8} {'유의':<5} {'β3(기울기)':<12} {'p(β3)':<8} {'유의':<5} {'R²'}")
    print(f"  {'-'*72}")
    for _, r in subset.iterrows():
        print(f"  {r['platform_label']:<12} {r['beta2']:>+8.1f}편   {r['p_beta2']:<8.4f} {'★' if r['sig_beta2'] else '-':<5}"
              f" {r['beta3']:>+8.4f}편/월 {r['p_beta3']:<8.4f} {'★' if r['sig_beta3'] else '-':<5} {r['r2']:.3f}")

# Holm-Bonferroni 다중 검정 보정 (6개 모델 × 2 계수 = 12개 검정)
all_pvals = results_df["p_beta2"].tolist() + results_df["p_beta3"].tolist()
_, pvals_corrected, _, _ = multipletests(all_pvals, method="holm")
n = len(results_df)
results_df["p_beta2_holm"] = [round(p, 4) for p in pvals_corrected[:n]]
results_df["p_beta3_holm"] = [round(p, 4) for p in pvals_corrected[n:]]
results_df["sig_beta2_holm"] = results_df["p_beta2_holm"] < 0.05
results_df["sig_beta3_holm"] = results_df["p_beta3_holm"] < 0.05

print("\n  [Holm-Bonferroni 보정 후 - 유의미 변화 있는 모델만]")
changed = results_df[results_df["sig_beta2"] != results_df["sig_beta2_holm"] |
                     (results_df["sig_beta3"] != results_df["sig_beta3_holm"])]
if len(changed) == 0:
    print("  보정 전후 유의미 판정 변화 없음 - 결과 안정적")
else:
    for _, r in changed.iterrows():
        print(f"  {r['platform_label']} x {r['event_id']}: β2 {r['p_beta2']:.4f}->{r['p_beta2_holm']:.4f}  β3 {r['p_beta3']:.4f}->{r['p_beta3_holm']:.4f}")

csv_path = PROCESSED_DIR / "03_02_its_by_platform.csv"
results_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
print(f"\n  저장: {csv_path}")

print("\n" + "=" * 60)
print("[완료] 03_02_its_by_platform.py")
print("=" * 60)
