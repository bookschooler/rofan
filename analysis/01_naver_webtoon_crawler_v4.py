"""
네이버 웹툰 로판 크롤러 v4
- 올바른 필터: /api/curation/list?type=CUSTOM_TAG&id=51 (로판 태그)
- GENRE_ROMANCE_FANTASY curationType은 존재하지 않음 (v3 오류 수정)
- 로판 태그(id=51)는 CUSTOM_TAG이며 249건 (완결 118 + 연재중 131)
- curationViewList에 rating, episode_count, finished 포함되어 info API 불필요
"""

import sys
import requests
import pandas as pd
import time
import re
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding="utf-8")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

OUT_PATH = "data/raw/naver_webtoon_works.csv"
CURATION_URL = "https://comic.naver.com/api/curation/list"

KNOWN_ORIGINAL_MAP = {
    "재혼 황후": "kp_재혼황후",
    "선재 업고 튀어": "ns_선재업고튀어",
}


def parse_date(date_str: str) -> str | None:
    if not date_str:
        return None
    m = re.match(r"(\d{2})[.\-](\d{2})[.\-](\d{2})", str(date_str))
    if m:
        yy, mm, dd = m.groups()
        year = f"20{yy}" if int(yy) <= 30 else f"19{yy}"
        return f"{year}-{mm}-{dd}"
    return None


def fetch_all_rofan() -> list[dict]:
    """CUSTOM_TAG id=51 (로판) 전체 목록 수집"""
    all_items = []
    page = 1
    while True:
        try:
            r = SESSION.get(
                CURATION_URL,
                params={"type": "CUSTOM_TAG", "id": 51, "page": page},
                timeout=10,
            )
            r.raise_for_status()
            data = r.json()
            items = data.get("curationViewList", [])
            if not items:
                break
            all_items.extend(items)
            page_info = data.get("pageInfo", {})
            total_pages = page_info.get("totalPages", 1)
            if page % 5 == 0 or page >= total_pages:
                print(f"  page {page}/{total_pages} | 누적 {len(all_items)}건")
            if page >= total_pages:
                break
            page += 1
            time.sleep(0.2)
        except Exception as e:
            print(f"  [p{page}] 오류: {e}")
            break
    return all_items


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


def build_record(item: dict, start_date: str | None, start_date_source: str, now: str) -> dict:
    tid = item.get("titleId")
    title = item.get("titleName", "")
    is_finished = item.get("finished", False)
    ep_count = int(item.get("articleTotalCount", 0) or 0)
    rating = float(item.get("averageStarScore", 0) or 0)

    genre_list = item.get("genreList", [])
    genre_raw = ",".join(g.get("description", "") for g in genre_list) or "로맨스판타지"

    authors = []
    for w in item.get("writers", []):
        authors.append(w.get("name", ""))
    author = "/".join(authors)

    original_work_id = None
    for known_title, orig_id in KNOWN_ORIGINAL_MAP.items():
        if known_title in title:
            original_work_id = orig_id
            break

    return {
        "work_id": f"nw_{tid}",
        "platform": "naver_webtoon",
        "content_type": "webtoon",
        "title": title,
        "author": author,
        "genre_raw": genre_raw,
        "start_date": start_date,
        "start_date_source": start_date_source,
        "complete_status": "completed" if is_finished else "ongoing",
        "complete_date": None,
        "rating": rating,
        "rating_count": 0,
        "bookmark_count": item.get("favoriteCount", None),
        "episode_count": ep_count,
        "primary_metric": float(ep_count) if ep_count > 0 else float(rating),
        "primary_metric_source": "episode_count" if ep_count > 0 else "rating",
        "tags": "",
        "original_work_id": original_work_id,
        "last_crawled_at": now,
    }


def crawl_naver_webtoon() -> pd.DataFrame:
    print("=== 네이버 웹툰 로판 크롤러 v4 (CUSTOM_TAG id=51 직접 수집) ===")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    print("\n[1] 로판 큐레이션 목록 수집 (CUSTOM_TAG id=51)...")
    rofan_items = fetch_all_rofan()
    finished_cnt = sum(1 for it in rofan_items if it.get("finished"))
    ongoing_cnt = len(rofan_items) - finished_cnt
    print(f"  수집 완료: {len(rofan_items)}건 (완결 {finished_cnt} / 연재중 {ongoing_cnt})")

    print("\n[2] start_date 수집 (에피소드 역추적)...")
    records = []
    for i, item in enumerate(rofan_items):
        if i % 50 == 0:
            print(f"  {i}/{len(rofan_items)}")
        tid = item.get("titleId")
        start_date, src = fetch_start_date(tid)
        time.sleep(0.3)
        records.append(build_record(item, start_date, src, now))

    df = pd.DataFrame(records)
    if df.empty:
        print("수집 결과 없음")
        return df

    df = df.drop_duplicates(subset=["work_id"])
    df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
    df = df.sort_values("start_date", ascending=False, na_position="last").reset_index(drop=True)

    df.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")
    print(f"\n=== 완료 ===")
    print(f"저장: {OUT_PATH} ({len(df):,}건)")
    print(f"complete_status: {df['complete_status'].value_counts().to_dict()}")
    print(f"start_date 보유: {df['start_date'].notna().sum()}건 ({df['start_date'].notna().mean()*100:.0f}%)")
    print(f"start_date 범위: {df['start_date'].min()} ~ {df['start_date'].max()}")
    return df


if __name__ == "__main__":
    df = crawl_naver_webtoon()
    if not df.empty:
        print(df[["work_id", "title", "start_date", "complete_status", "episode_count", "rating"]].head(10).to_string())
