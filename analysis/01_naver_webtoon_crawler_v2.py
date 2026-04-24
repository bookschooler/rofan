"""
네이버 웹툰 로판 크롤러 v2 — 장르 필터 버그 수정판
- 완결 API의 genre 파라미터가 서버에서 무시됨 (버그 확인)
- 전체 완결 2923건 수집 후 info API로 각각 is_rofan() 필터링
- 연재중: 요일별 API + is_rofan() 필터
- 제목 키워드 빠른 필터로 info API 호출 최소화
"""

import sys
import requests
import pandas as pd
import time
import re
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

OUT_PATH = "data/raw/naver_webtoon_works.csv"

QUICK_ROFAN_KW = {
    "황후", "공작", "황제", "귀족", "황녀", "이세계", "환생", "회귀", "빙의",
    "전하", "영주", "백작", "후작", "기사", "성녀", "왕비", "마법", "마녀",
    "마왕", "용사", "폐하", "왕자", "공녀", "남작", "계약", "환생", "빙의",
}

ROFAN_TAGS = {
    "이세계", "회귀", "빙의", "환생", "궁정", "귀족", "공작", "황후",
    "황제", "여주", "로판", "로맨스판타지", "계약결혼", "ROMANCE_FANTASY",
}

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


def is_rofan(title_item: dict, info: dict) -> bool:
    genre_raw = str(title_item.get("genre", "") or "")
    tags = info.get("curationTagList") or []
    tag_names = {t.get("tagName", "") for t in tags if isinstance(t, dict)}
    tag_url_paths = " ".join(t.get("urlPath", "") for t in tags if isinstance(t, dict))

    if any(rg.upper() in genre_raw.upper() for rg in ("ROMANCE_FANTASY", "로맨스판타지", "로판")):
        return True
    if any(rt in tag_names for rt in ROFAN_TAGS):
        return True
    if "ROMANCE_FANTASY" in tag_url_paths.upper():
        return True
    return False


def build_record(item: dict, info: dict, start_date: str | None,
                 start_date_source: str, now: str) -> dict:
    tid = item.get("titleId")
    title = item.get("titleName", "") or item.get("title", "")
    is_finished = item.get("finish", False) or item.get("finished", False)
    ep_count = int(item.get("totalEpisodeCount", 0) or item.get("episodeCount", 0) or 0)
    rating = float(item.get("starScore", 0) or 0)

    genre_tags = []
    if info.get("curationTagList"):
        genre_tags = [t.get("tagName", "") for t in info["curationTagList"]
                      if "GENRE" in t.get("curationType", "")]

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
        "genre_raw": ",".join(genre_tags) or "로맨스판타지",
        "start_date": start_date,
        "start_date_source": start_date_source,
        "complete_status": "completed" if is_finished else "ongoing",
        "complete_date": None,
        "rating": rating,
        "rating_count": 0,
        "bookmark_count": None,
        "episode_count": ep_count,
        "primary_metric": float(ep_count),
        "primary_metric_source": "episode_count",
        "tags": "",
        "original_work_id": original_work_id,
        "last_crawled_at": now,
    }


def collect_all_finished() -> dict:
    """완결 전체 2923건 수집 (장르 필터 무시됨 → 전체 수집 후 필터)"""
    all_titles = {}
    for page in range(1, 70):
        try:
            r = SESSION.get(
                f"https://comic.naver.com/api/webtoon/titlelist/finished?page={page}&genre=ROMANCE_FANTASY",
                timeout=12,
            )
            r.raise_for_status()
            data = r.json()
            items = data.get("titleList", [])
            if not items:
                break
            for t in items:
                tid = t.get("titleId")
                if tid:
                    all_titles[tid] = t
            if page % 10 == 0:
                print(f"  완결 수집: page {page} (누적 {len(all_titles)}건)")
            time.sleep(0.2)
        except Exception as e:
            print(f"  [완결 p{page}] 오류: {e}")
            break
    return all_titles


def collect_weekday_ongoing() -> dict:
    """요일별 연재 전체 수집"""
    all_titles = {}
    weekdays = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    for day in weekdays:
        try:
            r = SESSION.get(
                f"https://comic.naver.com/api/webtoon/titlelist/weekday?weekday={day}&orderType=UPDATE&channelPriorityOrder=false",
                timeout=12,
            )
            r.raise_for_status()
            data = r.json()
            titles = data.get("titleListMap", {})
            day_titles = titles.get(day.upper(), titles.get(day, []))
            for t in day_titles:
                tid = t.get("titleId")
                if tid and tid not in all_titles:
                    all_titles[tid] = t
            time.sleep(0.2)
        except Exception as e:
            print(f"  [{day}] 오류: {e}")
    return all_titles


def crawl_naver_webtoon() -> pd.DataFrame:
    print("=== 네이버 웹툰 로판 크롤러 v2 (is_rofan 필터 적용) ===")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 1. 완결 전체 수집
    print("\n[1] 완결 웹툰 전체 수집 (2,923건 예상)...")
    finished = collect_all_finished()
    print(f"  완결 수집 완료: {len(finished)}건")

    # 2. 연재중 수집
    print("\n[2] 요일별 연재 웹툰 수집...")
    ongoing = collect_weekday_ongoing()
    print(f"  연재중 수집 완료: {len(ongoing)}건 (전장르)")

    # 통합 (연재중은 완결에 없는 것만)
    all_candidates = dict(finished)
    for tid, t in ongoing.items():
        if tid not in all_candidates:
            all_candidates[tid] = t

    print(f"\n총 후보: {len(all_candidates)}건 → is_rofan 필터링 시작...")

    records = []
    rofan_count = 0
    skipped = 0
    info_calls = 0

    for i, (tid, item) in enumerate(all_candidates.items()):
        title = item.get("titleName", "") or item.get("title", "")

        if i % 200 == 0:
            print(f"  {i}/{len(all_candidates)} 처리 | 로판 확인: {rofan_count}건 | info호출: {info_calls}건")

        # 빠른 키워드 필터
        quick = any(kw in title for kw in QUICK_ROFAN_KW)

        if quick:
            info = {}
        else:
            info = fetch_title_info(tid)
            info_calls += 1
            time.sleep(0.25)
            if not is_rofan(item, info):
                skipped += 1
                continue

        rofan_count += 1

        start_date, src = fetch_start_date(tid)
        time.sleep(0.3)

        records.append(build_record(item, info, start_date, src, now))

    print(f"\n필터링 결과: {rofan_count}건 로판 확인 / {skipped}건 제외 / info호출 {info_calls}건")

    df = pd.DataFrame(records)
    if df.empty:
        print("수집 결과 없음")
        return df

    df = df.drop_duplicates(subset=["work_id"])
    df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
    df = df.sort_values("start_date", ascending=False, na_position="last").reset_index(drop=True)

    df.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")
    print(f"\n=== 완료 ===")
    print(f"저장: {OUT_PATH} ({len(df):,}행)")
    print(f"complete_status: {df['complete_status'].value_counts().to_dict()}")
    print(f"start_date 보유: {df['start_date'].notna().sum()}건 ({df['start_date'].notna().mean()*100:.0f}%)")
    print(f"start_date 범위: {df['start_date'].min()} ~ {df['start_date'].max()}")
    return df


if __name__ == "__main__":
    df = crawl_naver_webtoon()
    if not df.empty:
        print(df[["work_id", "title", "start_date", "complete_status", "episode_count", "rating"]].head(10).to_string())
