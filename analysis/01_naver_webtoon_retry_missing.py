"""
네이버 웹툰 start_date 결측 재시도 v2 (쿠키 인증)
- naver_webtoon_works.csv에서 start_date 결측인 작품만 재수집
- .naver_cookie_temp 파일의 인증 쿠키 사용 (성인 작품 접근)
"""

import sys, re, time, requests
from pathlib import Path
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

CSV_PATH = "data/raw/naver_webtoon_works.csv"
COOKIE_PATH = ".naver_cookie_temp"
SLEEP = 0.4

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

if Path(COOKIE_PATH).exists():
    raw_cookie = Path(COOKIE_PATH).read_text(encoding="utf-8").strip()
    SESSION.headers.update({"Cookie": raw_cookie})
    print(f"쿠키 로드 완료 ({len(raw_cookie)}자)")
else:
    print(f"[경고] {COOKIE_PATH} 없음")


def parse_date(date_str: str) -> str | None:
    if not date_str:
        return None
    m = re.match(r"(\d{2})[.\-](\d{2})[.\-](\d{2})", str(date_str))
    if m:
        yy, mm, dd = m.groups()
        year = f"20{yy}" if int(yy) <= 30 else f"19{yy}"
        return f"{year}-{mm}-{dd}"
    return None


def fetch_start_date(title_id: int) -> tuple[str | None, str]:
    try:
        r = SESSION.get(
            f"https://comic.naver.com/api/article/list?titleId={title_id}&page=1&sort=ASC",
            timeout=10,
        )
        r.raise_for_status()
        articles = r.json().get("articleList", [])
        if articles:
            parsed = parse_date(articles[0].get("serviceDateDescription", ""))
            if parsed:
                return parsed, "episode_backtrack"
    except Exception:
        pass
    return None, "unknown"


def main():
    df = pd.read_csv(CSV_PATH)

    missing = df[df["start_date"].isna()].copy()
    print(f"=== 네이버 웹툰 start_date 재수집: {len(missing)}건 ===")

    success = fail = 0

    for i, (_, row) in enumerate(missing.iterrows()):
        title_id = int(row["work_id"].replace("nw_", ""))
        start_date, source = fetch_start_date(title_id)

        df.loc[df["work_id"] == row["work_id"], "start_date"] = start_date
        df.loc[df["work_id"] == row["work_id"], "start_date_source"] = source

        if start_date:
            success += 1
            print(f"  ✓ {row['title']}: {start_date}")
        else:
            fail += 1
            print(f"  ✗ {row['title']}: 여전히 실패")

        time.sleep(SLEEP)

    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"\n=== 완료: 성공 {success}건 | 실패 {fail}건 ===")


if __name__ == "__main__":
    main()
