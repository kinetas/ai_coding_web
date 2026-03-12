# ai_coding_web

정적 HTML/CSS/JS 프론트 + FastAPI 백엔드(API)로 구성된 프로젝트입니다.

- 백엔드 인증: 서버 세션 쿠키 기반
- 저장소: SQLAlchemy 기반 DB 저장
- 로컬 기본 DB: SQLite
- 운영 DB 권장: PostgreSQL

운영 배포 순서와 추천 서비스는 `DEPLOYMENT.md`를 참고하세요.

## 실행 방법

### 1) 백엔드(FastAPI) 실행

먼저 `.env.example` 값을 참고해 환경변수를 준비하세요.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m backend.app.init_db
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

- 프론트 API 주소는 `frontend/assets/js/config.js` 에서 관리합니다.
- 기본값은 `http://127.0.0.1:8000` 입니다.

## 로그인 정책

- 분석 페이지(`analysis-1~4`)는 **로그인 없이 접근 가능**
- **내 분석 만들기/내 분석 보기** 페이지는 **로그인 필요**
  - `frontend/my-analysis.html`
  - `frontend/my-analyses.html`

로그인 방법:

- 로그인 페이지에서 직접 회원가입
- 또는 기본 데모 계정 사용: `demo@et.ai / etl1234`

## ETL 연결 확인

FastAPI를 켠 상태에서 아래를 실행한 뒤, 브라우저에서 새로고침해 보세요.

```bash
set ETL_SHARED_SECRET=change-me
python etl_demo.py
```

- `POST /api/ingest/wordcloud`로 워드클라우드 weight가 바뀌고
- `POST /api/ingest/analysis`로 분석 1 그래프 값이 바뀝니다.

운영에서는 `ETL_SHARED_SECRET` 값을 반드시 실제 비밀값으로 바꿔야 합니다.

## 배포 파일

- `Dockerfile`: 백엔드 컨테이너 배포용
- `.env.example`: 운영/로컬 환경변수 예시
- `DEPLOYMENT.md`: 실제 배포 및 ETL 운영 순서
- `learn.md`: 현재 프로젝트 구조 설명

---

## ai_coding_web 구조 이해하기

이 문서는 `ai_coding_web` 프로젝트가 **어떤 디렉터리 구조와 역할**로 동작하는지, 그리고 **프론트엔드가 백엔드와 어떻게 통신하는지**를 정리한 것입니다.

---

## 전체 구조 개요

- **frontend/**  
  정적 웹 페이지(HTML/CSS/JS).  
  사용자가 실제로 보는 화면과 브라우저에서 실행되는 자바스크립트 코드가 들어 있습니다.

- **backend/**  
  FastAPI 기반의 백엔드 서버.  
  프론트엔드에서 보내는 요청(API)을 받아 비즈니스 로직을 수행하고 JSON 형태로 응답합니다.

- **etl_demo.py**  
  데모용 ETL 스크립트.  
  FastAPI 서버가 켜진 상태에서 실행하면, 백엔드의 특정 API(ingest)를 호출해서 워드클라우드/분석 데이터 값을 바꿉니다.

- **requirements.txt**  
  백엔드 실행에 필요한 파이썬 패키지 목록입니다.

- **README.md**  
  실행 방법(백엔드/프론트 서버 켜는 방법)과 주요 API를 간단히 안내합니다.

- **learn.md (현재 파일)**  
  프로젝트 구조와 요청 흐름을 설명하는 문서입니다.

---

## 디렉터리별 역할 상세

### 1. frontend/

정적 리소스를 모아 둔 폴더입니다.

- **HTML 페이지**
  - `index.html`  
    메인 대시보드 / 진입 페이지.
  - `login.html`  
    로그인 화면.
  - `analysis-1.html` ~ `analysis-4.html`  
    로그인 없이 볼 수 있는 분석 화면들.
  - `my-analysis.html`, `my-analyses.html`  
    **로그인이 필요한** 내 분석 만들기/내 분석 보기 페이지.

- **assets/css/styles.css**  
  전체 UI 스타일(레이아웃, 색상, 폰트 등)을 담당합니다.

- **assets/js/*.js**  
  각 페이지에서 사용하는 자바스크립트 코드입니다.
  - `common.js` : 공통 유틸, API 호출 기본 베이스 URL 설정 등.
  - `index.js` : 메인/대시보드 관련 스크립트.
  - `analysis.js`, `charts.js` : 분석 페이지에서 그래프/차트 그리는 로직.
  - `login.js`, `auth.js` : 로그인/인증과 관련된 처리.
  - `my_analysis.js`, `my_analyses.js` : 내 분석 관련 화면을 위한 스크립트.

프론트는 기본적으로 `window.ET_API_BASE`(기본값은 `http://127.0.0.1:8000`)를 기준으로 백엔드 API를 호출합니다.

---

### 2. backend/

FastAPI 애플리케이션이 들어 있는 폴더입니다.

- **backend/app/main.py**  
  FastAPI 앱의 진입점입니다.  
  `uvicorn backend.app.main:app --reload ...` 명령으로 이 `app` 객체를 실행합니다.

- **backend/app/controllers/**  
  URL과 직접 연결되는 **API 엔드포인트(라우터)** 가 있는 곳입니다.
  - `health_controller.py` : `/api/health` 헬스 체크용 엔드포인트.
  - `analysis_controller.py` : `/api/analysis` 관련 엔드포인트.
  - `builder_controller.py` : `/api/builder/...` (분석 추천/지표 생성 등) 엔드포인트.
  - `wordcloud_controller.py` : `/api/wordcloud` 및 관련 ingest 엔드포인트.

- **backend/app/services/**  
  실제 비즈니스 로직을 담는 계층입니다.  
  컨트롤러는 요청을 받고, 실질적인 처리는 서비스 레이어에 위임합니다.
  - `analysis_service.py`
  - `builder_service.py`
  - `wordcloud_service.py`

- **backend/app/repositories/**  
  데이터 저장소(메모리/DB 대용)를 추상화한 계층입니다.
  - `memory_store.py` : 메모리에 데이터를 저장/조회하는 간단한 저장소.
  - `builder_store.py` : 내 분석(빌더) 관련 데이터를 저장/조회.

- **backend/app/models/**  
  API에서 사용하는 데이터 구조(스키마, 타입)를 정의합니다.
  - `types.py` : 공통 타입/Enum/데이터 클래스 등.
  - `analysis.py`, `builder.py`, `wordcloud.py` : 각 도메인별 모델.

- **backend/app/core/**  
  공통 유틸리티/핵심 기능.
  - `time.py` : 시간 관련 유틸 함수 등.

이렇게 **컨트롤러 → 서비스 → 리포지토리 → (메모리/저장소)** 흐름으로 계층이 나뉘어 있어, 역할이 분리된 구조입니다.

---

## 요청 흐름(프론트 ↔ 백엔드)

1. **사용자 브라우저에서 페이지 접속**
   - 사용자는 `index.html`, `analysis-1.html`, `my-analysis.html` 등 정적 페이지에 접속합니다.
   - 이 페이지 안에서 자바스크립트(`assets/js/*.js`)가 로드됩니다.

2. **프론트엔드 자바스크립트가 API 호출**
   - 예: 분석 차트 로딩 시 `GET /api/analysis?page=analysis-1`
   - 예: 워드클라우드 로딩 시 `GET /api/wordcloud?category=agri&region=kr`
   - 예: 내 분석 추천 시 `GET /api/builder/suggestions?keyword=게임`

3. **백엔드 컨트롤러가 요청 수신**
   - `analysis_controller.py` 등에서 FastAPI의 라우터가 요청을 받고,
   - 적절한 **서비스** 함수(예: `analysis_service`)를 호출합니다.

4. **서비스 → 리포지토리 → 데이터 처리**
   - 서비스 계층에서 비즈니스 로직을 처리합니다.
   - 필요하면 `memory_store.py`, `builder_store.py` 등 리포지토리를 통해 데이터를 읽거나 씁니다.

5. **JSON 응답 반환**
   - 서비스에서 만든 결과를 컨트롤러가 HTTP 응답(JSON)으로 변환해 브라우저로 돌려줍니다.
   - 프론트 자바스크립트는 이 JSON을 받아 차트/워드클라우드/리스트 등을 렌더링합니다.

---

## ETL 데모 흐름

1. FastAPI 백엔드를 실행합니다.
2. `python etl_demo.py` 를 실행하면, 이 스크립트가 **백엔드의 ingest API** 를 호출합니다.
   - `POST /api/ingest/wordcloud` : 워드클라우드 weight 변경
   - `POST /api/ingest/analysis` : 분석 1 그래프 값 변경
3. 브라우저에서 분석/워드클라우드 페이지를 새로고침하면 **변경된 데이터**가 반영된 그래프/워드클라우드를 볼 수 있습니다.

---

## 이 구조의 포인트

- **정적 프론트엔드 + FastAPI 백엔드** 라는 전형적인 SPA/MPA + API 백엔드 구조를 단순하게 보여주는 예제입니다.
- 프론트(HTML/JS)와 백엔드(FastAPI)를 **완전히 분리**해서, 각각 독립적으로 개발/배포할 수 있는 형태입니다.
- 백엔드는 **컨트롤러(라우터) → 서비스(비즈니스 로직) → 리포지토리(데이터 저장소)** 의 계층 구조를 따르고 있어, 규모가 커져도 유지보수하기 좋습니다.

---

## 데이터 엔지니어 관점에서 이 프로젝트 보기

이 프로젝트는 지금 당장 **PySpark가 실제로 적용된 상태는 아닙니다.**  
현재는 FastAPI와 프론트가 동작하는 **서비스 데모 + ETL 연결 연습용 구조**에 가깝습니다.

하지만 데이터 엔지니어 관점에서 보면, **PySpark / ETL / 배치 처리 / 스트리밍 처리**를 붙이기 좋은 출발점입니다.

---

## 현재 코드에서 PySpark가 "적용될 수 있는 위치"

현재 직접적으로 PySpark 코드가 들어간 파일은 없습니다.  
대신 아래 부분이 **PySpark나 Spark Streaming을 붙일 수 있는 지점**입니다.

### 1. `etl_demo.py`

- 지금은 단순히 API로 샘플 데이터를 보내는 작은 스크립트입니다.
- 데이터 엔지니어 관점에서는 이 파일이 **ETL의 Load 단계 예시**에 해당합니다.
- 나중에는 이 파일을 다음처럼 바꿀 수 있습니다.
  - 외부 데이터 수집
  - PySpark로 정제/집계
  - 결과를 DB 또는 API에 적재

즉, 지금의 `etl_demo.py`는 아주 작은 ETL 실행기라고 보면 됩니다.

### 2. `backend/app/controllers/analysis_controller.py`

- `POST /api/ingest/analysis`
- ETL 결과를 분석 데이터로 넣는 입구입니다.

PySpark로 집계한 결과가 있으면, 최종적으로 이 엔드포인트를 통해 적재하거나,  
더 발전시키면 API를 거치지 않고 DB에 바로 저장하는 방식으로 바꿀 수 있습니다.

### 3. `backend/app/controllers/wordcloud_controller.py`

- `POST /api/ingest/wordcloud`
- 키워드/가중치 집계 결과를 넣는 입구입니다.

예를 들어 뉴스/커뮤니티/SNS 데이터를 Spark로 모아서,
- 키워드 빈도 계산
- 불용어 제거
- 점수(weight) 계산

을 한 뒤 이쪽으로 넣는 구조를 만들 수 있습니다.

### 4. `backend/app/services/analysis_service.py`, `wordcloud_service.py`

- 이 레이어는 "집계된 결과를 서비스에서 어떻게 응답할 것인가"를 담당합니다.
- 데이터 엔지니어 입장에서는 **최종 산출물 serving 레이어**로 볼 수 있습니다.

즉, PySpark는 계산/집계를 담당하고,  
FastAPI는 그 결과를 사용자에게 보여주는 역할을 맡는 구조입니다.

### 5. 프론트의 분석/워드클라우드 페이지

- `frontend/index.html`
- `frontend/analysis-1.html` ~ `analysis-4.html`

이 부분은 Spark가 직접 붙는 곳은 아니지만,  
**PySpark가 만든 결과가 결국 사용자에게 보이는 최종 화면**입니다.

즉:

1. 원천 데이터 수집
2. Spark 집계
3. 결과 적재
4. FastAPI 조회
5. 프론트 렌더링

이 흐름의 마지막 단계입니다.

---

## 현재 코드에서 ETL을 공부할 때 참고할 부분

### 1. 가장 먼저 볼 파일: `etl_demo.py`

이 파일은 ETL 전체 중 아주 단순한 예시입니다.

- **Extract**: 현재는 없음
- **Transform**: 랜덤 값으로 조금 바꾸는 정도만 있음
- **Load**: `POST /api/ingest/...` 로 적재

즉, 완전한 ETL은 아니지만 **Load 중심의 데모**입니다.

ETL을 처음 공부할 때는 이 파일을 보면서:

- "적재 대상이 어디인가?"
- "어떤 형태의 payload를 보내는가?"
- "최종적으로 시스템에 어떻게 반영되는가?"

를 이해하면 좋습니다.

### 2. 적재 결과가 반영되는 곳

- `backend/app/controllers/analysis_controller.py`
- `backend/app/controllers/wordcloud_controller.py`
- `backend/app/services/analysis_service.py`
- `backend/app/services/wordcloud_service.py`
- 저장소 계층

이 부분을 보면 ETL이 만든 결과가 어떤 API를 통해 들어오고,  
어떻게 저장되고, 다시 사용자 요청 때 어떻게 응답되는지 알 수 있습니다.

### 3. 운영 관점의 ETL 힌트

현재 프로젝트에는 아래 운영 요소도 이미 들어가 있습니다.

- `ETL_SHARED_SECRET`
- 보호된 ingest 엔드포인트
- `.github/workflows/etl-demo.yml`
- `DEPLOYMENT.md`의 ETL 스케줄링 설명

즉 지금 구조는 단순 데모를 넘어서,
**"ETL 작업을 예약 실행하고 결과를 서비스에 반영하는 운영 구조"** 로 확장할 수 있게 되어 있습니다.

---

## PySpark를 배우려면 무엇부터 공부하면 좋은가

PySpark는 보통 아래 순서로 공부하면 좋습니다.

### 1. 파이썬 기본 자료 처리

먼저 알아야 할 것:

- list / dict / tuple
- 함수
- class
- file I/O
- JSON 처리
- CSV 처리

이게 익숙해야 Spark에서 데이터 프레임 다루는 게 쉬워집니다.

### 2. SQL

데이터 엔지니어에게 SQL은 거의 필수입니다.

먼저 공부할 것:

- `SELECT`, `WHERE`, `GROUP BY`, `ORDER BY`
- `JOIN`
- 서브쿼리
- 윈도우 함수
- 집계 함수
- 인덱스 기본 개념

이 프로젝트도 결국 분석 결과를 DB에 저장하고 읽기 때문에 SQL 감각이 중요합니다.

### 3. PySpark DataFrame API

핵심 학습 주제:

- `spark.read`
- `select`, `filter`, `withColumn`
- `groupBy`, `agg`
- `join`
- `orderBy`
- `write`

가장 먼저는 pandas처럼 보이지만 분산 처리라는 점이 다르다는 것을 이해해야 합니다.

### 4. 배치 ETL

중요 개념:

- extract / transform / load
- partition
- batch schedule
- retry
- idempotency
- logging
- data quality check

이 프로젝트에서는 `etl_demo.py`를 확장하는 식으로 연습할 수 있습니다.

### 5. Spark Streaming / Structured Streaming

그 다음에 공부할 것:

- stream source
- watermark
- window aggregation
- checkpoint
- exactly-once / at-least-once 개념

현재 `frontend/index.html`과 `analysis-1.html` 안의 설명에는 이미  
`Spark Streaming 아이디어`가 들어 있으므로, 프로젝트의 방향성과도 잘 맞습니다.

---

## 이 프로젝트에서 PySpark를 붙여 연습하려면 추천하는 순서

### 1단계. 가짜 원천 데이터 파일 만들기

예:

- `data/raw/news.csv`
- `data/raw/social.csv`
- `data/raw/market_prices.csv`

이런 샘플 파일을 만들고,
PySpark로 읽어서 집계 연습을 합니다.

### 2단계. PySpark 배치 스크립트 만들기

예:

- `jobs/wordcloud_job.py`
- `jobs/analysis_job.py`

역할:

- CSV/JSON 읽기
- 키워드 빈도 계산
- 카테고리별 집계
- 점수(weight) 계산
- 결과 JSON 생성

### 3단계. 결과를 현재 백엔드에 적재

적재 방식은 두 가지가 있습니다.

- 현재처럼 `POST /api/ingest/wordcloud`, `POST /api/ingest/analysis` 호출
- 또는 DB에 직접 write

처음 공부할 때는 **API 적재 방식**이 더 이해하기 쉽습니다.

### 4단계. 주기 실행

예:

- GitHub Actions schedule
- cron
- Airflow

처음에는 GitHub Actions로 충분하고,  
나중에는 Airflow로 옮기면 더 데이터 엔지니어다운 구조가 됩니다.

### 5단계. 결과 검증

체크할 것:

- 적재 성공 여부
- 집계 값이 예상대로 나오는지
- 중복 적재 없는지
- 실패 시 로그가 남는지

---

## ETL을 공부할 때 꼭 알아야 하는 개념

### 1. Extract

데이터를 가져오는 단계입니다.

예:

- API 호출
- CSV 파일 읽기
- DB 조회
- Kafka/로그 읽기

### 2. Transform

데이터를 정리/가공하는 단계입니다.

예:

- 결측치 처리
- 타입 변환
- 집계
- 조인
- 중복 제거
- 키워드 정규화

### 3. Load

가공 결과를 저장하는 단계입니다.

예:

- DB 저장
- 데이터 웨어하우스 적재
- API 전송
- 파일 저장(parquet/csv/json)

현재 이 프로젝트에서는 **Load 단계가 가장 잘 보이는 구조**입니다.

---

## 데이터 엔지니어 역량을 위해 추가로 공부하면 좋은 것

### 1. 데이터베이스 설계

공부할 것:

- 정규화
- PK/FK
- 인덱스
- 트랜잭션
- 쿼리 성능

현재 프로젝트에서 참고할 부분:

- `backend/app/db_models.py`

여기에 테이블 모델이 있기 때문에,
테이블 구조를 어떻게 잡는지 보는 연습이 가능합니다.

### 2. API와 데이터 서빙

공부할 것:

- FastAPI
- REST API
- 인증/인가
- pagination
- error handling

현재 프로젝트에서 참고할 부분:

- `backend/app/controllers/`
- `backend/app/services/`

데이터 엔지니어도 최종적으로 데이터를 서비스에 전달하는 구조를 이해해야 합니다.

### 3. 스케줄링/워크플로우

공부할 것:

- cron
- GitHub Actions
- Airflow
- Dagster

현재 프로젝트에서 참고할 부분:

- `.github/workflows/etl-demo.yml`
- `DEPLOYMENT.md`

### 4. 데이터 품질 관리

공부할 것:

- null check
- schema validation
- duplicate check
- data freshness
- anomaly detection

추가하면 좋은 것:

- ETL 실행 후 row count 검증
- 실패 시 알림
- 품질 체크 로그 저장

### 5. 로그/모니터링

공부할 것:

- structured logging
- metrics
- alerting
- retry 전략

추가하면 좋은 것:

- ETL 성공/실패 이력 테이블
- 에러 메시지 저장
- 실행 시간 기록

현재는 `etl_runs` 같은 개념으로 확장하기 좋은 구조입니다.

### 6. 파일 포맷과 데이터 레이크 개념

공부할 것:

- CSV
- JSON
- Parquet
- partitioning
- object storage(S3 등)

이 프로젝트에 추가하면 좋은 것:

- `data/raw/`
- `data/processed/`
- parquet 결과 저장

---

## 데이터 엔지니어 포트폴리오용으로 이 프로젝트에 추가하면 좋은 기능

아래 기능을 추가하면 "웹 데모"를 넘어서  
**데이터 엔지니어 포트폴리오 프로젝트** 느낌이 강해집니다.

### 1. 실제 수집 파이프라인

- 뉴스 API 수집
- 공공데이터 수집
- SNS/커뮤니티 데이터 수집

### 2. PySpark 배치 집계

- 일별/시간별 키워드 집계
- 카테고리별 wordcloud 생성
- Top N 변화율 계산

### 3. Airflow DAG

- `extract -> transform -> load`를 DAG로 구성
- 실패 시 retry
- 성공/실패 모니터링

### 4. 데이터 웨어하우스/마트 구조

- raw
- staging
- mart

이런 레이어를 나누면 훨씬 실무 느낌이 납니다.

### 5. 품질 검증

- 스키마 체크
- 중복 체크
- 누락 체크
- 이상치 탐지

### 6. 시계열 분석 강화

- rolling window
- moving average
- anomaly detection
- seasonality

현재 `analysis-*` 페이지와 아주 잘 연결될 수 있습니다.

---

## 공부 추천 순서

실제로는 아래 순서가 가장 효율적입니다.

1. 파이썬 기본 문법
2. SQL
3. ETL 개념
4. pandas로 작은 데이터 처리
5. PySpark DataFrame
6. Airflow 또는 스케줄러
7. Docker
8. 클라우드 배포
9. 모니터링/로그
10. Kafka 같은 스트리밍 도구

---

## 지금 이 프로젝트에서 가장 먼저 해보면 좋은 연습

1. `etl_demo.py`를 읽고 Load 흐름을 이해하기
2. 뉴스/키워드 CSV 파일 하나를 만들어서 직접 읽기
3. PySpark로 키워드 빈도 집계하기
4. 집계 결과를 `POST /api/ingest/wordcloud`로 넣기
5. 메인 페이지 워드클라우드가 바뀌는지 확인하기
6. 다음으로 `analysis`용 집계도 만들어 보기
7. 마지막으로 GitHub Actions나 Airflow로 자동화하기

이 순서로 가면 **ETL 기본기 + API 적재 + 서비스 연결 + 운영 자동화**를 한 번에 연습할 수 있습니다.

---

## 한 줄 정리

현재 프로젝트는 아직 PySpark가 직접 적용된 상태는 아니지만,  
**PySpark ETL 결과를 서비스에 연결해 보는 연습용 프로젝트로는 아주 좋습니다.**

특히 아래 파일들이 핵심 참고 지점입니다.

- `etl_demo.py`
- `backend/app/controllers/analysis_controller.py`
- `backend/app/controllers/wordcloud_controller.py`
- `backend/app/services/analysis_service.py`
- `backend/app/services/wordcloud_service.py`
- `backend/app/db_models.py`
- `.github/workflows/etl-demo.yml`
- `DEPLOYMENT.md`