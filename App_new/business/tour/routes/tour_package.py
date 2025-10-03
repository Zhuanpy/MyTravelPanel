import os
from datetime import datetime, timedelta
from flask import Blueprint, render_template, url_for, flash, redirect, request, jsonify
from flask import current_app as app
from flask_login import login_required, current_user
from App_new.utils.decorators import staff_only
from sqlalchemy.exc import SQLAlchemyError
from App_new.exts import db
from App_new.business.projects.forms.ProductForm import ProductForm
from App_new.shared.models.Accountsmodels import SupplierData
from ..models.Packagemodels import Product, ProductCity
from App_new.config import Config
from pathlib import Path

# 创建蓝图
package_blue = Blueprint('package_routes', __name__)


def get_all_pdf_files(directory):
    pdf_files = []
    for file in os.listdir(directory):
        full_path = Path(directory) / file
        if full_path.is_file() and file.endswith('.pdf'):
            pdf_files.append(file)
    return pdf_files


def get_file_creation_time(file_path):
    creation_time = os.path.getctime(file_path)
    creation_datetime = datetime.fromtimestamp(creation_time)
    return creation_datetime.date()

#
def construct_folder_path(*args) -> Path:
    """构建文件夹路径"""
    base_path = Config.TOUR_RESOURCES_PATH
    filtered_args = [arg for arg in args if arg]
    return base_path.joinpath(*filtered_args)


@login_required
@staff_only
@package_blue.route('/add_product_page')
def add_product_page():
    form = ProductForm()
    return render_template('business/tour/package/add_product.html', form=form)


@login_required
@staff_only
@package_blue.route('/add_product', methods=['GET', 'POST'])
def add_product():
    form = ProductForm()

    if form.validate_on_submit():
        product = Product(
            city_name=form.city_name.data,
            company_name=form.company_name.data,
            product_name=form.product_name.data,
            created_at=form.created_at.data,
            valid_until=form.valid_until.data
        )
        db.session.add(product)
        db.session.commit()
        flash("产品添加成功!", "success")
        return redirect(url_for('index.index'))

    return render_template('business/tour/package/add_product.html', form=form)


@login_required
@staff_only
@package_blue.route('/our_package/<city_name>')
def our_package(city_name):
    if not city_name:
        return jsonify({"error": "City parameter is required"}), 400
    country_name = ProductCity.get_country_name_by_city(city_name=city_name)
    products = Product.query.filter_by(city_name=city_name).all()
    return render_template('business/tour/package/tour_product_display.html', country_name=country_name,  city_name=city_name, products=products)


@package_blue.route('/open_company_package_folder/<country_name>/<city_name>/<company_name>', methods=['GET', 'POST'])
@login_required
@staff_only
def open_company_package_folder(country_name, city_name, company_name):
    if not country_name:
        return jsonify({"error": "Country_name parameter is required"}), 400
    if not city_name:
        return jsonify({"error": "City parameter is required"}), 400
    if not company_name:
        return jsonify({"error": "Company name parameter is required"}), 400
    path = construct_folder_path(country_name, city_name, company_name)
    app.logger.info(f"Attempting to open folder: {path}")
    
    # 如果文件夹不存在，则创建它
    if not path.exists():
        try:
            path.mkdir(parents=True, exist_ok=True)
            app.logger.info(f"Created folder: {path}")
        except Exception as e:
            error_message = f"创建文件夹失败: {e}"
            app.logger.error(error_message)
            return jsonify({"error": error_message}), 500
    
    try:
        os.startfile(str(path))
        return jsonify({"message": "Folder opened successfully"})
    except FileNotFoundError:
        error_message = "文件夹路径不存在，请检查路径是否正确。"
        app.logger.error(error_message)
        return jsonify({"error": error_message}), 404
    except Exception as e:
        error_message = f"打开文件夹时发生错误: {e}"
        app.logger.error(error_message)
        return jsonify({"error": error_message}), 500

@package_blue.route('/open_city_package_folder/<country_name>/<city_name>', methods=['GET','POST'])
@login_required
@staff_only
def open_city_package_folder(country_name, city_name):
    if not country_name:
        return jsonify({"error": "Country_name parameter is required"}), 400
    if not city_name:
        return jsonify({"error": "City parameter is required"}), 400
    path = construct_folder_path(country_name, city_name)
    app.logger.info(f"Attempting to open folder: {path}")
    
    # 如果文件夹不存在，则创建它
    if not path.exists():
        try:
            path.mkdir(parents=True, exist_ok=True)
            app.logger.info(f"Created folder: {path}")
        except Exception as e:
            error_message = f"创建文件夹失败: {e}"
            app.logger.error(error_message)
            return jsonify({"error": error_message}), 500
    
    try:
        os.startfile(str(path))
        return jsonify({"message": "Folder opened successfully"})
    except FileNotFoundError:
        error_message = "文件夹路径不存在，请检查路径是否正确。"
        app.logger.error(error_message)
        return jsonify({"error": error_message}), 500


@package_blue.route('/delete_product/<int:product_id>/<city_name>', methods=['POST'])
def delete_product(product_id, city_name):
    product = Product.query.get_or_404(product_id)
    try:
        db.session.delete(product)
        db.session.commit()
        flash('产品已成功删除', 'success')
    except Exception as e:
        db.session.rollback()
        flash('删除产品时出错，请重试', 'error')
        print(f"Error deleting product: {e}")
    return redirect(url_for('package_routes.our_package', city_name=city_name))


@package_blue.route('/delete_all_company_product/<city_name>/<company_name>', methods=['GET', 'POST'])
def delete_all_company_product(city_name, company_name):
    try:
        all_products = Product.query.filter_by(company_name=company_name).all()
        if not all_products:
            flash('未找到相关产品', 'info')
        else:
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
    return redirect(url_for('package_routes.our_package', city_name=city_name))


@package_blue.route('/update_company_products/<city_name>/<company_name>', methods=['GET', 'POST'])
def update_company_products(city_name, company_name):
    if not city_name or not company_name:
        flash("城市名称和公司名称不能为空！", "error")
        return redirect(url_for('package_routes.manage_cities'))
    country_name = ProductCity.get_country_name_by_city(city_name=city_name)
    path = construct_folder_path(country_name, city_name, company_name)
    products = get_all_pdf_files(path)
    if not products:
        flash("没有找到任何PDF文件。")
        return redirect(url_for('package_routes.our_package', city_name=city_name))
    for p in products:
        file_path = Path(path) / p
        create_timing = get_file_creation_time(file_path)
        valid_until = create_timing + timedelta(days=60)
        product_name = os.path.splitext(p)[0]
        if Product.product_exists(city_name, company_name, product_name):
            flash(f"产品 '{product_name}' 已存在，跳过更新。")
            continue
        try:
            Product.add_product(
                city_name=city_name,
                company_name=company_name,
                product_name=product_name,
                created_at=create_timing,
                valid_until=valid_until
            )
        except Exception as e:
            flash(f"添加产品时出错: {e}")
    flash("产品更新成功！")
    return redirect(url_for('package_routes.our_package', city_name=city_name))


@package_blue.route('/update_city_products/<city_name>', methods=['GET'])
def update_city_products(city_name):
    if not city_name:
        return jsonify({"error": "City parameter is required"}), 400
    country_name = ProductCity.get_country_name_by_city(city_name=city_name)
    base_path = Config.TOUR_RESOURCES_PATH / country_name
    def get_subfolder_names(folder_path):
        try:
            return [f.name for f in os.scandir(folder_path) if f.is_dir()]
        except FileNotFoundError:
            flash(f"文件夹 {folder_path} 不存在.")
            return []
        except Exception as e:
            flash(f"获取子文件夹时发生错误: {e}")
            return []
    folder_path = base_path / city_name
    all_company = get_subfolder_names(folder_path)
    for company in all_company:
        path = folder_path / company
        products = get_all_pdf_files(path)
        for p in products:
            file_path = path / p
            create_timing = get_file_creation_time(file_path)
            valid_until = create_timing + timedelta(days=60)
            product_name = os.path.splitext(p)[0]
            if Product.product_exists(city_name, company, product_name):
                flash(f"产品 '{product_name}' 已存在，跳过更新。")
                continue
            try:
                Product.add_product(
                    city_name=city_name,
                    company_name=company,
                    product_name=product_name,
                    created_at=create_timing,
                    valid_until=valid_until
                )
            except Exception as e:
                flash(f"添加产品时出错: {e}")
    flash("城市产品更新成功！")
    return redirect(url_for('package_routes.our_package', city_name=city_name))


@login_required
@staff_only
@package_blue.route('/show_supplier_info/<supplier_name>', methods=['GET', 'POST'])
def show_supplier_info(supplier_name=None):
    supplier_name = supplier_name or request.form.get('supplier_name')
    supplier = None
    if supplier_name:
        supplier = SupplierData.query.filter_by(name=supplier_name).first()
    return render_template('shared/supplier/supplier_detail.html', supplier=supplier, supplier_name=supplier_name)


@login_required
@staff_only
@package_blue.route('/edit_supplier_info/<supplier_name>', methods=['GET', 'POST'])
def edit_supplier_info(supplier_name):
    supplier = SupplierData.query.filter_by(name=supplier_name).first()
    if not supplier:
        flash(f"供应商 '{supplier_name}' 不存在。", 'error')
        return redirect(url_for('package_routes.show_supplier_info', supplier_name=supplier_name))
    if request.method == 'POST':
        try:
            supplier.address = request.form.get('address', supplier.address)
            supplier.contact_person = request.form.get('contact_person', supplier.contact_person)
            supplier.contact_info = request.form.get('contact_info', supplier.contact_info)
            supplier.status = request.form.get('status', supplier.status)
            supplier.country = request.form.get('country', supplier.country)
            supplier.region = request.form.get('region', supplier.region)
            supplier.rating = request.form.get('rating', supplier.rating)
            supplier.notes = request.form.get('notes', supplier.notes)
            db.session.commit()
            flash(f"供应商 '{supplier_name}' 信息已成功更新。", 'success')
            return redirect(url_for('package_routes.show_supplier_info', supplier_name=supplier.name))
        except Exception as e:
            db.session.rollback()
            flash(f"更新失败：{str(e)}", 'error')
            return redirect(url_for('package_routes.edit_supplier_info', supplier_name=supplier_name))
    return render_template('shared/supplier/supplier_edit.html', supplier=supplier)


@login_required
@staff_only
@package_blue.route('/add_supplier_info/', defaults={'supplier_name': None}, methods=['GET', 'POST'])
@package_blue.route('/add_supplier_info/<supplier_name>', methods=['GET', 'POST'])
def add_supplier_info(supplier_name):
    if request.method == 'POST':
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
        new_supplier =SupplierData()
        new_supplier.add_supplier(name=supplier_name, address=address,
                                  contact_person=contact_person, contact_info=contact_info,
                                  status=status, country=country,
                                  region=region, rating=rating, notes=notes)
        flash('新供应商添加成功！', 'success')
        return redirect(url_for('package_routes.show_supplier_info', supplier_name=supplier_name))
    return render_template('shared/supplier/supplier_add.html', supplier_name=supplier_name)


@login_required
@staff_only
@package_blue.route('/manage_cities', methods=['GET', 'POST'])
def manage_cities():
    if request.method == 'POST':
        country_name = request.form.get('country_name', '').strip()
        city_name = request.form.get('city_name', '').strip()
        display_name = request.form.get('display_name', '').strip()
        target_path = construct_folder_path(country_name, city_name)
        if not target_path.exists():
            target_path.mkdir(parents=True, exist_ok=True)
        if not country_name or not city_name or not display_name:
            flash("所有字段均为必填项，请重新填写。", "error")
            return redirect(url_for('package_routes.manage_cities'))
        try:
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
    cities = ProductCity.query.order_by(ProductCity.display_name).all()
    return render_template('shared/supplier/supplier_city_management.html', cities=cities)


@login_required
@staff_only
@package_blue.route('/edit_city/<int:city_id>', methods=['GET','POST'])
def edit_city(city_id):
    country_name = request.form.get('country_name', '').strip()
    city_name = request.form.get('city_name', '').strip()
    display_name = request.form.get('display_name', '').strip()
    city = ProductCity.query.get_or_404(city_id)
    city.country_name = country_name
    city.city_name = city_name
    city.display_name = display_name
    db.session.commit()
    base_path = Config.TOUR_RESOURCES_PATH
    target_path = base_path / country_name / city_name
    if not target_path.exists():
        target_path.mkdir(parents=True, exist_ok=True)
    return redirect(url_for('package_routes.manage_cities'))


@login_required
@staff_only
@package_blue.route('/delete_city/<int:city_id>', methods=['POST'])
def delete_city(city_id):
    city = ProductCity.query.get_or_404(city_id)
    db.session.delete(city)
    db.session.commit()
    return redirect(url_for('package_routes.manage_cities'))

def create_folder(base_dir, folder_name):
    folder_path = Path(base_dir) / folder_name
    folder_path.mkdir(parents=True, exist_ok=True)
    return folder_path


@package_blue.route('/tour_project', methods=['GET', 'POST'])
@login_required
@staff_only
def handle_tour_project():
    return redirect(url_for('tour_projects.create_tour_project'))


@package_blue.route('/')
@login_required
@staff_only
def index():
    cities = ProductCity.query.order_by(ProductCity.country_name, ProductCity.display_name).all()
    cities_by_country = {}
    for city in cities:
        if city.country_name not in cities_by_country:
            cities_by_country[city.country_name] = []
        cities_by_country[city.country_name].append(city)
    return render_template('index.html', cities_by_country=cities_by_country)

@login_required
@staff_only
@package_blue.route('/all_packages')
def all_packages():
    cities = ProductCity.query.order_by(ProductCity.display_name).all()
    cities_by_country = {}
    for city in cities:
        country = city.country_name
        if country not in cities_by_country:
            cities_by_country[country] = []
        cities_by_country[country].append(city)
    return render_template('business/tour/package/all_packages.html', cities_by_country=cities_by_country)

@login_required
@staff_only
@package_blue.route('/package_home')
def package_home():
    try:
        cities_by_country = {}
        # 添加重试机制和错误处理
        max_retries = 3
        for attempt in range(max_retries):
            try:
                cities = ProductCity.query.order_by(ProductCity.country_name).all()
                break
            except SQLAlchemyError as e:
                if attempt < max_retries - 1:
                    print(f"数据库查询失败，重试 {attempt + 1}/{max_retries}: {e}")
                    db.session.rollback()  # 回滚当前事务
                    continue
                else:
                    raise e
        
        for city in cities:
            if city.country_name not in cities_by_country:
                cities_by_country[city.country_name] = []
            cities_by_country[city.country_name].append(city)
        
        return render_template('business/tour/package/package_home.html', cities_by_country=cities_by_country)
    
    except SQLAlchemyError as e:
        print(f"数据库错误: {e}")
        flash('数据库连接失败，请稍后重试', 'error')
        return render_template('business/tour/package/package_home.html', cities_by_country={})
    except Exception as e:
        print(f"未知错误: {e}")
        flash('页面加载失败，请稍后重试', 'error')
        return render_template('business/tour/package/package_home.html', cities_by_country={})


@package_blue.route('/open_package_folder', methods=['GET', 'POST'])
def open_package_folder():
    """打开旅游产品资源文件夹"""
    try:
        from pathlib import Path
        import subprocess
        import os
        
        # 获取项目根目录
        current_dir = Path(__file__).resolve().parent.parent.parent.parent
        folder_path = current_dir / "资源" / "旅游产品"
        
        # 确保文件夹存在
        if not folder_path.exists():
            folder_path.mkdir(parents=True, exist_ok=True)
        
        # 使用 explorer 命令打开文件夹
        subprocess.run(['explorer', str(folder_path)], shell=True)
        
        return jsonify({"status": "success", "message": "文件夹已打开"})
    except Exception as e:
        print(f"打开文件夹失败: {e}")
        return jsonify({"status": "error", "message": f"打开文件夹失败: {str(e)}"})


@package_blue.route('/open_project_folder', methods=['GET', 'POST'])
def open_project_folder():
    """打开旅游项目文件夹"""
    try:
        from pathlib import Path
        import subprocess
        import os
        
        # 获取项目根目录
        current_dir = Path(__file__).resolve().parent.parent.parent.parent
        folder_path = current_dir / "资源" / "Project" / "Tour"
        
        # 确保文件夹存在
        if not folder_path.exists():
            folder_path.mkdir(parents=True, exist_ok=True)
        
        # 使用 explorer 命令打开文件夹
        subprocess.run(['explorer', str(folder_path)], shell=True)
        
        return jsonify({"status": "success", "message": "文件夹已打开"})
    except Exception as e:
        print(f"打开文件夹失败: {e}")
        return jsonify({"status": "error", "message": f"打开文件夹失败: {str(e)}"})
