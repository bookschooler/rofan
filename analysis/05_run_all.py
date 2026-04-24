"""
전체 분석 파이프라인 실행 스크립트
실행: python analysis/05_run_all.py

순서: 02_01 → 02_02 → 02_03 → 03_01 → 03_02 → 04_01
"""

import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPTS  = [
    "analysis/02_01_timeseries.py",
    "analysis/02_02_stl.py",
    "analysis/02_03_pelt.py",
    "analysis/03_01_its.py",
    "analysis/03_02_its_by_platform.py",
    "analysis/04_01_prophet.py",
]

print("=" * 60)
print("로판 분석 전체 파이프라인 실행")
print("=" * 60)

results = []
for script in SCRIPTS:
    path = BASE_DIR / script
    print(f"\n▶ {script}")
    start = time.time()
    result = subprocess.run(
        [sys.executable, str(path)],
        capture_output=True, text=True, cwd=str(BASE_DIR)
    )
    elapsed = time.time() - start
    status  = "PASS" if result.returncode == 0 else "FAIL"
    results.append((script, status, elapsed))
    print(f"  {status} ({elapsed:.1f}s)")
    if result.returncode != 0:
        print(f"  ERROR:\n{result.stderr[-500:]}")
        sys.exit(1)

print("\n" + "=" * 60)
print("파이프라인 완료 요약")
print("=" * 60)
for s, st, t in results:
    print(f"  {st}  {s:<45} ({t:.1f}s)")
print(f"\n  총 소요시간: {sum(t for _,_,t in results):.1f}s")
