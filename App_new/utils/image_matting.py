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
import logging
import os
from io import BytesIO

from PIL import Image

logger = logging.getLogger(__name__)

IMG_EXT = (".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff")

# 默认分割模型: u2net。实测对浅色/低对比证件最稳;
# isnet-general-use 在浅色卡片上会严重漏判(只抠出极小一块), 故不采用。
# 缺角问题改由 process_card 的"最小外接矩形拉正"几何方案解决(见下), 不依赖换模型。
DEFAULT_MODEL = "u2net"

# 处理前将图片最长边限制到此像素。证件只需 A4 打印, 2000px 足够清晰,
# 却能大幅减少大图(手机动辄1200万像素)的解码/透视变换/编码/内存开销, 加快处理。
# 注意: rembg 推理内部固定缩到 320, 故此项主要省"外围开销", 不改变AI推理耗时。
MAX_INPUT_SIDE = 2000


# ---------------- 基础工具 ----------------
def _downscale(pil_img, max_side=MAX_INPUT_SIDE):
    """若图片最长边超过 max_side, 等比缩小到 max_side; 否则原样返回。"""
    w, h = pil_img.size
    longest = max(w, h)
    if longest <= max_side:
        return pil_img
    scale = max_side / float(longest)
    new_size = (max(1, int(round(w * scale))), max(1, int(round(h * scale))))
    return pil_img.resize(new_size, Image.LANCZOS)


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

# onnxruntime 默认按核心数开线程, 一个抠图请求就能把整机 CPU 吃满 ——
# 推理跑在 gunicorn worker 里, 同一时刻的登录/查询全被饿死(实测登录从几十毫秒涨到 9 秒)。
# rembg.new_session 会读 OMP_NUM_THREADS 并据此设 inter/intra_op_num_threads,
# 所以建会话前先把它钉住, 给其它 worker 留出核心。
# 可用环境变量 MATTING_THREADS 覆盖; 留空则按 "核数 / gunicorn worker 数" 估算。
GUNICORN_WORKERS = 3          # 与 deploy/mytravelpanel.service 保持一致
MAX_MATTING_THREADS = 4       # 再多也换不来多少速度, 只会加剧抢占


def _matting_threads():
    """算出单次抠图推理最多用几个线程, 至少 1 个。"""
    env = os.environ.get('MATTING_THREADS')
    if env and env.isdigit() and int(env) > 0:
        return int(env)
    cores = os.cpu_count() or 2
    return max(1, min(MAX_MATTING_THREADS, cores // GUNICORN_WORKERS))


def get_session(model):
    from rembg import new_session
    if model not in _SESSION:
        threads = _matting_threads()
        # new_session 只在创建时读这个变量, 所以必须赶在它前面设
        os.environ['OMP_NUM_THREADS'] = str(threads)
        logger.info('创建抠图会话: 模型=%s 推理线程=%d (本机 %s 核)',
                    model, threads, os.cpu_count())
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


# ---------------- 掩码可靠性判定 ----------------
# 纸张铺满取景框时, 四边留白小于此比例即视为"纸已溢出画面"
BORDER_MARGIN_RATIO = 0.03
# 掩码实心度(掩码面积/凸包面积)低于此值, 说明圈住的是页面里的内容块而不是整张纸
MIN_SOLIDITY = 0.85


def mask_is_unreliable(cnt, img_w, img_h):
    """判断 AI 掩码能不能拿来裁剪, 返回 (不可信, 原因)。

    两种典型翻车(都会把证件切掉一块):
    1. 实心度低 —— 纸面和背景色接近时, AI 只圈住照片/印刷文字这些显著块,
       掩码支离破碎, 取它的四边形会把页眉页脚切掉;
    2. 三条以上边几乎没有留白 —— 纸张本来就拍到出框了, 没有背景可裁,
       此时掩码再小也只能是误判。

    命中任一条就不裁剪, 直接用整图 —— 少裁一点远比切掉半本护照强。
    """
    import cv2
    hull = cv2.convexHull(cnt)
    hull_area = cv2.contourArea(hull)
    if hull_area <= 0:
        return True, '掩码面积为空'

    solidity = cv2.contourArea(cnt) / hull_area
    if solidity < MIN_SOLIDITY:
        return True, f'掩码实心度过低({solidity:.2f})，疑似只圈住页面内容'

    x, y, w, h = cv2.boundingRect(hull)
    gaps = (x / img_w, y / img_h, (img_w - (x + w)) / img_w, (img_h - (y + h)) / img_h)
    tight = sum(1 for g in gaps if g < BORDER_MARGIN_RATIO)
    if tight >= 3:
        return True, f'{tight} 条边没有留白，纸张已拍出取景框'

    return False, ''


# 检出的四边形与掩码的交并比, 低于此值说明这个四边形根本不贴合纸张轮廓
MIN_QUAD_IOU = 0.90
# 四边形内角与 90° 的最大允许偏差。正常角度拍摄的证件不会超过 20° 左右,
# 偏差过大说明四个角找错了, 硬做透视变换会把页面拉成歪斜的平行四边形。
MAX_CORNER_DEVIATION = 25.0


def _quad_iou(mask, quad):
    """四边形区域与掩码的交并比。"""
    import numpy as np
    import cv2
    filled = np.zeros_like(mask)
    cv2.fillPoly(filled, [quad.astype(np.int32)], 255)
    a, b = mask > 0, filled > 0
    union = (a | b).sum()
    return float((a & b).sum()) / union if union else 0.0


def _max_corner_deviation(quad):
    """四个内角里偏离 90° 最多的那个, 单位为度。"""
    import numpy as np
    worst = 0.0
    for i in range(4):
        prev, cur, nxt = quad[(i - 1) % 4], quad[i], quad[(i + 1) % 4]
        v1, v2 = prev - cur, nxt - cur
        cosv = float(np.dot(v1, v2)) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-9)
        worst = max(worst, abs(np.degrees(np.arccos(np.clip(cosv, -1.0, 1.0))) - 90))
    return worst


def quad_is_unreliable(quad, mask):
    """判断检出的四边形能不能拿来做透视校正, 返回 (不可信, 原因)。

    掩码本身可信、但四个角找错的情况(常见于翻开的护照, AI 把对面那页也圈了进来):
    照着这个四边形硬拉, 页面会被拉成歪斜变形的样子。
    """
    iou = _quad_iou(mask, quad)
    if iou < MIN_QUAD_IOU:
        return True, f'四边形与掩码贴合度只有 {iou:.2f}'
    dev = _max_corner_deviation(quad)
    if dev > MAX_CORNER_DEVIATION:
        return True, f'四边形内角偏离直角 {dev:.0f}°，四角疑似找错'
    return False, ''


def _upright_rect(bgr, cnt, reason):
    """退化方案: 用最小外接矩形把纸张转正裁出来(只旋转不拉扯), 整块作为前景。

    透视校正失败时用它 —— 旋转矩形不会产生错误的形变, 最多是多留一点背景。
    """
    import numpy as np
    import cv2
    logger.info('抠图改用旋转矩形裁剪(不做透视校正): %s', reason)
    r = order_pts(cv2.boxPoints(cv2.minAreaRect(cnt)).astype("float32"))
    (tl, tr, br, bl) = r
    W = int(max(np.hypot(*(br - bl)), np.hypot(*(tr - tl))))
    H = int(max(np.hypot(*(tr - br)), np.hypot(*(tl - bl))))
    if W < 2 or H < 2:
        return _whole_image(bgr, '外接矩形异常')
    M = cv2.getPerspectiveTransform(
        r, np.array([[0, 0], [W - 1, 0], [W - 1, H - 1], [0, H - 1]], "float32"))
    rect = cv2.warpPerspective(bgr, M, (W, H), flags=cv2.INTER_CUBIC)
    return cv2.cvtColor(rect, cv2.COLOR_BGR2RGB), np.full((H, W), 255, np.uint8)


def _whole_image(bgr, reason):
    """兜底: 整图原样输出(前景为整幅), 不做透视裁剪。"""
    import numpy as np
    import cv2
    logger.info('抠图跳过裁剪, 直接用整图: %s', reason)
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), np.full(bgr.shape[:2], 255, np.uint8)


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
    bad, reason = mask_is_unreliable(cnt, bgr.shape[1], bgr.shape[0])
    if bad:
        return _whole_image(bgr, reason)
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
    bad, reason = mask_is_unreliable(cnt, bgr.shape[1], bgr.shape[0])
    if bad:
        return _whole_image(bgr, reason)
    peri = cv2.arcLength(cnt, True)
    quad = None
    for e in (.02, .03, .04, .05, .06, .08):
        ap = cv2.approxPolyDP(cnt, e * peri, True)
        if len(ap) == 4:
            quad = ap.reshape(4, 2).astype("float32")
            break
    if quad is None:
        return _upright_rect(bgr, cnt, '没找到四个角')
    quad = order_pts(quad)
    bad, reason = quad_is_unreliable(quad, mask)
    if bad:
        return _upright_rect(bgr, cnt, reason)
    r = quad
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


# ---------------- 输出体积控制 ----------------
# 证件/卡片下载下来多数是贴到表单或发邮件, PNG 存照片类内容几乎不压缩,
# 一张 2000px 的卡片动辄 1~3MB。这里按"目标体积"编码成 JPEG:
# 先限长边, 再从高到低试画质, 第一个落进目标体积的就用它。
QUALITY_PRESETS = {
    # 名称:   (长边上限, 目标KB, PDF dpi, PDF 内图片的 JPEG 画质)
    'small':  (1400, 180, 150, 68),
    'normal': (2000, 400, 200, 78),
    'high':   (None, None, 300, 90),   # 不压缩: 图走 PNG 原图, PDF 走 300dpi
}
DEFAULT_QUALITY = 'small'
# 试到哪个画质就停, 从高到低
JPEG_QUALITY_STEPS = (88, 82, 76, 70, 64, 58, 52)
# 最低画质仍超目标时, 按这个比例再缩一轮, 最多缩 MAX_SHRINK_ROUNDS 次
SHRINK_RATIO = 0.8
MAX_SHRINK_ROUNDS = 3


def get_quality_preset(name):
    """取画质预设 (长边上限, 目标KB, PDF dpi, PDF JPEG 画质), 名称非法时回落到默认。"""
    return QUALITY_PRESETS.get(name, QUALITY_PRESETS[DEFAULT_QUALITY])


def _limit_side(pil_img, max_side):
    """长边超过 max_side 就等比缩小, 否则原样返回。"""
    if not max_side:
        return pil_img
    w, h = pil_img.size
    if max(w, h) <= max_side:
        return pil_img
    scale = max_side / float(max(w, h))
    return pil_img.resize((max(1, int(round(w * scale))), max(1, int(round(h * scale)))),
                          Image.LANCZOS)


def to_jpeg_bytes(pil_img, target_kb=None, max_side=None):
    """把图编码成 JPEG, 尽量压到 target_kb 以内, 返回 BytesIO。

    透明底会先贴白底(JPEG 没有 alpha 通道)。target_kb 为空则只按最高画质存一次。
    """
    img = _limit_side(flatten_white(pil_img), max_side)
    target = target_kb * 1024 if target_kb else None
    best = None
    for _ in range(MAX_SHRINK_ROUNDS + 1):
        for q in JPEG_QUALITY_STEPS:
            buf = BytesIO()
            img.save(buf, 'JPEG', quality=q, optimize=True, progressive=True)
            best = buf
            if target is None or buf.tell() <= target:
                buf.seek(0)
                return buf
        # 最低画质还是超标: 再缩一轮尺寸重试(证件看清字即可, 不必保留大像素)
        w, h = img.size
        nw, nh = max(1, int(w * SHRINK_RATIO)), max(1, int(h * SHRINK_RATIO))
        if nw < 600:                       # 再缩就影响辨识了, 到此为止
            break
        img = img.resize((nw, nh), Image.LANCZOS)
    best.seek(0)
    return best


def to_image_bytes(pil_img, transparent=False, quality=DEFAULT_QUALITY):
    """把结果图编码成可下载的字节流, 返回 (BytesIO, 扩展名, mimetype)。

    透明底必须留 PNG(JPEG 没有 alpha); 白底且选了压缩就走 JPEG。
    """
    max_side, target_kb = get_quality_preset(quality)[:2]
    if transparent or target_kb is None:
        buf = BytesIO()
        _limit_side(pil_img, max_side).save(buf, 'PNG', optimize=True)
        buf.seek(0)
        return buf, 'png', 'image/png'
    return to_jpeg_bytes(pil_img, target_kb, max_side), 'jpg', 'image/jpeg'


# ---------------- PDF (A4, 自动横竖) ----------------
def flatten_white(pil_img):
    """带透明通道的图贴到白底上。

    直接 convert("RGB") 会把透明区域变成黑色, PDF 里就是一块黑底,
    所以透明底图必须先用 alpha 作蒙版贴到白底。
    """
    if pil_img.mode in ("RGBA", "LA") or (pil_img.mode == "P" and "transparency" in pil_img.info):
        src = pil_img.convert("RGBA")
        canvas = Image.new("RGB", src.size, "white")
        canvas.paste(src, mask=src.split()[-1])
        return canvas
    return pil_img.convert("RGB")


# A4 宽度(英寸), 统一页宽时用它作基准
A4_WIDTH_INCH = 8.27


def _a4_size(orientation, dpi=300):
    """返回 A4 页面像素尺寸。orientation: portrait(竖) | landscape(横)。"""
    if orientation == "landscape":
        return int(11.69 * dpi), int(8.27 * dpi)
    return int(8.27 * dpi), int(11.69 * dpi)


def pick_orientation(pil_images):
    """按多数图片的长宽比，给整本 PDF 定一个统一方向。

    横图(宽>高)多则整本用横向, 否则用竖向; 平票按竖向(A4 文件的常规方向)。
    """
    landscape = sum(1 for im in pil_images if im.size[0] > im.size[1])
    portrait = len(pil_images) - landscape
    return "landscape" if landscape > portrait else "portrait"


def _a4_page(pil_img, dpi=300, orientation="auto"):
    """把单张图居中排到一张 A4 页面上, 返回 PIL Image。

    orientation: auto=按图片自身长宽定横竖 | portrait=强制竖 | landscape=强制横。
    图片内容不旋转(保持正向可读), 只按页面可用区域等比缩放居中。
    """
    img = flatten_white(pil_img)
    iw, ih = img.size
    if orientation not in ("portrait", "landscape"):
        orientation = "landscape" if iw >= ih else "portrait"
    pw, ph = _a4_size(orientation, dpi)
    sc = min((pw * 0.92) / iw, (ph * 0.92) / ih)
    nw, nh = max(1, int(iw * sc)), max(1, int(ih * sc))
    page = Image.new("RGB", (pw, ph), "white")
    page.paste(img.resize((nw, nh), Image.LANCZOS), ((pw - nw) // 2, (ph - nh) // 2))
    return page


# PDF 里的图 Pillow 是按 JPEG(DCTDecode) 存的, 画质可以直接透传给编码器
PDF_JPEG_QUALITY = 75


def to_pdf_bytes(pil_img, dpi=300, orientation="auto", jpeg_quality=PDF_JPEG_QUALITY):
    """把 PIL Image 排版到 A4 页面，返回 PDF 字节流 (BytesIO)。

    dpi 既决定页面像素也决定文件大小: 证件 150dpi 打印已足够清楚, 300dpi 体积是它的四倍。
    """
    buf = BytesIO()
    _a4_page(pil_img, dpi, orientation).save(
        buf, "PDF", resolution=dpi, quality=jpeg_quality)
    buf.seek(0)
    return buf


def to_pdf_bytes_uniform_width(pil_images, page_width_inch=A4_WIDTH_INCH):
    """把多张图排成多页 PDF, 每页宽度一律是 A4 宽, 高度按各自比例。

    不缩放像素: 每张图单独存一页 PDF, 各自用 分辨率 = 像素宽 / 页宽英寸,
    再把这些单页拼起来 —— 页宽一致而画质无损(Pillow 存多页时分辨率是全局的,
    所以不能一次存完, 必须一页一页来)。
    """
    from pypdf import PdfWriter

    if not pil_images:
        raise ValueError("没有可导出的图片")

    writer = PdfWriter()
    for img in pil_images:
        img = flatten_white(img)
        one = BytesIO()
        img.save(one, "PDF", resolution=img.width / float(page_width_inch))
        one.seek(0)
        writer.append(one)

    buf = BytesIO()
    writer.write(buf)
    writer.close()
    buf.seek(0)
    return buf


def to_pdf_bytes_multi(pil_images, dpi=300, orientation="auto",
                       jpeg_quality=PDF_JPEG_QUALITY):
    """把多张图按顺序排成一个多页 PDF(每张一页 A4), 返回 PDF 字节流 (BytesIO)。

    orientation="auto" 时会先按多数图片的方向定下**整本统一**的横竖,
    不再每页各自判断 —— 否则一份 PDF 里会横竖混排, 打印和翻页都别扭。
    """
    if not pil_images:
        raise ValueError("没有可导出的图片")
    if orientation not in ("portrait", "landscape"):
        orientation = pick_orientation(pil_images)
    pages = [_a4_page(img, dpi, orientation) for img in pil_images]
    buf = BytesIO()
    pages[0].save(buf, "PDF", resolution=dpi, quality=jpeg_quality,
                  save_all=True, append_images=pages[1:])
    buf.seek(0)
    return buf


# ---------------- 对外主入口 ----------------
def process_single(pil_img, mode="card", model=DEFAULT_MODEL):
    """处理单张图，返回 (rgb_ndarray, mask_ndarray)。"""
    pil_img = _downscale(pil_img)          # 处理前先压缩大图, 省外围开销
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
