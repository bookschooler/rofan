"""
카카오페이지 로판 크롤러 v3 (장르 필터 방식)
- bff-page.kakao.com/api/gateway/view/v1/landing/genre 사용
- category_uid=11(웹소설), subcategory_uid=117(로판), screen_uid=84
- is_complete=false/true 각각 수집 (seen 집합 분리)
- badge 필드에서 완결 여부 보조 확인
- 24건/페이지, page=0부터 시작
- 총 약 21,181건 예상 (연재중 10,771 + 완결 10,410)
"""

import sys
import requests
import pandas as pd
import time
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding="utf-8")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://page.kakao.com/",
    "Origin": "https://page.kakao.com",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)

BFF_URL = "https://bff-page.kakao.com/api/gateway/view/v1/landing/genre"
OUT_PATH = "data/raw/kakaopage_works.csv"


def fetch_page(is_complete: bool, page: int) -> tuple[list[dict], int, bool]:
    params = {
        "category_uid": 11,
        "subcategory_uid": 117,
        "sort_type": "UPDATE",
        "is_complete": "true" if is_complete else "false",
        "screen_uid": 84,
        "page": page,
    }
    try:
        r = SESSION.get(BFF_URL, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        result = data.get("result", {})
        items = result.get("list", [])
        total = result.get("total_count", 0)
        is_end = result.get("is_end", True)
        return items, total, is_end
    except Exception as e:
        print(f"  [page {page}, is_complete={is_complete}] 오류: {e}")
        return [], 0, True


def parse_item(item: dict, fallback_status: str, now: str) -> dict:
    series_id = str(item.get("series_id", ""))
    badge = item.get("badge", "")
    # badge가 "완결"이면 completed, 아니면 루프에서 전달받은 fallback_status 사용
    if isinstance(badge, str) and "완결" in badge:
        complete_status = "completed"
    elif isinstance(badge, list) and any("완결" in str(b) for b in badge):
        complete_status = "completed"
    else:
        complete_status = fallback_status

    return {
        "work_id": f"kp_{series_id}",
        "platform": "kakaopage",
        "content_type": "novel",
        "title": item.get("title", ""),
        "author": "",
        "genre_raw": item.get("sub_category", "로판"),
        "start_date": None,
        "start_date_source": "unknown",
        "complete_status": complete_status,
        "complete_date": None,
        "rating": 0.0,
        "rating_count": 0,
        "bookmark_count": None,
        "view_count": None,
        "episode_count": 0,
        "primary_metric": 0.0,
        "primary_metric_source": "none",
        "tags": badge if isinstance(badge, str) else str(badge),
        "last_crawled_at": now,
    }


def collect_loop(label: str, is_complete: bool, status_str: str, now: str) -> list[dict]:
    """단일 is_complete 루프 수집. 독립 seen 집합 사용."""
    records = []
    seen = set()
    page = 0
    total = None

    print(f"\n[{label}] 수집 시작...")
    while True:
        items, t, is_end = fetch_page(is_complete, page)
        if total is None:
            total = t
            pages_est = (total + 23) // 24
            print(f"  [{label}] 총 {total}건 / 24건씩 약 {pages_est}페이지")

        new_count = 0
        for item in items:
            sid = str(item.get("series_id", ""))
            if sid and sid not in seen:
                seen.add(sid)
                records.append(parse_item(item, status_str, now))
                new_count += 1

        if page % 50 == 0 or is_end:
            print(f"  [{label}] page {page} → +{new_count}건 (누적 {len(records)}건)")

        if is_end or not items:
            break
        page += 1
        time.sleep(0.2)

    print(f"  [{label}] 완료: {len(records)}건")
    return records


def crawl_kakaopage() -> pd.DataFrame:
    print("=== 카카오페이지 장르 API 크롤링 시작 (subcategory_uid=117, 로판) ===")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    records_ongoing = collect_loop("연재중", False, "ongoing", now)
    records_completed = collect_loop("완결", True, "completed", now)

    # 두 결과 합치기
    all_records = records_ongoing + records_completed
    print(f"\n합산 전: 연재중 {len(records_ongoing)}건 + 완결 {len(records_completed)}건 = {len(all_records)}건")

    df = pd.DataFrame(all_records)
    if df.empty:
        print("수집 결과 없음")
        return df

    # 중복 work_id 처리: completed 우선 (완결이 더 확정적 정보)
    df_completed = df[df["complete_status"] == "completed"]
    df_ongoing = df[df["complete_status"] == "ongoing"]
    completed_ids = set(df_completed["work_id"])
    df_ongoing_only = df_ongoing[~df_ongoing["work_id"].isin(completed_ids)]
    df = pd.concat([df_completed, df_ongoing_only], ignore_index=True)
    df = df.reset_index(drop=True)

    df.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")

    print(f"\n=== 완료 ===")
    print(f"저장: {OUT_PATH} ({len(df)}행 x {len(df.columns)}열)")
    print(f"완결 여부:\n{df['complete_status'].value_counts().to_string()}")

    # 두 루프 간 중복 분석
    overlap = len(records_ongoing) + len(records_completed) - len(df)
    print(f"두 루프 간 중복 제거: {overlap}건")

    return df


if __name__ == "__main__":
    df = crawl_kakaopage()
    if not df.empty:
        print(df[["work_id", "title", "complete_status"]].head(10).to_string())
