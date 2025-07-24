"""
调试脚本模板: debug_template.py
功能: [在此描述调试功能]
作者: [开发者姓名]
创建时间: [YYYY-MM-DD]
最后修改: [YYYY-MM-DD]
"""

import sys
import os
import traceback
import logging
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'debug_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 导入项目模块
try:
    from App import create_app
    from App.exts import db
    # 根据需要导入其他模块
    # from App.models.YourModel import YourModel
    # from App.routes.your_route import your_blueprint
except ImportError as e:
    logger.error(f"导入错误: {e}")
    print("请确保在正确的环境中运行此脚本")
    sys.exit(1)

def setup_debug_environment():
    """设置调试环境"""
    try:
        app = create_app()
        app.config['DEBUG'] = True
        
        # 配置数据库连接（使用测试数据库）
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///debug.db'
        
        logger.info("调试环境设置完成")
        return app
    except Exception as e:
        logger.error(f"设置调试环境失败: {e}")
        traceback.print_exc()
        return None

def debug_database_connection():
    """调试数据库连接"""
    print("=== 调试数据库连接 ===")
    
    try:
        with app.app_context():
            # 测试数据库连接
            db.engine.execute("SELECT 1")
            logger.info("数据库连接正常")
            print("✅ 数据库连接正常")
            return True
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        print(f"❌ 数据库连接失败: {e}")
        traceback.print_exc()
        return False

def debug_model_operations():
    """调试模型操作"""
    print("=== 调试模型操作 ===")
    
    try:
        with app.app_context():
            # 在这里添加模型调试代码
            # 示例:
            # records = YourModel.query.all()
            # logger.info(f"找到 {len(records)} 条记录")
            # print(f"✅ 找到 {len(records)} 条记录")
            
            print("✅ 模型操作正常")
            return True
    except Exception as e:
        logger.error(f"模型操作失败: {e}")
        print(f"❌ 模型操作失败: {e}")
        traceback.print_exc()
        return False

def debug_route_functionality():
    """调试路由功能"""
    print("=== 调试路由功能 ===")
    
    try:
        with app.app_context():
            # 在这里添加路由调试代码
            # 示例:
            # with app.test_client() as client:
            #     response = client.get('/your-route')
            #     logger.info(f"路由响应状态: {response.status_code}")
            #     print(f"✅ 路由响应状态: {response.status_code}")
            
            print("✅ 路由功能正常")
            return True
    except Exception as e:
        logger.error(f"路由功能失败: {e}")
        print(f"❌ 路由功能失败: {e}")
        traceback.print_exc()
        return False

def debug_configuration():
    """调试配置信息"""
    print("=== 调试配置信息 ===")
    
    try:
        with app.app_context():
            # 输出关键配置信息
            config_keys = [
                'DEBUG',
                'TESTING',
                'SQLALCHEMY_DATABASE_URI',
                'SECRET_KEY',
                'CACHE_TYPE'
            ]
            
            for key in config_keys:
                value = app.config.get(key, 'NOT_SET')
                # 隐藏敏感信息
                if 'SECRET' in key or 'PASSWORD' in key:
                    value = '***HIDDEN***'
                logger.info(f"配置 {key}: {value}")
                print(f"  {key}: {value}")
            
            print("✅ 配置信息正常")
            return True
    except Exception as e:
        logger.error(f"配置信息获取失败: {e}")
        print(f"❌ 配置信息获取失败: {e}")
        traceback.print_exc()
        return False

def debug_specific_issue():
    """调试特定问题"""
    print("=== 调试特定问题 ===")
    
    try:
        # 在这里添加特定问题的调试代码
        # 根据具体问题定制
        
        print("✅ 特定问题调试完成")
        return True
    except Exception as e:
        logger.error(f"特定问题调试失败: {e}")
        print(f"❌ 特定问题调试失败: {e}")
        traceback.print_exc()
        return False

def cleanup_debug_environment():
    """清理调试环境"""
    try:
        # 清理临时文件
        debug_db = Path('debug.db')
        if debug_db.exists():
            debug_db.unlink()
            logger.info("清理调试数据库文件")
        
        print("✅ 调试环境清理完成")
    except Exception as e:
        logger.warning(f"清理调试环境时出现问题: {e}")

def main():
    """主调试函数"""
    print("开始调试...")
    logger.info("开始调试会话")
    
    # 设置调试环境
    global app
    app = setup_debug_environment()
    if not app:
        print("❌ 无法设置调试环境，调试终止")
        return False
    
    # 运行调试
    debug_results = []
    
    with app.app_context():
        debug_results.append(debug_configuration())
        debug_results.append(debug_database_connection())
        debug_results.append(debug_model_operations())
        debug_results.append(debug_route_functionality())
        debug_results.append(debug_specific_issue())
    
    # 清理调试环境
    cleanup_debug_environment()
    
    # 输出调试结果
    successful_debugs = sum(debug_results)
    total_debugs = len(debug_results)
    
    print(f"\n=== 调试结果 ===")
    print(f"成功: {successful_debugs}/{total_debugs}")
    
    if successful_debugs == total_debugs:
        print("🎉 所有调试项目通过!")
        logger.info("调试会话完成，所有项目正常")
        return True
    else:
        print("❌ 部分调试项目失败")
        logger.warning(f"调试会话完成，{total_debugs - successful_debugs} 个项目失败")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n调试被用户中断")
        logger.info("调试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"调试过程中发生未预期的错误: {e}")
        logger.error(f"调试过程中发生未预期的错误: {e}")
        traceback.print_exc()
        sys.exit(1) 