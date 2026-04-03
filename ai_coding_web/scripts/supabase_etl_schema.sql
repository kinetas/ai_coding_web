-- Supabase SQL Editor에서 한 번 실행하세요.
-- 앱의 SQLite 스키마(analysis_snapshots, wordcloud_terms, etl_runs)와 동일한 모양입니다.
-- ETL은 service_role 키로 적재하며 RLS를 우회합니다.

create table if not exists public.analysis_snapshots (
  id bigint generated always as identity primary key,
  page text not null,
  line jsonb not null default '[]'::jsonb,
  bar jsonb not null default '[]'::jsonb,
  donut jsonb not null default '[]'::jsonb,
  accents jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now(),
  constraint analysis_snapshots_page_key unique (page)
);

create index if not exists idx_analysis_snapshots_page on public.analysis_snapshots (page);

create table if not exists public.wordcloud_terms (
  id bigint generated always as identity primary key,
  category text not null,
  region text not null,
  text text not null,
  weight double precision not null,
  updated_at timestamptz not null default now(),
  constraint uq_wordcloud_term_scope unique (category, region, text)
);

create index if not exists idx_wordcloud_category_region on public.wordcloud_terms (category, region);

create table if not exists public.etl_runs (
  id bigint generated always as identity primary key,
  source text not null,
  status text not null,
  details text not null default '',
  created_at timestamptz not null default now()
);

create index if not exists idx_etl_runs_source on public.etl_runs (source);
create index if not exists idx_etl_runs_created_at on public.etl_runs (created_at desc);

alter table public.analysis_snapshots enable row level security;
alter table public.wordcloud_terms enable row level security;
alter table public.etl_runs enable row level security;

-- anon(프론트)에서 읽기만 허용하려면 아래 정책을 켭니다. 적재는 service_role만 사용하세요.
drop policy if exists "Allow public read analysis_snapshots" on public.analysis_snapshots;
create policy "Allow public read analysis_snapshots"
  on public.analysis_snapshots for select to anon using (true);

drop policy if exists "Allow public read wordcloud_terms" on public.wordcloud_terms;
create policy "Allow public read wordcloud_terms"
  on public.wordcloud_terms for select to anon using (true);

-- etl_runs는 운영 시 숨기는 편이 좋아 읽기 정책을 두지 않습니다.
