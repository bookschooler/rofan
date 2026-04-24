"""
3개 플랫폼 통합 데이터셋 생성
- kakaopage(10,770) + naver_series(18,778) + naver_webtoon(249) → all_works_integrated.csv
- 전체 29,797건 저장 (content_form 컬럼 유지 — 분석 시 serialized 필터 사용)
- DESA 팀 합의 컬럼만 포함 (tags, bookmark_count 제거)
"""

import sys
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

FINAL_COLS = [
    "work_id", "platform", "content_type", "title", "author",
    "start_date", "start_date_source",
    "complete_status", "complete_date",
    "content_form",
    "primary_metric", "primary_metric_source",
    "episode_count", "rating", "rating_count",
    "original_work_id",
    "last_crawled_at",
]

def load_kakaopage() -> pd.DataFrame:
    df = pd.read_csv("data/raw/kakaopage_works.csv")
    df["original_work_id"] = None
    return df[FINAL_COLS]

def load_naver_series() -> pd.DataFrame:
    df = pd.read_csv("data/raw/naver_series_works.csv")
    df["original_work_id"] = None
    return df[FINAL_COLS]

def load_naver_webtoon() -> pd.DataFrame:
    df = pd.read_csv("data/raw/naver_webtoon_works.csv")
    df["content_form"] = "serialized"  # 웹툰은 단행본/스핀오프 구분 없음
    return df[FINAL_COLS]

def main():
    kp = load_kakaopage()
    ns = load_naver_series()
    nw = load_naver_webtoon()

    df = pd.concat([kp, ns, nw], ignore_index=True)

    # 타입 변환
    df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
    df["complete_date"] = pd.to_datetime(df["complete_date"], errors="coerce")

    # ── 데이터 품질 리포트 ──────────────────────────────────────────
    print("=" * 55)
    print(f"전체 통합 건수: {len(df):,}건")
    print()

    print("[플랫폼별 건수]")
    print(df["platform"].value_counts().to_string())
    print()

    print("[content_form 분포]")
    print(df["content_form"].value_counts().to_string())
    print()

    # serialized만 필터링 후 결측률 확인 (Reviewer 요청)
    s = df[df["content_form"] == "serialized"].copy()
    print(f"serialized 필터링 후: {len(s):,}건")
    sd_missing = s["start_date"].isna().sum()
    print(f"  start_date 결측: {sd_missing:,}건 ({sd_missing/len(s)*100:.1f}%)")
    print(f"  start_date 보유: {s['start_date'].notna().sum():,}건 ({s['start_date'].notna().mean()*100:.1f}%)")
    print()

    print("[start_date 범위 (serialized)]")
    print(f"  최소: {s['start_date'].min()}")
    print(f"  최대: {s['start_date'].max()}")
    print()

    print("[플랫폼별 start_date 결측률 (serialized)]")
    for platform, group in s.groupby("platform"):
        missing = group["start_date"].isna().sum()
        print(f"  {platform}: {missing}건 결측 ({missing/len(group)*100:.1f}%)")
    print()

    # 저장
    out_path = "data/raw/all_works_integrated.csv"
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"저장 완료: {out_path}")
    print("=" * 55)

if __name__ == "__main__":
    main()
