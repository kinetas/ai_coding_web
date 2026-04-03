-- supabase_schema.sql / supabase_schema_nf.sql 로 만든 객체 제거용
-- Supabase SQL Editor에서 실행. public 스키마의 다른 커스텀 객체는 건드리지 않음.

-- 트리거는 테이블 삭제 시 함께 제거됨

-- 자식 → 부모 순서
DROP TABLE IF EXISTS public.forecast_points CASCADE;
DROP TABLE IF EXISTS public.forecast_metric_entries CASCADE;
DROP TABLE IF EXISTS public.forecast_runs CASCADE;

DROP TABLE IF EXISTS public.user_analysis_table_rows CASCADE;
DROP TABLE IF EXISTS public.user_analysis_chart_series CASCADE;
DROP TABLE IF EXISTS public.user_analysis_results CASCADE;
DROP TABLE IF EXISTS public.user_analysis_filters CASCADE;
DROP TABLE IF EXISTS public.user_analyses CASCADE;

DROP TABLE IF EXISTS public.population_stats CASCADE;
DROP TABLE IF EXISTS public.traffic_stats CASCADE;
DROP TABLE IF EXISTS public.real_estate_transactions CASCADE;

DROP TABLE IF EXISTS public.saved_builder_analyses CASCADE;

DROP TABLE IF EXISTS public.keyword_events CASCADE;
DROP TABLE IF EXISTS public.wordcloud_agg CASCADE;
DROP TABLE IF EXISTS public.keyword_terms CASCADE;
DROP TABLE IF EXISTS public.wordcloud_subcategories CASCADE;

-- NF 버전 wordcloud_terms (category_code FK) / 구버전 (category 텍스트) 동일 이름
DROP TABLE IF EXISTS public.wordcloud_terms CASCADE;

DROP TABLE IF EXISTS public.auth_sessions CASCADE;
DROP TABLE IF EXISTS public.users CASCADE;

DROP TABLE IF EXISTS public.metrics CASCADE;
DROP TABLE IF EXISTS public.datasets CASCADE;

DROP TABLE IF EXISTS public.analysis_snapshots CASCADE;
DROP TABLE IF EXISTS public.etl_runs CASCADE;

DROP TABLE IF EXISTS public.regions CASCADE;

DROP TABLE IF EXISTS public.wordcloud_categories CASCADE;
DROP TABLE IF EXISTS public.wordcloud_region_scopes CASCADE;

-- 룩업 (구 스키마에는 없을 수 있음 — IF EXISTS)
DROP TABLE IF EXISTS public.account_statuses CASCADE;
DROP TABLE IF EXISTS public.source_categories CASCADE;
DROP TABLE IF EXISTS public.analysis_types CASCADE;
DROP TABLE IF EXISTS public.chart_types CASCADE;
DROP TABLE IF EXISTS public.aggregation_methods CASCADE;
DROP TABLE IF EXISTS public.property_types CASCADE;
DROP TABLE IF EXISTS public.etl_statuses CASCADE;
DROP TABLE IF EXISTS public.etl_sources CASCADE;
DROP TABLE IF EXISTS public.forecast_model_types CASCADE;

-- 공통 함수
DROP FUNCTION IF EXISTS public.set_updated_at() CASCADE;
