"""
네이버 시리즈 로판(genreCode=207) 크롤러 — 전체 수집
- isFinished 구분 없이 단일 순회로 전체 작품 수집 (중복 방지)
- orderTypeCode=new 기준, 빈 페이지가 나오면 자동 종료
- start_date: 목록 수집 후 01_naver_series_enrich_startdate.py 로 별도 보강
  (volumeList.series → resultData[0].lastVolumeUpdateDate[:10])
- primary_metric: episode_count
"""

import sys
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding="utf-8")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://series.naver.com/",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)

BASE_URL = "https://series.naver.com/novel/categoryProductList.series"


def fetch_list_page(page: int, is_finished: bool = False) -> list[dict]:
    """
    장르 목록 페이지 파싱
    is_finished: True=완결, False=연재중
    """
    params = {
        "categoryTypeCode": "genre",
        "genreCode": "207",
        "orderTypeCode": "new",
        "isFinished": "true" if is_finished else "false",
        "page": page,
    }
    try:
        resp = SESSION.get(BASE_URL, params=params, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        items = []
        for li in soup.select("ul.lst_list li"):
            try:
                title_a = li.select_one("h3 a") or li.select_one(".title a")
                if not title_a:
                    continue
                title = re.sub(r"\s*\([^)]+화[^)]*\)", "", title_a.get_text(strip=True)).strip()
                href = title_a.get("href", "")
                product_no_m = re.search(r"productNo=(\d+)", href)
                product_no = product_no_m.group(1) if product_no_m else ""
                if not product_no:
                    continue

                full_text = li.get_text(" ", strip=True)

                ep_match = re.search(r"(\d+)화/", full_text)
                episode_count = int(ep_match.group(1)) if ep_match else 0

                if is_finished:
                    complete_status = "completed"
                elif "완결" in full_text and "미완결" not in full_text:
                    complete_status = "completed"
                elif "미완결" in full_text:
                    complete_status = "ongoing"
                else:
                    complete_status = "unknown"

                rating_m = re.search(r"평점\s*([\d.]+)", full_text)
                rating = float(rating_m.group(1)) if rating_m else 0.0

                parts = re.split(r"\s*\|\s*", full_text)
                author = ""
                for i, p in enumerate(parts):
                    if "평점" in p and i + 1 < len(parts):
                        author = parts[i + 1].strip()
                        break

                items.append({
                    "product_no": product_no,
                    "title": title,
                    "author": author,
                    "rating": rating,
                    "episode_count": episode_count,
                    "complete_status": complete_status,
                })
            except Exception:
                continue

        return items
    except Exception as e:
        print(f"  [{'완결' if is_finished else '연재중'} page {page}] 오류: {e}")
        return []


def crawl_naver_series() -> pd.DataFrame:
    print("=== 네이버 시리즈 전체 수집 시작 ===")
    print("  연재중 + 완결 각각 순회 후 통합 (중복 제거)")

    seen = set()
    all_items = []

    for label, is_finished in [("연재중", False), ("완결", True)]:
        page = 1
        consecutive_empty = 0
        while True:
            if page % 50 == 1:
                print(f"  [{label}] 페이지 {page} 수집 중... (누적 {len(all_items)}건)")
            items = fetch_list_page(page, is_finished=is_finished)
            if not items:
                consecutive_empty += 1
                if consecutive_empty >= 3:
                    print(f"  [{label}] 연속 빈 페이지 3회 → 종료 (마지막 페이지: {page})")
                    break
            else:
                consecutive_empty = 0
                new_count = 0
                for item in items:
                    pno = item["product_no"]
                    if pno and pno not in seen:
                        seen.add(pno)
                        all_items.append(item)
                        new_count += 1
                if new_count == 0 and page > 10:
                    print(f"  [{label}] 신규 항목 없음 → 종료 (페이지: {page})")
                    break
            page += 1
            time.sleep(0.5)

        print(f"  [{label}] 수집 완료. 현재 누적: {len(all_items)}건")

    print(f"\n총 고유 작품: {len(all_items)}건")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    records = []
    for item in all_items:
        ep_count = item["episode_count"]
        records.append({
            "work_id": f"ns_{item['product_no']}",
            "platform": "naver_series",
            "content_type": "novel",
            "title": item["title"],
            "author": item["author"],
            "genre_raw": "로판",
            "start_date": None,
            "start_date_source": "unknown",
            "complete_status": item["complete_status"],
            "complete_date": None,
            "rating": item["rating"],
            "rating_count": 0,
            "bookmark_count": None,
            "episode_count": ep_count,
            "primary_metric": float(ep_count),
            "primary_metric_source": "episode_count",
            "tags": "",
            "last_crawled_at": now,
        })

    df = pd.DataFrame(records)
    if df.empty:
        print("수집 결과 없음")
        return df

    df = df.drop_duplicates(subset=["work_id"]).reset_index(drop=True)

    out_path = "data/raw/naver_series_works.csv"
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"\n저장 완료: {out_path} ({len(df)}행 x {len(df.columns)}열)")
    print(f"  완결 여부 분포:\n{df['complete_status'].value_counts().to_string()}")
    print(f"  평균 에피소드 수: {df['episode_count'].mean():.1f}")
    print(f"  start_date 수집 가능 비율: 0% (JS-only, unknown 처리)")
    return df


if __name__ == "__main__":
    df = crawl_naver_series()
    if not df.empty:
        print(df[["work_id", "title", "author", "rating", "episode_count", "complete_status"]].head(5).to_string())
