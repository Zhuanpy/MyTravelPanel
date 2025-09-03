from flask import Blueprint, render_template, request, jsonify, send_file, flash, redirect, url_for
from App_new.exts import db
from ..models.Packagemodels import TourProduct, CompanyInfo
import io
import pdfkit
from datetime import datetime
import os
import base64

# 创建蓝图
product_details = Blueprint('product_details', __name__)

def clean_text(text):
    if not text:
        return ""
    # 移除多余的空格，但保留换行
    lines = text.split('\n')
    cleaned_lines = [line.strip() for line in lines]
    # 移除空行
    cleaned_lines = [line for line in cleaned_lines if line]
    return '\n'.join(cleaned_lines)

# 配置 wkhtmltopdf 路径
if os.name == 'nt':  # Windows 系统
    WKHTMLTOPDF_PATH = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
else:  # Linux/Unix 系统
    WKHTMLTOPDF_PATH = '/usr/local/bin/wkhtmltopdf'

# 创建 PDFKit 配置
config = pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH)

# 获取当前文件所在目录的上级目录（即应用根目录）
BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

def get_image_base64(image_path):
    """将图片转换为base64编码"""
    try:
        print(f"Trying to open image at path: {image_path}")  # 调试信息
        if not os.path.exists(image_path):
            print(f"File does not exist: {image_path}")  # 调试信息
            return None
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
            return f"data:image/png;base64,{encoded_string}"
    except Exception as e:
        print(f"Error reading image: {str(e)}")  # 调试信息
        return None

# 显示所有产品
@product_details.route('/tour_product_details')
def tour_product_details():
    products = TourProduct.query.order_by(TourProduct.created_at.desc()).all()
    company = CompanyInfo.query.first()
    return render_template('business/tour/package/旅游产品详细.html', products=products, company=company, is_pdf_export=False)

# 添加新产品
@product_details.route('/tour_product/add', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        try:
            new_product = TourProduct(
                title=clean_text(request.form['title']),
                itinerary=clean_text(request.form['itinerary']),
                included=clean_text(request.form['included']),
                not_included=clean_text(request.form['not_included']),
                price=float(request.form['price']),
                duration=clean_text(request.form['duration'])
            )
            db.session.add(new_product)
            db.session.commit()
            
            # 检查是否是AJAX请求
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True, 'message': '产品添加成功'})
            else:
                flash('产品添加成功！', 'success')
                return redirect(url_for('product_details.tour_product_details'))
        except Exception as e:
            db.session.rollback()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': str(e)})
            else:
                flash(f'添加失败：{str(e)}', 'error')
                return redirect(url_for('product_details.add_product'))
    
    return render_template('business/tour/package/add_product.html')

# 编辑产品
@product_details.route('/tour_product/edit/<int:id>', methods=['GET', 'POST'])
def edit_product(id):
    product = TourProduct.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            product.title = clean_text(request.form['title'])
            product.itinerary = clean_text(request.form['itinerary'])
            product.included = clean_text(request.form['included'])
            product.not_included = clean_text(request.form['not_included'])
            product.price = float(request.form['price'])
            product.duration = clean_text(request.form['duration'])
            
            db.session.commit()
            
            # 检查是否是AJAX请求
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True, 'message': '产品更新成功'})
            else:
                flash('产品更新成功！', 'success')
                return redirect(url_for('product_details.tour_product_details'))
        except Exception as e:
            db.session.rollback()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': str(e)})
            else:
                flash(f'更新失败：{str(e)}', 'error')
    
    return render_template('business/tour/package/edit_product.html', product=product)

# 删除产品
@product_details.route('/tour_product/delete/<int:id>', methods=['POST'])
def delete_product(id):
    try:
        product = TourProduct.query.get_or_404(id)
        db.session.delete(product)
        db.session.commit()
        flash('产品删除成功！', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'删除失败：{str(e)}', 'error')
    
    return redirect(url_for('product_details.tour_product_details'))

# 导出 PDF
@product_details.route('/generate_pdf/<int:id>')
def generate_pdf(id):
    try:
        # 获取指定ID的产品
        product = TourProduct.query.get_or_404(id)
        company = CompanyInfo.query.first()
        
        # 处理logo路径
        if company and company.logo_path:
            print(f"Original logo path: {company.logo_path}")  # 调试信息
            print(f"Base directory: {BASE_DIR}")  # 调试信息
            
            # 移除路径中的 'static/' 前缀（如果存在）
            logo_path = company.logo_path.replace('static/', '')
            
            # 构建完整的文件系统路径
            full_path = os.path.join(BASE_DIR, 'static', logo_path)
            full_path = os.path.normpath(full_path)  # 标准化路径
            full_path = full_path.replace('\\', '/')  # 统一使用正斜杠
            
            print(f"Full path to logo: {full_path}")  # 调试信息
            
            # 转换图片为base64
            company.logo_base64 = get_image_base64(full_path)
            if company.logo_base64 is None:
                print("Failed to convert image to base64")  # 调试信息
            
        rendered = render_template('business/tour/package/旅游产品详细.html', 
                                products=[product],  # 将单个产品放入列表中
                                company=company,
                                is_pdf_export=True)
        
        # 配置 PDF 选项
        options = {
            'page-size': 'A4',
            'margin-top': '0.8in',
            'margin-right': '0.3in',
            'margin-bottom': '0.3in',
            'margin-left': '0.3in',
            'encoding': 'UTF-8',
            'no-outline': None,
            'enable-local-file-access': None,
            'disable-smart-shrinking': None,
            'print-media-type': None,
            'dpi': 300,
            'zoom': '1.0',
            'quiet': None
        }
        
        # 使用配置生成 PDF
        pdf = pdfkit.from_string(rendered, False, options=options, configuration=config)
        
        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'tour_product_{product.title}_{timestamp}.pdf'
        
        return send_file(
            io.BytesIO(pdf),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        print(f"PDF generation error: {str(e)}")  # 调试信息
        flash(f'PDF生成失败：{str(e)}', 'error')
        return redirect(url_for('product_details.tour_product_details'))