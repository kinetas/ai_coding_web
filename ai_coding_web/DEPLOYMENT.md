## 운영 배포 가이드

이 문서는 현재 프로젝트를 "배포만 하면 되는 상태"로 운영하기 위해, 무엇을 어떤 순서로 해야 하는지 정리한 가이드입니다.

## 추천 구성

- 프론트 배포 사이트: `Cloudflare Pages`, `Netlify`, `Vercel` 중 하나
- 백엔드 배포 사이트: `Render`, `Railway`, `Fly.io`, `AWS App Runner` 중 하나
- 데이터베이스: `PostgreSQL`
- ETL 스케줄링:
  - 가장 쉬움: `GitHub Actions`의 `schedule`
  - 운영형: 배포 플랫폼의 `Cron Job` 또는 `AWS EventBridge`

## 실제로 필요한 프로그램/서비스

- 개발/배포 준비
  - `Python 3.11+`
  - `Git`
  - 선택: `Docker Desktop`
- DB
  - 로컬 테스트용: `SQLite` 기본 지원
  - 운영용: `Supabase`, `Neon`, `Railway Postgres`, `AWS RDS`
- 프론트 정적 호스팅
  - `Cloudflare Pages` 또는 `Netlify` 권장
- 백엔드 호스팅
  - `Render` 권장

## 가장 쉬운 배포 조합

복잡한 인프라를 직접 구성하지 않으려면 아래 조합이 가장 단순합니다.

1. 프론트: `Cloudflare Pages`
2. 백엔드: `Render Web Service`
3. DB: `Supabase Postgres`
4. ETL 스케줄: `GitHub Actions schedule`

## 로컬에서 먼저 확인하는 순서

1. `.env.example`을 복사해서 `.env` 또는 배포 환경변수로 준비합니다.
2. 최소한 아래 값은 먼저 정합니다.
   - `DATABASE_URL`
   - `CORS_ALLOWED_ORIGINS`
   - `ETL_SHARED_SECRET`
3. 백엔드 의존성을 설치합니다.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

4. DB를 초기화합니다.

```bash
python -m backend.app.init_db
```

5. 백엔드를 실행합니다.

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

6. 프론트 설정 파일 `frontend/assets/js/config.js` 의 `apiBase`가 백엔드 주소를 가리키는지 확인합니다.
7. 정적 서버로 프론트를 실행합니다.

```bash
cd frontend
python -m http.server 5500
```

8. 브라우저에서 `http://127.0.0.1:5500/index.html` 로 접속합니다.
9. 로그인 페이지에서 아래 중 하나로 접근합니다.
   - 새 계정 직접 회원가입
   - 기본 데모 계정: `demo@et.ai / etl1234`

## 운영 배포 순서

### 1. DB부터 만든다

- 운영용 Postgres를 먼저 생성합니다.
- 발급받은 접속 문자열을 `DATABASE_URL`에 넣습니다.

예시:

```env
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME
```

### 2. 백엔드를 배포한다

- `Render` 또는 다른 Python 호스팅에 이 프로젝트를 연결합니다.
- Docker 배포가 가능하면 루트 `Dockerfile`을 그대로 사용합니다.
- 필수 환경변수를 설정합니다.

필수 환경변수:

```env
APP_ENV=production
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME
CORS_ALLOWED_ORIGINS=https://your-frontend-domain.com
AUTH_COOKIE_SECURE=true
AUTH_COOKIE_SAMESITE=none
ETL_SHARED_SECRET=strong-random-secret
AUTH_SEED_DEMO_USER=false
```

주의:
- 프론트와 API 도메인이 다르면 쿠키 전달을 위해 `AUTH_COOKIE_SAMESITE=none` 이 필요할 수 있습니다.
- 이 경우 HTTPS가 반드시 필요하며 `AUTH_COOKIE_SECURE=true` 여야 합니다.

### 3. 프론트를 배포한다

- `frontend/` 폴더를 정적 호스팅에 올립니다.
- `frontend/assets/js/config.js` 의 `apiBase`를 운영 API 주소로 바꿉니다.

예시:

```javascript
window.ET_APP_CONFIG = {
  apiBase: "https://api.your-domain.com"
};
```

### 4. CORS를 맞춘다

- 백엔드 `CORS_ALLOWED_ORIGINS`에는 실제 프론트 도메인만 넣습니다.
- 예:

```env
CORS_ALLOWED_ORIGINS=https://app.your-domain.com
```

### 5. ETL을 연결한다

- ETL은 `etl_demo.py` 를 스케줄러에서 실행하면 됩니다.
- 이 스크립트는 `ETL_SHARED_SECRET` 을 `X-ETL-Token` 헤더로 보내므로, 운영에서도 바로 사용할 수 있습니다.

수동 실행 예시:

```bash
ET_API_BASE=https://api.your-domain.com
ETL_SHARED_SECRET=strong-random-secret
python etl_demo.py
```

Windows PowerShell 예시:

```powershell
$env:ET_API_BASE="https://api.your-domain.com"
$env:ETL_SHARED_SECRET="strong-random-secret"
python etl_demo.py
```

### 6. ETL 스케줄러를 붙인다

가장 쉬운 방법:
- `GitHub Actions`에서 매시간 또는 매일 실행
- 이미 예시 워크플로 파일 `.github/workflows/etl-demo.yml` 이 포함되어 있음

운영형 방법:
- `Render Cron Job`
- `Railway Scheduled Job`
- `AWS EventBridge + ECS/App Runner Job`

## 가장 쉬운 운영 체크 순서

1. `GET /api/health` 가 정상인지 확인
2. 회원가입이 되는지 확인
3. 로그인 후 `내 분석 만들기` 접근이 되는지 확인
4. `내 분석 저장` 후 `내 분석 보기`에 보이는지 확인
5. `python etl_demo.py` 실행 후 메인/분석1 데이터가 바뀌는지 확인
6. 브라우저 새로고침 후에도 저장한 분석이 유지되는지 확인
7. 서버 재시작 후에도 데이터가 유지되는지 확인

## 권장 배포 순서 요약

1. Postgres 만든다
2. `DATABASE_URL` 발급받는다
3. 백엔드 배포한다
4. 백엔드 환경변수 넣는다
5. 프론트 `config.js`에 운영 API 주소 넣는다
6. 프론트 정적 배포한다
7. 회원가입/로그인 테스트한다
8. ETL 토큰 넣고 `etl_demo.py` 수동 실행한다
9. GitHub Actions 또는 Cron Job으로 ETL 자동화한다
10. 도메인/CORS/쿠키 설정을 최종 점검한다

## 추천 결론

빠르게 운영하려면 아래처럼 가는 것이 가장 쉽습니다.

- 프론트: `Cloudflare Pages`
- 백엔드: `Render`
- DB: `Supabase Postgres`
- ETL: `GitHub Actions schedule`

이 조합은 초기 비용과 설정 난도가 낮고, 지금 프로젝트 구조와도 가장 잘 맞습니다.
