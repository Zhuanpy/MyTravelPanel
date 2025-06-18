from ..exts import db
from ..models.Visamodels import VisaLinks, VisaTypes

def update_visalinks():
    try:
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
        return True
        
    except Exception as e:
        db.session.rollback()
        print(f"更新visalinks表数据时发生错误: {str(e)}")
        return False

if __name__ == "__main__":
    update_visalinks() 