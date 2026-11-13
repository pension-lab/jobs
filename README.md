# 연금랩 · 건보료 계산기와 시니어 일자리

- `index.html` — 퇴직 후 지역 건보료 vs 일할 때(직장가입자) 건보료 비교 계산기 (2026년 기준)
- `jobs.html` — 고용24 채용정보 Open-API의 50세 이상 우대 공고 목록, 공고별 건보료 계산 연결
- `fetch_jobs.py` — 공고 수집 (`WORK24_AUTH_KEY` 필요, 없으면 `--sample`)

매일 06:00(KST) GitHub Actions가 공고를 새로 받아 GitHub Pages로 배포한다.
인증키는 저장소 Settings → Secrets and variables → Actions 의 `WORK24_AUTH_KEY` 에 둔다.

공고 출처: 고용24. 계산 결과는 참고용 추정치.
