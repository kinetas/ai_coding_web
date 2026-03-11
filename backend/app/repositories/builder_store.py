from __future__ import annotations

import random
import uuid
from typing import Dict, List

from backend.app.core.time import utc_now_iso


class BuilderStore:
  def __init__(self):
    # user -> list[dict]
    self._saved: Dict[str, List[dict]] = {}

  def list_saved(self, user: str) -> List[dict]:
    u = (user or "").strip() or "anonymous"
    return list(self._saved.get(u, []))

  def save(self, user: str, title: str, keyword: str, metric: str, metric_label: str) -> dict:
    u = (user or "").strip() or "anonymous"
    item = {
      "id": uuid.uuid4().hex[:12],
      "user": u,
      "title": title,
      "keyword": keyword,
      "metric": metric,
      "metric_label": metric_label,
      "saved_at": utc_now_iso(),
    }
    self._saved.setdefault(u, [])
    self._saved[u].insert(0, item)
    self._saved[u] = self._saved[u][:50]
    return item

  def build_metric(self, keyword: str, metric: str) -> dict:
    # 데모: keyword/metric에 따라 시드만 살짝 바꿔서 일관된 형태의 시계열 생성
    seed = abs(hash((keyword or "", metric or ""))) % 10_000
    rnd = random.Random(seed)

    line = [rnd.randint(14, 78) for _ in range(12)]
    bar = [rnd.randint(6, 28) for _ in range(5)]

    accents = {"line": "#6AE4FF", "bar": "#B79BFF"}
    if metric == "user_count":
      accents = {"line": "#9AF7D0", "bar": "#6AE4FF"}
    elif metric == "price_avg":
      accents = {"line": "#6AE4FF", "bar": "#B79BFF"}
    elif metric == "revenue":
      accents = {"line": "#FFD36A", "bar": "#FF7AD9"}

    return {"line": line, "bar": bar, "accents": accents}

