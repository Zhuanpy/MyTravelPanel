from flask import Blueprint, render_template, jsonify
from ..models.Packagemodels import ProductCity
from ..models.Visamodels import VisaTypes
import os
from pathlib import Path

dex = Blueprint("index", __name__)


@dex.route('/')
def index():
    packages = ProductCity.query.order_by(ProductCity.country_name, ProductCity.city_name).all()  # 假设 Package 是你的数据模型
    visa_categories = VisaTypes.query.order_by(VisaTypes.visa_type_name).all()
    return render_template('index.html', packages=packages, visa_categories=visa_categories)



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

