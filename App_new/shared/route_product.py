import os
import base64
from flask import current_app

@product_blue.route('/generate_pdf')
def generate_pdf():
    # 获取产品列表
    products = Product.query.all()
    
    # 读取公司抬头图片并转换为base64
    header_image_path = os.path.join(current_app.static_folder, 'images', 'company_header.png')
    header_image_base64 = None
    if os.path.exists(header_image_path):
        with open(header_image_path, 'rb') as img_file:
            header_image_base64 = base64.b64encode(img_file.read()).decode('utf-8')
    
    # 创建一个包含公司信息的对象
    company = {
        'header_image_base64': header_image_base64
    }
    
    # 渲染HTML模板
    html = render_template('package/旅游产品详细.html', 
                         products=products,
                         is_pdf_export=True,
                         company=company)
    
    # 配置PDF选项
    options = {
        'page-size': 'A4',
        'margin-top': '0mm',
        'margin-right': '0mm',
        'margin-bottom': '0mm',
        'margin-left': '0mm',
        'encoding': 'UTF-8',
        'no-outline': None,
        'enable-local-file-access': None
    }
    
    # 生成PDF
    pdf = pdfkit.from_string(html, False, options=options)
    
    # 返回PDF文件
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=products.pdf'
    return response 