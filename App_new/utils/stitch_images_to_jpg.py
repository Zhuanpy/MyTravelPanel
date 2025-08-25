import cv2
import os
import sys
import numpy as np
from PIL import Image


def load_images_from_folder(folder):
    images = []
    for filename in sorted(os.listdir(folder)):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
            img = cv2.imread(os.path.join(folder, filename))
            if img is not None:
                images.append(img)
    return images


def convert_to_jpg(image):
    """确保输出为 JPG 格式：BGR 无透明通道"""
    if image.shape[-1] == 4:
        # 删除 alpha 通道
        image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    return image


def find_template(img, template, threshold=0.85):
    """返回模板在img中的top和bottom像素位置"""
    res = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    if max_val > threshold:
        top = max_loc[1]
        bottom = top + template.shape[0]
        return top, bottom
    else:
        return None, None


def find_template_last(img, template, threshold=0.85):
    res = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
    loc = np.where(res >= threshold)
    if len(loc[0]) == 0:
        return None, None
    # 取最靠下的匹配
    top = loc[0].max()
    bottom = top + template.shape[0]
    return top, bottom


def crop_by_template(images, header, footer):
    cropped = []
    for i, img in enumerate(images):
        h = img.shape[0]
        head_top, head_bottom = find_template(img, header, threshold=0.85)
        foot_top, foot_bottom = find_template_last(img, footer, threshold=0.85)
        print(f"第{i+1}张 head_bottom: {head_bottom}, foot_top: {foot_top}")
        if i == 0:
            if foot_top:
                cropped.append(img[:foot_top, :])
            else:
                cropped.append(img)
        elif i == len(images) - 1:
            if head_bottom:
                cropped.append(img[head_bottom:, :])
            else:
                cropped.append(img)
        else:
            if head_bottom and foot_top:
                cropped.append(img[head_bottom:foot_top, :])
            else:
                cropped.append(img)
    return cropped


def vertical_concat(images):
    # 先统一宽度
    min_width = min(img.shape[1] for img in images)
    resized = [cv2.resize(img, (min_width, int(img.shape[0] * min_width / img.shape[1]))) for img in images]
    return np.vstack(resized)


if __name__ == "__main__":
    folder_path = sys.argv[1] if len(sys.argv) > 1 else r"E:/Todays file"
    header_path = os.path.abspath("template/header.jpg")
    footer_path = os.path.abspath("template/footer.jpg")
    print("header_path:", header_path)
    print("footer_path:", footer_path)

    # 用PIL测试
    try:
        img = Image.open(header_path)
        img.verify()
        print("header.jpg 可以用PIL正常打开")
    except Exception as e:
        print("header.jpg 用PIL也打不开:", e)

    if not os.path.exists(folder_path):
        print(f"文件夹不存在: {folder_path}")
        sys.exit(1)
    if not os.path.exists(header_path) or not os.path.exists(footer_path):
        print("请提供抬头和抬尾模板图片（header.jpg, footer.jpg）")
        sys.exit(1)

    print("header_path:", header_path, "exists:", os.path.exists(header_path))
    print("footer_path:", footer_path, "exists:", os.path.exists(footer_path))

    images = load_images_from_folder(folder_path)
    header = cv2.imread(header_path)
    footer = cv2.imread(footer_path)
    if header is None:
        print("cv2.imread 依然无法读取 header.jpg")
    else:
        print("cv2.imread 读取 header.jpg 成功")
    if footer is None:
        print(f"无法读取抬尾模板图片: {footer_path}")
        sys.exit(1)

    if len(images) < 2:
        print("至少需要两张图片进行拼接。")
    else:
        try:
            cropped_images = crop_by_template(images, header, footer)
            result = vertical_concat(cropped_images)
            result = convert_to_jpg(result)
            output_path = os.path.join(folder_path, "stitched_output.jpg")
            cv2.imwrite(output_path, result, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
            print(f"拼接完成，结果保存为 JPG 文件：{output_path}")
        except Exception as e:
            print("拼接出错：", e)