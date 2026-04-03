-- 의료·교통·관광·환경 등 공공 API 원본·범용 분석 (ETL: category_public_bundle + etl_supabase.py)

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

comment on table public.public_category_raw is 'ETL: PD_*_API_PATH 공공데이터 item 원본';
comment on table public.public_category_analytics is 'ETL: 범용 차트·요약 (스키마 변경 가능)';
