#!/usr/bin/env bash
# 一键发布 Maker Lab 到阿里云 ECS（diy-lab.mayf3.com 大陆加速镜像）
#
# 用法：  bash scripts/deploy-aliyun.sh
# 前提：  ① 本机 ~/.ssh/config 已配置部署专用的 Host 别名（密钥认证）
#         ② 环境变量给出别名与远端目录（不落盘、不入库）：
#            export DIYLAB_DEPLOY_HOST=你的ssh别名
#            export DIYLAB_DEPLOY_DIR=/var/www/diy-lab
#         ③ 服务器端 nginx vhost 已按部署说明就位
#
# 发布一致性规则（2026-11-10 审查收尾）：本脚本 **不** 使用本地工作目录构建，
# 而是 fetch origin/main 后在临时 worktree 里构建——镜像内容永远是已推送的
# 提交，与 GitHub Pages 同源，且不会把并行会话的未提交修改带上服务器。
# 安全说明：本脚本不包含任何服务器 IP、用户名或密钥信息；真实配置只存在于
# 维护者本机的 ~/.ssh/config 与 shell 环境中。
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST_ALIAS="${DIYLAB_DEPLOY_HOST:?需要设置 DIYLAB_DEPLOY_HOST（本机 ~/.ssh/config 中的部署别名）}"
REMOTE_ROOT="${DIYLAB_DEPLOY_DIR:?需要设置 DIYLAB_DEPLOY_DIR（服务器上的站点根目录）}"
DOMAIN="diy-lab.mayf3.com"

cd "$REPO_ROOT"

echo "[0/5] 确认本地 main 未领先 origin/main（否则先 push）…"
git fetch origin main
LOCAL_SHA=$(git rev-parse HEAD)
ORIGIN_SHA=$(git rev-parse origin/main)
if [ "$LOCAL_SHA" != "$ORIGIN_SHA" ]; then
  echo "⚠️  本地 HEAD($LOCAL_SHA) 与 origin/main($ORIGIN_SHA) 不一致——请先 push（或 pull）再发布。"
  exit 1
fi

echo "[1/5] 在干净 worktree 中准备 origin/main($ORIGIN_SHA)…"
WORKTREE="$(mktemp -d "${TMPDIR:-/tmp}/diy-lab-deploy.XXXXXX")"
cleanup() { git worktree remove --force "$WORKTREE" 2>/dev/null || rm -rf "$WORKTREE"; }
trap cleanup EXIT
git worktree add --detach -q "$WORKTREE" "$ORIGIN_SHA"

echo "[2/5] 质量门禁 check.py（worktree）…"
(cd "$WORKTREE" && python3 scripts/check.py)

echo "[3/5] 构建 dist/（worktree）…"
(cd "$WORKTREE" && python3 scripts/build.py)

echo "[4/5] 同步到 ${REMOTE_ROOT}（临时目录 + 原子换名）…"
tar -C "$WORKTREE/dist" -cf - . | ssh -o ConnectTimeout=15 "$HOST_ALIAS" "
  set -e
  sudo rm -rf ${REMOTE_ROOT}.new
  sudo mkdir -p ${REMOTE_ROOT}.new
  sudo tar -C ${REMOTE_ROOT}.new -xf - 2>/dev/null || true
  sudo rm -rf ${REMOTE_ROOT}.old
  if [ -d ${REMOTE_ROOT} ]; then sudo mv ${REMOTE_ROOT} ${REMOTE_ROOT}.old; fi
  sudo mv ${REMOTE_ROOT}.new ${REMOTE_ROOT}
  sudo rm -rf ${REMOTE_ROOT}.old
"

echo "[5/5] 线上验证…"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://${DOMAIN}/")
VERSION_PARAM=$(curl -s "https://${DOMAIN}/" | grep -o 'assets/main.js?v=[0-9a-f]*' | head -1)
if [ "$HTTP_CODE" = "200" ] && [ -n "$VERSION_PARAM" ]; then
  echo "✅ 发布成功：https://${DOMAIN}/ (HTTP $HTTP_CODE, 脚本版本标记 $VERSION_PARAM)"
else
  echo "⚠️  HTTP $HTTP_CODE / 版本标记=$VERSION_PARAM —— 请在服务器上检查 nginx 状态"
  exit 1
fi
