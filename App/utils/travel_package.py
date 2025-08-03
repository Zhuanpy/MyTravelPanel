import datetime
import os


def get_file_time_info(file_path):
    # 获取文件的创建时间
    creation_time = os.path.getctime(file_path)

    # 获取文件的修改时间
    modification_time = os.path.getmtime(file_path)

    # 获取文件的访问时间
    access_time = os.path.getatime(file_path)

    # 转换为可读的时间格式
    creation_time_readable = datetime.datetime.fromtimestamp(creation_time)
    modification_time_readable = datetime.datetime.fromtimestamp(modification_time)
    access_time_readable = datetime.datetime.fromtimestamp(access_time)

    return {
        'creation_time': creation_time_readable,
        'modification_time': modification_time_readable,
        'access_time': access_time_readable
    }


# 示例用法
file_path = r'E:/WORKING/A-AIR_TICKET/HOTE LIST.xls'

time_info = get_file_time_info(file_path)

print(f"文件创建时间：{time_info['creation_time']}")
print(f"文件修改时间：{time_info['modification_time']}")
print(f"文件访问时间：{time_info['access_time']}")
