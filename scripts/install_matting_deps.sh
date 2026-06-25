#!/usr/bin/env bash
# =============================================================================
# 安装「AI 抠图合并工具」所需依赖 (rembg / onnxruntime / opencv)
#   - 用法对应模块: App_new/utils/image_matting.py
#   - 服务器为无界面(headless)环境, 因此使用 opencv-python-headless
#     (普通 opencv-python 需要 libGL.so.1, headless 版无此依赖, 避免 import 报错)
#   - 安装后会预下载 rembg 的 u2net 模型 (~170MB), 避免首次请求时卡住
#
# 用法 (以 root 或部署用户运行):
#   bash /var/www/MyTravelPanel/scripts/install_matting_deps.sh
#
# 可选: 指定 venv 路径 (默认自动探测):
#   VENV_DIR=/var/www/MyTravelPanel/.venv bash scripts/install_matting_deps.sh
# =============================================================================

set -euo pipefail

# ---------- 1) 定位项目根目录与虚拟环境 ----------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# 允许通过环境变量覆盖, 否则在常见位置探测
VENV_DIR="${VENV_DIR:-}"
if [[ -z "${VENV_DIR}" ]]; then
    for cand in "${PROJECT_ROOT}/.venv" "${PROJECT_ROOT}/venv" /var/www/MyTravelPanel/.venv; do
        if [[ -x "${cand}/bin/python" ]]; then
            VENV_DIR="${cand}"
            break
        fi
    done
fi

if [[ -z "${VENV_DIR}" || ! -x "${VENV_DIR}/bin/python" ]]; then
    echo "❌ 找不到虚拟环境。请用 VENV_DIR=/路径/.venv 显式指定后重试。"
    exit 1
fi

PY="${VENV_DIR}/bin/python"
echo "==== 使用虚拟环境: ${VENV_DIR} ===="
"${PY}" --version

# ---------- 2) 安装依赖 ----------
echo "==== 升级 pip ===="
"${PY}" -m pip install --upgrade pip

echo "==== 安装抠图依赖 (rembg / onnxruntime / opencv-python-headless) ===="
"${PY}" -m pip install \
    "rembg==2.0.69" \
    "onnxruntime==1.23.2" \
    "opencv-python-headless==4.13.0.92"

# 若服务器之前误装了非 headless 版, 卸掉以免与 headless 冲突 (两者共用 cv2 命名空间)
if "${PY}" -m pip show opencv-python >/dev/null 2>&1; then
    echo "==== 检测到 opencv-python(非headless), 卸载以避免冲突 ===="
    "${PY}" -m pip uninstall -y opencv-python || true
fi

# ---------- 3) 预下载 u2net 模型 ----------
echo "==== 预下载 u2net 模型 (~170MB, 首次较慢) ===="
"${PY}" - <<'PYEOF'
from rembg import new_session
new_session("u2net")
print("u2net 模型就绪")
PYEOF

# ---------- 4) 校验导入 ----------
echo "==== 校验依赖可正常导入 ===="
"${PY}" - <<'PYEOF'
import cv2, numpy, onnxruntime
import rembg
print("cv2", cv2.__version__, "| onnxruntime", onnxruntime.__version__, "| rembg OK")
PYEOF

echo ""
echo "==== ✅ 依赖安装完成 ===="
echo "下一步: 重启服务使新功能生效"
echo "  bash ${PROJECT_ROOT}/scripts/restart_mytravelpanel.sh"
