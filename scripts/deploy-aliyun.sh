#!/usr/bin/env bash
# 一键发布 Maker Lab 到阿里云 ECS（diy-lab.mayf3.com 大陆加速镜像）
#
# 用法：  bash scripts/deploy-aliyun.sh
# 前提：  ① 本机 ~/.ssh/config 已配置部署专用的 Host 别名（密钥认证）
#         ② 环境变量给出别名与远端目录（不落盘、不入库）：
#            export DIYLAB_DEPLOY_HOST=你的ssh别名
#            export DIYLAB_DEPLOY_DIR=/var/www/diy-lab
#         ③ 服务器端 nginx vhost 已按 docs 部署说明就位
#
# 安全说明：本脚本不包含任何服务器 IP、用户名或密钥信息；真实配置只存在于
# 维护者本机的 ~/.ssh/config 与 shell 环境中。
# 与 GitHub Pages 的关系：双源并行——git push 仍走 pages.yml 自动部署，
# 本脚本只同步阿里云侧；两边内容同源（同一 dist/），正常顺序为先 push 再跑本脚本。
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST_ALIAS="${DIYLAB_DEPLOY_HOST:?需要设置 DIYLAB_DEPLOY_HOST（本机 ~/.ssh/config 中的部署别名）}"
REMOTE_ROOT="${DIYLAB_DEPLOY_DIR:?需要设置 DIYLAB_DEPLOY_DIR（服务器上的站点根目录）}"
DOMAIN="diy-lab.mayf3.com"

cd "$REPO_ROOT"

echo "[1/4] 质量门禁 check.py…"
python3 scripts/check.py

echo "[2/4] 构建 dist/…"
python3 scripts/build.py

echo "[3/4] 同步到 ${REMOTE_ROOT}（临时目录 + 原子换名）…"
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
  echo "⚠️  HTTP $HTTP_CODE —— 请在服务器上检查 nginx 状态"
  exit 1
fi
