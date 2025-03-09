import os
import time
import pickle  # 用于记录进度
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class WordToPDFConverter:

    def __init__(self, source_folder, driver_path=None):
        """
        初始化转换器
        :param source_folder: Word 文件所在的文件夹路径
        :param driver_path: ChromeDriver 的路径
        """
        self.source_folder = source_folder
        self.log_file = os.path.join(source_folder, "completed_files.pkl")  # 动态设置日志文件路径

        # 设置 ChromeDriver 路径
        self.driver_path = driver_path or r"E:\Project_Python\chromedriver-win64\chromedriver.exe"

        # 验证 Driver 路径是否有效
        if not os.path.exists(self.driver_path):
            raise FileNotFoundError(f"指定的 ChromeDriver 路径无效: {self.driver_path}")

        # 初始化浏览器驱动
        try:
            self.driver = self._init_driver()
        except Exception as e:
            raise RuntimeError(f"浏览器驱动初始化失败: {e}")

    def _init_driver(self):
        """初始化 Selenium Chrome 驱动"""
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--disable-extensions")
        service = Service(self.driver_path)
        return webdriver.Chrome(service=service, options=chrome_options)

    def _load_completed(self):
        """加载已完成文件列表"""
        if os.path.exists(self.log_file):
            with open(self.log_file, "rb") as f:
                return pickle.load(f)
        return set()

    def _save_completed(self, completed_files):
        """保存已完成文件列表"""
        with open(self.log_file, "wb") as f:
            pickle.dump(completed_files, f)

    def _get_word_files(self, completed_files):
        """获取所有未处理的 Word 文件"""
        all_files = [f for f in os.listdir(self.source_folder) if f.endswith((".docx", ".doc"))]
        return [f for f in all_files if f not in completed_files]

    def _convert_word_to_pdf(self, word_file):
        """转换单个 Word 文件为 PDF"""
        try:
            self.driver.get("https://www.ilovepdf.com/zh-cn/word_to_pdf")

            # 上传文件
            upload_btn = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
            )
            upload_btn.send_keys(os.path.join(self.source_folder, word_file))
            print(f"上传文件: {word_file}")

            # 点击转换按钮
            convert_btn = WebDriverWait(self.driver, 20).until(
                EC.element_to_be_clickable((By.ID, "processTask"))
            )
            convert_btn.click()
            print(f"开始转换文件: {word_file}")

            # 等待下载按钮出现，进行下载
            download_btn = WebDriverWait(self.driver, 60).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a.downloader__btn"))
            )
            download_btn.click()
            print(f"文件转换成功并下载: {word_file}")

            # 等待下载完成，暂停几秒确保文件保存
            time.sleep(10)
            return True
        except Exception as e:
            print(f"转换失败: {word_file}，错误: {e}")
            return False

    def process_files(self):
        """主流程：处理文件转换"""
        completed_files = self._load_completed()
        word_files = self._get_word_files(completed_files)

        if not word_files:
            print("没有未处理的文件！")
            self.driver.quit()
            return

        for word_file in word_files:
            success = self._convert_word_to_pdf(word_file)
            if success:
                completed_files.add(word_file)
                self._save_completed(completed_files)  # 更新完成记录
            else:
                print(f"文件未成功处理: {word_file}")
            time.sleep(5)  # 每次操作后暂停，防止过快

        print("所有文件处理完成！")
        self.driver.quit()

if __name__ == "__main__":
    # 示例用法
    SOURCE_FOLDER = r"E:\Python\Project\MyTravelPanel\MyWeb\App\static\资源\旅游产品\中国\湖南\CBJ 中国旅游\2025新加坡最新行程及报价\test"
    converter = WordToPDFConverter(SOURCE_FOLDER)
    converter.process_files()

