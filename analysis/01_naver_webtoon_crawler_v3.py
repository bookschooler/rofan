"""
네이버 웹툰 로판 크롤러 v3
- 공식 장르 코드 기반 필터: curationTagList.curationType == 'GENRE_ROMANCE_FANTASY'
- 완결: 전체 2923건 info API 호출 후 GENRE_ROMANCE_FANTASY 확인
- 연재중: 요일별 API(MONDAY 키 수정) + 동일 필터
- v2 버그 수정: 요일 키 'MON' → 'MONDAY', 장르 태그 'GENRE_ROMANCE_FANTASY' 엄격 필터
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

WEEKDAY_KEYS = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]

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


def fetch_title_info(title_id: int) -> dict:
    try:
        r = SESSION.get(
            f"https://comic.naver.com/api/article/list/info?titleId={title_id}&page=1",
            timeout=10,
        )
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}


def is_romance_fantasy(info: dict) -> bool:
    """공식 장르 코드 GENRE_ROMANCE_FANTASY 확인"""
    for tag in info.get("curationTagList") or []:
        if tag.get("curationType") == "GENRE_ROMANCE_FANTASY":
            return True
    return False


def get_genre_tags(info: dict) -> str:
    tags = [
        t.get("tagName", "")
        for t in (info.get("curationTagList") or [])
        if t.get("curationType", "").startswith("GENRE_")
    ]
    return ",".join(tags)


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


def collect_all_finished() -> dict:
    """완결 전체 수집 (genre 파라미터 작동 안 함 → 전체 수집)"""
    all_titles = {}
    for page in range(1, 70):
        try:
            r = SESSION.get(
                f"https://comic.naver.com/api/webtoon/titlelist/finished?page={page}",
                timeout=12,
            )
            r.raise_for_status()
            items = r.json().get("titleList", [])
            if not items:
                break
            for t in items:
                tid = t.get("titleId")
                if tid:
                    all_titles[tid] = t
            if page % 10 == 0:
                print(f"  완결 수집: page {page} ({len(all_titles)}건)")
            time.sleep(0.2)
        except Exception as e:
            print(f"  [p{page}] 오류: {e}")
            break
    return all_titles


def collect_weekday_ongoing() -> dict:
    """요일별 연재 수집 — 키: MONDAY/TUESDAY/..."""
    all_titles = {}
    weekdays = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    for day in weekdays:
        try:
            r = SESSION.get(
                f"https://comic.naver.com/api/webtoon/titlelist/weekday"
                f"?weekday={day}&orderType=UPDATE&channelPriorityOrder=false",
                timeout=12,
            )
            r.raise_for_status()
            title_map = r.json().get("titleListMap", {})
            # 키가 "MONDAY" 형식
            day_key = day.upper() + ("DAY" if day not in ("sat", "sun") else
                                     ("URDAY" if day == "sat" else "DAY"))
            # 안전하게 매핑
            key_map = {
                "mon": "MONDAY", "tue": "TUESDAY", "wed": "WEDNESDAY",
                "thu": "THURSDAY", "fri": "FRIDAY", "sat": "SATURDAY", "sun": "SUNDAY",
            }
            items = title_map.get(key_map[day], [])
            for t in items:
                tid = t.get("titleId")
                if tid and tid not in all_titles:
                    all_titles[tid] = t
            time.sleep(0.2)
        except Exception as e:
            print(f"  [{day}] 오류: {e}")
    return all_titles


def build_record(item: dict, info: dict, start_date: str | None,
                 start_date_source: str, now: str) -> dict:
    tid = item.get("titleId")
    title = item.get("titleName", "") or item.get("title", "")
    is_finished = item.get("finish", False) or item.get("finished", False)
    ep_count = int(item.get("totalEpisodeCount", 0) or item.get("episodeCount", 0) or 0)
    rating = float(item.get("starScore", 0) or 0)
    genre_raw = get_genre_tags(info) or "로맨스판타지"

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
        "author": item.get("author", ""),
        "genre_raw": genre_raw,
        "start_date": start_date,
        "start_date_source": start_date_source,
        "complete_status": "completed" if is_finished else "ongoing",
        "complete_date": None,
        "rating": rating,
        "rating_count": 0,
        "bookmark_count": None,
        "episode_count": ep_count,
        "primary_metric": float(ep_count) if ep_count > 0 else float(rating),
        "primary_metric_source": "episode_count" if ep_count > 0 else "rating",
        "tags": "",
        "original_work_id": original_work_id,
        "last_crawled_at": now,
    }


def crawl_naver_webtoon() -> pd.DataFrame:
    print("=== 네이버 웹툰 로판 크롤러 v3 (GENRE_ROMANCE_FANTASY 필터) ===")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 1. 완결 전체 수집
    print("\n[1] 완결 웹툰 전체 수집...")
    finished = collect_all_finished()
    print(f"  완결 {len(finished)}건 수집 완료")

    # 2. 연재중 수집
    print("\n[2] 요일별 연재 웹툰 수집...")
    ongoing = collect_weekday_ongoing()
    print(f"  연재중 {len(ongoing)}건 수집 완료 (전장르)")

    all_candidates = dict(finished)
    for tid, t in ongoing.items():
        if tid not in all_candidates:
            all_candidates[tid] = t
    print(f"\n총 후보: {len(all_candidates)}건 → GENRE_ROMANCE_FANTASY 필터링 시작...")

    records = []
    rf_count = 0
    skipped = 0

    for i, (tid, item) in enumerate(all_candidates.items()):
        if i % 300 == 0:
            print(f"  {i}/{len(all_candidates)} | 로맨스판타지: {rf_count}건 | 제외: {skipped}건")

        info = fetch_title_info(tid)
        time.sleep(0.25)

        if not is_romance_fantasy(info):
            skipped += 1
            continue

        rf_count += 1
        start_date, src = fetch_start_date(tid)
        time.sleep(0.3)
        records.append(build_record(item, info, start_date, src, now))

    print(f"\n필터 결과: ROMANCE_FANTASY {rf_count}건 / 제외 {skipped}건")

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
