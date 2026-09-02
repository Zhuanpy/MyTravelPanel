# -*- coding: utf-8 -*-
"""
多张图片拼接成一张长图

手机不支持长截图时只能连续截多张，这里按顺序拼回一整张。

连续滚动截出来的相邻两张之间通常有一段重复内容（手指滑一下，屏幕只往下走了
一部分），直接首尾相接会把同一段内容印两遍。所以默认开启重叠检测，自动裁掉
后一张顶部的重复区域。

检测思路：从后一张顶部取一条窄带（strip），在前一张的下半部分滑窗找最相似的
位置，相对位移就是重叠量。

两个关键点：
1. 只把图片缩窄、**不缩高**。缩高会让两张图各自的降采样行边界错开，密集文字
   一模糊差异就超阈值，重叠量非整数行时几乎必然漏检。保持行不变则整像素对齐。
2. 窄带从多个起始偏移各试一次。手机截图顶部有状态栏（时间、电量），它不随内容
   滚动，从第 0 行取带会被它带偏；跳过一段再取就绕开了。

只依赖 Pillow + numpy，项目里都已有，不引入新依赖。
"""

from io import BytesIO

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from PIL import Image, ImageOps

# ========== 参数 ==========
NARROW_WIDTH = 64          # 匹配时缩到这个宽度（高度保持不变）
MIN_OVERLAP_PX = 20        # 小于这个像素的重叠不认（噪声容易误判）
MAX_OVERLAP_RATIO = 0.95   # 重叠最多占较短那张的比例
FLAT_STD_LIMIT = 2.0       # 窄带灰度标准差下限，纯色区域匹配上了也没意义
MATCH_DIFF_LIMIT = 12.0    # 缩窄后平均灰度差上限，只作粗筛

# 窄带方案 (高度, 起始行)：
# - 起始行跳过手机截图顶部的状态栏（时间、电量不随内容滚动，会把匹配带偏）
# - 能检测到的最小重叠 = 高度 + 起始行，所以补一档矮窄带覆盖小重叠
STRIP_PASSES = ((64, 0), (64, 96), (64, 192), (24, 0), (24, 96))
MAX_VERIFY = 5             # 粗筛后按得分复核前几个候选

# 全宽复核的两道门槛。实测：真实重叠即使各自经 JPEG q60 压缩，
# 差异超过 32 的像素占比也只有 0.02%；而假匹配在 0.6% 以上，差 30 倍。
VERIFY_DIFF_LIMIT = 3.0        # 平均灰度差上限
VERIFY_PIXEL_DIFF = 32         # 单像素算"明显不同"的灰度差
VERIFY_MISMATCH_RATIO = 0.002  # 明显不同的像素占比上限

MAX_OUTPUT_PIXELS = 260_000_000   # 输出总像素上限，防止内存吃满
JPEG_MAX_SIDE = 65500      # JPEG 单边上限（格式限制 65535）

# ---- 固定框架（状态栏、标题栏、底部导航栏）识别 ----
# App 截图里这些区域不随内容滚动，每张都一样。不裁掉的话它们会重复出现在长图中间，
# 更要命的是重叠检测会拿它们去匹配（每张都相同，必然"匹配上"），把结果彻底带偏。
# 判据：同一 y 位置逐行比较，几乎没变化的行就是固定框架。
CHROME_ROW_DIFF = 1.5      # 逐行平均灰度差小于此值视为"没变"
CHROME_MIN_RUN = 40        # 连续"没变"够这么多行才算框架，短的是内容里的空白
CHROME_MARGIN = 6          # 边界往内让几行，避开标题栏阴影、滚动指示条的残留
CHROME_MAX_RATIO = 0.35    # 单侧框架最多占这么高，防止误判把内容整片吃掉


def _gray(img, width=None):
    """转灰度 numpy 数组；给了 width 就只缩宽度，行数保持不变"""
    gray = img.convert('L')
    if width and width != gray.width:
        gray = gray.resize((width, gray.height), Image.BILINEAR)
    return np.asarray(gray, dtype=np.float32)


def detect_overlap(top_img, bottom_img):
    """检测两张等宽图片的重叠高度（像素）

    返回"后一张顶部需要裁掉多少行"，没检测到重叠则返回 0。
    """
    if top_img.width != bottom_img.width:
        return 0

    h_top, h_bottom = top_img.height, bottom_img.height
    max_overlap = int(min(h_top, h_bottom) * MAX_OVERLAP_RATIO)
    if max_overlap < MIN_OVERLAP_PX:
        return 0

    narrow_top = _gray(top_img, NARROW_WIDTH)
    narrow_bottom = _gray(bottom_img, NARROW_WIDTH)
    width = narrow_top.shape[1]

    # ---------- 粗筛：每种窄带方案各找一个最佳位置 ----------
    candidates = []
    for strip_rows, offset in STRIP_PASSES:
        rows = min(strip_rows, h_bottom - offset, h_top)
        if rows < 8:
            continue
        strip = narrow_bottom[offset:offset + rows]
        if float(strip.std()) < FLAT_STD_LIMIT:
            continue    # 纯色窄带（空白、状态栏底色）匹配上了也说明不了问题

        # 窄带落在前一张的第 pos 行时，重叠量 overlap = h_top - pos + offset
        # 反解出 pos 的合法范围
        pos_low = max(0, h_top + offset - max_overlap)
        pos_high = min(h_top - rows, h_top + offset - MIN_OVERLAP_PX)
        if pos_high < pos_low:
            continue

        region = narrow_top[pos_low:pos_high + rows]
        if region.shape[0] < rows:
            continue
        windows = sliding_window_view(region, (rows, width))[:, 0]
        diffs = np.abs(windows - strip).mean(axis=(1, 2))

        index = int(diffs.argmin())
        score = float(diffs[index])
        if score > MATCH_DIFF_LIMIT:
            continue
        overlap = h_top - (pos_low + index) + offset
        if MIN_OVERLAP_PX <= overlap <= max_overlap:
            candidates.append((score, overlap, rows, offset))

    if not candidates:
        return 0

    # ---------- 全宽复核：缩窄后容易撞上假匹配，按得分逐个用原分辨率确认 ----------
    candidates.sort(key=lambda item: item[0])
    full_top = _gray(top_img)
    full_bottom = _gray(bottom_img)
    checked = set()

    for _, overlap, rows, offset in candidates[:MAX_VERIFY]:
        if overlap in checked:
            continue
        checked.add(overlap)

        start = h_top - overlap + offset
        if start < 0 or start + rows > h_top:
            continue
        seg_top = full_top[start:start + rows]
        seg_bottom = full_bottom[offset:offset + rows]
        if seg_top.shape != seg_bottom.shape:
            continue

        delta = np.abs(seg_top - seg_bottom)
        if float(delta.mean()) > VERIFY_DIFF_LIMIT:
            continue
        # 均差会被大片背景稀释，再看"明显不同"的像素占比才分得开真假
        if float((delta > VERIFY_PIXEL_DIFF).mean()) > VERIFY_MISMATCH_RATIO:
            continue
        return overlap

    return 0


def _chrome_edge(same, cap, reverse=False):
    """取靠近这一端的最长"没变"连续段，用它的内侧边界作为框架厚度

    不能简单地"从第 0 行往下数连续没变的行"：状态栏里的时钟、电量数字每张都
    不一样，会把这一段从中间截断，顶栏就只认出时钟上面那几十行。
    改成挑最长的一段：时钟把顶栏切成 80 + 241 两段时，取 241 那段的末尾，
    边界依然落在真正的顶栏下沿。

    也不能改成"允许跨过短空隙"——实测内容区里的变化段（24、49 行）和时钟空隙
    （31 行）大小相当，跨不出区别，反而会在内容里连锁跑飞。
    """
    series = same[::-1] if reverse else same
    length = len(series)

    best_len, boundary = 0, 0
    i = 0
    while i < length:
        if not series[i]:
            i += 1
            continue
        j = i
        while j < length and series[j]:
            j += 1
        # 只认起点落在这一端窗口内的段，中间那些内容空白不参与
        if i < cap and (j - i) > best_len:
            best_len, boundary = j - i, j
        i = j

    if best_len < CHROME_MIN_RUN:
        return 0
    return min(boundary, cap)


def detect_fixed_chrome(images):
    """识别所有图片共有的固定顶栏/底栏高度，返回 (top, bottom)

    对相邻两张逐行比对，取各对结果的中位数——用中位数是因为万一有两张几乎
    一样（重复截图），那一对会把整张图都判成"没变"，取最大值就被它带偏了。
    """
    if len(images) < 2:
        return 0, 0
    heights = {im.height for im in images}
    widths = {im.width for im in images}
    if len(heights) != 1 or len(widths) != 1:
        return 0, 0      # 尺寸不一致就没法逐行比对

    height = images[0].height
    cap = int(height * CHROME_MAX_RATIO)
    if cap < 10:
        return 0, 0

    tops, bottoms = [], []
    for i in range(len(images) - 1):
        g1 = _gray(images[i])
        g2 = _gray(images[i + 1])
        same = np.abs(g1 - g2).mean(axis=1) < CHROME_ROW_DIFF
        if bool(same.all()):
            continue     # 两张完全一样，这一对给不出有效信息
        tops.append(_chrome_edge(same, cap))
        bottoms.append(_chrome_edge(same, cap, reverse=True))

    if not tops:
        return 0, 0

    top = int(np.median(tops))
    bottom = int(np.median(bottoms))
    if top:
        top = min(top + CHROME_MARGIN, cap)
    if bottom:
        bottom = min(bottom + CHROME_MARGIN, cap)
    # 顶底加起来把内容挤没了就当没识别到
    if top + bottom >= height - MIN_OVERLAP_PX * 2:
        return 0, 0
    return top, bottom


def _normalize(images, align='min', axis='width'):
    """统一宽度（竖拼）或高度（横拼），并修正 EXIF 方向

    默认按最小边缩放，避免放大糊掉。
    """
    fixed = []
    for img in images:
        img = ImageOps.exif_transpose(img)
        if img.mode not in ('RGB', 'RGBA'):
            img = img.convert('RGB')
        fixed.append(img)

    sizes = [im.width if axis == 'width' else im.height for im in fixed]
    target = min(sizes) if align == 'min' else max(sizes)

    out = []
    for im in fixed:
        if axis == 'width' and im.width != target:
            height = max(1, round(im.height * target / im.width))
            im = im.resize((target, height), Image.LANCZOS)
        elif axis == 'height' and im.height != target:
            width = max(1, round(im.width * target / im.height))
            im = im.resize((width, target), Image.LANCZOS)
        out.append(im)
    return out


def _guard_size(width, height):
    """输出尺寸兜底：像素太多会直接把内存吃光"""
    if width <= 0 or height <= 0:
        raise ValueError('拼接结果尺寸异常')
    if width * height > MAX_OUTPUT_PIXELS:
        raise ValueError(
            f'拼接结果太大（{width}x{height}，约 {width * height / 1e6:.0f} 百万像素），'
            f'请减少图片数量或分批拼接'
        )


def merge_images(images, direction='vertical', auto_overlap=True,
                 gap=0, bg=(255, 255, 255), align='min', trim_chrome=True):
    """把多张图片拼成一张

    direction    : vertical 竖向 / horizontal 横向
    auto_overlap : 自动裁掉相邻两张的重复内容（仅竖向有效）
    trim_chrome  : 自动识别并只保留一份固定顶栏/底栏（仅竖向有效）
    gap          : 图片之间留白像素（检测到重叠时不留白，否则接缝会断开）
    返回 (合成图, 统计信息 dict)
    """
    if not images:
        raise ValueError('没有可拼接的图片')

    # ---------- 横向 ----------
    if direction == 'horizontal':
        prepared = _normalize(images, align, axis='height')
        width = sum(im.width for im in prepared) + gap * (len(prepared) - 1)
        height = prepared[0].height
        _guard_size(width, height)

        canvas = Image.new('RGB', (width, height), bg)
        x = 0
        for im in prepared:
            canvas.paste(im.convert('RGB'), (x, 0))
            x += im.width + gap
        return canvas, {'count': len(prepared), 'overlaps': [], 'size': (width, height)}

    # ---------- 竖向 ----------
    prepared = _normalize(images, align, axis='width')
    width = prepared[0].width

    # 先识别固定顶栏/底栏。必须在重叠检测之前做：这些区域每张都一样，
    # 留着的话匹配器会拿它们去对齐，重叠量必然算错。
    top, bottom = (0, 0)
    if trim_chrome and len(prepared) > 1:
        top, bottom = detect_fixed_chrome(prepared)

    # 重叠只在滚动内容区上检测
    if top or bottom:
        regions = [im.crop((0, top, im.width, max(top + 1, im.height - bottom)))
                   for im in prepared]
    else:
        regions = prepared

    # overlaps[i] = 第 i+1 张的内容区顶部要裁掉的行数
    if auto_overlap and len(prepared) > 1:
        overlaps = [detect_overlap(regions[i], regions[i + 1])
                    for i in range(len(prepared) - 1)]
    else:
        overlaps = [0] * (len(prepared) - 1)

    # 去掉重叠后还留间距，接缝处会出现一条断带，所以两者互斥
    effective_gap = 0 if any(overlaps) else gap

    # 切块：首张保留顶栏、去掉底栏；中间各张只取新增内容；末张补回底栏
    last = len(prepared) - 1
    pieces = [prepared[0].crop((0, 0, width, max(1, prepared[0].height - bottom)))]
    for i, im in enumerate(prepared[1:], start=1):
        start = top + overlaps[i - 1]
        end = im.height if i == last else im.height - bottom
        if start >= end:
            continue     # 这张全是重复内容，整张跳过
        pieces.append(im.crop((0, start, width, end)))

    height = sum(p.height for p in pieces) + effective_gap * (len(pieces) - 1)
    _guard_size(width, height)

    canvas = Image.new('RGB', (width, height), bg)
    y = 0
    for index, piece in enumerate(pieces):
        if index:
            y += effective_gap
        canvas.paste(piece.convert('RGB'), (0, y))
        y += piece.height

    return canvas, {
        'count': len(prepared),
        'used': len(pieces),
        'overlaps': overlaps,
        'chrome': (top, bottom),
        'size': (width, height),
    }


def to_bytes(img, fmt='png', quality=90):
    """导出为字节流，返回 (BytesIO, mimetype, 扩展名)"""
    buf = BytesIO()
    if fmt == 'jpeg':
        if max(img.size) > JPEG_MAX_SIDE:
            raise ValueError(
                f'长图边长 {max(img.size)} 超过 JPEG 上限 {JPEG_MAX_SIDE}，请改存 PNG'
            )
        img.convert('RGB').save(buf, 'JPEG', quality=quality, optimize=True)
        mimetype, ext = 'image/jpeg', 'jpg'
    else:
        img.save(buf, 'PNG', optimize=True)
        mimetype, ext = 'image/png', 'png'
    buf.seek(0)
    return buf, mimetype, ext
