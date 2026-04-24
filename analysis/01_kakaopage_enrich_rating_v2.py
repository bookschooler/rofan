"""
카카오페이지 rating 보강 v2 - 순차 실행 (rate limit 방지)
- sleep 0.8초로 안전하게
- 체크포인트로 재개 가능
- 완료 후 kakaopage_works.csv에 병합
"""

import sys, re, time, json, requests
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

DATA_PATH = "data/raw/kakaopage_works.csv"
CHECKPOINT_PATH = "data/raw/kp_rating_v2_checkpoint.csv"
SLEEP = 0.8

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://page.kakao.com/",
}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def fetch_fields(series_id: str) -> dict | None:
    """None=예외(재시도 필요), dict=정상(rating_count=0 포함)"""
    try:
        r = SESSION.get(f"https://page.kakao.com/content/{series_id}", timeout=15)
        r.raise_for_status()
        m = re.search(
            r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
            r.text, re.DOTALL
        )
        if not m:
            return None
        data = json.loads(m.group(1))
        sp = (data["props"]["pageProps"]["initialProps"]
              ["dehydratedState"]["queries"][0]
              ["state"]["data"]["contentHomeOverview"]["content"]["serviceProperty"])
        rc = int(sp.get("ratingCount", 0) or 0)
        rs = int(sp.get("ratingSum", 0) or 0)
        cc = int(sp.get("commentCount", 0) or 0)
        return {
            "rating": round(rs / rc, 4) if rc > 0 else 0.0,
            "rating_count": rc,
            "comment_count": cc,
        }
    except Exception:
        return None


def main():
    df = pd.read_csv(DATA_PATH)
    print(f"=== 카카오페이지 rating 보강 v2: {len(df):,}건 ===")

    # 체크포인트 로드
    if pd.io.common.file_exists(CHECKPOINT_PATH):
        cp = pd.read_csv(CHECKPOINT_PATH)
        done = dict(zip(cp["work_id"], cp.to_dict("records")))
        print(f"  체크포인트: {len(done):,}건 이미 처리 → 이어서")
    else:
        done = {}

    todo = df[~df["work_id"].isin(done.keys())]
    print(f"  남은 작업: {len(todo):,}건 (sleep={SLEEP}s, 예상 {len(todo)*SLEEP/60:.0f}분)")

    start = time.time()
    success = sum(1 for v in done.values() if v.get("rating_count", 0) > 0)
    fail = 0

    for i, (_, row) in enumerate(todo.iterrows()):
        sid = row["work_id"].replace("kp_", "")
        result = fetch_fields(sid)

        if result is not None:
            done[row["work_id"]] = {"work_id": row["work_id"], **result}
            if result["rating_count"] > 0:
                success += 1
        else:
            # 예외 → 일단 0으로 저장 (나중에 재시도 가능)
            done[row["work_id"]] = {"work_id": row["work_id"], "rating": 0.0, "rating_count": 0, "comment_count": 0}
            fail += 1

        if (i + 1) % 200 == 0:
            cp_df = pd.DataFrame(done.values())
            cp_df.to_csv(CHECKPOINT_PATH, index=False, encoding="utf-8-sig")
            elapsed = (time.time() - start) / 60
            remaining = elapsed / (i + 1) * (len(todo) - i - 1)
            print(f"  [{i+1}/{len(todo)}] rating>0: {success}건 | 예외: {fail}건 | {elapsed:.0f}분 경과 | 남은: {remaining:.0f}분")

        time.sleep(SLEEP)

    # 최종 체크포인트 저장
    cp_df = pd.DataFrame(done.values())
    cp_df.to_csv(CHECKPOINT_PATH, index=False, encoding="utf-8-sig")

    # 원본 CSV에 병합
    merge_df = cp_df[["work_id", "rating", "rating_count", "comment_count"]]
    df2 = df.drop(columns=["rating", "rating_count", "comment_count"], errors="ignore")
    df2 = df2.merge(merge_df, on="work_id", how="left")
    df2.to_csv(DATA_PATH, index=False, encoding="utf-8-sig")

    elapsed = (time.time() - start) / 60
    print(f"\n=== 완료 ({elapsed:.0f}분) ===")
    print(f"저장: {DATA_PATH}")
    print(f"rating > 0: {(df2['rating'].fillna(0)>0).sum():,}건 ({(df2['rating'].fillna(0)>0).mean()*100:.1f}%)")
    print(f"rating 중앙값 (>0): {df2[df2['rating']>0]['rating'].median():.2f}")
    print(f"rating_count 중앙값 (>0): {df2[df2['rating_count']>0]['rating_count'].median():,.0f}")
    print(f"comment_count 중앙값 (>0): {df2[df2['comment_count']>0]['comment_count'].median():,.0f}")
    print()
    print("상위 5개:")
    print(df2.nlargest(5, "rating_count")[["title", "rating", "rating_count", "comment_count"]].to_string(index=False))


if __name__ == "__main__":
    main()
