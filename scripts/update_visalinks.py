import sys
import os
import click
from flask.cli import with_appcontext

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App.exts import db
from App.models.Visamodels import VisaLinks, VisaTypes

@click.command()
@with_appcontext
def update_visalinks():
    """更新visalinks表数据，将visa_type转换为visa_type_id"""
    try:
        print("开始更新visalinks表数据...")
        
        # 1. 获取所有现有的visalinks记录
        old_links = VisaLinks.query.all()
        
        # 2. 创建临时表来存储新的数据
        temp_links = []
        for link in old_links:
            # 根据visa_type字符串查找对应的VisaTypes记录
            visa_type = VisaTypes.query.filter_by(visa_type=link.visa_type).first()
            if visa_type:
                temp_links.append({
                    'id': link.id,
                    'visa_type_id': visa_type.id,
                    'name': link.name,
                    'link': link.link
                })
            else:
                print(f"警告: 找不到visa_type为 '{link.visa_type}' 的记录")
        
        # 3. 删除旧表数据
        db.session.query(VisaLinks).delete()
        
        # 4. 插入新数据
        for link_data in temp_links:
            new_link = VisaLinks(
                id=link_data['id'],
                visa_type_id=link_data['visa_type_id'],
                name=link_data['name'],
                link=link_data['link']
            )
            db.session.add(new_link)
        
        # 5. 提交更改
        db.session.commit()
        print("成功更新visalinks表数据！")
        print(f"共更新了 {len(temp_links)} 条记录")
        return True
        
    except Exception as e:
        db.session.rollback()
        print(f"更新visalinks表数据时发生错误: {str(e)}")
        return False

if __name__ == "__main__":
    update_visalinks() 