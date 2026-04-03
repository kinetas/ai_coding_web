"""
워드클라우드용: 용어가 특정 카테고리(의료·교통 등)와 얼마나 연관되는지 0~1 점수.

- WORDCLOUD_USE_ML_REL=1 일 때 활성(기본 비활성).
- scikit-learn 사용 가능하면 HashingVectorizer + SGD(log loss) 이진 분류(시드·타카테고리·불용어).
- 없으면 시드 부분일치 휴리스틱.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

_PIPE_CACHE: dict[str, Any] = {}


def _ml_enabled() -> bool:
  v = (os.getenv("WORDCLOUD_USE_ML_REL") or "").strip().lower()
  return v in ("1", "true", "yes", "on")


@lru_cache(maxsize=1)
def _try_sklearn():
  try:
    from sklearn.feature_extraction.text import HashingVectorizer
    from sklearn.linear_model import SGDClassifier
    from sklearn.pipeline import Pipeline as SkPipeline

    return SkPipeline, HashingVectorizer, SGDClassifier
  except Exception:
    return None


def _heuristic_score(term: str, category: str) -> float:
  from crawler.news_pipeline import BAR_SEEDS, CATEGORY_SEARCH_KR, CATEGORY_SEARCH_GLOBAL

  t = (term or "").strip().lower()
  if len(t) < 2:
    return 0.1
  seeds = [s.lower() for s in BAR_SEEDS.get(category, []) if s]
  seeds.append((CATEGORY_SEARCH_KR.get(category) or "").lower())
  seeds.append((CATEGORY_SEARCH_GLOBAL.get(category) or "").lower())
  for s in seeds:
    if len(s) >= 2 and (s in t or t in s):
      return min(1.0, 0.55 + 0.1 * min(len(t), 8))
  return 0.38


def _build_pipe(category: str):
  from crawler.news_pipeline import BAR_SEEDS, CATEGORY_SEARCH_KR, KR_STOPWORDS

  pack = _try_sklearn()
  if pack is None:
    return None
  SkPipeline, HashingVectorizer, SGDClassifier = pack

  pos = list(BAR_SEEDS.get(category, [])) + [CATEGORY_SEARCH_KR.get(category, ""), category]
  neg: list[str] = []
  for o, seeds in BAR_SEEDS.items():
    if o == category:
      continue
    neg.extend(seeds)
    neg.append(CATEGORY_SEARCH_KR.get(o, ""))
  neg.extend(list(KR_STOPWORDS)[:100])
  neg = [x for x in neg if x and len(str(x).strip()) >= 1]

  pos_list = [str(x) for x in pos if x]
  neg_list = [str(x) for x in neg if x]
  X = pos_list + neg_list
  y = [1] * len(pos_list) + [0] * len(neg_list)
  if len(set(y)) < 2:
    return None

  pipe = SkPipeline(
    [
      (
        "vec",
        HashingVectorizer(analyzer="char_wb", ngram_range=(2, 5), n_features=(2**15)),
      ),
      (
        "clf",
        SGDClassifier(loss="log_loss", max_iter=400, random_state=42, alpha=1e-5),
      ),
    ]
  )
  pipe.fit(X, y)
  return pipe


def _pipe_for(category: str):
  if category not in _PIPE_CACHE:
    _PIPE_CACHE[category] = _build_pipe(category)
  return _PIPE_CACHE[category]


def term_category_relevance(term: str, category: str) -> float:
  if not _ml_enabled():
    return 1.0
  pipe = _pipe_for(category)
  if pipe is None:
    return _heuristic_score(term, category)
  try:
    t = (term or "").strip() or "-"
    proba = pipe.predict_proba([t])[0]
    clf = pipe.named_steps["clf"]
    classes = list(getattr(clf, "classes_", []))
    if 1 in classes:
      return float(max(0.0, min(1.0, proba[classes.index(1)])))
    return float(max(0.0, min(1.0, max(proba))))
  except Exception:
    return _heuristic_score(term, category)


def apply_relevance_to_word_weights(
  words: list[dict[str, float]],
  category: str,
  *,
  top_n: int = 18,
  min_score: float | None = None,
) -> list[dict[str, float]]:
  if not _ml_enabled():
    return words[:top_n]
  floor = float((os.getenv("WORDCLOUD_ML_MIN_SCORE") or "0.25").strip() or "0.25") if min_score is None else min_score
  out: list[dict[str, float]] = []
  for w in words:
    t = str(w.get("text", ""))
    rel = term_category_relevance(t, category)
    weight = float(w.get("weight", 0)) * rel
    if weight < floor:
      continue
    out.append({"text": t[:64], "weight": round(max(1.0, weight), 2)})
  out.sort(key=lambda x: -x["weight"])
  return out[:top_n] if out else []
