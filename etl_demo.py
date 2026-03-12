import argparse
import json
import os
import random
import urllib.request


def parse_args():
  parser = argparse.ArgumentParser(description="운영/테스트용 ETL 적재 스크립트")
  parser.add_argument("--api-base", default=os.getenv("ET_API_BASE", "http://127.0.0.1:8000"))
  parser.add_argument("--etl-token", default=os.getenv("ETL_SHARED_SECRET", ""))
  return parser.parse_args()


def post(api_base: str, etl_token: str, path: str, payload: dict) -> dict:
  url = api_base.rstrip("/") + path
  data = json.dumps(payload).encode("utf-8")
  req = urllib.request.Request(url, data=data, method="POST")
  req.add_header("Content-Type", "application/json; charset=utf-8")
  if etl_token:
    req.add_header("X-ETL-Token", etl_token)
  with urllib.request.urlopen(req, timeout=10) as res:
    return json.loads(res.read().decode("utf-8"))


def main():
  args = parse_args()
  if not args.etl_token:
    raise SystemExit("ETL_SHARED_SECRET 또는 --etl-token 값을 설정해 주세요.")

  base_words = [
    {"text": "사과", "weight": 86},
    {"text": "배추", "weight": 72},
    {"text": "양파", "weight": 66},
    {"text": "쌀값", "weight": 64},
    {"text": "도매가격", "weight": 58},
    {"text": "기상", "weight": 52},
    {"text": "산지", "weight": 50},
    {"text": "수급", "weight": 46},
    {"text": "물가", "weight": 44},
  ]

  words = []
  for w in base_words:
    jitter = random.randint(-6, 9)
    words.append({"text": w["text"], "weight": max(0, w["weight"] + jitter)})

  r1 = post(
    args.api_base,
    args.etl_token,
    "/api/ingest/wordcloud",
    {"category": "agri", "region": "kr", "words": words},
  )

  # 분석 차트: line/bar/donut도 살짝 변화
  line = [random.randint(18, 80) for _ in range(12)]
  bar = [random.randint(6, 28) for _ in range(5)]
  donut = [random.randint(10, 50) for _ in range(4)]

  r2 = post(
    args.api_base,
    args.etl_token,
    "/api/ingest/analysis",
    {
      "page": "analysis-1",
      "line": line,
      "bar": bar,
      "donut": donut,
      "accents": {"line": "#6AE4FF", "bar": "#B79BFF"},
    },
  )

  print("OK:", r1, r2)
  print("적재 완료 후 브라우저에서 메인/분석1 페이지를 새로고침하면 최신 값이 반영됩니다.")


if __name__ == "__main__":
  main()

