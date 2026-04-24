"""
네이버 웹툰 로맨스/로판 크롤러
- 요일별 API: 연재중 전체 수집
- 완결 API: 완결작 수집
- start_date: article/list?sort=ASC&page=1 → serviceDateDescription
platform='naver_webtoon', content_type='webtoon'
"""

import requests
import pandas as pd
import time
import re
from datetime import datetime, timezone

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)

# 원작 웹소설 매핑 (수작업, 주요 작품)
KNOWN_ORIGINAL_MAP = {
    "재혼 황후": "kp_재혼황후",
    "선재 업고 튀어": "ns_선재업고튀어",
    "외과의사 엘리제": None,
    "악녀는 두 번 산다": None,
    "황제의 외동딸": None,
    "공작님의 아이를 가졌습니다": None,
    "어느 날 공주가 되어버렸다": None,
    "나의 남편과 결혼해줘": None,
    "버림받은 황비": None,
}

# 로맨스판타지 관련 장르 키워드
ROFAN_GENRES = {
    "ROMANCE_FANTASY", "PURE_LOVE", "ROMANCE",
    "순정", "로맨스", "로판", "로맨스판타지",
}

# 로판 관련 curationTag 키워드
ROFAN_TAGS = {
    "이세계", "회귀", "빙의", "환생", "궁정", "귀족", "공작", "황후",
    "황제", "여주", "로판", "로맨스판타지", "계약결혼",
}


def parse_date(date_str: str) -> str | None:
    """serviceDateDescription '25.11.29' → '2025-11-29'"""
    if not date_str:
        return None
    m = re.match(r"(\d{2})[.\-](\d{2})[.\-](\d{2})", str(date_str))
    if m:
        yy, mm, dd = m.groups()
        year = f"20{yy}" if int(yy) <= 30 else f"19{yy}"
        return f"{year}-{mm}-{dd}"
    return None


def fetch_weekday_titles() -> list[dict]:
    """요일별 연재 웹툰 전체 수집"""
    all_titles = {}
    weekdays = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    for day in weekdays:
        try:
            url = f"https://comic.naver.com/api/webtoon/titlelist/weekday?weekday={day}&orderType=UPDATE&channelPriorityOrder=false"
            r = SESSION.get(url, timeout=12)
            r.raise_for_status()
            data = r.json()
            titles = data.get("titleListMap", {})
            # 요일 키가 대문자 또는 소문자
            day_titles = titles.get(day.upper(), titles.get(day, []))
            for t in day_titles:
                tid = t.get("titleId")
                if tid and tid not in all_titles:
                    all_titles[tid] = t
            time.sleep(0.3)
        except Exception as e:
            print(f"  [{day}] 오류: {e}")
    return list(all_titles.values())


def fetch_finished_titles(genre: str = "ROMANCE_FANTASY", max_pages: int = 70) -> list[dict]:
    """완결 장르별 웹툰 수집 (ROMANCE_FANTASY: ~65페이지)"""
    titles = {}
    for page in range(1, max_pages + 1):
        try:
            url = f"https://comic.naver.com/api/webtoon/titlelist/finished?page={page}&genre={genre}"
            r = SESSION.get(url, timeout=12)
            r.raise_for_status()
            data = r.json()
            items = data.get("titleList", [])
            if not items:
                print(f"  [finished {genre} p{page}] 빈 페이지 → 종료")
                break
            for t in items:
                tid = t.get("titleId")
                if tid and tid not in titles:
                    titles[tid] = t
            page_info = data.get("pageInfo", {})
            if page % 10 == 0:
                total = page_info.get("totalRows", "?")
                print(f"  [finished {genre}] page {page}/{page_info.get('totalPages','?')} (누적 {len(titles)}/{total}건)")
            if page >= page_info.get("totalPages", max_pages):
                break
            time.sleep(0.3)
        except Exception as e:
            print(f"  [finished {genre} p{page}] 오류: {e}")
            break
    return list(titles.values())


def fetch_start_date(title_id: int) -> tuple[str | None, str]:
    """에피소드 1번 날짜로 연재 시작일 계산"""
    try:
        url = f"https://comic.naver.com/api/article/list?titleId={title_id}&page=1&sort=ASC"
        r = SESSION.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        articles = data.get("articleList", [])
        if articles:
            ep1 = articles[0]
            date_desc = ep1.get("serviceDateDescription", "")
            parsed = parse_date(date_desc)
            if parsed:
                return parsed, "episode_backtrack"
    except Exception:
        pass
    return None, "unknown"


def is_rofan(title_item: dict, info: dict | None = None) -> bool:
    """작품이 로판/로맨스판타지인지 태그/장르로 판별"""
    genre_raw = str(title_item.get("genre", "") or "")
    tags = title_item.get("curationTagList") or (info.get("curationTagList") if info else []) or []
    tag_names = {t.get("tagName", "") for t in tags if isinstance(t, dict)}
    tag_url_paths = " ".join(t.get("urlPath", "") for t in tags if isinstance(t, dict))

    # 장르 체크
    for rg in ROFAN_GENRES:
        if rg.upper() in genre_raw.upper():
            return True
    # 태그 체크
    for rt in ROFAN_TAGS:
        if rt in tag_names:
            return True
    # URL path에 ROMANCE_FANTASY 포함
    if "ROMANCE_FANTASY" in tag_url_paths.upper() or "romance_fantasy" in tag_url_paths.lower():
        return True
    return False


def fetch_title_info(title_id: int) -> dict:
    """작품 상세 info (장르, 태그, 연재일 등)"""
    try:
        url = f"https://comic.naver.com/api/article/list/info?titleId={title_id}&page=1"
        r = SESSION.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}


def crawl_naver_webtoon() -> pd.DataFrame:
    print("=== 네이버 웹툰 크롤링 시작 (전체 수집) ===")

    all_raw = {}
    # ROMANCE_FANTASY 완결 여부 추적 (start_date 호출 없이 바로 포함)
    confirmed_rofan = set()

    # 1. ROMANCE_FANTASY 완결 전체 수집 (필터 불필요, API가 이미 필터됨)
    print("\n[1] ROMANCE_FANTASY 완결 전체 수집 (65페이지)...")
    finished_rf = fetch_finished_titles(genre="ROMANCE_FANTASY", max_pages=70)
    print(f"  ROMANCE_FANTASY 완결: {len(finished_rf)}건")
    for t in finished_rf:
        tid = t.get("titleId")
        if tid:
            all_raw[tid] = t
            confirmed_rofan.add(tid)

    # 2. 요일별 연재 수집 (로판 필터 적용)
    print("\n[2] 요일별 연재 웹툰 수집 (로판 필터링)...")
    weekday_titles = fetch_weekday_titles()
    print(f"  요일별 총 고유 작품: {len(weekday_titles)}건 → 로판 필터 적용 중...")
    for t in weekday_titles:
        tid = t.get("titleId")
        if not tid or tid in all_raw:
            continue
        title = t.get("titleName", "") or t.get("title", "")
        quick_rofan = any(kw in title for kw in ["황후", "공작", "황제", "귀족", "황녀", "이세계", "환생", "회귀", "빙의", "왕", "전하"])
        if quick_rofan:
            all_raw[tid] = t
            confirmed_rofan.add(tid)
        else:
            info = fetch_title_info(tid)
            if is_rofan(t, info):
                all_raw[tid] = t
                confirmed_rofan.add(tid)
            time.sleep(0.2)

    print(f"\n총 로판 후보: {len(all_raw)}건 → start_date 수집 중...")

    records = []

    for i, (tid, item) in enumerate(all_raw.items()):
        if i % 100 == 0:
            print(f"  {i}/{len(all_raw)} 처리 중... (완료: {len(records)}건)")

        title = item.get("titleName", "") or item.get("title", "")
        author = item.get("author", "")
        rating = float(item.get("starScore", 0) or 0)
        is_finished = item.get("finish", False) or item.get("finished", False)
        ep_count = int(item.get("totalEpisodeCount", 0) or item.get("episodeCount", 0) or 0)

        start_date, start_date_source = fetch_start_date(tid)
        time.sleep(0.3)

        original_work_id = None
        for known_title, orig_id in KNOWN_ORIGINAL_MAP.items():
            if known_title in title:
                original_work_id = orig_id
                break

        complete_status = "completed" if is_finished else "ongoing"

        records.append({
            "work_id": f"nw_{tid}",
            "platform": "naver_webtoon",
            "content_type": "webtoon",
            "title": title,
            "author": author,
            "genre_raw": "로맨스판타지",
            "start_date": start_date,
            "start_date_source": start_date_source,
            "complete_status": complete_status,
            "complete_date": None,
            "rating": rating,
            "rating_count": 0,
            "bookmark_count": None,
            "episode_count": ep_count,
            "primary_metric": float(ep_count),
            "primary_metric_source": "episode_count",
            "tags": "",
            "original_work_id": original_work_id,
            "last_crawled_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        })

    df = pd.DataFrame(records)
    if df.empty:
        print("수집 결과 없음")
        return df

    df = df.drop_duplicates(subset=["work_id"])
    df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
    df = df.sort_values("start_date", ascending=False, na_position="last").reset_index(drop=True)

    out_path = "data/raw/naver_webtoon_works.csv"
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"\n저장 완료: {out_path} ({len(df)}행 x {len(df.columns)}열)")
    print(f"  start_date 범위: {df['start_date'].min()} ~ {df['start_date'].max()}")
    print(f"  start_date 누락: {df['start_date'].isna().sum()}건")
    print(f"  완결 여부:\n{df['complete_status'].value_counts().to_string()}")
    return df


if __name__ == "__main__":
    df = crawl_naver_webtoon()
    if not df.empty:
        print(df[["work_id", "title", "start_date", "complete_status", "episode_count"]].head(5).to_string())
