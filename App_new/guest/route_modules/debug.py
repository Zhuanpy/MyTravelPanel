# -*- coding: utf-8 -*-
"""
调试相关路由
"""

from flask import Blueprint, render_template, jsonify, current_app
from urllib.parse import unquote
import html

# 创建调试蓝图
debug_bp = Blueprint('debug', __name__)

@debug_bp.route('/debug-db')
def debug_db():
    """调试：检查数据库连接"""
    try:
        from App_new.exts import db
        # 简单的数据库连接测试
        result = db.session.execute(db.text('SELECT 1 as test')).fetchone()
        return f"Database connection OK: {result[0] if result else 'No result'}"
    except Exception as e:
        return f"Database Error: {str(e)}", 500

@debug_bp.route('/test-visa-detail/<visa_type_name>')
def test_visa_detail(visa_type_name):
    """测试签证详细页面的简化版本"""
    try:
        current_app.logger.info(f"测试签证详细页面: {visa_type_name}")
        
        # 简单的模拟数据
        visa_detail_info = {
            'name': visa_type_name,
            'country': '测试国家',
            'description': f'{visa_type_name}签证办理服务',
            'processing_time': '3-5个工作日',
            'fee': 'SGD 200',
            'required_documents': ['护照', '申请表', '照片'],
            'identities': ['PR', 'EP', 'SP'],
            'additional_info': '测试信息'
        }
        
        return render_template('guest/visa/visa_detail.html', visa_type=visa_detail_info)
    except Exception as e:
        current_app.logger.error(f"测试签证详细页面失败: {str(e)}")
        import traceback
        current_app.logger.error(f"详细错误信息: {traceback.format_exc()}")
        return f"Test Error: {str(e)}", 500

@debug_bp.route('/simple-test')
def simple_test():
    """最简单的测试路由"""
    try:
        return "Hello World - Route is working!"
    except Exception as e:
        return f"Simple Test Error: {str(e)}", 500

@debug_bp.route('/test-json')
def test_json():
    """测试JSON响应"""
    try:
        return jsonify({
            'status': 'success',
            'message': 'JSON test is working',
            'timestamp': '2024-01-01 12:00:00'
        })
    except Exception as e:
        return f"JSON Test Error: {str(e)}", 500

@debug_bp.route('/test-html')
def test_html():
    """测试直接返回HTML"""
    try:
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test Page</title>
        </head>
        <body>
            <h1>Test HTML Response</h1>
            <p>This is a direct HTML response without templates.</p>
        </body>
        </html>
        """
        return html_content
    except Exception as e:
        return f"HTML Test Error: {str(e)}", 500

@debug_bp.route('/visa-detail-simple/<visa_type_name>')
def visa_detail_simple(visa_type_name):
    """简化的签证详细页面，不依赖数据库"""
    try:
        # URL解码参数
        decoded_visa_type = unquote(visa_type_name)
        decoded_visa_type = html.unescape(decoded_visa_type)
        
        # 使用模拟数据
        visa_detail_info = {
            'name': decoded_visa_type,
            'country': '日本',
            'description': f'{decoded_visa_type}签证办理服务',
            'processing_time': '3-5个工作日',
            'fee': 'SGD 200',
            'required_documents': ['护照原件', '申请表', '照片', '行程单'],
            'identities': ['PR', 'EP', 'SP', 'SHARE'],
            'additional_info': '请根据您的身份类型准备相应材料，如有疑问请联系我们。'
        }
        
        return render_template('guest/visa/visa_detail.html', visa_type=visa_detail_info)
    except Exception as e:
        current_app.logger.error(f"简化签证详细页面失败: {str(e)}")
        import traceback
        current_app.logger.error(f"详细错误信息: {traceback.format_exc()}")
        return f"Simple Visa Detail Error: {str(e)}", 500

@debug_bp.route('/template-test')
def template_test():
    """测试模板渲染"""
    try:
        test_data = {
            'name': '测试签证',
            'country': '测试国家',
            'description': '测试描述',
            'processing_time': '3-5个工作日',
            'fee': 'SGD 200',
            'required_documents': [],
            'identities': [],
            'additional_info': '测试信息'
        }
        return render_template('guest/visa/visa_detail.html', visa_type=test_data)
    except Exception as e:
        current_app.logger.error(f"模板测试失败: {str(e)}")
        import traceback
        current_app.logger.error(f"详细错误信息: {traceback.format_exc()}")
        return f"Template Test Error: {str(e)}", 500

@debug_bp.route('/debug-visa-types')
def debug_visa_types():
    """调试：查看所有签证类型"""
    try:
        # 尝试导入模型
        try:
            from App_new.business.visa.models.Visamodels import VisaTypes, VisaCountries
            current_app.logger.info("成功导入VisaTypes和VisaCountries模型")
        except ImportError as ie:
            current_app.logger.error(f"导入模型失败: {str(ie)}")
            return f"Import Error: {str(ie)}", 500
        
        # 尝试查询数据
        try:
            all_visa_types = VisaTypes.query.all()
            all_countries = VisaCountries.query.all()
            current_app.logger.info(f"查询到 {len(all_visa_types)} 个签证类型，{len(all_countries)} 个国家")
        except Exception as qe:
            current_app.logger.error(f"查询数据失败: {str(qe)}")
            return f"Query Error: {str(qe)}", 500
        
        # 构建结果
        try:
            result = {
                'countries': [{'id': c.id, 'name_cn': c.country_name_CN, 'name_en': c.country_name_EN} for c in all_countries],
                'visa_types': [{'id': vt.id, 'visa_type': vt.visa_type, 'country_id': vt.country_id} for vt in all_visa_types]
            }
            
            return jsonify(result)
        except Exception as re:
            current_app.logger.error(f"构建结果失败: {str(re)}")
            return f"Result Error: {str(re)}", 500
            
    except Exception as e:
        current_app.logger.error(f"调试路由总错误: {str(e)}")
        import traceback
        current_app.logger.error(f"详细错误信息: {traceback.format_exc()}")
        return f"General Error: {str(e)}", 500
