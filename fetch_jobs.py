#!/usr/bin/env python3
"""고용24 채용공고를 가져와 시니어용으로 걸러 calculator/jobs.json 으로 저장.

인증키는 프로젝트 루트 .env 의 WORK24_AUTH_KEY (git에 안 올라감).
키가 없거나 --sample 이면 예시 데이터를 만든다(화면 확인용, sample: true 로 표시).

  python3 calculator/fetch_jobs.py            # 실제 API
  python3 calculator/fetch_jobs.py --sample   # 예시 데이터

브라우저에서 API를 직접 부르지 않는다: 키가 노출되고 CORS도 막힌다.
하루 한 번 이 스크립트로 jobs.json 을 갱신해 정적 사이트와 함께 올린다.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "jobs.json"
API = "https://www.work24.go.kr/cm/openApi/call/wk/callOpenApiSvcInfo210L01.do"
KST = timezone(timedelta(hours=9))

# 2026 최저임금 시급 10,320원 × 월 60시간 ≈ 62만 원: 이보다 적은 월급이면 60시간 미만일 가능성이 큼
MIN_MONTHLY_FOR_60H = 620_000


def load_key() -> str | None:
    key = os.environ.get("WORK24_AUTH_KEY")
    if key:
        return key.strip()
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("WORK24_AUTH_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def fetch_page(key: str, page: int, display: int = 100) -> ET.Element:
    params = {
        "authKey": key,
        "callTp": "L",
        "returnType": "XML",
        "startPage": page,
        "display": display,
        "pfPreferential": "B",  # 준고령자(50세 이상) 우대 공고
    }
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "pension-lab-jobs/0.1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return ET.fromstring(r.read())


def text(el: ET.Element, tag: str) -> str:
    v = el.findtext(tag)
    return (v or "").strip()


def to_int(s: str) -> int:
    try:
        return int(s.replace(",", "").strip())
    except ValueError:
        return 0


def normalize(w: ET.Element) -> dict:
    sal_tp = text(w, "salTpNm")  # 월급 / 시급 / 일급 / 연봉
    min_sal = to_int(text(w, "minSal"))
    max_sal = to_int(text(w, "maxSal"))
    monthly = None
    if "월" in sal_tp and min_sal:
        monthly = min_sal
    elif "연" in sal_tp and min_sal:
        monthly = min_sal // 12
    return {
        "id": text(w, "wantedAuthNo"),
        "title": text(w, "title"),
        "company": text(w, "company"),
        "industry": text(w, "indTpNm"),
        "region": text(w, "region"),
        "pay_type": sal_tp,
        "pay_text": text(w, "sal"),
        "min_pay": min_sal,
        "max_pay": max_sal,
        "monthly_wage": monthly,
        "holiday": text(w, "holidayTpNm"),
        "career": text(w, "career"),
        "closes": text(w, "closeDt"),
        "registered": text(w, "regDt"),
        "url": text(w, "wantedMobileInfoUrl") or text(w, "wantedInfoUrl"),
        "health_insurance": coverage(sal_tp, monthly),
    }


def coverage(pay_type: str, monthly: int | None) -> str:
    """회사 건강보험(월 60시간 이상) 가능성. 목록 API에 근무시간이 없어서 급여로 추정한다."""
    if monthly is not None:
        return "likely" if monthly >= MIN_MONTHLY_FOR_60H else "unlikely"
    return "check"


def from_api(key: str, pages: int) -> list[dict]:
    jobs: list[dict] = []
    for p in range(1, pages + 1):
        root = fetch_page(key, p)
        err = root.findtext("message") or root.findtext("error")
        if err and not root.findall("wanted"):
            raise SystemExit(f"API 오류: {err}")
        items = root.findall("wanted")
        jobs.extend(normalize(w) for w in items)
        if len(items) < 100:
            break
    return jobs


def sample() -> list[dict]:
    """화면 확인용 예시. 실제 회사가 아님."""
    rows = [
        ("아파트 관리사무소 경리 보조", "예시 관리(주)", "서울 노원구", "월급", 1_800_000, "주5일"),
        ("물류센터 입출고 검수 (오전)", "예시 로지스", "경기 이천시", "월급", 1_500_000, "주5일"),
        ("주민센터 민원 안내", "예시 시설관리", "서울 강서구", "시급", 10_320, "주5일"),
        ("요양원 시설 관리", "예시 실버케어", "인천 남동구", "월급", 2_100_000, "주5일"),
        ("학교 배움터지킴이", "예시 교육재단", "부산 해운대구", "월급", 900_000, "주5일"),
        ("편의점 야간 (주2일)", "예시 리테일", "대전 서구", "월급", 520_000, "기타"),
    ]
    out = []
    today = datetime.now(KST).date()
    for i, (title, co, region, pt, pay, hol) in enumerate(rows, 1):
        monthly = pay if pt == "월급" else None
        out.append({
            "id": f"SAMPLE-{i}", "title": title, "company": co, "industry": "",
            "region": region, "pay_type": pt,
            "pay_text": f"{pay:,}원" if pt == "시급" else f"{pay // 10000}만 원",
            "min_pay": pay, "max_pay": pay, "monthly_wage": monthly, "holiday": hol,
            "career": "관계없음", "closes": (today + timedelta(days=14 + i)).isoformat(),
            "registered": today.isoformat(), "url": "",
            "health_insurance": coverage(pt, monthly),
        })
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", action="store_true", help="예시 데이터로 jobs.json 생성")
    ap.add_argument("--pages", type=int, default=5, help="가져올 페이지 수 (페이지당 100건)")
    args = ap.parse_args()

    key = None if args.sample else load_key()
    if key:
        jobs, is_sample = from_api(key, args.pages), False
    else:
        if not args.sample:
            print("WORK24_AUTH_KEY 가 없어 예시 데이터로 만듭니다.", file=sys.stderr)
        jobs, is_sample = sample(), True

    data = {
        "updated": datetime.now(KST).isoformat(timespec="minutes"),
        "source": "고용24 채용정보 Open-API (50세 이상 우대 공고)",
        "sample": is_sample,
        "jobs": jobs,
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(jobs)}건 → {OUT.relative_to(ROOT)}" + (" (예시)" if is_sample else ""))


if __name__ == "__main__":
    main()
