import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import os
from PyPDF2 import PdfReader, PdfWriter
try:
    # Optional imports available in newer PyPDF2/pypdf versions
    from PyPDF2 import PageObject, Transformation  # type: ignore
except Exception:  # pragma: no cover
    PageObject = None
    Transformation = None


class MyPdfFile:

    def __init__(self, folder: str):
        self.files = folder

    def merge_pdf2pdf(self):
        try:
            output_path = os.path.join(self.files, 'Pdf.pdf')

            pdf_lst = [f for f in os.listdir(self.files) if f.lower().endswith('.pdf')]

            if not pdf_lst:
                raise ValueError("文件夹中没有找到PDF文件")

            pdf_paths = [os.path.join(self.files, filename) for filename in sorted(pdf_lst)]

            writer = PdfWriter()
            total_pages_added = 0

            for pdf_path in pdf_paths:
                try:
                    with open(pdf_path, 'rb') as fh:
                        try:
                            reader = PdfReader(fh, strict=False)
                        except TypeError:
                            # some versions don't support strict kw
                            reader = PdfReader(fh)

                        if getattr(reader, 'is_encrypted', False):
                            try:
                                reader.decrypt("")
                            except Exception as e:
                                print(f"跳过加密的PDF文件 {pdf_path}: {str(e)}")
                                continue

                        num_pages = len(reader.pages)
                        # 统一输出为A4尺寸（单位：pt）
                        A4_W = 595.276  # 210mm
                        A4_H = 841.890  # 297mm

                        for page_index in range(num_pages):
                            try:
                                page = reader.pages[page_index]
                                # 将每页内容缩放/居中到A4尺寸
                                if PageObject is not None and Transformation is not None:
                                    try:
                                        orig_w = float(page.mediabox.width)
                                        orig_h = float(page.mediabox.height)
                                        if orig_w <= 0 or orig_h <= 0:
                                            raise ValueError("invalid page size")

                                        scale = min(A4_W / orig_w, A4_H / orig_h)
                                        tx = (A4_W - orig_w * scale) / 2.0
                                        ty = (A4_H - orig_h * scale) / 2.0

                                        blank = PageObject.create_blank_page(width=A4_W, height=A4_H)
                                        blank.merge_transformed_page(
                                            page,
                                            Transformation().scale(scale, scale).translate(tx, ty)
                                        )
                                        writer.add_page(blank)
                                    except Exception as _e:
                                        # 回退：无法转换时直接添加原始页面
                                        print(f"A4标准化失败，使用原始页面: {pdf_path} 第 {page_index + 1} 页，原因: {_e}")
                                        writer.add_page(page)
                                else:
                                    # 缺少必要API时，直接添加原始页面
                                    writer.add_page(page)
                                total_pages_added += 1
                            except AssertionError as e:
                                # 针对 PyPDF2 clone 过程中出现的断言错误，跳过该页
                                print(f"跳过损坏页面 {pdf_path} 第 {page_index + 1} 页: {str(e)}")
                                continue
                            except Exception as e:
                                print(f"添加页面失败 {pdf_path} 第 {page_index + 1} 页: {str(e)}")
                                continue
                    print(f"成功处理文件: {pdf_path}，页数: {num_pages}")
                except Exception as e:
                    print(f"跳过损坏的PDF文件 {pdf_path}: {str(e)}")
                    continue

            if total_pages_added == 0:
                raise ValueError("未能从任何PDF添加有效页面，可能所有文件均损坏或加密")

            with open(output_path, 'wb') as out_fh:
                writer.write(out_fh)
            print(f"PDF合并完成，输出文件: {output_path}，共添加页数: {total_pages_added}")

        except Exception as e:
            print(f"PDF合并失败: {str(e)}")
            raise

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
    def korea_visa_fill_form(cls, visa_folder: str, static_path):
        """
        根据提供的表格信息填充表单，并生成对应的图片和 PDF 文件。

        :param visa_folder: 项目文件夹夹名称
        :param static_path: 数据 flask 项目 static 文件夹路径，其它资源文件通过此文件夹找
        """
        from App_new.config import Config
        visa_project_path = Config.VISA_PROJECTS_PATH

        form_path = os.path.join(visa_project_path, visa_folder)
        form_temp_path = os.path.join(form_path, "temp")

        """检查路径是否存在，如果不存在则创建它。"""
        os.makedirs(form_temp_path, exist_ok=True)

        from App_new.config import Config
        source_path = os.path.join(Config.PROJECT_ROOT, "资源", "签证", "韩国签证", "source")  # 韩国签证 图片文件和坐标文件路径

        # 检查源路径是否存在
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"韩国签证资源路径不存在: {source_path}")

        for p in range(1, 6):
            page = f'PAGE0{p}'
            loc_file = os.path.join(source_path, "坐标列表.xls")
            
            # 检查坐标文件是否存在
            if not os.path.exists(loc_file):
                raise FileNotFoundError(f"坐标列表文件不存在: {loc_file}")
            
            # 读取坐标信息
            try:
                loc_list = pd.read_excel(loc_file, sheet_name='Sheet1')
                print(f"坐标文件列名: {list(loc_list.columns)}")
                print(f"查找页面: {page}")
                
                # 过滤当前页面的数据
                loc_list = loc_list[loc_list['PAGE'] == page]
                print(f"找到 {len(loc_list)} 条坐标数据")
                
                # 确保坐标序列是字符串类型
                loc_list['坐标序列'] = loc_list['坐标序列'].astype(str)
                
                # 确保坐标X和坐标Y是整数类型
                loc_list['坐标X'] = loc_list['坐标X'].astype(int)
                loc_list['坐标Y'] = loc_list['坐标Y'].astype(int)
                
                print(f"坐标序列示例: {list(loc_list['坐标序列'].head())}")
                
            except Exception as e:
                raise Exception(f"读取坐标文件失败: {str(e)}")

            # 清理填写表格信息
            form_sample = os.path.join(form_path, "FormSample.xls")
            
            print(f"尝试读取表单文件: {form_sample}")
            
            # 检查表单模板文件是否存在
            if not os.path.exists(form_sample):
                print(f"错误: 表单模板文件不存在: {form_sample}")
                print(f"请确保在项目文件夹 {form_path} 中有 FormSample.xls 文件")
                raise FileNotFoundError(f"表单模板文件不存在: {form_sample}")
            
            print(f"成功找到表单文件: {form_sample}")
            
            try:
                form = pd.read_excel(form_sample, sheet_name='Sheet1')
                
                # 检查必需的列是否存在
                required_columns = ['PAGE', 'DETAIL', '坐标序列', '类型']
                missing_columns = [col for col in required_columns if col not in form.columns]
                
                if missing_columns:
                    print(f"警告: FormSample.xls 缺少以下列: {missing_columns}")
                    print(f"现有列: {list(form.columns)}")
                    
                    # 如果缺少PAGE列，添加默认值
                    if 'PAGE' not in form.columns:
                        form['PAGE'] = page
                        print(f"已添加默认PAGE列: {page}")
                    
                    # 如果缺少其他列，添加空值
                    for col in missing_columns:
                        if col != 'PAGE':
                            form[col] = ''
                            print(f"已添加空列: {col}")
                
                # 过滤当前页面的数据
                form = form[form['PAGE'] == page]
                
                # 过滤非空数据
                if 'DETAIL' in form.columns:
                    form = form[~(form['DETAIL'].isnull())]
                
                # 确保数据类型正确
                if '坐标序列' in form.columns and 'DETAIL' in form.columns:
                    form[["坐标序列", "DETAIL"]] = form[["坐标序列", "DETAIL"]].astype(str)
                
                print(f"处理页面 {page}，找到 {len(form)} 条数据")
                
            except Exception as e:
                raise Exception(f"读取表单模板文件失败: {str(e)}")

            # 打开图片并创建绘图对象
            image_name = f"Form-page-{p}.jpg"  # 使用Form-page-1.jpg, Form-page-2.jpg等格式
            image_path = os.path.join(source_path, image_name)
            
            print(f"尝试读取图片: {image_path}")
            
            # 检查图片文件是否存在
            if not os.path.exists(image_path):
                print(f"警告: 图片文件不存在，跳过页面 {p}: {image_path}")
                print(f"请确保在 {source_path} 文件夹中有以下图片文件:")
                for i in range(1, 6):
                    print(f"  - Form-page-{i}.jpg")
                
                # 创建一个简单的占位图片
                try:
                    # 创建一个简单的白色图片作为占位符
                    placeholder_image = Image.new('RGB', (800, 1000), color='white')
                    draw = ImageDraw.Draw(placeholder_image)
                    
                    # 尝试加载字体
                    try:
                        font = ImageFont.truetype("simsun.ttc", 30)
                    except OSError:
                        font = ImageFont.load_default()
                    
                    # 在图片上添加提示文字
                    draw.text((50, 50), f"韩国签证表格 - 第{p}页", font=font, fill=(0, 0, 0))
                    draw.text((50, 100), "请准备对应的表单模板图片", font=font, fill=(255, 0, 0))
                    draw.text((50, 150), f"文件路径: {image_path}", font=font, fill=(0, 0, 255))
                    
                    # 保存占位图片
                    placeholder_image.save(image_path)
                    print(f"已创建占位图片: {image_path}")
                    
                    # 重新打开图片
                    image = Image.open(image_path)
                    draw = ImageDraw.Draw(image)
                except Exception as e:
                    print(f"创建占位图片失败: {str(e)}")
                    continue
            else:
                print(f"成功找到图片文件: {image_path}")
            
            try:
                image = Image.open(image_path)
                draw = ImageDraw.Draw(image)
            except Exception as e:
                raise Exception(f"打开图片文件失败 {image_path}: {str(e)}")

            # 设置字体、字号和颜色
            try:
                font = ImageFont.truetype("simsun.ttc", 50)  # 楷体字体文件
            except OSError:
                # 如果找不到simsun.ttc，尝试使用默认字体
                try:
                    font = ImageFont.load_default()
                except Exception as e:
                    raise Exception(f"无法加载字体: {str(e)}")
            
            text_color = (0, 0, 255)  # 文字颜色

            for i in form.index:
                try:
                    # 安全获取数据，提供默认值
                    filling_texts = form.loc[i, 'DETAIL'] if 'DETAIL' in form.columns else ''
                    form_type = form.loc[i, '类型'] if '类型' in form.columns else '文本'
                    filling_Number = form.loc[i, '坐标序列'] if '坐标序列' in form.columns else ''

                    # 跳过空数据
                    if not filling_texts or not filling_Number:
                        print(f"跳过空数据: 行 {i}, 文本='{filling_texts}', 坐标序列='{filling_Number}'")
                        continue

                    if form_type == "选择":
                        filling_Number = filling_Number + filling_texts
                        filling_texts = "√"

                    # 查找坐标
                    print(f"查找坐标序列: '{filling_Number}'")
                    print(f"可用的坐标序列: {list(loc_list['坐标序列'].unique())}")
                    
                    coord_data = loc_list.loc[loc_list['坐标序列'] == filling_Number]
                    if coord_data.empty:
                        print(f"警告: 未找到坐标序列 '{filling_Number}'，跳过")
                        print(f"请检查坐标文件中的坐标序列是否与FormSample.xls中的坐标序列匹配")
                        continue

                    x = coord_data['坐标X'].iloc[0]
                    y = coord_data['坐标Y'].iloc[0]

                    text_position = (x, y)
                    draw.text(text_position, filling_texts, font=font, fill=text_color)
                    print(f"成功填写: '{filling_texts}' 到坐标 ({x}, {y})")
                    
                except Exception as e:
                    print(f"警告: 处理表单数据时出错 (行 {i}): {str(e)}")
                    continue

            # 保存图片
            try:
                save_image_name = f"{page}.jpg"
                save_path = os.path.join(form_temp_path, save_image_name)
                image.save(save_path)
                print(f"保存图片到: {save_path}")
            except Exception as e:
                raise Exception(f"保存图片失败: {str(e)}")

        # 合并为PDF
        try:
            cls.combine_JPG2Pdf(form_temp_path, form_path)
        except Exception as e:
            raise Exception(f"合并PDF失败: {str(e)}")

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
