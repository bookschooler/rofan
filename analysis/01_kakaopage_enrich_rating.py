"""
카카오페이지 rating, rating_count, comment_count 보강
- 상세 페이지 __NEXT_DATA__ 에서 ratingSum, ratingCount, commentCount 추출
- rating = ratingSum / ratingCount (가중 평균)
- 체크포인트: 200건마다 저장 (중단 후 재개 가능)
"""

import sys
import re
import time
import json
import requests
import pandas as pd
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://page.kakao.com/",
}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

DATA_PATH = "data/raw/kakaopage_works.csv"
CHECKPOINT_PATH = "data/raw/kakaopage_rating_checkpoint.csv"
SLEEP = 0.35


def fetch_rating_fields(series_id: str) -> dict:
    try:
        r = SESSION.get(f"https://page.kakao.com/content/{series_id}", timeout=12)
        r.raise_for_status()
        m = re.search(
            r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
            r.text, re.DOTALL
        )
        if not m:
            return {}
        data = json.loads(m.group(1))
        queries = data["props"]["pageProps"]["initialProps"]["dehydratedState"]["queries"]
        sp = queries[0]["state"]["data"]["contentHomeOverview"]["content"]["serviceProperty"]
        rating_count = int(sp.get("ratingCount", 0) or 0)
        rating_sum = int(sp.get("ratingSum", 0) or 0)
        comment_count = int(sp.get("commentCount", 0) or 0)
        rating = round(rating_sum / rating_count, 4) if rating_count > 0 else 0.0
        return {
            "rating": rating,
            "rating_count": rating_count,
            "comment_count": comment_count,
        }
    except Exception:
        return {}


def main():
    df = pd.read_csv(DATA_PATH)
    total = len(df)
    print(f"=== 카카오페이지 rating 보강 시작: {total:,}건 ===")

    # 체크포인트 로드
    if pd.io.common.file_exists(CHECKPOINT_PATH):
        cp = pd.read_csv(CHECKPOINT_PATH)
        done_ids = set(cp["work_id"])
        print(f"  체크포인트 발견: {len(done_ids):,}건 이미 처리됨 → 이어서 진행")
    else:
        cp = pd.DataFrame(columns=["work_id", "rating", "rating_count", "comment_count"])
        done_ids = set()

    results = cp.to_dict("records")
    start_time = time.time()
    success = 0
    fail = 0

    todo = df[~df["work_id"].isin(done_ids)]
    print(f"  남은 작업: {len(todo):,}건")

    for i, (_, row) in enumerate(todo.iterrows()):
        series_id = row["work_id"].replace("kp_", "")
        fields = fetch_rating_fields(series_id)

        if fields:
            results.append({"work_id": row["work_id"], **fields})
            success += 1
        else:
            results.append({"work_id": row["work_id"], "rating": 0.0, "rating_count": 0, "comment_count": 0})
            fail += 1

        # 200건마다 체크포인트 저장
        if (i + 1) % 200 == 0:
            cp_df = pd.DataFrame(results)
            cp_df.to_csv(CHECKPOINT_PATH, index=False, encoding="utf-8-sig")
            elapsed = (time.time() - start_time) / 60
            remaining = elapsed / (i + 1) * (len(todo) - i - 1)
            print(f"  [{i+1}/{len(todo)}] 성공: {success} | 실패: {fail} | 경과: {elapsed:.0f}분 | 남은 예상: {remaining:.0f}분")

        time.sleep(SLEEP)

    # 최종 저장
    cp_df = pd.DataFrame(results)
    cp_df.to_csv(CHECKPOINT_PATH, index=False, encoding="utf-8-sig")

    # 원본 CSV에 병합
    df = df.drop(columns=["rating", "rating_count"], errors="ignore")
    if "comment_count" not in df.columns:
        df["comment_count"] = None

    merge_df = cp_df[["work_id", "rating", "rating_count", "comment_count"]]
    df = df.merge(merge_df, on="work_id", how="left")

    df.to_csv(DATA_PATH, index=False, encoding="utf-8-sig")

    total_elapsed = (time.time() - start_time) / 60
    print(f"\n=== 완료 ({total_elapsed:.0f}분 소요) ===")
    print(f"저장: {DATA_PATH}")
    print(f"성공: {success:,}건 / 실패: {fail:,}건")
    print(f"rating > 0: {(df['rating'].fillna(0) > 0).sum():,}건 ({(df['rating'].fillna(0) > 0).mean()*100:.0f}%)")
    print(f"rating 중앙값: {df[df['rating']>0]['rating'].median():.2f}")
    print(f"rating_count 중앙값: {df[df['rating_count']>0]['rating_count'].median():,.0f}")
    print(f"comment_count 중앙값: {df[df['comment_count']>0]['comment_count'].median():,.0f}")


if __name__ == "__main__":
    main()
