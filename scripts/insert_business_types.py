from App import create_app
from App.models.Product.BusinessType import BusinessType
from App.exts import db

def insert_business_types():
    """插入默认业务类型数据"""
    app = create_app()
    with app.app_context():
        try:
            # 检查是否已有数据
            if BusinessType.query.first() is not None:
                print("业务类型数据已存在，跳过插入")
                return

            # 定义默认业务类型
            default_types = [
                {'name': '机票', 'code': 'airline', 'description': '航空机票服务', 'sort_order': 10},
                {'name': '景点/活动', 'code': 'attraction', 'description': '景点门票和活动预订', 'sort_order': 20},
                {'name': '租车', 'code': 'car', 'description': '汽车租赁服务', 'sort_order': 30},
                {'name': '邮轮', 'code': 'cruise', 'description': '邮轮旅游服务', 'sort_order': 40},
                {'name': '渡轮', 'code': 'ferry', 'description': '渡轮运输服务', 'sort_order': 50},
                {'name': '酒店', 'code': 'hotel', 'description': '酒店住宿服务', 'sort_order': 60},
                {'name': '保险', 'code': 'insurance', 'description': '旅游保险服务', 'sort_order': 70},
                {'name': '地接', 'code': 'land_tour', 'description': '当地旅游接待服务', 'sort_order': 80},
                {'name': '其他', 'code': 'miscellaneous', 'description': '其他未分类服务', 'sort_order': 90},
                {'name': '火车/大巴', 'code': 'rail_coach', 'description': '铁路和长途汽车服务', 'sort_order': 100},
                {'name': '服务费', 'code': 'service_fee', 'description': '各类服务费用', 'sort_order': 110},
                {'name': '门票', 'code': 'ticket', 'description': '各类景点门票', 'sort_order': 120},
                {'name': '接送', 'code': 'transfer', 'description': '接送机和交通服务', 'sort_order': 130},
                {'name': '签证', 'code': 'visa', 'description': '签证办理服务', 'sort_order': 140},
                {'name': '代金券', 'code': 'voucher', 'description': '旅游代金券服务', 'sort_order': 150},
                {'name': '旅游套餐', 'code': 'tour_package', 'description': '组合旅游产品套餐', 'sort_order': 160},
            ]

            # 插入数据
            for type_info in default_types:
                business_type = BusinessType(
                    name=type_info['name'],
                    code=type_info['code'],
                    description=type_info['description'],
                    sort_order=type_info['sort_order'],
                    is_active=True
                )
                db.session.add(business_type)

            db.session.commit()
            print("成功插入所有业务类型数据")

        except Exception as e:
            db.session.rollback()
            print(f"插入数据时出错: {str(e)}")

if __name__ == '__main__':
    insert_business_types() 