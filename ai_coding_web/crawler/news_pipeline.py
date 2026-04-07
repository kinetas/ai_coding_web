"""
카테고리별 검색어로 뉴스 RSS를 수집합니다.

- 한국: Google News 검색(농산물·의료·교통·관광·환경) → 해당 키워드 기사만 모아 워드클라우드·차트에 반영
- 검색 실패 시에만 섹션 RSS(DIRECT_FEEDS)로 폴백

워드클라우드 ETL 환경변수(선택):
- NEWS_RSS_MAX_ITEMS: 피드당 합산 최대 기사 수(기본 80, 상한 250)
- WORDCLOUD_MIN_TERM_COUNT: 동일 카테고리·지역 코퍼스에서 토큰 출현 횟수 하한(기본 15, 미만은 DB 후보에서 제외)
- WORDCLOUD_TOP_N: 위 조건을 통과한 단어 중 빈도 상위 개수(기본 15)
"""
from __future__ import annotations

import calendar
import html
import os
import re
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable
from urllib.parse import quote_plus

import feedparser
import httpx

# 앱 카테고리 코드 → 사용자 지정 검색어 (한국 / 글로벌)
CATEGORY_SEARCH_KR: dict[str, str] = {
  "agri": "농산물",
  "health": "의료",
  "traffic": "교통",
  "tour": "관광",
  "env": "환경",
}

CATEGORY_SEARCH_GLOBAL: dict[str, str] = {
  "agri": "agricultural products OR farming",
  "health": "healthcare OR medical",
  "traffic": "transportation OR traffic",
  "tour": "tourism OR travel",
  "env": "environment OR climate",
}

# 카테고리별 RSS (검색 피드 실패 시에만 순서대로 시도)
DIRECT_FEEDS_KR: dict[str, list[str]] = {
  "agri": ["https://www.yna.co.kr/rss/economy.xml", "https://www.korea.kr/rss/economy.xml"],
  "health": ["https://www.yna.co.kr/rss/health.xml"],
  "traffic": ["https://www.yna.co.kr/rss/society.xml"],
  "tour": ["https://www.yna.co.kr/rss/culture.xml", "https://www.korea.kr/rss/culture.xml"],
  "env": ["https://www.yna.co.kr/rss/local.xml"],
}

DIRECT_FEEDS_GLOBAL: dict[str, list[str]] = {
  "agri": ["http://feeds.bbci.co.uk/news/business/rss.xml"],
  "health": ["http://feeds.bbci.co.uk/news/health/rss.xml"],
  "traffic": ["http://feeds.bbci.co.uk/news/technology/rss.xml"],
  "tour": ["http://feeds.bbci.co.uk/news/world/rss.xml"],
  "env": ["http://feeds.bbci.co.uk/news/science_and_environment/rss.xml"],
}


def _google_news_search_rss_url(query: str, region: str) -> str:
  q = quote_plus(query)
  if region == "kr":
    return f"https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko"
  return f"https://news.google.com/rss/search?q={q}&hl=en&gl=US&ceid=US:en"

# 피드에서 가져올 최대 기사 수(합산). NEWS_RSS_MAX_ITEMS 로 덮어씀.
DEFAULT_MAX_ITEMS = 80


def news_rss_max_items() -> int:
  raw = (os.getenv("NEWS_RSS_MAX_ITEMS") or "").strip()
  if raw:
    try:
      return max(15, min(250, int(raw)))
    except ValueError:
      pass
  return DEFAULT_MAX_ITEMS


def _wordcloud_min_term_count() -> int:
  raw = (os.getenv("WORDCLOUD_MIN_TERM_COUNT") or "3").strip()
  try:
    return max(1, int(raw))
  except ValueError:
    return 3


def _wordcloud_top_n() -> int:
  raw = (os.getenv("WORDCLOUD_TOP_N") or "25").strip()
  try:
    return max(1, min(80, int(raw)))
  except ValueError:
    return 25

# HTTP: 브라우저에 가깝게(일부 서버가 비표준 UA를 거부하는 경우 완화)
_HTTP_HEADERS = {
  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
  "Accept": "application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
}

# 분석 페이지(차트)와 집계할 카테고리 매핑 — env는 차트 슬롯이 없어 워드클라우드만 별도 적재
CATEGORY_TO_ANALYSIS_PAGE: dict[str, str] = {
  "agri": "analysis-1",
  "health": "analysis-2",
  "traffic": "analysis-3",
  "tour": "analysis-4",
  "env": "analysis-5",
}

BAR_SEEDS: dict[str, list[str]] = {
  "agri": ["농산물", "농업", "수출", "가격", "채소", "과일", "farm", "crop", "price"],
  "health": ["의료", "병원", "치료", "환자", "백신", "hospital", "patient", "health"],
  "traffic": ["교통", "지하철", "버스", "도로", "subway", "bus", "train", "traffic"],
  "tour": ["관광", "여행", "호텔", "항공", "travel", "tour", "hotel", "flight"],
  "env": ["환경", "기후", "탄소", "미세먼지", "climate", "carbon", "environment"],
}

KR_STOPWORDS = frozenset(
  """
  및 또는 은 는 이 가 을 를 에 의 에서 로 와 과 도 만 또 그 이거 저희 다른 통해 위한 있다 없다 대한
  google 관련 뉴스 minutes ago hour hours news 연합뉴스 뉴스1 뉴시스 기자 무단 전재 재배포
  """.split()
)

# 워드클라우드: HTML 잔재·포털·도메인 조각 등 (형식/출처 노이즈)
WORDCLOUD_NOISE_TOKENS = frozenset(
  """
  nbsp quot amp apos lt gt semi copy reg trade sup1 sup2 sup3 hellip mdash ndash
  laquo raquo bull middot para sect curren ordm macr acute
  com net org edu gov mil int info biz name io app dev
  www href src alt html htm xml rss cdata utf utf8 div span img strong em b u font
  script style table tr td br link meta body head title
  http https mailto ssl tls
  daum naver kakao nate yonhap yna korea bbc bbci reuters ap afp cnn
  feedburner feeds wordpress blogspot tistory go
  """.split()
)

_TOKEN_RE = re.compile(r"[가-힣]{2,}|[A-Za-z]{3,}")


def _normalize_for_wordcloud_text(s: str) -> str:
  """HTML 엔티티·URL·흔한 도메인 표기를 걷어내 토큰 노이즈를 줄입니다."""
  t = html.unescape(s or "")
  t = t.replace("\u00a0", " ").replace("\ufeff", "")
  t = re.sub(r"https?://[^\s<>\"']+", " ", t, flags=re.I)
  t = re.sub(r"\bmailto:[^\s<>\"']+", " ", t, flags=re.I)
  t = re.sub(r"\bwww\.[^\s<>\"'\]]+", " ", t, flags=re.I)
  t = re.sub(
    r"\b[a-z0-9][a-z0-9-]{0,48}\.(?:com|net|org|co\.kr|go\.kr|ne\.jp|re\.kr|ac\.kr|kr)(?:/[^\s]*)?\b",
    " ",
    t,
    flags=re.I,
  )
  t = re.sub(r"&[#!]?[a-zA-Z0-9]{1,24};", " ", t)
  return t


def _utc_from_struct(st: time.struct_time | None) -> datetime | None:
  if not st:
    return None
  try:
    return datetime.fromtimestamp(calendar.timegm(st), tz=timezone.utc)
  except Exception:
    return None


@dataclass
class NewsItem:
  title: str
  summary: str
  published_at: datetime | None


def fetch_rss_items(feed_url: str, *, timeout: float = 22.0, max_items: int = DEFAULT_MAX_ITEMS) -> list[NewsItem]:
  """단일 RSS URL에서 항목만 파싱(HTTP 오류는 예외)."""
  with httpx.Client(timeout=timeout, headers=_HTTP_HEADERS, follow_redirects=True) as client:
    r = client.get(feed_url)
    r.raise_for_status()
    raw = r.text

  parsed = feedparser.parse(raw)

  out: list[NewsItem] = []
  for entry in getattr(parsed, "entries", []) or []:
    title = (getattr(entry, "title", None) or "").strip()
    summary = (getattr(entry, "summary", None) or getattr(entry, "description", None) or "").strip()
    pub = _utc_from_struct(getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None))
    if title:
      out.append(NewsItem(title=title, summary=summary, published_at=pub))
    if len(out) >= max_items:
      break
  return out


def _collect_from_feed_urls(urls: list[str], *, max_items: int) -> list[NewsItem]:
  out: list[NewsItem] = []
  seen: set[str] = set()
  for url in urls:
    if len(out) >= max_items:
      break
    try:
      need = max_items - len(out)
      batch = fetch_rss_items(url, max_items=need + 5)
    except Exception:
      continue
    for it in batch:
      key = it.title.strip()[:160]
      if key in seen:
        continue
      seen.add(key)
      out.append(it)
      if len(out) >= max_items:
        break
  return out


def collect_for_category(category: str, region: str, *, max_items: int | None = None) -> list[NewsItem]:
  """1) 키워드 Google News RSS → 2) 실패 시 섹션 피드 폴백."""
  if max_items is None:
    max_items = news_rss_max_items()
  qmap = CATEGORY_SEARCH_KR if region == "kr" else CATEGORY_SEARCH_GLOBAL
  query = qmap.get(category)
  if not query:
    return []

  search_url = _google_news_search_rss_url(query, region)
  try:
    items = _collect_from_feed_urls([search_url], max_items=max_items)
    if items:
      return items
  except Exception:
    pass

  feed_map = DIRECT_FEEDS_KR if region == "kr" else DIRECT_FEEDS_GLOBAL
  urls = feed_map.get(category, [])
  if not urls:
    return []
  return _collect_from_feed_urls(urls, max_items=max_items)


def category_keyword_label(category: str, region: str) -> str:
  m = CATEGORY_SEARCH_KR if region == "kr" else CATEGORY_SEARCH_GLOBAL
  return m.get(category, category)


def tokenize(text: str) -> list[str]:
  text_l = _normalize_for_wordcloud_text(text).lower()
  found = _TOKEN_RE.findall(text_l)
  skip = KR_STOPWORDS | WORDCLOUD_NOISE_TOKENS
  return [t for t in found if t not in skip and len(t) >= 2]


def _merge_item_texts(items: Iterable[NewsItem]) -> str:
  parts: list[str] = []
  for it in items:
    parts.append(it.title)
    if it.summary:
      parts.append(re.sub(r"<[^>]+>", " ", it.summary))
  return "\n".join(parts)


def _category_stopwords(category: str) -> frozenset[str]:
  """카테고리 검색어 자체(및 구성 토큰)를 워드클라우드에서 제외."""
  terms: set[str] = set()
  for qmap in (CATEGORY_SEARCH_KR, CATEGORY_SEARCH_GLOBAL):
    q = qmap.get(category, "")
    for tok in _TOKEN_RE.findall(q.lower()):
      terms.add(tok)
  return frozenset(terms)


def build_word_weights(
  entries: list[NewsItem],
  *,
  category: str,
  top_n: int | None = None,
  min_term_count: int | None = None,
) -> list[dict[str, float]]:
  """카테고리별 수집 텍스트 전체에 대해 토큰 빈도를 집계한 뒤, 최소 출현 횟수·상위 N만 워드클라우드 후보로 씁니다."""
  tn = _wordcloud_top_n() if top_n is None else max(1, min(80, top_n))
  mtc = _wordcloud_min_term_count() if min_term_count is None else max(1, min_term_count)

  blob = _merge_item_texts(entries)
  toks = tokenize(blob)
  if not toks:
    return []
  counts = Counter(toks)
  cat_stop = _category_stopwords(category)
  candidates = [(w, c) for w, c in counts.items() if c >= mtc and w not in cat_stop]
  candidates.sort(key=lambda x: (-x[1], x[0]))
  selected = candidates[:tn]
  if not selected:
    return []
  max_c = float(selected[0][1])
  words: list[dict[str, float]] = []
  for w, c in selected:
    weight = max(1.0, round(100.0 * float(c) / max_c, 2))
    words.append({"text": w[:64], "weight": weight})
  from crawler.term_category_ml import apply_relevance_to_word_weights

  return apply_relevance_to_word_weights(words, category, top_n=tn)


def _empty_line_bar_donut() -> tuple[list[float], list[float], list[float]]:
  line = [12, 14, 13, 15, 16, 18, 17, 19, 20, 21, 22, 24]
  bar = [10, 12, 11, 14, 13]
  donut = [40, 25, 20, 15]
  return line, bar, donut


def build_analysis_payload(category: str, region: str, entries: list[NewsItem]) -> dict:
  """12일 라인, 시드 키워드 bar, 요일대 donut + accents."""
  del region  # 동일 로직; 향후 지역별 분기용
  accents = {"line": "#6AE4FF", "bar": "#B79BFF"}
  if category in ("agri", "health"):
    accents = {"line": "#9AF7D0", "bar": "#6AE4FF"}
  if category in ("traffic", "tour", "env"):
    accents = {"line": "#7CFCA0", "bar": "#5BC0EB"} if category == "env" else {"line": "#FFD36A", "bar": "#FF7AD9"}

  if len(entries) < 3:
    line, bar, donut = _empty_line_bar_donut()
    return {"line": line, "bar": bar, "donut": donut, "accents": accents}

  today = datetime.now(timezone.utc).date()
  day_starts = [today - timedelta(days=11 - i) for i in range(12)]
  day_index = {d: i for i, d in enumerate(day_starts)}
  line_counts = [0] * 12
  wd_counts = [0, 0, 0, 0]

  for it in entries:
    if not it.published_at:
      continue
    d = it.published_at.date()
    if d in day_index:
      line_counts[day_index[d]] += 1
    wd = it.published_at.weekday()
    if wd <= 3:
      wd_counts[0] += 1
    elif wd == 4:
      wd_counts[1] += 1
    elif wd == 5:
      wd_counts[2] += 1
    else:
      wd_counts[3] += 1

  if sum(line_counts) == 0:
    line_counts = [max(1, len(entries) // 12 + (1 if i < len(entries) % 12 else 0)) for i in range(12)]

  base = min(line_counts) or 1
  line = [max(4.0, float(c) / base * 18.0) for c in line_counts]
  line = [round(x, 2) for x in line]

  seeds = BAR_SEEDS.get(category, list(BAR_SEEDS.values())[0])
  blob = " ".join((it.title + " " + it.summary).lower() for it in entries)
  bar_raw = []
  for s in seeds[:8]:
    bar_raw.append((s, blob.count(s.lower())))
  bar_raw.sort(key=lambda x: x[1], reverse=True)
  if bar_raw[0][1] == 0:
    bar = [float(x) for x in [12, 16, 14, 18, 15]]
  else:
    top5 = bar_raw[:5]
    m = max(1, top5[0][1])
    bar = [max(4.0, round(28.0 * c / m, 2)) for _, c in top5]
    while len(bar) < 5:
      bar.append(8.0)

  total_wd = sum(wd_counts) or 1
  donut = [max(5.0, round(100.0 * c / total_wd, 2)) for c in wd_counts]

  return {"line": line, "bar": bar, "donut": donut, "accents": accents}


_CRAWL_STEPS = [80, 150, 250]  # 단어 부족 시 단계적으로 더 많은 기사 수집
_WORDCLOUD_MIN_WORDS = 20     # 카테고리당 목표 최소 단어 종류


def pipeline_wordcloud(category: str, region: str) -> list[dict[str, float]]:
  words: list[dict[str, float]] = []
  for max_items in _CRAWL_STEPS:
    entries = collect_for_category(category, region, max_items=max_items)
    words = build_word_weights(entries, category=category)
    if len(words) >= _WORDCLOUD_MIN_WORDS:
      break
  return words


def pipeline_analysis(page: str, *, region_kr: bool = True) -> dict:
  cat = None
  for c, p in CATEGORY_TO_ANALYSIS_PAGE.items():
    if p == page:
      cat = c
      break
  if not cat:
    line, bar, donut = _empty_line_bar_donut()
    return {"line": line, "bar": bar, "donut": donut, "accents": {"line": "#6AE4FF", "bar": "#B79BFF"}}
  region = "kr" if region_kr else "global"
  entries = collect_for_category(cat, region)
  body = build_analysis_payload(cat, region, entries)
  return body
