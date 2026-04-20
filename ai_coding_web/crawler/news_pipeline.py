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
import functools
import html
import logging
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

logger = logging.getLogger(__name__)


def _retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0):
  """지수 백오프로 max_retries 회 재시도하는 데코레이터 (네트워크 호출용)."""
  def decorator(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
      last_exc = None
      for attempt in range(max_retries):
        try:
          return fn(*args, **kwargs)
        except Exception as exc:
          last_exc = exc
          delay = base_delay * (2 ** attempt)
          logger.warning(
            "[retry] %s 실패 (시도 %d/%d), %.1f초 후 재시도: %s",
            fn.__name__, attempt + 1, max_retries, delay, exc,
          )
          time.sleep(delay)
      logger.error("[retry] %s %d회 모두 실패: %s", fn.__name__, max_retries, last_exc)
      raise last_exc
    return wrapper
  return decorator

# 앱 카테고리 코드 → 사용자 지정 검색어 (한국 / 글로벌)
CATEGORY_SEARCH_KR: dict[str, str] = {
  "agri": "농산물 가격",
}

CATEGORY_SEARCH_GLOBAL: dict[str, str] = {
  "agri": "agricultural price OR farm price OR crop price",
}

# 주요 농산물 품목별 검색어 — 품목 키워드 수집 및 가격-뉴스 연결에 사용
CROP_SEARCH_KR: dict[str, list[str]] = {
  "배추": ["배추 가격", "배추 작황", "배추 폭등", "배추 폭락"],
  "무": ["무 가격", "무 작황", "무 생산"],
  "사과": ["사과 가격", "사과 작황", "사과 수확"],
  "대파": ["대파 가격", "대파 폭등", "대파 작황"],
  "양파": ["양파 가격", "양파 작황", "양파 수급"],
  "감자": ["감자 가격", "감자 작황", "감자 생산"],
  "고추": ["고추 가격", "고추 작황", "고춧가루 가격"],
  "쌀": ["쌀 가격", "쌀 생산량", "쌀 수급"],
  "토마토": ["토마토 가격", "토마토 작황"],
  "오이": ["오이 가격", "오이 작황"],
}

# 카테고리별 RSS (검색 피드 실패 시에만 순서대로 시도)
DIRECT_FEEDS_KR: dict[str, list[str]] = {
  "agri": ["https://www.yna.co.kr/rss/economy.xml", "https://www.korea.kr/rss/economy.xml"],
}

DIRECT_FEEDS_GLOBAL: dict[str, list[str]] = {
  "agri": ["http://feeds.bbci.co.uk/news/business/rss.xml"],
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

# 분석 페이지(차트)와 집계할 카테고리 매핑
CATEGORY_TO_ANALYSIS_PAGE: dict[str, str] = {
  "agri": "analysis-1",
}

BAR_SEEDS: dict[str, list[str]] = {
  "agri": ["배추", "무", "사과", "대파", "양파", "감자", "고추", "쌀", "작황", "수급", "폭등", "폭락"],
}

KR_STOPWORDS = frozenset(
  """
  및 또는 은 는 이 가 을 를 에 의 에서 로 와 과 도 만 또 그 이거 저희 다른 통해 위한 있다 없다 대한
  google 관련 뉴스 minutes ago hour hours news 연합뉴스 뉴스1 뉴시스 기자 무단 전재 재배포
  한국 지난 올해 내년 지역 전국 기준 대비 통해 위해 따라 경우 이후 현재 오는 정도 수준 이상 이하
  분야 상황 활용 운영 실시 추진 관련 개선 확대 지원 강화 마련 시행 제공 발표 계획 진행 예정 완료
  서울 정부 국가 국내 국외 국제 정책 사업 제도 문제 해결 필요 중요 주요 핵심
  대통령 국회 장관 위원회 부처 당국 기관 기업 업계 단체 협회
  억원 조원 만원 천원 억달러 예산 비용 투자 지출 재원
  오늘 어제 내일 이번 다음 최근 지금 당시 그동안 올해부터 내년부터
  하지만 그러나 따라서 때문에 그리고 또한 아울러 한편
  """.split()
)

# 카테고리별 도메인 특수 불용어 (공통 불용어 외 추가)
CATEGORY_STOPWORDS_KR: dict[str, frozenset[str]] = {
  "agri": frozenset([
    "농산물", "농업", "농가", "농촌", "농식품", "농림", "작물", "품목",
    "출하", "도매", "소매", "유통", "판매", "구매", "구입", "공급", "수요",
    "시장", "물가", "상승", "하락", "변동",
  ]),
}

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
  url: str = ""


@_retry_with_backoff(max_retries=3, base_delay=2.0)
def fetch_rss_items(feed_url: str, *, timeout: float = 22.0, max_items: int = DEFAULT_MAX_ITEMS) -> list[NewsItem]:
  """단일 RSS URL에서 항목만 파싱(HTTP 오류는 예외). 네트워크 실패 시 지수 백오프 재시도."""
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
    url = (getattr(entry, "link", None) or "").strip()
    if title:
      out.append(NewsItem(title=title, summary=summary, published_at=pub, url=url))
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
  """1) 키워드 Google News RSS → 2) 실패 시 섹션 피드 폴백(카테고리 키워드 포함 기사만 필터링)."""
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

  # 섹션 피드는 광범위하므로 카테고리 검색 토큰이 포함된 기사만 남김
  raw = _collect_from_feed_urls(urls, max_items=max_items * 4)
  query_tokens = set(_TOKEN_RE.findall(query.lower()))
  filtered = [
    it for it in raw
    if any(tok in (it.title + " " + it.summary).lower() for tok in query_tokens)
  ]
  # 필터 결과가 너무 적으면 원본 사용 (아예 없는 것보다 낫기 때문)
  return filtered[:max_items] if len(filtered) >= 5 else raw[:max_items]


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
  """카테고리 검색어 자체(및 구성 토큰) + 카테고리별 도메인 특수 불용어를 워드클라우드에서 제외."""
  terms: set[str] = set()
  # 검색어 토큰 제거
  for qmap in (CATEGORY_SEARCH_KR, CATEGORY_SEARCH_GLOBAL):
    q = qmap.get(category, "")
    for tok in _TOKEN_RE.findall(q.lower()):
      terms.add(tok)
  # 카테고리별 도메인 특수 불용어 추가
  domain_stops = CATEGORY_STOPWORDS_KR.get(category, frozenset())
  for w in domain_stops:
    terms.add(w.lower())
    # 토큰 단위로도 추가 (복합어 구성 단어 분리)
    for tok in _TOKEN_RE.findall(w.lower()):
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


def pipeline_crop_keywords(crop: str, region: str = "kr") -> list[dict[str, float]]:
  """특정 농산물 품목 뉴스에서 키워드를 수집합니다. 가격-뉴스 상관 분석용."""
  queries = CROP_SEARCH_KR.get(crop) if region == "kr" else None
  if not queries:
    return []
  all_items: list[NewsItem] = []
  seen: set[str] = set()
  for q in queries:
    url = _google_news_search_rss_url(q, region)
    try:
      items = fetch_rss_items(url, max_items=60)
      for it in items:
        key = it.title.strip()[:160]
        if key not in seen:
          seen.add(key)
          all_items.append(it)
    except Exception:
      continue
  if not all_items:
    return []
  return build_word_weights(all_items, category="agri", top_n=15)


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


def fetch_agri_news(*, crop: str | None = None, limit: int = 30, region: str = "kr") -> list[dict]:
  """농업 뉴스 목록(제목+링크+날짜) 반환. crop 지정 시 해당 품목 전용 검색."""
  if crop and crop in CROP_SEARCH_KR:
    queries = CROP_SEARCH_KR[crop]
    items: list[NewsItem] = []
    seen: set[str] = set()
    for q in queries:
      feed_url = _google_news_search_rss_url(q, region)
      try:
        batch = fetch_rss_items(feed_url, max_items=limit)
        for it in batch:
          key = it.title.strip()[:160]
          if key not in seen:
            seen.add(key)
            items.append(it)
            if len(items) >= limit:
              break
      except Exception:
        continue
  else:
    items = collect_for_category("agri", region, max_items=limit)

  return [
    {
      "title": it.title,
      "url": it.url,
      "summary": (it.summary or "")[:200],
      "published_at": it.published_at.isoformat() if it.published_at else None,
    }
    for it in items[:limit]
    if it.url
  ]
