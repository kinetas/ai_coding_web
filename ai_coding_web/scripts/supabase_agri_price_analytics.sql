-- 농산물 공공데이터 ETL 심층 분석(지역·분포·단기 추정) 저장
-- Supabase SQL Editor에서 한 번 실행(이미 있으면 생략).

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

-- 공공데이터 API 원본 행(items.item[] 등 파싱 결과) — 가공 전 스냅샷
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
