"""
네이버 시리즈 start_date 결측 재시도 v2 (쿠키 인증)
- naver_series_works.csv에서 start_date 결측인 serialized 작품만 재수집
- .naver_cookie_temp 파일의 인증 쿠키 사용 (성인 작품 접근)
- 완료 후 naver_series_works.csv 업데이트
"""

import sys, json, time, requests
from pathlib import Path
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

CSV_PATH = "data/raw/naver_series_works.csv"
COOKIE_PATH = ".naver_cookie_temp"
SLEEP = 0.4

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://series.naver.com/",
}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

# 쿠키 로드
if Path(COOKIE_PATH).exists():
    raw_cookie = Path(COOKIE_PATH).read_text(encoding="utf-8").strip()
    SESSION.headers.update({"Cookie": raw_cookie})
    print(f"쿠키 로드 완료 ({len(raw_cookie)}자)")
else:
    print(f"[경고] {COOKIE_PATH} 없음 — 비인증 상태로 실행")


def fetch_start_date(product_no: str) -> tuple[str | None, str]:
    url = f"https://series.naver.com/novel/volumeList.series?productNo={product_no}"
    try:
        r = SESSION.get(url, timeout=10)
        if r.status_code != 200 or not r.text.strip():
            return None, f"api_error_{r.status_code}"
        items = json.loads(r.text).get("resultData", [])
        if items:
            raw = items[0].get("lastVolumeUpdateDate", "")
            if raw:
                return raw[:10], "volumeList_ep1_cookie"
        return None, "no_episode"
    except Exception:
        return None, "exception"


def main():
    df = pd.read_csv(CSV_PATH)

    # serialized 중 결측만 추출 (book_edition 제외)
    missing = df[(df["start_date"].isna()) & (df["content_form"] == "serialized")].copy()
    print(f"serialized 전체 결측: {df[(df['start_date'].isna()) & (df['content_form'] == 'serialized')].shape[0]}건")
    print(f"(전체 결측 {df['start_date'].isna().sum()}건 중 serialized만 재수집)")
    print(f"=== 네이버 시리즈 start_date 재수집 (쿠키 인증): {len(missing):,}건 ===")
    print(f"예상 시간: 약 {len(missing) * SLEEP / 60:.0f}분")

    results = {}
    success = fail = 0

    for i, (_, row) in enumerate(missing.iterrows()):
        product_no = row["work_id"].replace("ns_", "")
        start_date, source = fetch_start_date(product_no)

        results[row["work_id"]] = {"start_date": start_date, "start_date_source": source}

        if start_date:
            success += 1
        else:
            fail += 1

        if (i + 1) % 200 == 0:
            print(f"  [{i+1}/{len(missing)}] 성공: {success}건 | 실패: {fail}건", flush=True)
            # 중간 저장
            for work_id, vals in results.items():
                df.loc[df["work_id"] == work_id, "start_date"] = vals["start_date"]
                df.loc[df["work_id"] == work_id, "start_date_source"] = vals["start_date_source"]
            df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")

        time.sleep(SLEEP)

    # 최종 저장
    for work_id, vals in results.items():
        df.loc[df["work_id"] == work_id, "start_date"] = vals["start_date"]
        df.loc[df["work_id"] == work_id, "start_date_source"] = vals["start_date_source"]

    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")

    total_missing_after = df["start_date"].isna().sum()
    print(f"\n=== 완료 ===")
    print(f"성공: {success}건 | 여전히 실패: {fail}건")
    print(f"저장 후 전체 결측: {total_missing_after}건 ({total_missing_after/len(df)*100:.1f}%)")


if __name__ == "__main__":
    main()
