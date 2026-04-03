-- ETL 저장소와 코드(etl_supabase.py / at_price_trend.py) 정합 — idempotent, 여러 번 실행 가능.
-- Supabase SQL Editor에서 실행.

-- 농산물 심층 분석(지역·분포·추정)
create table if not exists public.agri_price_analytics (
  id bigint generated always as identity primary key,
  slug text not null default 'latest',
  region_stats jsonb not null default '[]'::jsonb,
  overall jsonb not null default '{}'::jsonb,
  forecast jsonb not null default '{}'::jsonb,
  distribution jsonb not null default '{}'::jsonb,
  chart_bundle jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now(),
  constraint agri_price_analytics_slug_key unique (slug)
);

alter table public.agri_price_analytics add column if not exists source text not null default 'data_go_kr';
alter table public.agri_price_analytics add column if not exists meta jsonb not null default '{}'::jsonb;

create index if not exists idx_agri_price_analytics_slug on public.agri_price_analytics (slug);

alter table public.agri_price_analytics enable row level security;

drop policy if exists "Allow public read agri_price_analytics" on public.agri_price_analytics;
create policy "Allow public read agri_price_analytics"
  on public.agri_price_analytics for select to anon using (true);

comment on table public.agri_price_analytics is 'ETL: etl_supabase.py _upsert_agri_analytics / crawler/at_price_trend.fetch_full_agri_from_env';

-- 원본 API item[] (파싱된 dict 배열)
create table if not exists public.agri_price_raw (
  id bigint generated always as identity primary key,
  slug text not null default 'latest',
  items jsonb not null default '[]'::jsonb,
  api_meta jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now(),
  constraint agri_price_raw_slug_key unique (slug)
);

alter table public.agri_price_raw add column if not exists source text not null default 'data_go_kr';
alter table public.agri_price_raw add column if not exists meta jsonb not null default '{}'::jsonb;

create index if not exists idx_agri_price_raw_slug on public.agri_price_raw (slug);

alter table public.agri_price_raw enable row level security;

drop policy if exists "Allow public read agri_price_raw" on public.agri_price_raw;
create policy "Allow public read agri_price_raw"
  on public.agri_price_raw for select to anon using (true);

comment on table public.agri_price_raw is 'ETL: etl_supabase.py _upsert_agri_price_raw — 공공데이터 포털 JSON item 원본';

-- public_category_* 는 scripts/supabase_public_category.sql 과 동일 (SQL Editor에 함께 붙여 넣거나 해당 파일 실행)
create table if not exists public.public_category_raw (
  id bigint generated always as identity primary key,
  category_code text not null,
  slug text not null default 'latest',
  items jsonb not null default '[]'::jsonb,
  api_meta jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now(),
  constraint public_category_raw_cat_slug_key unique (category_code, slug)
);
alter table public.public_category_raw add column if not exists source text not null default 'data_go_kr';
alter table public.public_category_raw add column if not exists meta jsonb not null default '{}'::jsonb;
create index if not exists idx_public_category_raw_cat on public.public_category_raw (category_code);
alter table public.public_category_raw enable row level security;
drop policy if exists "Allow public read public_category_raw" on public.public_category_raw;
create policy "Allow public read public_category_raw"
  on public.public_category_raw for select to anon using (true);

create table if not exists public.public_category_analytics (
  id bigint generated always as identity primary key,
  category_code text not null,
  slug text not null default 'latest',
  chart_bundle jsonb not null default '{}'::jsonb,
  summary jsonb not null default '{}'::jsonb,
  distribution jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now(),
  constraint public_category_analytics_cat_slug_key unique (category_code, slug)
);
alter table public.public_category_analytics add column if not exists source text not null default 'data_go_kr';
alter table public.public_category_analytics add column if not exists meta jsonb not null default '{}'::jsonb;
create index if not exists idx_public_category_analytics_cat on public.public_category_analytics (category_code);
alter table public.public_category_analytics enable row level security;
drop policy if exists "Allow public read public_category_analytics" on public.public_category_analytics;
create policy "Allow public read public_category_analytics"
  on public.public_category_analytics for select to anon using (true);

-- 조사일별 품목 스냅샷 (앱 조회·재분석은 DB 우선)
create table if not exists public.agri_price_history (
  id bigint generated always as identity primary key,
  exmn_ymd text not null,
  item_key text not null,
  item_cd text,
  vrty_cd text,
  grd_cd text,
  se_cd text,
  payload jsonb not null default '{}'::jsonb,
  ingested_at timestamptz not null default now(),
  constraint agri_price_history_exmn_item_key unique (exmn_ymd, item_key)
);
create index if not exists idx_agri_price_history_exmn on public.agri_price_history (exmn_ymd desc);
create index if not exists idx_agri_price_history_item_cd on public.agri_price_history (item_cd, exmn_ymd desc);
alter table public.agri_price_history enable row level security;
drop policy if exists "Allow public read agri_price_history" on public.agri_price_history;
create policy "Allow public read agri_price_history"
  on public.agri_price_history for select to anon using (true);
comment on table public.agri_price_history is 'ETL: API item payload, scripts/supabase_agri_price_history.sql 동일';
