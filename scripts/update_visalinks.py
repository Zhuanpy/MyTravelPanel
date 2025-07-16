import os
import pandas as pd

# 设置文件路径
input_path = r"E:\Todays file\aaa\202208.xls"
output_path = r"E:\Todays file\aaa\202208_fixed.xlsx"


# 尝试修复
def try_fix_xls(file_path, output_file):
    try_encodings = ['utf-8', 'gbk', 'gb2312']
    success = False

    for enc in try_encodings:
        try:
            # 假设文件实际是 CSV 格式但扩展名是 .xls
            df = pd.read_csv(file_path, encoding=enc, delimiter='\t', engine='python', error_bad_lines=False)
            df.to_excel(output_file, index=False)
            print(f"成功读取并转换文件，使用编码：{enc}")
            success = True
            break
        except Exception as e:
            print(f"尝试编码 {enc} 失败：{e}")

    if not success:
        print("无法修复该文件。可能不是文本格式或已损坏。")


if __name__ == "__main__":
    if os.path.exists(input_path):
        try_fix_xls(input_path, output_path)
    else:
        print("文件不存在，请确认路径是否正确。")