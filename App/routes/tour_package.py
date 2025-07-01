import logging
import os
from datetime import datetime, timedelta
import sys
import subprocess
from flask import Blueprint, render_template, url_for, flash, redirect, request, jsonify
from flask import current_app as app
from sqlalchemy.exc import SQLAlchemyError

from ..exts import db
from ..forms.ProductForm import ProductForm
from ..models.Accountsmodels import SupplierData
from ..models.Packagemodels import Product, ProductCity


# 创建蓝图
package_blue = Blueprint('package_routes', __name__)


def get_all_pdf_files(directory):
    """
     获取指定目录（不包括子目录）中的所有 PDF 文件名。

     参数：
         directory (str): 要搜索的主目录路径。

     返回：
         list: 包含所有找到的 PDF 文件名的列表（不包括路径）。
     """
    # 用于存储找到的 PDF 文件名
    pdf_files = []

    # 获取指定目录下的所有文件和子目录
    # os.listdir 返回的是指定目录中的条目（文件和子目录）的列表
    for file in os.listdir(directory):
        # 构造完整路径以检查是否是文件
        full_path = os.path.join(directory, file)

        # 检查当前条目是否是文件且扩展名为 .pdf
        if os.path.isfile(full_path) and file.endswith('.pdf'):
            # 将文件名添加到结果列表中
            pdf_files.append(file)

    return pdf_files


def get_file_creation_time(file_path):
    creation_time = os.path.getctime(file_path)
    # 将时间戳转换为可读格式
    creation_datetime = datetime.fromtimestamp(creation_time)
    # 返回date对象
    return creation_datetime.date()  # 返回仅包含日期的部分

#
def construct_folder_path(*args) -> str:
    """构建文件夹路径"""
    base_path = os.path.join(app.root_path, app.static_folder, "资源", "旅游产品")
    # 过滤掉 None 和空字符串参数
    filtered_args = [arg for arg in args if arg]
    # 拼接路径
    return os.path.join(base_path, *filtered_args)


@package_blue.route('/add_product_page')
def add_product_page():
    form = ProductForm()
    return render_template('package/add_product.html', form=form)


@package_blue.route('/add_product', methods=['GET', 'POST'])
def add_product():
    form = ProductForm()

    if form.validate_on_submit():
        # 获取表单数据
        product = Product(
            city_name=form.city_name.data,
            company_name=form.company_name.data,
            product_name=form.product_name.data,
            created_at=form.created_at.data,
            valid_until=form.valid_until.data
        )
        # 添加到数据库
        db.session.add(product)
        db.session.commit()
        flash("产品添加成功!", "success")

        # 重定向到产品列表页面
        return redirect(url_for('index.index'))

    return render_template('package/add_product.html', form=form)


@package_blue.route('/our_package/<city_name>')
def our_package(city_name):

    # 确保提供了城市名称参数
    if not city_name:
        return jsonify({"error": "City parameter is required"}), 400

    country_name = ProductCity.get_country_name_by_city(city_name=city_name)

    products = Product.query.filter_by(city_name=city_name).all()

    return render_template('package/旅游产品展示.html', country_name=country_name,  city_name=city_name, products=products)


@package_blue.route('/open_company_package_folder/<country_name>/<city_name>/<company_name>', methods=['GET', 'POST'])
def open_company_package_folder(country_name, city_name, company_name):
    """
    打开指定城市和公司对应的旅游产品文件夹。
    如果公司名称未提供，则返回错误。

    :param country_name: 国家名称
    :param city_name: 城市名称
    :param company_name: 公司名称（必选）
    :return: 返回操作状态的 JSON 响应
    """

    # 确保提供了国家名称和城市名称
    if not country_name:
        return jsonify({"error": "Country_name parameter is required"}), 400

    if not city_name:
        return jsonify({"error": "City parameter is required"}), 400

    # 确保提供了公司名称
    if not company_name:
        return jsonify({"error": "Company name parameter is required"}), 400

    path = construct_folder_path(country_name, city_name, company_name)
    # 打印路径日志
    app.logger.info(f"Attempting to open folder: {path}")

    try:
        # 尝试打开文件夹
        os.startfile(path)
    except FileNotFoundError:
        error_message = "文件夹路径不存在，请检查路径是否正确。"
        app.logger.error(error_message)
        return jsonify({"error": error_message}), 404
    except Exception as e:
        error_message = f"打开文件夹时发生错误: {e}"
        app.logger.error(error_message)
        return jsonify({"error": error_message}), 500

    # 如果操作成功，返回成功消息
    return jsonify({"message": "Folder opened successfully"})

@package_blue.route('/open_city_package_folder/<country_name>/<city_name>', methods=['GET','POST'])
def open_city_package_folder(country_name, city_name):
    # 确保提供了城市名称参数
    if not country_name:
        return jsonify({"error": "Country_name parameter is required"}), 400

    # 确保提供了城市名称参数
    if not city_name:
        return jsonify({"error": "City parameter is required"}), 400

    path = construct_folder_path(country_name, city_name)

    # 打印路径日志
    app.logger.info(f"Attempting to open folder: {path}")

    try:
        # 尝试打开文件夹
        os.startfile(path)
        return jsonify({"message": "Folder opened successfully"})

    except FileNotFoundError:
        error_message = "文件夹路径不存在，请检查路径是否正确。"
        app.logger.error(error_message)
        return jsonify({"error": error_message}), 500


@package_blue.route('/delete_product/<int:product_id>/<city_name>', methods=['POST'])
def delete_product(product_id, city_name):
    # 查找产品并删除
    product = Product.query.get_or_404(product_id)

    try:
        db.session.delete(product)
        db.session.commit()
        flash('产品已成功删除', 'success')

    except Exception as e:
        db.session.rollback()
        flash('删除产品时出错，请重试', 'error')
        print(f"Error deleting product: {e}")

    # 重定向到产品列表页面
    return redirect(url_for('package_routes.our_package', city_name=city_name))


@package_blue.route('/delete_all_company_product/<city_name>/<company_name>', methods=['GET', 'POST'])
def delete_all_company_product(city_name, company_name):
    """删除指定公司所有产品"""
    try:
        # 查询所有属于该公司的产品
        all_products = Product.query.filter_by(company_name=company_name).all()

        if not all_products:
            flash('未找到相关产品', 'info')
        else:
            # 删除所有产品
            for product in all_products:
                print(product)
                db.session.delete(product)
            db.session.commit()
            flash('所有产品已成功删除', 'success')

    except SQLAlchemyError as e:
        db.session.rollback()
        flash('删除产品时出错，请重试', 'error')
        app.logger.error(f"Error deleting products for company '{company_name}': {e}")

    except Exception as e:
        db.session.rollback()
        flash('发生未知错误，请稍后重试', 'error')
        app.logger.error(f"Unexpected error: {e}")

    # 无论是否删除成功，都重定向到产品列表页面
    return redirect(url_for('package_routes.our_package', city_name=city_name))


@package_blue.route('/update_company_products/<city_name>/<company_name>', methods=['GET', 'POST'])
def update_company_products(city_name, company_name):
    # 从请求中获取城市和公司名称

    # 参数验证
    if not city_name or not company_name:
        flash("城市名称和公司名称不能为空！", "error")
        return redirect(url_for('package_routes.manage_cities'))

    country_name = ProductCity.get_country_name_by_city(city_name=city_name)
    # 构造文件夹路径
    path = construct_folder_path(country_name, city_name, company_name)

    # 获取指定路径下的所有PDF文件
    products = get_all_pdf_files(path)

    # 检查是否找到任何PDF文件
    if not products:
        flash("没有找到任何PDF文件。")  # 提示用户
        return redirect(url_for('package_routes.our_package', city_name=city_name))  # 重定向

    # 遍历所有找到的产品文件
    for p in products:
        file_path = os.path.join(path, p)  # 拼接文件路径
        create_timing = get_file_creation_time(file_path)  # 获取文件创建时间
        valid_until = create_timing + timedelta(days=60)  # 设置有效期为60天
        product_name = os.path.splitext(p)[0]  # 提取文件名（去掉扩展名）

        # 检查产品是否已经存在
        if Product.product_exists(city_name, company_name, product_name):
            flash(f"产品 '{product_name}' 已存在，跳过更新。")  # 提示用户
            continue  # 跳过此产品，继续下一个

        # 尝试添加产品，处理可能的错误
        try:
            Product.add_product(
                city_name=city_name,  # 城市名称
                company_name=company_name,  # 公司名称
                product_name=product_name,  # 产品名称
                created_at=create_timing,  # 文件创建日期
                valid_until=valid_until  # 产品有效期
            )
        except Exception as e:
            flash(f"添加产品时出错: {e}")  # 提示错误信息

    flash("产品更新成功！")  # 提示用户更新成功
    return redirect(url_for('package_routes.our_package', city_name=city_name))  # 重定向到产品页面


@package_blue.route('/update_city_products/<city_name>', methods=['GET'])
def update_city_products(city_name):
    """
    更新指定城市的旅游产品。
    根据指定城市名称，从静态文件夹中读取该城市下的公司及其旅游产品（PDF文件），并将这些产品信息添加到数据库。
    """
    if not city_name:
        return jsonify({"error": "City parameter is required"}), 400

    country_name = ProductCity.get_country_name_by_city(city_name=city_name)
    # 定义基本路径
    base_path = os.path.join(app.root_path, app.static_folder, "资源", "旅游产品", country_name)  # 获取当前文件的绝对路径

    def get_subfolder_names(folder_path):
        """
        获取指定文件夹内的所有子文件夹名称。
        :param folder_path: 文件夹路径
        :return: 子文件夹名称列表
        """

        try:
            # 使用列表推导式获取所有子文件夹
            return [f.name for f in os.scandir(folder_path) if f.is_dir()]

        except FileNotFoundError:
            flash(f"文件夹 {folder_path} 不存在.")

            return []

        except Exception as e:
            flash(f"获取子文件夹时发生错误: {e}")
            return []

    # 构建完整的文件夹路径
    folder_path = os.path.join(base_path, city_name)

    # 获取子文件夹名称
    all_company = get_subfolder_names(folder_path)

    for company in all_company:
        # 构造文件夹路径
        path = os.path.join(folder_path, company)
        # 获取指定路径下的所有PDF文件
        products = get_all_pdf_files(path)

        # 遍历每个产品文件并添加到数据库
        for p in products:

            file_path = os.path.join(path, p)  # 拼接文件路径
            create_timing = get_file_creation_time(file_path)  # 获取文件创建时间
            valid_until = create_timing + timedelta(days=60)  # 设置有效期为60天
            product_name = os.path.splitext(p)[0]  # 提取文件名（去掉扩展名）

            # 检查产品是否已经存在
            if Product.product_exists(city_name, company, product_name):
                flash(f"产品 '{product_name}' 已存在，跳过更新。")  # 提示用户
                continue  # 跳过此产品，继续下一个

            # 尝试添加产品，处理可能的错误
            try:
                Product.add_product(
                    city_name=city_name,  # 城市名称
                    company_name=company,  # 公司名称
                    product_name=product_name,  # 产品名称
                    created_at=create_timing,  # 文件创建日期
                    valid_until=valid_until  # 产品有效期
                )
            except Exception as e:
                flash(f"添加产品时出错: {e}")  # 提示错误信息

    # 重定向到产品展示页面
    flash("城市产品更新成功！")  # 提示用户更新成功

    return redirect(url_for('package_routes.our_package', city_name=city_name))


@package_blue.route('/show_supplier_info/<supplier_name>', methods=['GET', 'POST'])
def show_supplier_info(supplier_name=None):
    supplier_name = supplier_name or request.form.get('supplier_name')
    supplier = None

    if supplier_name:
        # 查询供应商信息
        supplier = SupplierData.query.filter_by(name=supplier_name).first()

    return render_template('package/供应商介绍.html', supplier=supplier, supplier_name=supplier_name)


@package_blue.route('/edit_supplier_info/<supplier_name>', methods=['GET', 'POST'])
def edit_supplier_info(supplier_name):
    # 查询供应商信息
    supplier = SupplierData.query.filter_by(name=supplier_name).first()

    if not supplier:

        flash(f"供应商 '{supplier_name}' 不存在。", 'error')

        return redirect(url_for('package_routes.show_supplier_info', supplier_name=supplier_name))

    if request.method == 'POST':
        try:
            # 获取表单数据，更新供应商信息
            supplier.address = request.form.get('address', supplier.address)
            supplier.contact_person = request.form.get('contact_person', supplier.contact_person)
            supplier.contact_info = request.form.get('contact_info', supplier.contact_info)
            supplier.status = request.form.get('status', supplier.status)
            supplier.country = request.form.get('country', supplier.country)
            supplier.region = request.form.get('region', supplier.region)
            supplier.rating = request.form.get('rating', supplier.rating)
            supplier.notes = request.form.get('notes', supplier.notes)

            # 提交修改到数据库
            db.session.commit()

            # 用户反馈
            flash(f"供应商 '{supplier_name}' 信息已成功更新。", 'success')

            return redirect(url_for('package_routes.show_supplier_info', supplier_name=supplier.name))

        except Exception as e:
            # 数据库异常处理
            db.session.rollback()
            flash(f"更新失败：{str(e)}", 'error')
            return redirect(url_for('package_routes.edit_supplier_info', supplier_name=supplier_name))

    # 渲染模板，展示当前供应商信息
    return render_template('package/供应商信息编辑.html', supplier=supplier)


@package_blue.route('/add_supplier_info/', defaults={'supplier_name': None}, methods=['GET', 'POST'])
@package_blue.route('/add_supplier_info/<supplier_name>', methods=['GET', 'POST'])
def add_supplier_info(supplier_name):
    if request.method == 'POST':
        # 获取表单数据
        address = request.form.get('address')
        contact_person = request.form.get('contact_person')
        contact_info = request.form.get('contact_info')
        status = request.form.get('status')
        country = request.form.get('country')
        region = request.form.get('region')
        rating = request.form.get('rating')
        notes = request.form.get('notes')

        if not address:
            flash('名称和地址是必填项', 'error')
            return redirect(url_for('package_routes.add_supplier_info', supplier_name=supplier_name))

        # 创建新供应商实例并提交到数据库
        new_supplier =SupplierData()
        new_supplier.add_supplier(name=supplier_name, address=address,
                                  contact_person=contact_person, contact_info=contact_info,
                                  status=status, country=country,
                                  region=region, rating=rating, notes=notes)


        flash('新供应商添加成功！', 'success')

        return redirect(url_for('package_routes.show_supplier_info', supplier_name=supplier_name))


    return render_template('package/供应商信息添加.html', supplier_name=supplier_name)


@package_blue.route('/manage_cities', methods=['GET', 'POST'])
def manage_cities():

    if request.method == 'POST':
        # 获取表单数据
        country_name = request.form.get('country_name', '').strip()
        city_name = request.form.get('city_name', '').strip()
        display_name = request.form.get('display_name', '').strip()

        # 构造目标文件夹路径
        target_path = construct_folder_path(country_name, city_name)

        # 检查文件夹是否存在，如果不存在则创建
        if not os.path.exists(target_path):
            os.makedirs(target_path)

        # 数据验证
        if not country_name or not city_name or not display_name:
            flash("所有字段均为必填项，请重新填写。", "error")
            return redirect(url_for('package_routes.manage_cities'))


        # 尝试插入新城市
        try:
            # 检查数据库中是否已经存在相同的数据
            existing_city = db.session.query(ProductCity).filter_by(
                country_name=country_name,
                city_name=city_name,
                display_name=display_name
            ).first()

            if existing_city is None:
                new_city = ProductCity(country_name=country_name, city_name=city_name, display_name=display_name)
                db.session.add(new_city)
                db.session.commit()
                flash("城市添加成功！", "success")

            else:
                flash("该城市已存在，无法重复添加。", "warning")

        except Exception as e:
            db.session.rollback()
            flash(f"发生错误：{str(e)}", "error")

        return redirect(url_for('package_routes.manage_cities'))

    # 查询所有城市并排序
    cities = ProductCity.query.order_by(ProductCity.display_name).all()
    # 供应商所属城市管理

    return render_template('package/供应商所属城市管理.html', cities=cities)


@package_blue.route('/edit_city/<int:city_id>', methods=['GET','POST'])
def edit_city(city_id):
    # 获取表单数据
    country_name = request.form.get('country_name', '').strip()
    city_name = request.form.get('city_name', '').strip()
    display_name = request.form.get('display_name', '').strip()

    # 查找对应的城市
    city = ProductCity.query.get_or_404(city_id)

    # 更新城市数据
    city.country_name = country_name
    city.city_name = city_name
    city.display_name = display_name

    # 保存更新到数据库
    db.session.commit()

    # 构建文件夹路径
    base_path = os.path.join(app.root_path, app.static_folder, "资源", "旅游产品")
    target_path = os.path.join(base_path, country_name, city_name)

    # 检查文件夹是否存在，如果不存在则创建
    if not os.path.exists(target_path):
        os.makedirs(target_path)

    # 重定向到城市管理页面
    return redirect(url_for('package_routes.manage_cities'))


@package_blue.route('/delete_city/<int:city_id>', methods=['POST'])
def delete_city(city_id):
    city = ProductCity.query.get_or_404(city_id)
    db.session.delete(city)
    db.session.commit()
    return redirect(url_for('package_routes.manage_cities'))

def create_folder(base_dir, folder_name):
    """
    在指定目录下创建文件夹，如果存在则忽略。
    :param base_dir: 基础目录
    :param folder_name: 要创建的文件夹名称
    :return: 创建的完整路径
    """
    folder_path = os.path.join(base_dir, folder_name)

    # 使用 os.makedirs()，如果文件夹已经存在，则不会报错
    os.makedirs(folder_path, exist_ok=True)

    return folder_path


@package_blue.route('/tour_project', methods=['GET', 'POST'])
def handle_tour_project():
    """重定向到新的旅游项目创建页面"""
    return redirect(url_for('tour_projects.create_tour_project'))


@package_blue.route('/')
def index():
    # 获取所有城市信息并按国家分组
    cities = ProductCity.query.order_by(ProductCity.country_name, ProductCity.display_name).all()
    cities_by_country = {}
    
    for city in cities:
        if city.country_name not in cities_by_country:
            cities_by_country[city.country_name] = []
        cities_by_country[city.country_name].append(city)
    
    return render_template('index.html', cities_by_country=cities_by_country)

@package_blue.route('/all_packages')
def all_packages():
    # 获取所有城市，按国家分组
    cities = ProductCity.query.order_by(ProductCity.display_name).all()
    cities_by_country = {}
    
    for city in cities:
        country = city.country_name
        if country not in cities_by_country:
            cities_by_country[country] = []
        cities_by_country[country].append(city)
    
    return render_template('package/all_packages.html', cities_by_country=cities_by_country)

@package_blue.route('/package_home')
def package_home():
    """配套首页路由"""
    # 获取所有城市信息并按国家分组
    cities_by_country = {}
    cities = ProductCity.query.order_by(ProductCity.country_name).all()
    
    for city in cities:
        if city.country_name not in cities_by_country:
            cities_by_country[city.country_name] = []
        cities_by_country[city.country_name].append(city)
    
    return render_template('package/配套首页.html', cities_by_country=cities_by_country)
