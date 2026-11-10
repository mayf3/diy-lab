#!/usr/bin/env bash
# 一键发布 Maker Lab 到阿里云 ECS（diy-lab.mayf3.com 大陆加速镜像）
#
# 用法：  bash scripts/deploy-aliyun.sh
# 前提：  ~/.ssh/config 已配置 prod-root（8.163.44.127，root-operator + 免密 sudo）
# 依赖：  rsync/tar 本地可用；服务器端 nginx vhost /etc/nginx/sites-enabled/diy-lab 已就位
#
# 与 GitHub Pages 的关系：双源并行——git push 仍走 pages.yml 自动部署，
# 本脚本只同步阿里云侧；两边内容同源（同一 dist/），正常顺序为先 push 再跑本脚本。
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST_ALIAS="prod-root"
REMOTE_ROOT="/var/www/diy-lab"
DOMAIN="diy-lab.mayf3.com"

cd "$REPO_ROOT"

echo "[1/4] 质量门禁 check.py…"
python3 scripts/check.py

echo "[2/4] 构建 dist/…"
python3 scripts/build.py

echo "[3/4] 同步到 ${HOST_ALIAS}:${REMOTE_ROOT}（临时目录 + 原子换名）…"
tar -C dist -cf - . | ssh -o ConnectTimeout=15 "$HOST_ALIAS" "
  set -e
  sudo rm -rf ${REMOTE_ROOT}.new
  sudo mkdir -p ${REMOTE_ROOT}.new
  sudo tar -C ${REMOTE_ROOT}.new -xf -
  sudo rm -rf ${REMOTE_ROOT}.old
  if [ -d ${REMOTE_ROOT} ]; then sudo mv ${REMOTE_ROOT} ${REMOTE_ROOT}.old; fi
  sudo mv ${REMOTE_ROOT}.new ${REMOTE_ROOT}
  sudo rm -rf ${REMOTE_ROOT}.old
"

echo "[4/4] 线上验证…"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://${DOMAIN}/")
if [ "$HTTP_CODE" = "200" ]; then
  echo "✅ 发布成功：https://${DOMAIN}/ (HTTP $HTTP_CODE)"
else
  echo "⚠️  HTTP $HTTP_CODE —— 检查服务器：ssh ${HOST_ALIAS} 'sudo nginx -t && sudo systemctl status nginx'"
  exit 1
fi
