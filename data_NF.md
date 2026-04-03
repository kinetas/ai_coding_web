# `data.md` 기반 정규화 작업 및 최종 테이블 (`data_NF.md`)

`data.md`의 도메인을 읽고 **BCNF에 가깝게** 엔티티·코드·계층을 분리한 뒤, **JSON·집계·목록 조회**처럼 실무상 이득이 큰 부분만 **의도적으로 정규형을 내려** 맞춘 **최종 정리본**이다.

---

## 1. 용어 (이 문서에서의 직관)

| 정규형 | 직관 |
| --- | --- |
| **BCNF** | 결정자마다 후보키가 되도록 테이블을 쪼갠 쪽 |
| **3NF** | 비키 → 비키 전이 제거. 룩업 일부를 열 하나(`CHECK`)로 합친 **완화**를 말할 때 |
| **2NF** | 복합키 부분 종속 제거. `metric`↔`label` 같은 **마스터 중복 저장**을 허용한 완화 |
| **1NF 쪽** | 스키마를 속성 단위로 쪼개지 않고 **`jsonb` 한 덩어리**·혼합 `x`축 등으로 둔 완화 |

**“내렸다”** = 정규화를 완화해 **중복·비원자 표현**을 허용한다.

---

## 2. 정규화 작업에서 한 일 (요약)

| 단계 | 내용 |
| --- | --- |
| 코드 분리 | `status`, 분석/차트/집계/부동산 유형, ETL 상태·소스 등을 **코드 테이블 + FK** 로 분리 (`data.md`의 반복 문자열 제거) |
| 지역 | `region_large`/`mid`/`small` 문자열 반복 → **`regions` 계층 + `region_id` FK** |
| 데이터셋·지표 | `dataset_name`, `metric_name` → **`datasets`, `metrics`** 로 고정하고 분석 정의는 FK만 |
| 필터 | `filter_json` → 행 단위 **`user_analysis_filters`** (원하면 여전히 JSON 병행 가능) |
| 키워드 | `keyword`+분류 반복 → **`keyword_terms` + 이벤트/집계는 FK** |
| 남긴 완화 | 스냅샷·일부 결과·예측 메트릭은 **JSON 유지 시 1NF 쪽으로 내렸다**고 본다 |

---

## 3. 최종 테이블 목록 (전체 인덱스)

| 구분 | 테이블명 |
| --- | --- |
| 룩업 | `account_statuses`, `source_categories`, `analysis_types`, `chart_types`, `aggregation_methods`, `property_types`, `etl_statuses`, `etl_sources`, `forecast_model_types` |
| 지역·원본 | `regions`, `real_estate_transactions`, `population_stats`, `traffic_stats` |
| 데이터셋·지표 | `datasets`, `metrics` |
| 유저·인증 | `users`, `auth_sessions` |
| 유저 분석 | `user_analyses`, `user_analysis_filters`, `user_analysis_results`, `user_analysis_chart_series`, `user_analysis_table_rows` |
| 예측 | `forecast_runs`, `forecast_metric_entries`, `forecast_points` |
| 워드클라우드 | `wordcloud_region_scopes`, `wordcloud_categories`, `wordcloud_subcategories`, `keyword_terms`, `keyword_events`, `wordcloud_agg`, `wordcloud_terms` |
| 서비스 | `analysis_snapshots`, `saved_builder_analyses`, `etl_runs` |

---

## 4. 최종 테이블 정의 (컬럼)

### 4-1. 룩업 (코드 마스터)

#### `account_statuses`

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `code` | 상태 코드 | PK (`active`, `inactive`, `deleted`) |
| `display_name` | 화면용 이름 | 선택 |

#### `source_categories`

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `code` | 대분류 코드 | PK (예: `real_estate`) |
| `display_name` | 설명 | 선택 |

#### `analysis_types` · `chart_types` · `aggregation_methods` · `property_types` · `etl_statuses` · `forecast_model_types`

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `code` | 코드 | PK |
| `display_name` | 화면용 이름 | 선택 |

#### `etl_sources`

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `code` | ETL/수집 소스 식별자 | PK (`data.md`의 `source`, `source_name` 정규화) |
| `display_name` | 설명 | 선택 |

---

### 4-2. 지역

#### `regions`

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `id` | 지역 PK | PK |
| `parent_region_id` | 상위 지역 | FK → `regions.id`, NULL 허용(최상위) |
| `level` | 계층 단계 | 예: 1=시도, 2=시군구, 3=동 |
| `name` | 표시명 | |
| `admin_code` | 법정/행정 코드 | 선택, UNIQUE 권장 |

---

### 4-3. 데이터셋 · 지표

#### `datasets`

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `code` | 데이터셋 코드 | PK (예: `apartment_trade_price`) |
| `source_category_code` | 출처 대분류 | FK → `source_categories.code` |
| `display_name` | 설명 | 선택 |

#### `metrics`

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `code` | 지표 코드 | PK (`sale_price` 등), `dataset_code` 와 복합 유니크 권장 |
| `dataset_code` | 소속 데이터셋 | FK → `datasets.code` |
| `default_label` | 기본 라벨 | `saved_builder_analyses`의 `metric_label` 중복 제거용 |

---

### 4-4. 유저 · 인증

#### `users`

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `id` | 유저 PK | PK |
| `email` | 로그인 이메일 | UNIQUE |
| `nickname` | 닉네임 | |
| `password_hash` | 비밀번호 해시 | 원문 저장 금지 |
| `status_code` | 계정 상태 | FK → `account_statuses.code` |
| `created_at` | 생성 시각 | |
| `updated_at` | 수정 시각 | |

**완화 옵션**: `status_code` 대신 `status text CHECK (...)` 만 쓰면 룩업 테이블을 없애 **3NF 쪽으로 내렸다**고 본다.

#### `auth_sessions`

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `id` | 세션 PK | PK |
| `user_id` | 유저 | FK → `users.id` |
| `token_hash` | 토큰 해시 | UNIQUE |
| `created_at` | 생성 시각 | |
| `expires_at` | 만료 시각 | 인덱스 권장 |

---

### 4-5. 유저 분석 (정의 · 필터 · 결과 · 차트 · 표)

#### `user_analyses`

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `id` | 분석 PK | PK |
| `user_id` | 유저 | FK → `users.id` |
| `analysis_type_code` | 분석 종류 | FK → `analysis_types.code` |
| `title` | 유저 지정 제목 | |
| `dataset_code` | 데이터셋 | FK → `datasets.code` |
| `metric_code` | 지표 | FK → `metrics.code` (동일 dataset과 일치하도록 앱/제약) |
| `aggregation_method_code` | 집계 방식 | FK → `aggregation_methods.code` |
| `group_by_field` | 그룹 기준 | 텍스트 (예: `region`, `month`) |
| `chart_type_code` | 시각화 타입 | FK → `chart_types.code` |
| `created_at` | 생성 시각 | |
| `updated_at` | 수정 시각 | |

**완화 옵션**: `filter_json` 을 여기에 두고 `user_analysis_filters` 를 쓰지 않으면 **1NF 쪽으로 내렸다**.

#### `user_analysis_filters`

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `id` | PK | PK |
| `analysis_id` | 분석 | FK → `user_analyses.id` ON DELETE CASCADE |
| `field_code` | 필드 식별 | |
| `operator` | 연산자 | |
| `value_text` | 문자 값 | NULL 허용 |
| `value_num` | 수치 값 | NULL 허용 |
| `sort_order` | 조건 순서 | |

#### `user_analysis_results`

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `id` | 결과 PK | PK |
| `analysis_id` | 분석 | FK → `user_analyses.id` |
| `result_version` | 버전 | |
| `result_json` | 요약/메타·여분 | **1NF 쪽으로 내렸다** (큰 덩어리 허용) |
| `summary_text` | 자연어 요약 | |
| `generated_at` | 생성 시각 | |

#### `user_analysis_chart_series`

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `id` | PK | PK |
| `analysis_result_id` | 결과 | FK → `user_analysis_results.id` ON DELETE CASCADE |
| `series_name` | 시리즈 이름 | |
| `x_date` | x가 날짜일 때 | NULL 허용 |
| `x_text` | x가 문자일 때 | NULL 허용 |
| `y_value` | y값 | |
| `series_order` | 표시 순서 | |

**완화 옵션**: `x_date`/`x_text` 대신 `x_value` 텍스트 하나만 쓰면 타입 혼합 **1NF 쪽으로 내렸다**.

#### `user_analysis_table_rows`

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `id` | PK | PK |
| `analysis_result_id` | 결과 | FK → `user_analysis_results.id` ON DELETE CASCADE |
| `row_order` | 행 순서 | |
| `row_json` | 행 단위 셀 묶음 | **1NF 쪽으로 내렸다** (열을 셀 테이블로 쪼개지 않음) |

---

### 4-6. 원본 데이터 (부동산 · 확장)

#### `real_estate_transactions`

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `id` | 거래 PK | PK |
| `region_id` | 지역 | FK → `regions.id` |
| `property_type_code` | 부동산 유형 | FK → `property_types.code` |
| `deal_date` | 거래일 | |
| `area_m2` | 면적 | |
| `sale_price` | 매매가 | |
| `rent_price` | 전월세 | 선택 |
| `floor` | 층 | 선택 |
| `build_year` | 준공연도 | 선택 |
| `source_code` | 수집 출처 | FK → `etl_sources.code` |
| `created_at` | 적재 시각 | |

**완화 옵션**: `region_id` 대신 `region_large`/`mid`/`small` 문자열을 유지하면 **BCNF보다 내려간 것** (적재 단순화).

#### `population_stats` · `traffic_stats` (동일 패턴 예시)

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `id` | PK | PK |
| `region_id` | 지역 | FK → `regions.id` |
| `period_start` | 집계 시작 | date |
| `period_end` | 집계 끝 | date |
| `metric_code` 또는 전용 코드 | 지표 | FK 또는 별도 룩업 |
| `value` | 값 | numeric |
| `source_code` | 출처 | FK → `etl_sources.code` |
| `created_at` | 적재 시각 | |

---

### 4-7. 예측

#### `forecast_runs`

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `id` | PK | PK |
| `analysis_id` | 분석 | FK → `user_analyses.id` |
| `model_type_code` | 모델 | FK → `forecast_model_types.code` |
| `train_start_date` | 학습 시작 | |
| `train_end_date` | 학습 종료 | |
| `prediction_start_date` | 예측 시작 | |
| `prediction_end_date` | 예측 종료 | |
| `created_at` | 생성 시각 | |

#### `forecast_metric_entries` (BCNF: `metrics_json` 대체)

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `id` | PK | PK |
| `forecast_run_id` | 실행 | FK → `forecast_runs.id` ON DELETE CASCADE |
| `metric_key` | 예: `mae`, `rmse` | |
| `metric_value` | 수치 | numeric |

**완화 옵션**: 이 테이블 없이 `forecast_runs.metrics_json` 만 쓰면 **1NF 쪽으로 내렸다**.

#### `forecast_points`

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `id` | PK | PK |
| `forecast_run_id` | 실행 | FK → `forecast_runs.id` ON DELETE CASCADE |
| `target_date` | 시점 | |
| `actual_value` | 실제값 | NULL 허용 |
| `predicted_value` | 예측값 | |
| `lower_bound` | 하한 | |
| `upper_bound` | 상한 | |

---

### 4-8. 워드클라우드

#### `wordcloud_region_scopes`

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `code` | `kr`, `global` 등 | PK |

#### `wordcloud_categories`

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `id` | PK | PK |
| `code` | `agri`, `health` 등 | UNIQUE |

#### `wordcloud_subcategories`

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `id` | PK | PK |
| `category_id` | 대분류 | FK → `wordcloud_categories.id` |
| `code` | 중분류 코드 | category 내 UNIQUE |

#### `keyword_terms`

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `id` | PK | PK |
| `term_text` | 키워드 문자열 | |
| `category_id` | 대분류 | FK → `wordcloud_categories.id` |
| `subcategory_id` | 중분류 | FK → `wordcloud_subcategories.id`, NULL 허용 |
| `wc_region_code` | 워드클라우드 지역 구분 | FK → `wordcloud_region_scopes.code` |

#### `keyword_events`

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `id` | PK | PK |
| `keyword_term_id` | 키워드 | FK → `keyword_terms.id` |
| `source_code` | 수집 출처 | FK → `etl_sources.code` |
| `event_date` | 일자 | |
| `count_value` | 건수 | |

#### `wordcloud_agg`

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `id` | PK | PK |
| `keyword_term_id` | 키워드 | FK → `keyword_terms.id` |
| `aggregation_date` | 집계 시점 | |
| `count_value` | 원시 카운트 | |
| `weight` | 시각화 가중치 | |

**완화 옵션**: 집계 행에 `category`/`keyword` 문자열을 다시 넣어 조인을 줄이면 **2NF~3NF보다 낮게** 둔 것.

#### `wordcloud_terms` (`data.md` 호환·단순 캐시)

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `id` | PK | PK |
| `category_code` | 대분류 | FK → `wordcloud_categories.code` 권장 |
| `wc_region_code` | 지역 구분 | FK → `wordcloud_region_scopes.code` |
| `term_text` | 키워드 | |
| `weight` | 가중치 | |
| `updated_at` | 갱신 시각 | |

메인 페이지 **빠른 조회**용이면 `keyword_terms`+집계와 **중복**이므로 정규형은 **내려간 쪽**이다.

---

### 4-9. 서비스 · ETL

#### `analysis_snapshots`

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `id` | PK | PK |
| `page` | 페이지 ID | UNIQUE (`analysis-1` 등) |
| `line` | 라인 데이터 | jsonb, **1NF 쪽으로 내렸다** |
| `bar` | 바 데이터 | jsonb |
| `donut` | 도넛 데이터 | jsonb |
| `accents` | 색상 설정 | jsonb |
| `updated_at` | 갱신 시각 | |

#### `saved_builder_analyses`

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `id` | PK | PK |
| `user_id` | 유저 | FK → `users.id` |
| `title` | 제목 | |
| `keyword` | 키워드 | 자유 텍스트 유지 |
| `metric_code` | 지표 | FK → `metrics.code` |
| `created_at` | 저장 시각 | |

`data.md`의 `metric_label` 은 **`metrics.default_label` 조인**으로 대체. 목록에서 조인을 없애려고 `metric_label` 컬럼을 **같이 저장**하면 **2NF 근처로 내렸다**.

#### `etl_runs`

| 컬럼 | 설명 | 제약/비고 |
| --- | --- | --- |
| `id` | PK | PK |
| `source_code` | 어떤 ETL인지 | FK → `etl_sources.code` |
| `status_code` | 성공/실패 등 | FK → `etl_statuses.code` |
| `details` | 로그 | text |
| `created_at` | 실행 시각 | |

**완화 옵션**: `source`/`status` 를 자유 텍스트로 두면 룩업 없이 **3NF 쪽으로 내렸다**.

---

## 5. `data.md` ↔ 최종 테이블 대응

| `data.md` | 최종 (`data_NF.md`) |
| --- | --- |
| `users.status` 문자열 | `account_statuses` + `users.status_code` |
| `user_analyses` 의 이름·코드 열들 | `*_code` FK 다수 + `datasets`/`metrics` |
| `filter_json` | `user_analysis_filters` (또는 JSON 유지 시 완화) |
| `result_json` | 그대로 두되 “1NF 쪽 완화”로 명시 |
| `real_estate_transactions` 지역 3컬럼 | `regions` + `region_id` |
| `property_type`, `source_name` | `property_types`, `etl_sources` |
| `metrics_json` | `forecast_metric_entries` (또는 JSON 유지) |
| `wordcloud_terms` / `keyword_events` / `wordcloud_agg` | `keyword_terms` 중심 + 이벤트/집계 FK, 운영용 `wordcloud_terms` 병행 가능 |
| `saved_builder_analyses.metric` + `metric_label` | `metric_code` FK + `metrics.default_label` (라벨 중복 저장 시 완화) |

---

## 6. BCNF 방향과 “내렸다” 요약 (기존 논의 유지)

| 구역 | BCNF 방향 | 자주 쓰면 / 비효율이면 |
| --- | --- | --- |
| 유저·세션 | 상태 코드 테이블 | `CHECK` 텍스트만 → **3NF로 내렸다** |
| 룩업 | 타입·차트·집계·부동산·ETL 별 테이블 | 열 하나로 합침 → **3NF로 내렸다** |
| 지역 | `regions` + `region_id` | 문자열 3컬럼 유지 → **더 내려감** |
| 분석 필터 | 행 단위 필터 테이블 | `filter_json` 유지 → **1NF 쪽** |
| 결과·스냅샷 | 속성 단위 분해 | 큰 `jsonb` 유지 → **1NF 쪽** |
| 집계 | `keyword_term_id`만 | 문자열 중복 집계 → **2NF~3NF보다 낮게** |

---

## 7. 결론

- **`data.md`의 기능 범위는 유지**하면서, 반복되는 분류·지역·지표는 **테이블로 빼 BCNF에 가깝게** 정리했다.
- **스냅샷·요약 JSON·표 행 JSON·집계 캐시**는 운영·조회 효율을 위해 **단계를 내려** 두었다고 명시해 두었다.
- Supabase DDL은 `supabase_schema.sql` 과 병합할 때 **본 문서의 FK·이름**을 기준으로 맞추면 된다.
