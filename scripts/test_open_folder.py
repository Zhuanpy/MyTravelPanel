import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_open_folder_path():
    """测试open_folder函数的路径构建逻辑"""
    
    # 模拟参数
    folder_type = 'project'
    project_folder = '中国护照_171466_MU YUMING_工作准证'
    visa_type = '中国护照'
    
    # 获取项目根目录（模拟visa_project.py中的逻辑）
    # 注意：visa_project.py 在 App/routes/projects/VisaProjects/ 目录下
    # 所以需要往上4级才能到项目根目录
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent  # scripts -> MyTravelPanel
    
    print(f"当前文件: {current_file}")
    print(f"项目根目录: {project_root}")
    
    # 构建路径（按照visa_project.py中的逻辑）
    if folder_type == 'project' and project_folder and visa_type:
        base_folder = project_root / "App" / "static" / "资源" / "Project" / "Visa"
        print(f"基础文件夹: {base_folder}")
        print(f"基础文件夹是否存在: {base_folder.exists()}")
        
        # 首先尝试在签证类型子文件夹中查找
        folder_path1 = base_folder / visa_type / project_folder
        print(f"路径1 (签证类型子文件夹): {folder_path1}")
        print(f"路径1是否存在: {folder_path1.exists()}")
        
        # 如果不存在，尝试在根目录中查找
        folder_path2 = base_folder / project_folder
        print(f"路径2 (根目录): {folder_path2}")
        print(f"路径2是否存在: {folder_path2.exists()}")
        
        # 确定最终路径
        if folder_path1.exists():
            final_path = folder_path1
        elif folder_path2.exists():
            final_path = folder_path2
        else:
            final_path = None
            
        print(f"最终路径: {final_path}")
        print(f"最终路径是否存在: {final_path.exists() if final_path else False}")
        
        return final_path
    
    return None

if __name__ == "__main__":
    test_open_folder_path() 