import json
import random
import time
import urllib.request

API_BASE = "http://127.0.0.1:8000"


def post(path: str, payload: dict) -> dict:
  url = API_BASE + path
  data = json.dumps(payload).encode("utf-8")
  req = urllib.request.Request(url, data=data, method="POST")
  req.add_header("Content-Type", "application/json; charset=utf-8")
  with urllib.request.urlopen(req, timeout=10) as res:
    return json.loads(res.read().decode("utf-8"))


def main():
  # 워드클라우드: weight를 흔들어서 “연결 확인”하기
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
    "/api/ingest/wordcloud",
    {"category": "agri", "region": "kr", "words": words},
  )

  # 분석 차트: line/bar/donut도 살짝 변화
  line = [random.randint(18, 80) for _ in range(12)]
  bar = [random.randint(6, 28) for _ in range(5)]
  donut = [random.randint(10, 50) for _ in range(4)]

  r2 = post(
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
  print("다시 브라우저(메인/분석1)를 새로고침하면 값이 바뀐 걸 확인할 수 있습니다.")


if __name__ == "__main__":
  main()

