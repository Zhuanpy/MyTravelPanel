#!/usr/bin/env python3
"""
创建签证文档相关表的脚本
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App import create_app
from App.exts import db
from App.models import VisaDocumentsList

def create_visa_documents_tables():
    """创建签证文档相关的表"""
    app = create_app()
    
    with app.app_context():
        try:
            print("开始创建签证文档相关表...")
            
            # 创建表
            db.create_all()
            print("✅ 表创建完成")
            
            # 检查visa_documents_list表是否存在
            try:
                count = VisaDocumentsList.query.count()
                print(f"✅ visa_documents_list表存在，当前有 {count} 条记录")
            except Exception as e:
                print(f"❌ visa_documents_list表不存在或有问题: {e}")
                return False
            
            # 如果表为空，插入一些基础数据
            if count == 0:
                print("📝 插入基础文档数据...")
                base_documents = [
                    ('护照原件', '申请人护照原件', '身份证明'),
                    ('护照复印件', '申请人护照复印件', '身份证明'),
                    ('近期护照照片', '近期拍摄的护照规格照片', '身份证明'),
                    ('身份证复印件', '申请人身份证复印件', '身份证明'),
                    ('出生证明', '申请人出生证明', '身份证明'),
                    ('结婚证明', '申请人结婚证明（如适用）', '身份证明'),
                    ('学历证明', '申请人学历证明', '教育背景'),
                    ('工作证明', '申请人工作证明', '工作背景'),
                    ('银行对账单', '申请人银行对账单', '财务证明'),
                    ('申请表', '签证申请表', '申请材料'),
                    ('邀请函', '邀请函或担保函', '申请材料'),
                    ('行程安排', '详细的行程安排', '申请材料'),
                    ('酒店预订', '酒店预订确认', '申请材料'),
                    ('机票预订', '往返机票预订', '申请材料'),
                    ('保险证明', '旅行保险证明', '申请材料'),
                    ('在职证明', '在职证明信', '工作背景'),
                    ('收入证明', '收入证明文件', '财务证明'),
                    ('房产证明', '房产证明文件', '财务证明'),
                    ('车辆证明', '车辆证明文件', '财务证明'),
                    ('无犯罪记录证明', '无犯罪记录证明', '背景调查')
                ]
                
                for name, description, category in base_documents:
                    doc = VisaDocumentsList(
                        name=name,
                        description=description,
                        category=category
                    )
                    db.session.add(doc)
                
                db.session.commit()
                print(f"✅ 成功插入 {len(base_documents)} 条基础文档数据")
            
            print("🎉 签证文档表创建和初始化完成！")
            return True
            
        except Exception as e:
            print(f"❌ 创建表时发生错误: {e}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    success = create_visa_documents_tables()
    if success:
        print("\n✅ 脚本执行成功！")
        sys.exit(0)
    else:
        print("\n❌ 脚本执行失败！")
        sys.exit(1) 