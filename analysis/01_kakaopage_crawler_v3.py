"""
카카오페이지 로판 크롤러 v3 (landing/genre API)
- bff-page.kakao.com/api/gateway/view/v1/landing/genre
- subcategory_uid=117 (로판), category_uid=11 (웹소설)
- sort_type: UPDATE + PRODUCT_LATEST 두 가지 수집 후 중복 제거
- is_complete: false(연재중) + true(완결) 각각 수집
- start_sale_dt 포함 → start_date 직접 수집 가능
- 예상 수집: 15,000~20,000건 (중복 제거 후)
"""

import sys
import requests
import pandas as pd
import time
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://page.kakao.com/",
    "Origin": "https://page.kakao.com",
}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

BASE = "https://bff-page.kakao.com/api/gateway/view/v1/landing/genre"
OUT_PATH = "data/raw/kakaopage_works.csv"
CHECKPOINT_PATH = "data/raw/kakaopage_v3_checkpoint.pkl"


def fetch_page(sort_type: str, is_complete: bool, page: int) -> tuple[list[dict], bool]:
    params = {
        "category_uid": 11,
        "subcategory_uid": 117,
        "sort_type": sort_type,
        "is_complete": "true" if is_complete else "false",
        "screen_uid": 84,
        "page": page,
    }
    for attempt in range(3):
        try:
            r = SESSION.get(BASE, params=params, timeout=20)
            r.raise_for_status()
            d = r.json().get("result", {})
            return d.get("list", []), d.get("is_end", True)
        except Exception as e:
            if attempt == 2:
                print(f"  [오류] sort={sort_type} is_complete={is_complete} page={page}: {e}")
            time.sleep(2)
    return [], True


def parse_item(item: dict, now: str) -> dict:
    series_id = str(item.get("series_id", ""))
    on_issue = item.get("on_issue", "N")
    complete_status = "ongoing" if on_issue == "Y" else "completed"

    start_raw = item.get("start_sale_dt", "") or ""
    start_date = start_raw[:10] if start_raw else None

    last_raw = item.get("last_slide_added_dt", "") or ""
    complete_date = last_raw[:10] if (complete_status == "completed" and last_raw) else None

    svc = item.get("service_property", {}) or {}
    view_count = int(svc.get("view_count", 0) or 0)

    return {
        "work_id": f"kp_{series_id}",
        "platform": "kakaopage",
        "content_type": "novel",
        "title": item.get("title", ""),
        "author": item.get("authors", ""),
        "genre_raw": item.get("sub_category", "로판"),
        "start_date": start_date,
        "start_date_source": "api_start_sale_dt" if start_date else "unknown",
        "complete_status": complete_status,
        "complete_date": complete_date,
        "rating": 0.0,
        "rating_count": 0,
        "bookmark_count": None,
        "view_count": view_count,
        "episode_count": 0,
        "primary_metric": float(view_count),
        "primary_metric_source": "view_count",
        "tags": "",
        "last_crawled_at": now,
    }


def crawl_segment(sort_type: str, is_complete: bool, seen: set, now: str) -> list[dict]:
    label = f"{sort_type}/{'완결' if is_complete else '연재중'}"
    records = []
    page = 1
    consecutive_empty = 0

    while True:
        items, is_end = fetch_page(sort_type, is_complete, page)

        if not items:
            consecutive_empty += 1
            if consecutive_empty >= 3 or is_end:
                print(f"  [{label}] 종료 (page={page}, 빈페이지={consecutive_empty})")
                break
        else:
            consecutive_empty = 0
            new_count = 0
            for item in items:
                sid = str(item.get("series_id", ""))
                if sid and sid not in seen:
                    seen.add(sid)
                    records.append(parse_item(item, now))
                    new_count += 1

        if page % 50 == 0:
            print(f"  [{label}] page {page} | 신규 누적: {len(records)}건")

        if is_end:
            print(f"  [{label}] is_end=True → 종료 (page={page})")
            break

        page += 1
        time.sleep(0.25)

    print(f"  [{label}] 완료: {len(records)}건 신규")
    return records


def crawl_kakaopage() -> pd.DataFrame:
    print("=== 카카오페이지 로판 전체 크롤링 v3 ===")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    seen = set()
    all_records = []

    combos = [
        ("UPDATE",          False),
        ("UPDATE",          True),
        ("PRODUCT_LATEST",  False),
        ("PRODUCT_LATEST",  True),
    ]

    for sort_type, is_complete in combos:
        print(f"\n[{sort_type} / {'완결' if is_complete else '연재중'}] 시작...")
        records = crawl_segment(sort_type, is_complete, seen, now)
        all_records.extend(records)
        print(f"  현재 총 고유 작품: {len(all_records):,}건")
        time.sleep(1)

    df = pd.DataFrame(all_records)
    if df.empty:
        print("수집 결과 없음")
        return df

    df = df.drop_duplicates(subset=["work_id"]).reset_index(drop=True)
    df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
    df = df.sort_values("start_date", ascending=False, na_position="last").reset_index(drop=True)

    df.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")

    print(f"\n=== 완료 ===")
    print(f"저장: {OUT_PATH} ({len(df):,}행 x {len(df.columns)}열)")
    print(f"complete_status:\n{df['complete_status'].value_counts().to_string()}")
    print(f"start_date 보유: {df['start_date'].notna().sum():,}건 ({df['start_date'].notna().mean()*100:.0f}%)")
    print(f"start_date 범위: {df['start_date'].min()} ~ {df['start_date'].max()}")
    print(f"view_count > 0: {(df['primary_metric'] > 0).sum():,}건")
    print(f"view_count 중앙값: {df['primary_metric'].median():,.0f}")
    return df


if __name__ == "__main__":
    df = crawl_kakaopage()
    if not df.empty:
        print(df[["work_id", "title", "start_date", "complete_status", "primary_metric"]].head(10).to_string())
