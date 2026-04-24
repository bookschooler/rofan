"""
데이터 품질 검증 스크립트 (크롤링 완료 직후 실행)
- 각 플랫폼별 CSV 파일 존재 여부 및 품질 항목 체크
- 통합 파일(all_works_integrated.csv)이 있으면 추가 검증
- 최종 PASS / FAIL 판정 출력
"""

import pandas as pd
from pathlib import Path

# ── 경로 설정 ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent  # Rofan/
DATA_DIR = BASE_DIR / "data"

# 검증 대상 파일 목록 (플랫폼명: 파일명)
TARGET_FILES = {
    "kakaopage":    "kakaopage_works.csv",
    "naver_series": "naver_series_works.csv",
    "naver_webtoon": "naver_webtoon_works.csv",
}

# 각 파일에 반드시 있어야 하는 컬럼
REQUIRED_COLS = [
    "work_id",
    "title",
    "author",
    "platform",
    "start_date",
    "genre_raw",
    "complete_status",
]

# 플랫폼별 기대 값
EXPECTED_PLATFORM_VALUES = {
    "kakaopage":    "kakaopage",
    "naver_series": "naver_series",
    "naver_webtoon": "naver_webtoon",
}

# FAIL 사유 누적 리스트
fail_reasons = []

print("=" * 60)
print("=== 데이터 품질 검증 보고서 ===")
print("=" * 60)

# ── 파일별 검증 ────────────────────────────────────────────────────────────────
all_dfs = {}  # 통합 중복 체크용

for platform, filename in TARGET_FILES.items():
    filepath = DATA_DIR / filename
    print(f"\n[{filename}]")

    # 1. 파일 존재 여부
    if not filepath.exists():
        msg = f"{filename} 파일 없음"
        print(f"  파일 존재: FAIL ✗  ({msg})")
        fail_reasons.append(msg)
        continue  # 파일 없으면 이하 항목 건너뜀

    print(f"  파일 존재: PASS ✓")

    # 2. 파일 로드
    try:
        df = pd.read_csv(filepath, low_memory=False)
    except Exception as e:
        msg = f"{filename} 로드 실패: {e}"
        print(f"  로드: FAIL ✗  ({msg})")
        fail_reasons.append(msg)
        continue

    all_dfs[platform] = df

    # 3. 행 수 / 컬럼 수
    print(f"  행 수: {len(df):,}  |  컬럼 수: {df.shape[1]}")
    if len(df) == 0:
        msg = f"{filename} 데이터가 비어 있음 (0행)"
        print(f"  → FAIL ✗ ({msg})")
        fail_reasons.append(msg)

    # 4. 필수 컬럼 존재 여부
    missing_cols = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing_cols:
        msg = f"{filename} 필수 컬럼 누락: {missing_cols}"
        print(f"  필수 컬럼: FAIL ✗  누락={missing_cols}")
        fail_reasons.append(msg)
    else:
        print(f"  필수 컬럼: PASS ✓  ({len(REQUIRED_COLS)}개 모두 존재)")

    # 5. 결측치 비율 (컬럼별, 1% 이상인 경우만 출력)
    null_ratio = (df.isnull().sum() / len(df) * 100).round(1)
    notable_nulls = null_ratio[null_ratio > 0].sort_values(ascending=False)
    if notable_nulls.empty:
        print("  결측치: 없음")
    else:
        null_str = "  |  ".join([f"{col} {pct}%" for col, pct in notable_nulls.items()])
        print(f"  결측치: {null_str}")

    # 6. 중복 행 수 (title + author + platform 기준)
    dup_cols = [c for c in ["title", "author", "platform"] if c in df.columns]
    if len(dup_cols) == 3:
        n_dup = df.duplicated(subset=dup_cols).sum()
        dup_label = "PASS ✓" if n_dup == 0 else "주의 ⚠"
        print(f"  중복 행 (title+author+platform): {n_dup}건  {dup_label}")
        if n_dup > 0:
            fail_reasons.append(f"{filename} 중복 {n_dup}건 (title+author+platform)")
    else:
        print(f"  중복 체크: 건너뜀 (dup_cols={dup_cols} 불완전)")

    # 7. start_date 범위 및 파싱 성공률
    if "start_date" in df.columns:
        parsed = pd.to_datetime(df["start_date"], errors="coerce")
        n_total = len(parsed)
        n_valid = parsed.notna().sum()
        parse_rate = n_valid / n_total * 100 if n_total > 0 else 0
        rate_label = "PASS ✓" if parse_rate >= 90 else "FAIL ✗"
        print(f"  start_date 파싱 성공률: {parse_rate:.1f}%  {rate_label}")
        if n_valid > 0:
            print(f"  start_date 범위: {parsed.min().date()} ~ {parsed.max().date()}")
        if parse_rate < 90:
            fail_reasons.append(f"{filename} start_date 파싱 성공률 {parse_rate:.1f}% (기준: 90%)")
    else:
        print("  start_date: 컬럼 없음 (필수 컬럼 체크에서 이미 반영)")

    # 8. platform 값 일관성 체크
    if "platform" in df.columns:
        actual_values = df["platform"].dropna().unique().tolist()
        expected_val = EXPECTED_PLATFORM_VALUES[platform]
        if expected_val in actual_values:
            print(f"  platform 값: PASS ✓  '{expected_val}' 확인")
        else:
            msg = f"{filename} platform 값 불일치: 기대={expected_val}, 실제={actual_values}"
            print(f"  platform 값: FAIL ✗  기대='{expected_val}', 실제={actual_values}")
            fail_reasons.append(msg)

# ── 통합 파일 검증 ─────────────────────────────────────────────────────────────
integrated_path = DATA_DIR / "all_works_integrated.csv"
print(f"\n[all_works_integrated.csv]")

if not integrated_path.exists():
    print("  파일 없음 — 아직 통합 미완료 (건너뜀)")
else:
    try:
        df_all = pd.read_csv(integrated_path, low_memory=False)
        print(f"  행 수: {len(df_all):,}  |  컬럼 수: {df_all.shape[1]}")

        # 플랫폼별 행 수 분포
        if "platform" in df_all.columns:
            platform_counts = df_all["platform"].value_counts()
            print("  플랫폼별 행 수:")
            for plat, cnt in platform_counts.items():
                print(f"    {plat}: {cnt:,}건")

        # 개별 파일 합계 vs 통합 파일 행 수 비교
        expected_total = sum(len(v) for v in all_dfs.values())
        if expected_total > 0:
            diff = len(df_all) - expected_total
            diff_label = "PASS ✓" if abs(diff) == 0 else f"차이 {diff:+d}건"
            print(f"  개별 합계 {expected_total:,} vs 통합 {len(df_all):,}: {diff_label}")
            if abs(diff) > 0:
                fail_reasons.append(f"통합 파일 행 수 불일치: 개별합={expected_total}, 통합={len(df_all)}")

        # 통합 후 중복 체크
        dup_cols = [c for c in ["title", "author", "platform"] if c in df_all.columns]
        if len(dup_cols) == 3:
            n_dup = df_all.duplicated(subset=dup_cols).sum()
            dup_label = "PASS ✓" if n_dup == 0 else "주의 ⚠"
            print(f"  통합 중복 (title+author+platform): {n_dup}건  {dup_label}")
            if n_dup > 0:
                fail_reasons.append(f"통합 파일 중복 {n_dup}건")

    except Exception as e:
        msg = f"all_works_integrated.csv 로드 실패: {e}"
        print(f"  로드: FAIL ✗  ({msg})")
        fail_reasons.append(msg)

# ── 최종 판정 ─────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
if not fail_reasons:
    print("[최종 판정] PASS ✓")
    print("  모든 검증 항목 통과. 분석 진행 가능.")
else:
    print("[최종 판정] FAIL ✗")
    print("  사유:")
    for i, reason in enumerate(fail_reasons, 1):
        print(f"    {i}. {reason}")
print("=" * 60)
