"""
Phase 3 - Step 3-1: ITS (Interrupted Time Series) 분석
입력: data/processed/02_01_timeseries_monthly.csv
출력: data/processed/03_01_its_results.csv
      charts/03_01_its_E001.png
      charts/03_01_its_E003.png
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
    "E001": {"date": "2019-10", "label": "재혼황후 웹툰 연재 시작"},
    "E003": {"date": "2024-04", "label": "선재업고튀어 드라마 방영"},
}

# ── 1. 시계열 로드 ─────────────────────────────────────────────────────────────
print("=" * 60)
print("[1] 시계열 로드")
print("=" * 60)

monthly = pd.read_csv(
    PROCESSED_DIR / "02_01_timeseries_monthly.csv", encoding="utf-8-sig"
)
monthly["month"] = pd.to_datetime(monthly["month"])
monthly = monthly.set_index("month")["new_works"]

# 2026-04는 크롤링 마감으로 미수집분 있음 → 제외
monthly = monthly[monthly.index < "2026-04-01"]
print(f"  시계열: {len(monthly)}개월 ({monthly.index.min().strftime('%Y-%m')} ~ {monthly.index.max().strftime('%Y-%m')})")
print(f"  (2026-04 수집 편향으로 제외)")

# ── 2. ITS 회귀 함수 ───────────────────────────────────────────────────────────
def run_its(series, event_date_str, event_label, event_id):
    event_date = pd.Timestamp(event_date_str)

    # ITS 변수 생성
    df = pd.DataFrame({"new_works": series})
    df["time"]            = np.arange(1, len(df) + 1)                           # 전체 시간 인덱스
    df["intervention"]    = (df.index >= event_date).astype(int)                 # 이벤트 이후 1
    df["time_since"]      = np.where(                                            # 이벤트 이후 경과 개월
        df.index >= event_date,
        np.arange(1, len(df) + 1) - (df.index < event_date).sum(),
        0
    )

    pre_n  = (df.index < event_date).sum()
    post_n = (df.index >= event_date).sum()

    print(f"\n  [{event_id}] {event_label} ({event_date_str})")
    print(f"    이벤트 전: {pre_n}개월  |  이벤트 후: {post_n}개월")

    # OLS 회귀
    model  = smf.ols("new_works ~ time + intervention + time_since", data=df).fit()

    b0 = model.params["Intercept"]
    b1 = model.params["time"]
    b2 = model.params["intervention"]
    b3 = model.params["time_since"]
    p2 = model.pvalues["intervention"]
    p3 = model.pvalues["time_since"]
    r2 = model.rsquared

    print(f"    β1 (기본 기울기):   {b1:+.3f} 편/월")
    print(f"    β2 (레벨 변화):     {b2:+.3f}편  (p={p2:.4f})  {'★ 유의미' if p2 < 0.05 else '유의미하지 않음'}")
    print(f"    β3 (기울기 변화):   {b3:+.3f} 편/월  (p={p3:.4f})  {'★ 유의미' if p3 < 0.05 else '유의미하지 않음'}")
    print(f"    R²: {r2:.4f}")

    # 예측선 (반사실 포함)
    df["fitted"]       = model.fittedvalues

    # 반사실(counterfactual): intervention=0, time_since=0으로 가정한 예측
    cf = df.copy()
    cf["intervention"] = 0
    cf["time_since"]   = 0
    df["counterfactual"] = model.predict(cf)

    # 차트
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(df.index, df["new_works"],      color="steelblue",  linewidth=1,   label="실제 신작 수")
    ax.plot(df.index, df["fitted"],         color="tomato",     linewidth=1.5, label="ITS 회귀선")
    ax.plot(df.index, df["counterfactual"], color="gray",       linewidth=1.2,
            linestyle="--", label="반사실선 (이벤트 없었을 경우 예측)")
    ax.axvline(event_date, color="purple", linewidth=2, linestyle="--",
               label=f"{event_label} ({event_date_str})")

    ax.set_title(f"ITS 분석: {event_label} ({event_date_str})",
                 fontsize=11, fontweight="bold")

    stats_text = (
        f"레벨 변화  β2 = {b2:+.1f}편   p = {p2:.3f} {'★' if p2 < 0.05 else ''}\n"
        f"기울기 변화  β3 = {b3:+.3f}편/월   p = {p3:.3f} {'★' if p3 < 0.05 else ''}\n"
        f"R² = {r2:.4f}"
    )
    ax.text(0.98, 0.05, stats_text, transform=ax.transAxes,
            fontsize=9, verticalalignment="bottom", horizontalalignment="right",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="lightyellow", alpha=0.85))

    ax.set_xlabel("연월")
    ax.set_ylabel("신작 수")
    ax.legend(fontsize=8, loc="upper left")
    plt.tight_layout()

    chart_path = CHART_DIR / f"03_01_its_{event_id}.png"
    plt.savefig(chart_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"    차트 저장: {chart_path}")

    return {
        "event_id":    event_id,
        "event_label": event_label,
        "event_date":  event_date_str,
        "pre_n":       pre_n,
        "post_n":      post_n,
        "beta1":       round(b1, 4),
        "beta2":       round(b2, 3),
        "beta3":       round(b3, 4),
        "p_beta2":     round(p2, 4),
        "p_beta3":     round(p3, 4),
        "sig_beta2":   p2 < 0.05,
        "sig_beta3":   p3 < 0.05,
        "r2":          round(r2, 4),
    }

# ── 3. 이벤트별 ITS 실행 ──────────────────────────────────────────────────────
print("\n[2] 이벤트별 ITS 회귀 실행")

results = []
for eid, meta in EVENTS.items():
    row = run_its(monthly, meta["date"], meta["label"], eid)
    results.append(row)

# ── 4. 결과 요약 및 CSV 저장 ──────────────────────────────────────────────────
print("\n" + "=" * 60)
print("[3] 결과 요약")
print("=" * 60)

results_df = pd.DataFrame(results)
print(results_df[["event_id","event_date","beta2","p_beta2","sig_beta2",
                   "beta3","p_beta3","sig_beta3","r2"]].to_string(index=False))

# Holm-Bonferroni 다중 검정 보정 (β2, β3 각각 - 2개 모델 × 2 계수 = 4개 검정)
all_pvals = results_df["p_beta2"].tolist() + results_df["p_beta3"].tolist()
_, pvals_corrected, _, _ = multipletests(all_pvals, method="holm")
n = len(results_df)
results_df["p_beta2_holm"] = [round(p, 4) for p in pvals_corrected[:n]]
results_df["p_beta3_holm"] = [round(p, 4) for p in pvals_corrected[n:]]
results_df["sig_beta2_holm"] = results_df["p_beta2_holm"] < 0.05
results_df["sig_beta3_holm"] = results_df["p_beta3_holm"] < 0.05

print("\n  [Holm-Bonferroni 보정 후 결과]")
print(f"  {'이벤트':<10} {'β2 p(원본)':<12} {'β2 p(보정)':<12} {'β3 p(원본)':<12} {'β3 p(보정)'}")
print(f"  {'-'*58}")
for _, r in results_df.iterrows():
    print(f"  {r['event_id']:<10} {r['p_beta2']:<12.4f} {r['p_beta2_holm']:<12.4f} {r['p_beta3']:<12.4f} {r['p_beta3_holm']:.4f}")

csv_path = PROCESSED_DIR / "03_01_its_results.csv"
results_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
print(f"\n  저장: {csv_path}")

print("\n" + "=" * 60)
print("[완료] 03_01_its.py")
print("=" * 60)
