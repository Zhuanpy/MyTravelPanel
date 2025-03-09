import os
import cv2
import pandas as pd
from PIL import Image, ImageDraw, ImageFont


def nums_files(folder_path):
    # 使用 os.listdir() 获取文件夹中所有文件和子文件夹的列表
    items = os.listdir(folder_path)

    # 使用列表推导式筛选出只是文件而不是文件夹的项
    file_items = [item for item in items if os.path.isfile(os.path.join(folder_path, item))]

    # 获取文件数量
    file_count = len(file_items)
    return file_count


# 获取图片坐标函数
def get_locations(original, temp):  # 获取图片坐标函数

    # 读取大图片和小图片
    large_image = cv2.imread(original)
    small_image = cv2.imread(temp)

    # 使用匹配方法
    result = cv2.matchTemplate(large_image, small_image, cv2.TM_CCOEFF_NORMED)

    # 获取最大匹配位置
    _, _, _, max_loc = cv2.minMaxLoc(result)

    # 打印小图标在大图片中的位置
    return max_loc


def template_locations(folder: str):
    _root = 'E:/WORKING/A-AIR_TICKET/01_Visa/VisaDocumentRequirements/ChinaTravelPassport'
    temppath = os.path.join(_root, folder, 'template')
    original = os.path.join(_root, folder, 'FormSample.jpg')

    list_loc = []
    num = nums_files(temppath)  # 统计出文件数量

    for i in range(num):
        f = i + 1

        if f < 10:
            f = f'0{f}.jpg'

        else:
            f = f'{f}.jpg'

        f_name = os.path.join(temppath, f)
        loc = get_locations(original, f_name)
        list_loc.append(loc)

    return list_loc


def get_full_filename(folder_path):
    # 使用列表推导式获取所有的 .jpg 文件名称
    jpg_files = [f for f in os.listdir(folder_path) if f.endswith('.jpg')]
    return jpg_files


def get_full_location():
    df_list = []
    _path = f'E:/WORKING/A-AIR_TICKET/KoraVisaForm'
    for i in range(1, 6):
        page_folder = f'PAGE0{i}'
        template_path_ = os.path.join(_path, 'page_folder', 'template')
        form_sample = 'FormSample.jpg'

        jpg_files = get_full_filename(template_path_)

        for f in jpg_files:
            file_name = str(f[:2])
            # 获取 original, temp
            original = os.path.join(_path, page_folder, form_sample)
            temp = os.path.join(template_path_, f)

            xy = get_locations(original, temp)
            file_list = [page_folder, f, file_name, xy]
            df_list.append(file_list)

    # 储存 excel
    # print(f'{_path}/图片坐标列表.xls')
    colum_names = ['页面', '图片全名称', '图片名', '坐标']
    df = pd.DataFrame(df_list, columns=colum_names)
    df.to_excel(f'{_path}/图片坐标列表.xls', sheet_name='Sheet1', header=True, index=False)


def edit_form_jpg(folder: str, location_list: list, information_list: list):
    _root_path = 'E:/WORKING/A-AIR_TICKET'
    image_path = os.path.join(_root_path, folder, 'Form.jpg')
    image = Image.open(image_path)
    # 创建一个Draw对象
    draw = ImageDraw.Draw(image)
    # 选择字体,字号,颜色
    font = ImageFont.truetype("simsun.ttc", 50)  # 楷体字体文件
    text_color = (0, 0, 0)  # # 选择文字颜色

    for i in range(len(information_list)):
        texts = str(information_list[i])
        text_position = location_list[i]  # 文字在图片中的位置，以左上角为原点
        # 添加 customer name 到图片
        draw.text(text_position, texts, font=font, fill=text_color)  #

    # 保存修改后的图片
    out_path = ''
    image.save(f'{out_path}/{folder}.jpg')


if __name__ == '__main__':

    for p in range(1, 6):
        page = f'PAGE0{p}'
        loc_list = pd.read_excel('E:/WORKING/A-AIR_TICKET/KoraVisaForm/图片坐标列表.xls', sheet_name='Sheet1')
        form = pd.read_excel('E:/WORKING/A-AIR_TICKET/KoraVisaForm/Form.xls', sheet_name='Sheet1')
        loc_list = loc_list[loc_list['页面'] == page]

        #  清理填写表格信息
        form = form[form['PAGE'] == page]
        form = form[~(form['序列'].isnull())]

        form['序列'] = form['序列'].astype(int)

        form = form[(form['序列'] > 0) & (form['DETAIL'] != 'N/A')]
        form = form[~(form['DETAIL'].isnull())]

        loc_list['图片名'] = loc_list['图片名'].astype(int)

        image_path = F'E:/WORKING/A-AIR_TICKET/KoraVisaForm/{page}/Form.jpg'
        image = Image.open(image_path)
        # 创建一个Draw对象
        draw = ImageDraw.Draw(image)
        # 选择字体,字号,颜色
        font = ImageFont.truetype("simsun.ttc", 50)  # 楷体字体文件
        text_color = (0, 0, 0)  # # 选择文字颜色

        # exit()
        # print(form)

        for i in form.index:
            texts = str(form.loc[i, 'DETAIL'])
            temp_name = form.loc[i, '序列']
            temp_loc = loc_list[loc_list['图片名'] == temp_name]['坐标'].iloc[0]

            # print(temp_loc)
            temp_loc = temp_loc[1:-1].split(',')
            x = int(temp_loc[0])
            y = int(temp_loc[1])
            text_position = (x, y)
            draw.text(text_position, texts, font=font, fill=text_color)

        out_path = ''
        image.save(f'E:/WORKING/A-AIR_TICKET/KoraVisaForm/{page}.jpg')
