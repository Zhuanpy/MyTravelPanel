from flask import Blueprint, render_template, jsonify, send_from_directory
from ..models.Packagemodels import ProductCity
from ..models.Visamodels import VisaTypes
import os
from pathlib import Path

dex = Blueprint("index", __name__)


@dex.route('/')
def index():
    # 获取所有城市信息并按国家分组
    cities = ProductCity.query.order_by(ProductCity.country_name, ProductCity.display_name).all()
    cities_by_country = {}
    
    for city in cities:
        if city.country_name not in cities_by_country:
            cities_by_country[city.country_name] = []
        cities_by_country[city.country_name].append(city)
    
    # 获取签证类别
    visa_categories = VisaTypes.query.all()
    
    return render_template('index.html', 
                         cities_by_country=cities_by_country,
                         visa_categories=visa_categories)



@dex.route('/open_package_folder', methods=['GET', 'POST'])
def open_package_folder():
    current_dir = Path.cwd()
    folder_path = current_dir / "App" / "static" / "资源" / "旅游产品"
    folder_path = os.path.join(folder_path)
    os.startfile(folder_path)
    # 返回JSON响应，表示成功操作
    return jsonify({"status": "success"})


@dex.route('/open_package_project_folder', methods=['GET', 'POST'])
def open_package_project_folder():
    current_dir = Path.cwd()
    folder_path = current_dir / "App" / "static" / "资源" / "Project" / "Tour"
    folder_path = os.path.join(folder_path)
    os.startfile(folder_path)
    return jsonify({"status": "success"})


@dex.route('/open_bill_project_folder', methods=['GET', 'POST'])
def open_bill_project_folder():
    current_dir = Path.cwd()
    folder_path = current_dir / "App" / "static" / "资源" / "账单"
    folder_path = os.path.join(folder_path)
    os.startfile(folder_path)
    return jsonify({"status": "success"})


@dex.route('/add_visa_information', methods=['POST'])
def add_visa_information():
    # Logic to edit the city would go here
    pass


@dex.route('/resource/<path:filename>')
def resource_file(filename):
    import os
    from pathlib import Path
    base_dir = Path.cwd() / '资源' / '旅游产品'
    # 安全性校验，防止路径穿越
    safe_path = os.path.normpath(os.path.join(base_dir, filename))
    if not safe_path.startswith(str(base_dir)):
        return '非法路径', 403
    return send_from_directory(base_dir, filename)

