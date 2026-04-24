"""
네이버 시리즈 start_date 보강 스크립트
- volumeList.series?productNo={id} → resultData[0].lastVolumeUpdateDate
- 기존 naver_series_works.csv에 start_date 채워넣기
- 중단 후 재시작 가능 (체크포인트 저장)
"""

import sys
import requests
import pandas as pd
import json
import time
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://series.naver.com/",
}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

CSV_PATH = "data/raw/naver_series_works.csv"
CHECKPOINT_PATH = "data/raw/naver_series_startdate_checkpoint.csv"


def fetch_start_date(product_no: str) -> tuple[str | None, str]:
    """volumeList episode1 lastVolumeUpdateDate → start_date"""
    url = f"https://series.naver.com/novel/volumeList.series?productNo={product_no}"
    try:
        r = SESSION.get(url, timeout=10)
        if r.status_code != 200 or not r.text.strip():
            return None, "api_error"
        items = json.loads(r.text).get("resultData", [])
        if items:
            raw = items[0].get("lastVolumeUpdateDate", "")
            if raw:
                return raw[:10], "volumeList_ep1"
        return None, "no_episode"
    except Exception:
        return None, "exception"


def enrich_start_dates():
    df = pd.read_csv(CSV_PATH)
    total = len(df)
    print(f"=== start_date 보강 시작: {total}건 ===")
    print(f"  예상 시간: 약 {total * 0.5 / 3600:.1f}시간")

    # 체크포인트 로드 (중단 재시작용)
    if Path(CHECKPOINT_PATH).exists():
        initial_cp = pd.read_csv(CHECKPOINT_PATH)
        done_ids = set(initial_cp["work_id"])
        print(f"  체크포인트 발견: {len(done_ids)}건 이미 처리됨 → 이어서 진행")
    else:
        initial_cp = pd.DataFrame(columns=["work_id", "start_date", "start_date_source"])
        done_ids = set()

    results = []
    processed = 0
    failed = 0

    for idx, row in df.iterrows():
        work_id = row["work_id"]

        # 이미 처리됐으면 스킵
        if work_id in done_ids:
            continue

        product_no = work_id.replace("ns_", "")
        start_date, source = fetch_start_date(product_no)

        results.append({"work_id": work_id, "start_date": start_date, "start_date_source": source})
        processed += 1

        if start_date is None:
            failed += 1

        if processed % 200 == 0:
            elapsed_min = processed * 0.5 / 60
            remain_min = (total - len(done_ids) - processed) * 0.5 / 60
            print(f"  [{processed}/{total - len(done_ids)}] 날짜 수집됨: {processed - failed}건 / 실패: {failed}건"
                  f" | 경과: {elapsed_min:.0f}분 | 남은 예상: {remain_min:.0f}분")

            # 체크포인트 저장 (기존 + 신규 합산, 메모리 기반)
            cp_combined = pd.concat(
                [initial_cp, pd.DataFrame(results)], ignore_index=True
            ).drop_duplicates("work_id")
            cp_combined.to_csv(CHECKPOINT_PATH, index=False, encoding="utf-8-sig")

        time.sleep(0.4)

    # 최종 체크포인트 저장
    cp_final = pd.concat(
        [initial_cp, pd.DataFrame(results)], ignore_index=True
    ).drop_duplicates("work_id")
    cp_final.to_csv(CHECKPOINT_PATH, index=False, encoding="utf-8-sig")

    # 최종 CSV 업데이트
    all_dates = pd.read_csv(CHECKPOINT_PATH) if Path(CHECKPOINT_PATH).exists() else pd.DataFrame(results)
    df_final = pd.read_csv(CSV_PATH)
    df_final = df_final.drop(columns=["start_date", "start_date_source"], errors="ignore")
    df_final = df_final.merge(all_dates[["work_id", "start_date", "start_date_source"]], on="work_id", how="left")
    df_final["start_date"] = pd.to_datetime(df_final["start_date"], errors="coerce")
    df_final = df_final.sort_values("start_date", ascending=False, na_position="last").reset_index(drop=True)

    df_final.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"\n=== 완료 ===")
    print(f"저장: {CSV_PATH} ({len(df_final)}행)")
    print(f"start_date 수집됨: {df_final['start_date'].notna().sum()}건 / {len(df_final)}건")
    print(f"start_date 범위: {df_final['start_date'].min()} ~ {df_final['start_date'].max()}")


if __name__ == "__main__":
    enrich_start_dates()
