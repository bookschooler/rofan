"""
카카오페이지 rating 보강 - 청크 단위 실행 v2
Usage: python script.py <chunk_no>  (0~4)
sleep=1.5s → 5프로세스 합산 초당 3.3req (rate limit 안전)
"""

import sys, re, time, json, requests
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

CHUNK_NO = int(sys.argv[1]) if len(sys.argv) > 1 else 0
INPUT_PATH = f"data/raw/kp_chunk_{CHUNK_NO}.csv"
OUTPUT_PATH = f"data/raw/kp_rating_chunk_{CHUNK_NO}.csv"
SLEEP = 1.5

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://page.kakao.com/",
}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def fetch_fields(series_id: str) -> dict | None:
    """None=예외(네트워크 오류), dict=정상응답(ratingCount=0 포함)"""
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
    df = pd.read_csv(INPUT_PATH)
    print(f"[chunk_{CHUNK_NO}] {len(df)}건 시작 (sleep={SLEEP}s)...")

    records = []
    success = fail = 0
    start = time.time()

    for i, (_, row) in enumerate(df.iterrows()):
        sid = row["work_id"].replace("kp_", "")
        result = fetch_fields(sid)

        if result is not None:
            records.append({"work_id": row["work_id"], **result})
            if result["rating_count"] > 0:
                success += 1
        else:
            records.append({"work_id": row["work_id"], "rating": 0.0, "rating_count": 0, "comment_count": 0})
            fail += 1

        if (i + 1) % 100 == 0:
            elapsed = (time.time() - start) / 60
            remaining = elapsed / (i + 1) * (len(df) - i - 1)
            print(f"  [chunk_{CHUNK_NO}] {i+1}/{len(df)} | rating>0: {success} | 예외: {fail} | {elapsed:.0f}분↑ | 남은: {remaining:.0f}분")
            # 중간 저장
            pd.DataFrame(records).to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

        time.sleep(SLEEP)

    pd.DataFrame(records).to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
    elapsed = (time.time() - start) / 60
    print(f"[chunk_{CHUNK_NO}] 완료: rating>0 {success}건 | 예외 {fail}건 | {elapsed:.0f}분")


if __name__ == "__main__":
    main()
