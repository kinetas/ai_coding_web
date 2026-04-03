# detail.md — Cloudflare Pages(프론트) + Render(백엔드) 상세 배포 순서

이 문서는 `DEPLOYMENT.md`의 “가장 쉬운 배포 조합”을 그대로 따르되, **Cloudflare Pages에서 프론트를 어떻게 올리는지**, **Render에서 백엔드를 어떻게 올리는지**를 “클릭/입력 단위”로 더 자세히 풀어쓴 실전 가이드입니다.

이 프로젝트 구조(중요)

- 프론트는 **정적 HTML/CSS/JS** 입니다. `frontend/` 폴더를 그대로 정적 호스팅에 올리면 됩니다.
- 백엔드는 **FastAPI** 입니다. Render에서 실행되면 API는 `https://.../api/*` 로 노출됩니다.
- 인증은 **쿠키 기반 세션**입니다.
  - 프론트의 `fetch`는 기본적으로 `credentials: "include"`를 사용합니다. (즉, 백엔드가 세션 쿠키를 제대로 내려주고 브라우저가 쿠키를 보내도록 CORS/쿠키 옵션이 맞아야 합니다.)
- 프론트의 API 주소는 `frontend/assets/js/config.js`의 `window.ET_APP_CONFIG.apiBase`가 기준입니다.

---

## 0) 배포 전에 먼저 정할 것(필수 체크리스트)

- **프론트 도메인(Cloudflare Pages)**: 예) `https://myapp.pages.dev` 또는 커스텀 도메인 `https://app.example.com`
- **백엔드 도메인(Render)**: 예) `https://myapp-api.onrender.com`
- **DB(Postgres) 연결 문자열**: Supabase/Neon/Railway 등에서 발급
- **ETL 토큰(선택)**: `ETL_SHARED_SECRET` (랜덤 문자열)

---

## 1) DB부터 만든다 (운영: Postgres 권장)

로컬 SQLite도 되지만 운영은 Postgres 권장입니다.

### 1-1. Supabase(예시)에서 Postgres 생성

1. Supabase에서 프로젝트 생성
2. `Project Settings` → `Database` → 연결 문자열(Connection string) 확인
3. 이 프로젝트는 SQLAlchemy + psycopg를 쓰므로 보통 아래 형태를 권장합니다.

- **권장 형태**

  - `postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME`

- **자주 필요한 옵션(서비스에 따라)**

  - SSL이 강제면: `?sslmode=require`
  - 예: `postgresql+psycopg://.../DBNAME?sslmode=require`

> 팁: 서비스가 `postgresql://...`만 제공하더라도 대부분 동작하지만, 문서/예시는 `postgresql+psycopg://`를 권장합니다. (문제 생기면 이 형태로 바꾸는 게 가장 빠른 해결책입니다.)

---

## 2) Render에 백엔드 올리기 (Docker 방식 권장)

이 저장소 루트에 `Dockerfile`이 있고, 컨테이너 시작 시 자동으로 `python -m backend.app.init_db`를 실행한 뒤 `uvicorn`을 띄웁니다.

### 2-1. Render Web Service 생성 (Docker)

1. Render 로그인
2. `New` → `Web Service`
3. GitHub 저장소 연결(처음이면 GitHub 연동)
4. 해당 repo 선택
5. 설정 화면에서 아래처럼 선택
   - **Environment**: `Docker`
   - **Branch**: 배포할 브랜치(보통 `main`)
   - **Root Directory**: 비워둠(루트에 `Dockerfile`이 있음)
   - **Region/Plan**: 원하는 것으로 선택

### 2-2. Render 환경변수(Environment Variables) 설정 (중요)

Render 서비스의 `Environment` 탭(또는 생성 과정의 env 섹션)에서 아래를 설정합니다.

필수(운영 기준):

- `APP_ENV=production`
- `DATABASE_URL=...` (1번에서 만든 Postgres DSN)
- `CORS_ALLOWED_ORIGINS=...` (프론트 도메인 정확히)
- `ETL_SHARED_SECRET=...` (ETL 쓸 거면 필수, 안 쓰면 빈 값도 가능)

쿠키/로그인(프론트와 백엔드 도메인이 다르면 사실상 필수):

- `AUTH_COOKIE_SECURE=true`
- `AUTH_COOKIE_SAMESITE=none`

데모 계정 시드(원하면 켜고, 원치 않으면 끔):

- `AUTH_SEED_DEMO_USER=false` (운영에서 데모 계정 자동 생성이 싫으면 false)

예시(프론트가 Cloudflare Pages, 백엔드가 Render인 전형적인 케이스):

```env
APP_ENV=production
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME?sslmode=require

# Cloudflare Pages 도메인(정확히 "https://도메인" 형태, 슬래시/와일드카드 없이)
CORS_ALLOWED_ORIGINS=https://myapp.pages.dev

# 쿠키 기반 세션(크로스 사이트면 None+Secure 필요)
AUTH_COOKIE_SECURE=true
AUTH_COOKIE_SAMESITE=none

# ETL(선택)
ETL_SHARED_SECRET=strong-random-secret

# 데모 계정 시드(선택)
AUTH_SEED_DEMO_USER=false
```

주의(가장 흔한 실패 원인):

- `CORS_ALLOWED_ORIGINS`는 **콤마로 구분된 정확한 origin 목록**입니다.
  - 예: `https://app.example.com,https://staging-app.example.com`
  - `https://app.example.com/` 처럼 **끝에 슬래시**를 넣지 마세요.
  - `*` 와일드카드는 이 프로젝트 설정(쿠키 포함)과 같이 쓰기 어렵습니다.
- 프론트/백엔드가 다른 도메인이면 브라우저가 쿠키를 차단할 수 있으니,
  - `AUTH_COOKIE_SAMESITE=none`
  - `AUTH_COOKIE_SECURE=true`
  - 프론트/백엔드 모두 HTTPS
  - CORS에서 `allow_credentials=True` (이미 코드에 설정됨)
  - 위 조건이 같이 맞아야 정상 로그인됩니다.

### 2-3. 배포/기동 확인

Render가 빌드/배포를 마치면 서비스 URL이 생깁니다.

1. 헬스 체크 확인
   - `GET https://<render-domain>/api/health`
2. CORS 사전 확인(브라우저에서 프론트 도메인으로 접근했을 때 호출이 되는지)
3. 로그인/회원가입 API 확인(프론트 붙이기 전에 Postman/브라우저 콘솔로 테스트해도 됨)

---

## 3) Cloudflare Pages에 프론트 올리기 (정적 호스팅)

이 프로젝트 프론트는 빌드가 필요 없는 정적 사이트입니다. 핵심은 **배포 대상 디렉터리를 `frontend/`로 지정**하고, **프론트가 호출할 API 주소(apiBase)를 운영 백엔드 주소로 바꾸는 것**입니다.

### 3-1. 먼저 프론트의 API 주소를 운영용으로 설정

파일: `frontend/assets/js/config.js`

현재 기본값은 로컬(`http://127.0.0.1:8000`)입니다. 운영에서는 Render URL로 바꿔야 합니다.

예:

```javascript
window.ET_APP_CONFIG = {
  apiBase: "https://myapp-api.onrender.com"
};
```

> 운영/로컬을 동시에 편하게 쓰고 싶다면(선택):
> - 가장 단순: `config.js`는 로컬로 두고, 운영용 브랜치에서만 운영 apiBase로 바꿔 배포
> - 또는: Cloudflare Pages의 “Preview(브랜치)” 배포를 활용해 `main`은 운영, 다른 브랜치는 테스트로 사용

### 3-2. Cloudflare Pages 프로젝트 생성

1. Cloudflare 대시보드 → `Workers & Pages` → `Pages`
2. `Create a project` → Git 연결(GitHub 연동)
3. 저장소 선택

### 3-3. 빌드 설정(정적)

Cloudflare Pages 설정 화면에서 아래 중 하나로 맞추면 됩니다. (UI가 바뀌어도 핵심은 “결과물 디렉터리가 `frontend/`”입니다.)

권장 설정(가장 단순):

- **Framework preset**: `None` (또는 “Static”에 해당하는 옵션)
- **Build command**: 비워두기(가능하면) 또는 `echo "no build"`
- **Build output directory**: `frontend`
- **Root directory**: 비워두기

대안(루트 디렉터리로 `frontend`를 지정하는 UI인 경우):

- **Root directory**: `frontend`
- **Build output directory**: `.` 또는 `./` (UI가 허용하는 값)
- **Build command**: 비워두기 또는 `echo "no build"`

### 3-4. 배포 후 접속 확인

배포가 끝나면 Pages 도메인이 생성됩니다.

- `https://<project>.pages.dev/index.html` 접속
- 내비게이션 링크로 각 페이지 이동 확인

> 팁: 이 프로젝트는 `index.html`, `login.html`, `analysis-1.html` 처럼 “여러 HTML 파일” 구조입니다. SPA 라우팅(모든 경로를 index로 리라이트) 설정이 보통 필요 없습니다.

---

## 4) 프론트 ↔ 백엔드 연동 최종 점검(가장 중요)

### 4-1. CORS와 쿠키(로그인) 성공 조건 요약

프론트와 백엔드가 다른 도메인이면 아래가 모두 맞아야 합니다.

- 프론트 JS 요청은 `credentials: "include"`여야 함 (이미 적용됨)
- 백엔드는 CORS에서 `allow_credentials=True`여야 함 (이미 적용됨)
- 백엔드 환경변수
  - `CORS_ALLOWED_ORIGINS`에 **프론트 도메인**을 정확히 넣기
  - `AUTH_COOKIE_SAMESITE=none`
  - `AUTH_COOKIE_SECURE=true`
- 프론트/백엔드 모두 HTTPS

### 4-2. 실제 테스트 순서(권장)

1. 백엔드 헬스
   - `GET https://<render>/api/health`
2. 프론트에서 API 호출 확인
   - 메인/분석 페이지가 데이터를 잘 가져오는지 확인
3. 회원가입 → 로그인
4. “내 분석 만들기 / 내 분석 보기” 접근
5. 새로고침/브라우저 재접속 후에도 로그인 유지 확인(쿠키 유지)

문제 발생 시 빠른 진단 포인트:

- 네트워크 탭에서 `/api/auth/login` 응답에 `Set-Cookie`가 내려오는지
- 요청에 `Cookie`가 포함되어 다시 보내지는지
- 응답 헤더에 `Access-Control-Allow-Origin: https://<your-pages-domain>`이 정확히 찍히는지

---

## 5) (선택) ETL 연결/스케줄링

ETL 데모는 `etl_demo.py`가 백엔드 ingest API를 호출하는 형태입니다.

### 5-1. 수동 실행(운영)

PowerShell 예시:

```powershell
$env:ET_API_BASE="https://myapp-api.onrender.com"
$env:ETL_SHARED_SECRET="strong-random-secret"
python etl_demo.py
```

### 5-2. GitHub Actions schedule(가장 쉬움)

`DEPLOYMENT.md`에 적힌 것처럼 `.github/workflows/etl-demo.yml`을 활용하고, repo secrets에 아래를 넣습니다.

- `ET_API_BASE`
- `ETL_SHARED_SECRET`

---

## 6) 운영 팁(권장)

- **프론트/백엔드를 가능하면 같은 최상위 도메인으로 맞추기**
  - 예: `app.example.com`(프론트), `api.example.com`(백엔드)
  - 쿠키/CORS 이슈가 줄어듭니다.
- **CORS_ALLOWED_ORIGINS를 환경별로 분리**
  - 운영/스테이징/프리뷰 도메인을 각각 정확히 등록
- **DB 백업/마이그레이션**
  - 현재는 `create_all` 기반이라 스키마 변경이 잦아지면 Alembic 같은 마이그레이션 도구 도입을 고려하세요.

