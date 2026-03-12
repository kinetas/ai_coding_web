## 데이터베이스 설계 정리

이 문서는 현재 `ai_coding_web`의 구현 상태를 기준으로, 운영에 필요한 테이블과 앞으로 확장할 테이블을 표 중심으로 정리한 문서입니다.

핵심 방향:

- 현재 구현된 인증/분석/워드클라우드/ETL 구조는 유지
- 유저 분석 기능은 "분석 정의"와 "분석 결과"를 분리
- 부동산 같은 실제 데이터셋을 위한 원본 테이블 추가
- 예측, 차트, 표 저장 구조까지 확장 가능하게 설계

---

## 1. 현재 구현된 테이블 요약

| 테이블명 | 용도 | 주요 컬럼 | 현재 구현 여부 | 확장 필요 여부 |
| --- | --- | --- | --- | --- |
| `users` | 유저 계정 저장 | `id`, `email`, `name/password_hash`, `created_at` | 구현됨 | 필요 |
| `auth_sessions` | 로그인 세션 저장 | `id`, `user_id`, `token_hash`, `expires_at` | 구현됨 | 낮음 |
| `analysis_snapshots` | 분석 페이지 기본 그래프 저장 | `page`, `line`, `bar`, `donut`, `accents` | 구현됨 | 보통 |
| `wordcloud_terms` | 메인 워드클라우드 저장 | `category`, `region`, `text`, `weight` | 구현됨 | 보통 |
| `saved_builder_analyses` | 유저 저장 분석 목록 | `user_id`, `title`, `keyword`, `metric` | 구현됨 | 높음 |
| `etl_runs` | ETL 실행 이력 | `source`, `status`, `details`, `created_at` | 구현됨 | 보통 |

현재 구현은 이미 아래 흐름과 연결됩니다.

1. 유저 로그인
2. 서버 데이터 조회
3. 워드클라우드/분석 결과 표시
4. 유저가 분석 저장
5. ETL이 데이터를 갱신

---

## 2. 유저 및 인증 테이블

### 2-1. `users`

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `id` | 유저 PK | PK |
| `email` | 로그인용 이메일 | UNIQUE |
| `nickname` | 화면 표시용 닉네임 | 현재 `name` 필드와 유사 |
| `password_hash` | 비밀번호 해시값 | 원문 저장 금지 |
| `status` | 계정 상태 | `active`, `inactive`, `deleted` |
| `created_at` | 생성 시각 |  |
| `updated_at` | 수정 시각 | 확장 권장 |

요청하신 유저 초안은 현재 구조에 바로 적용 가능합니다.  
비밀번호는 반드시 원문이 아닌 `password_hash`로 저장하는 방향이 맞습니다.

### 2-2. `auth_sessions`

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `id` | 세션 PK | PK |
| `user_id` | 유저 FK | FK -> `users.id` |
| `token_hash` | 세션 토큰 해시 | UNIQUE |
| `created_at` | 생성 시각 |  |
| `expires_at` | 만료 시각 | 인덱스 권장 |

이 테이블은 현재 로그인 유지 기능에 직접 필요합니다.

---

## 3. 유저 분석 테이블

요청하신 "유저 분석" 초안은 방향이 좋지만, 실제로는 분석 정의와 결과를 분리하는 편이 더 좋습니다.

### 3-1. `user_analyses`

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `id` | 분석 PK | PK |
| `user_id` | 유저 FK | FK -> `users.id` |
| `analysis_type` | 분석 종류 | `aggregation`, `comparison`, `prediction` 등 |
| `title` | 분석 이름 | 유저 저장 제목 |
| `source_category` | 데이터 출처 대분류 | 예: `real_estate` |
| `dataset_name` | 데이터셋 이름 | 예: `apartment_trade_price` |
| `metric_name` | 분석 대상 지표 | 예: `sale_price` |
| `aggregation_method` | 분석 방식 | `sum`, `avg`, `median`, `count` 등 |
| `group_by_field` | 그룹 기준 | 예: `region`, `month` |
| `filter_json` | 필터 조건 | JSON |
| `chart_type` | 시각화 타입 | `line`, `bar`, `table`, `mixed` |
| `created_at` | 생성 시각 |  |
| `updated_at` | 수정 시각 |  |

### 3-2. `user_analysis_results`

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `id` | 결과 PK | PK |
| `analysis_id` | 분석 FK | FK -> `user_analyses.id` |
| `result_version` | 결과 버전 | 재실행 대비 |
| `result_json` | 전체 결과 JSON | 요약/메타 포함 |
| `summary_text` | 결과 설명 | 자연어 요약 |
| `generated_at` | 생성 시각 |  |

### 3-3. `user_analysis_chart_series`

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `id` | 시리즈 PK | PK |
| `analysis_result_id` | 결과 FK | FK -> `user_analysis_results.id` |
| `series_name` | 시리즈 이름 | 예: `서울 평균가` |
| `x_value` | x축 값 | 날짜/지역명 등 |
| `y_value` | y축 값 | 수치 |
| `series_order` | 표시 순서 |  |

### 3-4. `user_analysis_table_rows`

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `id` | 행 PK | PK |
| `analysis_result_id` | 결과 FK | FK -> `user_analysis_results.id` |
| `row_order` | 행 순서 |  |
| `row_json` | 표 한 줄 데이터 | JSON |

`saved_builder_analyses`는 현재 기능 유지용 목록 테이블로 두고, 실제 확장은 위 4개 테이블로 가는 것이 좋습니다.

---

## 4. 실제 분석용 원본 데이터 테이블 (예시)

부동산 평균/합계/중간값/예측 기능을 하려면 원본 데이터 테이블이 먼저 필요합니다.

### 4-1. `real_estate_transactions`

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `id` | 거래 PK | PK |
| `region_large` | 시/도 |  |
| `region_mid` | 시/군/구 | group by 후보 |
| `region_small` | 동/읍/면 | 선택 |
| `property_type` | 부동산 유형 | 아파트/오피스텔 등 |
| `deal_date` | 거래 일자 | 시계열 분석용 |
| `area_m2` | 면적 |  |
| `sale_price` | 매매가 | 주요 지표 |
| `rent_price` | 전월세가 | 선택 |
| `floor` | 층수 | 선택 |
| `build_year` | 준공연도 | 선택 |
| `source_name` | 수집 출처 | ETL 추적용 |
| `created_at` | 적재 시각 |  |

이 테이블이 있으면 아래 분석이 가능합니다.

- 지역별 평균 가격
- 지역별 합계
- 지역별 중간값
- 월별 가격 추이
- 특정 지역 향후 가격 예측

필요하면 같은 패턴으로 `population_stats`, `traffic_stats` 같은 원본 테이블도 추가하면 됩니다.

---

## 5. 예측 기능 테이블

### 5-1. `forecast_runs`

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `id` | 예측 실행 PK | PK |
| `analysis_id` | 분석 FK | FK -> `user_analyses.id` |
| `model_type` | 예측 모델 | `arima`, `prophet`, `xgboost`, `lstm` 등 |
| `train_start_date` | 학습 시작일 |  |
| `train_end_date` | 학습 종료일 |  |
| `prediction_start_date` | 예측 시작일 |  |
| `prediction_end_date` | 예측 종료일 |  |
| `metrics_json` | 성능 지표 | `mae`, `rmse` 등 |
| `created_at` | 생성 시각 |  |

### 5-2. `forecast_points`

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `id` | 예측 포인트 PK | PK |
| `forecast_run_id` | 실행 FK | FK -> `forecast_runs.id` |
| `target_date` | 대상 시점 |  |
| `actual_value` | 실제값 | 있을 때만 저장 |
| `predicted_value` | 예측값 |  |
| `lower_bound` | 하한선 | 신뢰구간 |
| `upper_bound` | 상한선 | 신뢰구간 |

예측 기능은 단순 집계와 분리하는 것이 관리에 유리합니다.

---

## 6. 메인페이지 워드클라우드 및 집계 테이블

요청하신 "메인페이지 워드클라우드용 테이블"은 현재 구현과 매우 잘 맞습니다.

### 6-1. 현재 구조: `wordcloud_terms`

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `id` | PK | PK |
| `category` | 대분류 | 예: `agri`, `health` |
| `region` | 지역 구분 | `kr`, `global` |
| `text` | 키워드 |  |
| `weight` | 가중치 | count 또는 score |
| `updated_at` | 갱신 시각 |  |

### 6-2. 확장 구조: `keyword_events`

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `id` | PK | PK |
| `category` | 대분류 |  |
| `sub_category` | 중분류 |  |
| `keyword` | 키워드 |  |
| `source_name` | 수집 출처 | 뉴스/SNS 등 |
| `event_date` | 이벤트 일자 |  |
| `count_value` | 발생 수 |  |

### 6-3. 확장 구조: `wordcloud_agg`

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `id` | PK | PK |
| `category` | 대분류 |  |
| `sub_category` | 중분류 |  |
| `keyword` | 키워드 |  |
| `count_value` | 원시 카운트 |  |
| `weight` | 최종 가중치 | 시각화용 |
| `aggregation_date` | 집계 시점 |  |

운영에서는 `wordcloud_agg`를 집계 테이블로 두거나, 조회 중심이면 materialized view로 바꾸는 것도 가능합니다.

---

## 7. 현재 기능에 필요한 서비스 테이블

### 7-1. `analysis_snapshots`

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `id` | PK | PK |
| `page` | 분석 페이지 ID | `analysis-1`~`analysis-4` |
| `line` | 라인 그래프 데이터 | JSON |
| `bar` | 바 그래프 데이터 | JSON |
| `donut` | 도넛 그래프 데이터 | JSON |
| `accents` | 색상 설정 | JSON |
| `updated_at` | 갱신 시각 |  |

### 7-2. `saved_builder_analyses`

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `id` | PK | PK |
| `user_id` | 유저 FK | FK -> `users.id` |
| `title` | 저장 제목 |  |
| `keyword` | 키워드 |  |
| `metric` | 선택 지표 |  |
| `metric_label` | 화면 표시 이름 |  |
| `created_at` | 저장 시각 |  |

### 7-3. `etl_runs`

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `id` | PK | PK |
| `source` | 실행 소스 | 어떤 ETL인지 |
| `status` | 상태 | `success`, `failed` 등 |
| `details` | 상세 로그 | 텍스트 |
| `created_at` | 실행 시각 |  |

이 세 테이블은 현재 기능과 가장 직접적으로 연결됩니다.

---

## 8. 현재 구조에 적용하는 순서

| 단계 | 작업 | 추가/유지 테이블 |
| --- | --- | --- |
| 1 | 현재 구조 유지 및 필드명 정리 | `users`, `auth_sessions`, `analysis_snapshots`, `wordcloud_terms`, `saved_builder_analyses`, `etl_runs` |
| 2 | 유저 분석 기능 확장 | `user_analyses`, `user_analysis_results`, `user_analysis_chart_series`, `user_analysis_table_rows` |
| 3 | 실제 원본 데이터 추가 | `real_estate_transactions`, 필요 시 `population_stats`, `traffic_stats` |
| 4 | 집계 자동화 | `wordcloud_agg`, 분석 집계 테이블 또는 materialized view |
| 5 | 예측 기능 추가 | `forecast_runs`, `forecast_points` |

이 순서로 가면 현재 기능을 깨지 않고 점진적으로 확장할 수 있습니다.

---

## 9. 유저 분석 기능에 꼭 필요한 추가 요소

| 구분 | 필요한 항목 | 설명 |
| --- | --- | --- |
| 필수 | 원본 데이터 테이블 | 합계/평균/중간값/예측의 기반 |
| 필수 | 분석 정의 테이블 | 유저가 어떤 분석을 만들었는지 저장 |
| 필수 | 분석 결과 테이블 | 재조회 가능한 결과 저장 |
| 필수 | 차트 데이터 테이블 | 그래프 재렌더링용 |
| 필수 | 표 데이터 테이블 | 표 재표시용 |
| 필수 | 예측 실행/포인트 테이블 | 미래값 저장 |
| 선택 | 공개/비공개 | 분석 공유 기능 |
| 선택 | 즐겨찾기 | 자주 보는 분석 빠른 접근 |
| 선택 | 최근 조회 기록 | 사용자 행동 추적 |
| 선택 | 실패 로그/실행 시간 | 운영 및 디버깅 강화 |

---

## 10. 최소 운영 버전과 확장 버전

### 최소 운영 버전

| 구분 | 테이블 |
| --- | --- |
| 인증/유저 | `users`, `auth_sessions` |
| 서비스 데이터 | `analysis_snapshots`, `wordcloud_terms` |
| 유저 기능 | `saved_builder_analyses` |
| 운영 | `etl_runs` |

### 확장 버전

| 구분 | 테이블 |
| --- | --- |
| 원본 데이터 | `real_estate_transactions`, `population_stats`, `traffic_stats` |
| 유저 분석 | `user_analyses`, `user_analysis_results`, `user_analysis_chart_series`, `user_analysis_table_rows` |
| 예측 | `forecast_runs`, `forecast_points` |
| 집계/워드클라우드 | `keyword_events`, `wordcloud_agg` |

---

## 11. 결론

현재 구현에는 이미 아래 기반이 있습니다.

- 유저
- 로그인 세션
- 워드클라우드
- 분석 스냅샷
- 저장된 유저 분석
- ETL 실행 이력

즉, 지금 구조는 유지하면서 아래만 추가하면 됩니다.

- 원본 데이터 테이블
- 유저 분석 정의/결과 테이블
- 예측 결과 테이블

이렇게 확장하면 부동산 평균/합계/중간값/예측/그래프/표 저장까지 자연스럽게 연결할 수 있습니다.
