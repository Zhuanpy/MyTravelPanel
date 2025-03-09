import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import os
from PyPDF2 import PdfMerger


class MyPdfFile:

    def __init__(self, folder: str):
        self.files = folder

    def merge_pdf2pdf(self):

        output_path = os.path.join(self.files, 'MyPdf.pdf')

        pdf_lst = [f for f in os.listdir(self.files) if f.endswith('.pdf')]

        pdf_lst = [os.path.join(self.files, filename) for filename in pdf_lst]

        file_merger = PdfMerger()

        for f in pdf_lst:
            file_merger.append(f)  # 合并pdf文件

        file_merger.write(output_path)

    # Merge images into PDF
    def merge_images2pdf(self):
        pdfFilePath = os.path.join(self.files, 'CombinePdf.pdf')
        files = os.listdir(self.files)

        files_list = []
        sources = []

        image_extensions = ['jpg', 'png', 'jpeg', 'webp']

        for file in files:
            split_files = file.split('.')
            extension = split_files[-1].lower()

            if extension in image_extensions:
                file_path_ = os.path.join(self.files, file)
                try:
                    if int(split_files[0]) <= 5 and len(split_files[0]) == 1:
                        continue
                    files_list.append(file_path_)

                except ValueError:
                    files_list.append(file_path_)

        files_list.sort()
        output = Image.open(files_list[0])
        files_list.pop(0)

        for file in files_list:

            pngFile = Image.open(file)

            if pngFile.mode == "RGB":
                pngFile = pngFile.convert("RGB")

            sources.append(pngFile)

        output.save(pdfFilePath, "pdf", save_all=True, append_images=sources)


class VisasUtils:

    @classmethod
    def combine_JPG2Pdf(cls, folderPath: str, destination_path: str):
        """
        将指定文件夹中的图片合并为 PDF 文件。

        :param folderPath: 包含图片的文件夹路径
        :param destination_path: 生成的 PDF 文件路径

        """

        # 设定输出 PDF 文件路径
        pdfFilePath = os.path.join(destination_path, 'visa_form.pdf')

        # 获取文件夹中的所有文件
        files = os.listdir(folderPath)
        pngFiles = []
        sources = []

        THRESHOLD_VALUE = 0  # 设定不转化的图片的阈值
        for file in files:
            # 筛选出图片文件
            if any(ext in file.lower() for ext in ['jpg', 'png', 'jpeg', 'webp']):
                filename = os.path.splitext(file)[0]

                try:
                    # 判断文件名是否为大于阈值的数字
                    if int(filename) > THRESHOLD_VALUE:
                        pngFiles.append(os.path.join(folderPath, file))

                except ValueError:
                    # 如果文件名不是数字，直接添加
                    pngFiles.append(os.path.join(folderPath, file))

        pngFiles.sort()
        output = Image.open(pngFiles[0])
        pngFiles.pop(0)

        for file in pngFiles:

            pngFile = Image.open(file)
            # 确保图片模式为 RGB
            if pngFile.mode == "RGB":
                pngFile = pngFile.convert("RGB")

            sources.append(pngFile)

        # 保存为 PDF 文件
        output.save(pdfFilePath, "pdf", save_all=True, append_images=sources)

    @classmethod
    def fill_form(cls, folder: str):
        """
        根据提供的表格信息填充表单，并生成对应的图片和 PDF 文件。

        :param folder: 目标文件夹名称

        """
        folder_title = "Korea_Visa"
        base_path = r'E:\WORKING\A-AIR_TICKET'

        form_folder = f'{folder_title}_{folder}'
        form_path = os.path.join(base_path, form_folder)
        form_temp_path = os.path.join(form_path, "temp")

        source_path = os.path.join(base_path, "01_Visa", "VisaDocumentRequirements", "01_Korea_visa", "source")

        for p in range(1, 6):

            page = f'PAGE0{p}'
            loc_file = os.path.join(source_path, "坐标列表.xls")
            # 读取坐标信息
            loc_list = pd.read_excel(loc_file, sheet_name='Sheet1')
            loc_list = loc_list[loc_list['PAGE'] == page]
            loc_list[["坐标序列"]] = loc_list[["坐标序列"]].astype(str)
            loc_list[["坐标X", "坐标Y"]] = loc_list[["坐标X", "坐标Y"]].astype(int)

            # 清理填写表格信息
            form_sample = os.path.join(form_path, "FormSample.xls")
            form = pd.read_excel(form_sample, sheet_name='Sheet1')
            form = form[form['PAGE'] == page]
            form = form[~(form['DETAIL'].isnull())]
            form[["坐标序列", "DETAIL"]] = form[["坐标序列", "DETAIL"]].astype(str)

            # 打开图片并创建绘图对象
            image_name = f"Form-page-{p}.jpg"
            image_path = os.path.join(source_path, image_name)
            image = Image.open(image_path)
            draw = ImageDraw.Draw(image)

            # 设置字体、字号和颜色
            font = ImageFont.truetype("simsun.ttc", 50)  # 楷体字体文件
            text_color = (0, 0, 255)  # 文字颜色

            for i in form.index:
                filling_texts = form.loc[i, 'DETAIL']
                form_type = form.loc[i, '类型']
                filling_Number = form.loc[i, '坐标序列']

                if form_type == "选择":
                    filling_Number = filling_Number + filling_texts
                    filling_texts = "√"

                x = loc_list.loc[loc_list['坐标序列'] == filling_Number, '坐标X'].iloc[0]
                y = loc_list.loc[loc_list['坐标序列'] == filling_Number, '坐标Y'].iloc[0]

                text_position = (x, y)
                draw.text(text_position, filling_texts, font=font, fill=text_color)

            image_name = f"{page}.jpg"
            image.save(f"{form_temp_path}/{image_name}")

        cls.combine_JPG2Pdf(form_temp_path, form_path)

    @classmethod
    def check_and_create_folder(cls, path):
        """检查路径是否存在，如果不存在则创建它。"""
        os.makedirs(path, exist_ok=True)

    @classmethod
    def load_excel_files(cls, source_path, destination_folder_path):
        """加载坐标列表和表单模板Excel文件。"""
        loc_file = os.path.join(source_path, "坐标列表.xls")
        form_sample = os.path.join(destination_folder_path, "FormSample.xls")

        try:
            loc_list = pd.read_excel(loc_file, sheet_name='Sheet1')
            form_data = pd.read_excel(form_sample, sheet_name='Sheet1')

        except FileNotFoundError as e:
            print(f"File not found: {e}")
            return None, None

        except Exception as e:
            print(f"Error reading Excel files: {e}")
            return None, None

        return loc_list, form_data

    @classmethod
    def setup_font(cls, ):
        """设置字体和文字颜色。"""
        try:
            font = ImageFont.truetype("simsun.ttc", 50)
        except IOError:
            print("字体文件 'simsun.ttc' 未找到，请确认路径正确。")
            return None

        return font, (0, 0, 255)  # 蓝色文字

    @classmethod
    def process_image(cls, page, loc_list, form_data, font, text_color, source_path, temp_folder):
        """处理单张图片，并将文本填充到指定坐标位置。"""
        print(loc_list)
        loc_page_data = loc_list[loc_list['PAGE'] == page]
        loc_page_data[["坐标序列"]] = loc_page_data[["坐标序列"]].astype(str)
        loc_page_data[["坐标X", "坐标Y"]] = loc_page_data[["坐标X", "坐标Y"]].astype(int)

        form_page_data = form_data[form_data['PAGE'] == page]
        form_page_data = form_page_data[~form_page_data['DETAIL'].isnull()]
        form_page_data[["坐标序列", "DETAIL"]] = form_page_data[["坐标序列", "DETAIL"]].astype(str)

        image_name = f"Form-page-{page[-1]}.jpg"
        image_path = os.path.join(source_path, image_name)

        if not os.path.exists(image_path):
            print(f"Image {image_name} not found. Skipping.")
            return

        # 打开图片并创建绘图对象
        with Image.open(image_path) as image:
            draw = ImageDraw.Draw(image)

            for i in form_page_data.index:
                filling_texts = form_page_data.loc[i, 'DETAIL']
                form_type = form_page_data.loc[i, '类型']
                filling_number = form_page_data.loc[i, '坐标序列']

                if form_type == "选择":
                    filling_number = filling_number + filling_texts
                    filling_texts = "√"

                loc_data = loc_page_data[loc_page_data['坐标序列'] == filling_number]
                if loc_data.empty:
                    print(f"坐标序列 '{filling_number}' 未找到，跳过。")
                    continue

                x = loc_data['坐标X'].iloc[0]
                y = loc_data['坐标Y'].iloc[0]
                draw.text((x, y), filling_texts, font=font, fill=text_color)

            save_image_name = f"{page}.jpg"
            save_path = os.path.join(temp_folder, save_image_name)
            image.save(save_path)
            print(f"保存图片到: {save_path}")
