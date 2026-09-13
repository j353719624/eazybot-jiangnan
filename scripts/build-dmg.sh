#!/bin/bash
# 从官方 1.0.7 基础包构建 EazyBot-jiangnan DMG（双架构）。
# 用法: ./build-dmg.sh <架构 x64|arm64> <官方基础.app路径> <输出目录>
#   x64   基础包 = 官方 EazyBot 1.0.7 mac x64（env 已组好，python 改名副本已存在）
#   arm64 基础包 = 官方 EazyBot 1.0.7 mac arm64（launcher 为 CFBundleExecutable，
#                  env/bin/python3.10 为真身；脚本负责换牌 + overlay + python 副本）
set -euo pipefail

ARCH="${1:?用法: build-dmg.sh <x64|arm64> <基础.app> <输出目录>}"
SRC_APP="${2:?缺少基础包路径}"
OUT_DIR="${3:-$(pwd)/dist}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

APP_NAME="EazyBot-jiangnan.app"
STAGE="$(mktemp -d)/$APP_NAME"
echo "[1/6] 复制基础包"
mkdir -p "$STAGE"
ditto "$SRC_APP" "$STAGE"

echo "[2/6] 应用 overlay（全部定制文件）"
cp -R "$REPO_ROOT/overlay/Contents/" "$STAGE/Contents/"

if [ "$ARCH" = "x64" ]; then
  VOLNAME="Install EazyBot-jiangnan-1.0.7-x64"
  OUT_DMG="EazyBot-jiangnan-1.0.7-mac-x64.dmg"
  echo "[3/6] 编译启动器（x86_64）+ 安装 python 副本"
  cc -arch x86_64 -O2 -Wall -o "$STAGE/Contents/MacOS/EazyBot" "$REPO_ROOT/launcher/launcher.c"
  cp "$STAGE/Contents/Resources/env/bin/EazyBot-jiangnan" "$STAGE/Contents/MacOS/EazyBot-jiangnan"
else
  VOLNAME="Install EazyBot-jiangnan-1.0.7-arm64"
  OUT_DMG="EazyBot-jiangnan-1.0.7-mac-arm64.dmg"
  echo "[3/6] 交叉编译启动器（arm64）+ 换牌 + 安装 python 副本"
  /usr/libexec/PlistBuddy \
    -c "Set :CFBundleIdentifier com.eazytec.eazybot.jiangnan.desktop" \
    -c "Set :CFBundleName EazyBot-jiangnan" \
    -c "Set :CFBundleDisplayName EazyBot-jiangnan" \
    -c "Set :CFBundleIconFile EazyBot-jiangnan" \
    "$STAGE/Contents/Info.plist"
  OURS="${EAZYBOT_X64_APP:-/Applications/EazyBot-jiangnan.app/Contents/Resources}"
  cp "$OURS/EazyBot-jiangnan.icns" "$STAGE/Contents/Resources/"
  rm -f "$STAGE/Contents/Resources/app.icns"
  cp "$STAGE/Contents/Resources/env/bin/python3.10" "$STAGE/Contents/Resources/env/bin/EazyBot-jiangnan"
  cp "$STAGE/Contents/Resources/env/bin/python3.10" "$STAGE/Contents/MacOS/EazyBot-jiangnan"
  cc -arch arm64 -O2 -Wall -o "$STAGE/Contents/MacOS/launcher" "$REPO_ROOT/launcher/launcher.c"
  codesign --force --sign - "$STAGE/Contents/MacOS/launcher"
fi

echo "[4/6] 清理 console 预压缩缓存（保证补丁生效）"
CONSOLE="$STAGE/Contents/Resources/env/lib/python3.1*/site-packages/eazybot/console"
rm -f "$CONSOLE/assets/index-BiWh193y.js.br" "$CONSOLE/assets/index-BiWh193y.js.gz" "$CONSOLE/assets/index-DGXSMDPA.js.br" "$CONSOLE/assets/index-DGXSMDPA.js.gz"

echo "[5/6] 放入种子数据（首启播种，凭据零打包）"
mkdir -p "$STAGE/Contents/Resources/seed"
cp -R "$REPO_ROOT/seed/eazybot-data" "$STAGE/Contents/Resources/seed/eazybot-data"

echo "[6/6] 打包 DMG"
mkdir -p "$OUT_DIR"
TMP_DMG="$(mktemp -d)/tmp.dmg"
hdiutil create -size 4g -fs HFS+ -volname "$VOLNAME" "$TMP_DMG" >/dev/null
hdiutil attach "$TMP_DMG" -nobrowse >/dev/null
V="/Volumes/$VOLNAME"
trap 'hdiutil detach "$V" >/dev/null 2>&1 || true' EXIT
ln -s /Applications "$V/Applications"
ditto "$STAGE" "$V/$APP_NAME"
hdiutil detach "$V" >/dev/null
trap - EXIT
hdiutil convert "$TMP_DMG" -format UDZO -o "$OUT_DIR/$OUT_DMG" >/dev/null
rm -rf "$(dirname "$STAGE")" "$(dirname "$TMP_DMG")"

echo "完成: $OUT_DIR/$OUT_DMG"
