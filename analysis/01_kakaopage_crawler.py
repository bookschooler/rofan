"""
카카오페이지 로판 크롤러 (requests + __NEXT_DATA__ 방식)
- 목록 페이지 __NEXT_DATA__에서 seriesId 추출
- 각 content 상세 페이지 __NEXT_DATA__로 상세 정보 수집
- start_date: content.startSaleDt (연재 시작일)
- bookmark/rating: serviceProperty.ratingCount, ratingSum
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import json
from datetime import datetime, timezone, timedelta

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://page.kakao.com/",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)

# 로판 관련 화면 ID 목록
SCREEN_IDS = [
    92,   # 로판 (메인)
    94,   # 실시간 랭킹
    63,   # 지금핫한
    85,   # 여성인기
    84,   # 장르전체
]


def extract_next_data(soup: BeautifulSoup) -> dict:
    tag = soup.find("script", id="__NEXT_DATA__")
    if not tag or not tag.string:
        return {}
    try:
        return json.loads(tag.string)
    except Exception:
        return {}


def collect_series_ids_from_screen(screen_id: int) -> set[str]:
    """화면 페이지에서 seriesId 목록 추출"""
    url = f"https://page.kakao.com/menu/10011/screen/{screen_id}"
    try:
        r = SESSION.get(url, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        data = extract_next_data(soup)
        text = json.dumps(data)
        ids = set(re.findall(r'"seriesId"\s*:\s*(\d+)', text))
        # href 링크에서도 추출
        link_ids = set(
            m.group(1)
            for a in soup.find_all("a", href=True)
            if (m := re.search(r"/content/(\d+)", a["href"]))
        )
        return ids | link_ids
    except Exception as e:
        print(f"  [screen {screen_id}] 오류: {e}")
        return set()


def parse_content_detail(series_id: str) -> dict | None:
    """
    상세 페이지 __NEXT_DATA__ → 스키마 변환
    핵심 필드:
      content.startSaleDt     → start_date (연재 시작일)
      content.lastSlideAddedDate → 최신 에피소드 날짜
      content.onIssue          → ongoing/completed
      serviceProperty.ratingCount, ratingSum → rating
      serviceProperty.wishCount → bookmark_count
    """
    url = f"https://page.kakao.com/content/{series_id}"
    try:
        r = SESSION.get(url, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        nd = extract_next_data(soup)
        if not nd:
            return None

        queries = nd.get("props", {}).get("pageProps", {}).get(
            "initialProps", {}
        ).get("dehydratedState", {}).get("queries", [])

        # contentHomeOverview 쿼리 탐색
        overview = None
        for q in queries:
            d = q.get("state", {}).get("data", {})
            if "contentHomeOverview" in d:
                overview = d["contentHomeOverview"]
                break

        if not overview:
            return None

        content = overview.get("content", {})
        svc = content.get("serviceProperty", {})

        # 로판 필터: subcategory 확인
        subcategory = content.get("subcategory", "")
        category_type = content.get("categoryType", "")
        if category_type != "Webnovel":
            return None  # 웹소설만

        # start_date: startSaleDt
        start_sale_raw = content.get("startSaleDt", "")
        start_date = None
        if start_sale_raw:
            m = re.match(r"(\d{4})-(\d{2})-(\d{2})", start_sale_raw)
            if m:
                start_date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

        # complete_date / status
        on_issue = content.get("onIssue", "")
        complete_status = "completed" if on_issue in ("End", "Fin", "Complete") else "ongoing"
        last_added_raw = content.get("lastSlideAddedDate", "")
        complete_date = None
        if complete_status == "completed" and last_added_raw:
            m2 = re.match(r"(\d{4})-(\d{2})-(\d{2})", last_added_raw)
            if m2:
                complete_date = f"{m2.group(1)}-{m2.group(2)}-{m2.group(3)}"

        # rating
        rating_count = int(svc.get("ratingCount", 0) or 0)
        rating_sum = int(svc.get("ratingSum", 0) or 0)
        rating = round(rating_sum / rating_count, 2) if rating_count > 0 else 0.0

        # bookmark (wishCount)
        bookmark_count = int(svc.get("wishCount", 0) or 0)

        # episode_count: freeSlideCount 이 아닌 총 회차는 별도 API 필요
        # 여기서는 lastSlideAddedDate로 에피소드 수 추정 생략 → 0
        episode_count = 0

        # primary_metric
        primary_metric = float(bookmark_count) if bookmark_count > 0 else float(rating_count)
        primary_metric_source = "bookmark_count" if bookmark_count > 0 else "rating_count"

        # tags
        tags_raw = content.get("tags") or []
        tags = ",".join(t.get("name", "") for t in tags_raw) if isinstance(tags_raw, list) else ""

        return {
            "work_id": f"kp_{series_id}",
            "platform": "kakaopage",
            "content_type": "novel",
            "title": content.get("title", ""),
            "author": content.get("authors", ""),
            "genre_raw": subcategory or "로판",
            "start_date": start_date,
            "start_date_source": "api_startSaleDt" if start_date else "unknown",
            "complete_status": complete_status,
            "complete_date": complete_date,
            "rating": rating,
            "rating_count": rating_count,
            "bookmark_count": bookmark_count,
            "episode_count": episode_count,
            "primary_metric": primary_metric,
            "primary_metric_source": primary_metric_source,
            "tags": tags,
            "last_crawled_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    except Exception as e:
        print(f"  [content {series_id}] 오류: {e}")
        return None


def crawl_kakaopage(target_count: int = 400) -> pd.DataFrame:
    print("=== 카카오페이지 크롤링 시작 ===")

    # 1. 여러 화면에서 seriesId 수집
    all_ids = set()
    for sid in SCREEN_IDS:
        print(f"  화면 {sid} 에서 ID 수집 중...")
        ids = collect_series_ids_from_screen(sid)
        all_ids |= ids
        print(f"  -> {len(ids)}개 (누적 {len(all_ids)}개)")
        time.sleep(0.8)

    print(f"\n총 고유 seriesId: {len(all_ids)}개")
    print(f"상세 페이지 수집 시작 (최대 {target_count}건)...")

    records = []
    failed = 0

    for i, sid in enumerate(sorted(all_ids)):
        if len(records) >= target_count:
            break
        if i % 20 == 0:
            print(f"  {i}/{len(all_ids)} 처리 중... (수집됨: {len(records)}건, 실패: {failed}건)")

        detail = parse_content_detail(sid)
        if detail:
            records.append(detail)
        else:
            failed += 1
        time.sleep(0.6)

    df = pd.DataFrame(records)
    if df.empty:
        print("수집 결과 없음")
        return df

    df = df.drop_duplicates(subset=["work_id"])
    df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
    df = df.sort_values("start_date", ascending=False, na_position="last").reset_index(drop=True)

    out_path = "data/raw/kakaopage_works.csv"
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"\n저장 완료: {out_path} ({len(df)}행 x {len(df.columns)}열)")
    print(f"  start_date 범위: {df['start_date'].min()} ~ {df['start_date'].max()}")
    print(f"  start_date 누락: {df['start_date'].isna().sum()}건")
    print(f"  완결 여부:\n{df['complete_status'].value_counts().to_string()}")
    print(f"  평균 평점: {df['rating'].mean():.2f}")
    return df


if __name__ == "__main__":
    df = crawl_kakaopage(target_count=400)
    if not df.empty:
        print(df[["work_id", "title", "start_date", "rating", "bookmark_count", "complete_status"]].head(5).to_string())
