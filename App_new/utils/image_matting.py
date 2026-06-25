# -*- coding: utf-8 -*-
"""
抠图合并工具核心逻辑 (AI 背景去除)
====================================
用 AI 模型 (rembg / u2net) 自动去除证件、卡片、护照页等图片的背景，
可选自动摆正 / 透视校正，并把多张图合并成一张，导出 PNG / 透明 PNG / 可打印 PDF。

本模块从命令行脚本移植而来，改为内存处理（接收 PIL Image，返回 PIL Image），
供 Web 路由 (App_new/shared/routes/utils.py) 调用。

依赖: rembg, onnxruntime, opencv-python, pillow, numpy
注意: cv2 / rembg 体积较大且非必装，全部采用延迟导入，
      未安装时由路由层捕获 ImportError 并返回友好提示。
"""
from io import BytesIO

from PIL import Image

IMG_EXT = (".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff")

# 默认分割模型: u2net。实测对浅色/低对比证件最稳;
# isnet-general-use 在浅色卡片上会严重漏判(只抠出极小一块), 故不采用。
# 缺角问题改由 process_card 的"最小外接矩形拉正"几何方案解决(见下), 不依赖换模型。
DEFAULT_MODEL = "u2net"


# ---------------- 基础工具 ----------------
def _pil_to_bgr(pil_img):
    """PIL Image -> OpenCV BGR ndarray。"""
    import numpy as np
    import cv2
    return cv2.cvtColor(np.array(pil_img.convert("RGB")), cv2.COLOR_RGB2BGR)


def largest_cc(m):
    import numpy as np
    import cv2
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    if n <= 1:
        return m
    return (lab == 1 + np.argmax(st[1:, cv2.CC_STAT_AREA])).astype(np.uint8) * 255


def fill_holes(m):
    import numpy as np
    import cv2
    h, w = m.shape
    ff = m.copy()
    z = np.zeros((h + 2, w + 2), np.uint8)
    cv2.floodFill(ff, z, (0, 0), 255)
    return m | cv2.bitwise_not(ff)


def order_pts(p):
    import numpy as np
    r = np.zeros((4, 2), "float32")
    s = p.sum(1)
    d = np.diff(p, 1)
    r[0] = p[np.argmin(s)]
    r[2] = p[np.argmax(s)]
    r[1] = p[np.argmin(d)]
    r[3] = p[np.argmax(d)]
    return r


def rotate_keep(img, ang, border, fl=None):
    import numpy as np
    import cv2
    if fl is None:
        fl = cv2.INTER_CUBIC
    h, w = img.shape[:2]
    c = (w / 2, h / 2)
    M = cv2.getRotationMatrix2D(c, ang, 1.0)
    co, si = abs(M[0, 0]), abs(M[0, 1])
    nW, nH = int(h * si + w * co), int(h * co + w * si)
    M[0, 2] += nW / 2 - c[0]
    M[1, 2] += nH / 2 - c[1]
    return cv2.warpAffine(img, M, (nW, nH), flags=fl,
                          borderMode=cv2.BORDER_CONSTANT, borderValue=border)


# ---------------- AI 抠图 ----------------
_SESSION = {}


def get_session(model):
    from rembg import new_session
    if model not in _SESSION:
        _SESSION[model] = new_session(model)
    return _SESSION[model]


def ai_mask(bgr, model):
    import numpy as np
    import cv2
    from rembg import remove
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    alpha = np.array(remove(Image.fromarray(rgb), session=get_session(model),
                            alpha_matting=False))[:, :, 3]
    m = largest_cc((alpha > 50).astype(np.uint8) * 255)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    return largest_cc(fill_holes(m))


def to_rgba(rgb, mask):
    import numpy as np
    return np.dstack([rgb, mask])


def composite_white(rgb, mask):
    import numpy as np
    a = (mask.astype(np.float32) / 255)[..., None]
    return (rgb.astype(np.float32) * a + 255 * (1 - a)).astype(np.uint8)


# ---------------- 两种处理模式 ----------------
def process_card(bgr, model):
    """证件/卡片：用最小外接矩形把卡片透视拉正并补成完整矩形。

    证件是规则矩形, 直接取掩码的最小外接矩形(minAreaRect)作为卡片边界,
    透视校正到正矩形 —— 即便掩码在某个浅色/低对比的角漏判, 也由矩形补全,
    彻底避免"凸包斜切缺角"。整块矩形作为前景输出。
    """
    import numpy as np
    import cv2
    mask = ai_mask(bgr, model)
    cnt = max(cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0],
              key=cv2.contourArea)
    box = cv2.boxPoints(cv2.minAreaRect(cnt)).astype("float32")
    r = order_pts(box)
    ctr = r.mean(0)
    r = (ctr + (r - ctr) * 0.99).astype("float32")        # 轻微内缩, 去掉边缘细背景条
    (tl, tr, br, bl) = r
    W = int(max(np.hypot(*(br - bl)), np.hypot(*(tr - tl))))
    H = int(max(np.hypot(*(tr - br)), np.hypot(*(tl - bl))))
    if W < 2 or H < 2:                                     # 兜底: 矩形异常时退回原图
        return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), mask
    M = cv2.getPerspectiveTransform(
        r, np.array([[0, 0], [W - 1, 0], [W - 1, H - 1], [0, H - 1]], "float32"))
    persp = cv2.warpPerspective(bgr, M, (W, H), flags=cv2.INTER_CUBIC)
    if persp.shape[0] > persp.shape[1]:                   # 统一成横向
        persp = cv2.rotate(persp, cv2.ROTATE_90_CLOCKWISE)
    full = np.full(persp.shape[:2], 255, np.uint8)        # 整块矩形为前景, 永不缺角
    return cv2.cvtColor(persp, cv2.COLOR_BGR2RGB), full


def process_page(bgr, model):
    """文件/护照页：检测四角做透视校正(拉平)，再用掩码清边。"""
    import numpy as np
    import cv2
    mask = ai_mask(bgr, model)
    cnt = max(cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0],
              key=cv2.contourArea)
    peri = cv2.arcLength(cnt, True)
    quad = None
    for e in (.02, .03, .04, .05, .06, .08):
        ap = cv2.approxPolyDP(cnt, e * peri, True)
        if len(ap) == 4:
            quad = ap.reshape(4, 2).astype("float32")
            break
    if quad is None:
        quad = cv2.boxPoints(cv2.minAreaRect(cnt))
    r = order_pts(quad)
    ctr = r.mean(0)
    r = (ctr + (r - ctr) * 0.985).astype("float32")  # 内缩去细边
    (tl, tr, br, bl) = r
    W = int(max(np.hypot(*(br - bl)), np.hypot(*(tr - tl))))
    H = int(max(np.hypot(*(tr - br)), np.hypot(*(tl - bl))))
    M = cv2.getPerspectiveTransform(r, np.array([[0, 0], [W - 1, 0], [W - 1, H - 1], [0, H - 1]], "float32"))
    persp = cv2.warpPerspective(bgr, M, (W, H), flags=cv2.INTER_CUBIC)
    solid = np.zeros_like(mask)
    cv2.fillPoly(solid, [cv2.convexHull(cnt)], 255)
    pm = cv2.warpPerspective(solid, M, (W, H), flags=cv2.INTER_NEAREST)
    pm = cv2.erode((pm > 127).astype(np.uint8) * 255, np.ones((5, 5), np.uint8))
    return cv2.cvtColor(persp, cv2.COLOR_BGR2RGB), pm


# ---------------- 合并 ----------------
def merge_images(items, layout, width, gap, margin, transparent):
    """items: list of (rgb, mask)。返回合并后的 PIL Image。"""
    import numpy as np
    import cv2
    ch = 4 if transparent else 3

    def fit(rgb, mask):
        h, w = rgb.shape[:2]
        nh = int(h * width / w)
        rgb2 = cv2.resize(rgb, (width, nh), interpolation=cv2.INTER_AREA)
        if transparent:
            m2 = cv2.resize(mask, (width, nh), interpolation=cv2.INTER_NEAREST)
            return np.dstack([rgb2, m2])
        return composite_white(rgb2, cv2.resize(mask, (width, nh)))

    tiles = [fit(r, m) for r, m in items]
    bg = (0, 0, 0, 0) if transparent else (255, 255, 255)

    if layout == "grid":
        import math
        cols = int(math.ceil(math.sqrt(len(tiles))))
        rows = int(math.ceil(len(tiles) / cols))
        rh = max(t.shape[0] for t in tiles)
        cw = width
        H = margin + rows * rh + (rows - 1) * gap + margin
        Wd = margin + cols * cw + (cols - 1) * gap + margin
        canvas = np.full((H, Wd, ch), bg, np.uint8)
        for i, t in enumerate(tiles):
            rr, cc = divmod(i, cols)
            y = margin + rr * (rh + gap)
            x = margin + cc * (cw + gap)
            canvas[y:y + t.shape[0], x:x + cw] = t
    elif layout == "horizontal":
        H = max(t.shape[0] for t in tiles)
        Wd = margin * 2 + sum(t.shape[1] for t in tiles) + gap * (len(tiles) - 1)
        canvas = np.full((H + margin * 2, Wd, ch), bg, np.uint8)
        x = margin
        for t in tiles:
            canvas[margin:margin + t.shape[0], x:x + t.shape[1]] = t
            x += t.shape[1] + gap
    else:  # vertical
        Wd = width + margin * 2
        H = margin + sum(t.shape[0] for t in tiles) + gap * (len(tiles) - 1) + margin
        canvas = np.full((H, Wd, ch), bg, np.uint8)
        y = margin
        for t in tiles:
            canvas[y:y + t.shape[0], margin:margin + width] = t
            y += t.shape[0] + gap
    mode = "RGBA" if transparent else "RGB"
    return Image.fromarray(canvas, mode)


# ---------------- PDF (A4, 300dpi, 自动横竖) ----------------
def to_pdf_bytes(pil_img, dpi=300):
    """把 PIL Image 排版到 A4 页面，返回 PDF 字节流 (BytesIO)。"""
    img = pil_img.convert("RGB")
    iw, ih = img.size
    if iw >= ih:
        pw, ph = int(11.69 * dpi), int(8.27 * dpi)   # A4 横
    else:
        pw, ph = int(8.27 * dpi), int(11.69 * dpi)   # A4 竖
    sc = min((pw * 0.92) / iw, (ph * 0.92) / ih)
    nw, nh = int(iw * sc), int(ih * sc)
    page = Image.new("RGB", (pw, ph), "white")
    page.paste(img.resize((nw, nh), Image.LANCZOS), ((pw - nw) // 2, (ph - nh) // 2))
    buf = BytesIO()
    page.save(buf, "PDF", resolution=dpi)
    buf.seek(0)
    return buf


# ---------------- 对外主入口 ----------------
def process_single(pil_img, mode="card", model=DEFAULT_MODEL):
    """处理单张图，返回 (rgb_ndarray, mask_ndarray)。"""
    proc = process_page if mode == "page" else process_card
    return proc(_pil_to_bgr(pil_img), model)


def result_to_image(rgb, mask, transparent=False):
    """把 (rgb, mask) 转成单张 PIL Image（白底或透明底）。"""
    if transparent:
        return Image.fromarray(to_rgba(rgb, mask), "RGBA")
    return Image.fromarray(composite_white(rgb, mask), "RGB")


def matting(pil_images, mode="card", bg="white", merge="none", model=DEFAULT_MODEL,
            width=1100, gap=45, margin=45):
    """
    批量抠图主入口。

    参数:
        pil_images  : list[PIL.Image]  待处理图片
        mode        : "card" | "page"  card=证件/卡片(默认), page=透视校正
        bg          : "white" | "transparent"  输出背景
        merge       : "none" | "vertical" | "horizontal" | "grid"  合并方式
        model       : rembg 模型名, 默认 isnet-general-use
        width/gap/margin : 合并排版参数

    返回:
        merge != none -> {"merged": PIL.Image}
        merge == none -> {"singles": [PIL.Image, ...]}
    """
    transparent = (bg == "transparent")
    results = [process_single(img, mode=mode, model=model) for img in pil_images]

    if merge != "none":
        merged = merge_images(results, merge, width, gap, margin, transparent)
        return {"merged": merged}

    singles = [result_to_image(rgb, mask, transparent) for rgb, mask in results]
    return {"singles": singles}
