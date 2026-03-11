# ai_coding_web

정적 HTML/CSS/JS 프론트 + FastAPI 백엔드(API)로 구성된 데모입니다.

## 실행 방법

### 1) 백엔드(FastAPI) 실행

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

- 확인: `GET http://127.0.0.1:8000/api/health`
- 워드클라우드: `GET /api/wordcloud?category=agri&region=kr`
- 분석 차트: `GET /api/analysis?page=analysis-1`
- 내 분석 만들기(추천): `GET /api/builder/suggestions?keyword=게임`
- 내 분석 만들기(지표): `GET /api/builder/metric?keyword=게임&metric=user_count`

### 2) 프론트 실행

정적 서버(예: VSCode Live Server)로 `frontend/index.html`을 열면 됩니다.

간단히 파이썬 정적 서버를 쓰려면:

```bash
cd frontend
python -m http.server 5500
```

그 다음 `http://127.0.0.1:5500/index.html`로 접속하세요.

- 프론트는 기본적으로 `http://127.0.0.1:8000`의 API를 호출합니다.
- 필요하면 콘솔에서 `window.ET_API_BASE = "http://127.0.0.1:8000"`처럼 바꿔서 사용할 수 있습니다.

## 로그인 정책(현재 데모)

- 분석 페이지(`analysis-1~4`)는 **로그인 없이 접근 가능**
- **내 분석 만들기/내 분석 보기** 페이지는 **로그인 필요**
  - `frontend/my-analysis.html`
  - `frontend/my-analyses.html`

## ETL(데모)로 연결 확인

FastAPI를 켠 상태에서 아래를 실행한 뒤, 브라우저에서 새로고침해 보세요.

```bash
python etl_demo.py
```

- `POST /api/ingest/wordcloud`로 워드클라우드 weight가 바뀌고
- `POST /api/ingest/analysis`로 분석 1 그래프 값이 바뀝니다.