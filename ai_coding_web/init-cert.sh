#!/bin/bash
# 최초 1회만 실행 — 인증서 발급 후에는 certbot 컨테이너가 자동 갱신

DOMAIN="datagarden.p-e.kr"
EMAIL="kinetas7308@gmail.com"

echo "=== Step 1: nginx를 HTTP 전용으로 먼저 기동 ==="
# 443 블록 없는 임시 설정으로 nginx 실행
docker compose up -d nginx --no-deps

echo "=== Step 2: 인증서 발급 ==="
docker compose run --rm certbot certbot certonly \
  --webroot \
  --webroot-path /var/www/certbot \
  --domain "$DOMAIN" \
  --email "$EMAIL" \
  --agree-tos \
  --non-interactive

if [ $? -ne 0 ]; then
  echo "인증서 발급 실패. 도메인 DNS와 포트(80) 포워딩을 확인하세요."
  exit 1
fi

echo "=== Step 3: 전체 스택 재시작 (HTTPS 활성화) ==="
docker compose down
docker compose up -d

echo "=== 완료 ==="
echo "https://$DOMAIN 접속 확인"
