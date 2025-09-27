# -*- coding: utf-8 -*-
"""
API相关路由
"""

from flask import Blueprint, jsonify, current_app
from urllib.parse import unquote
import html

# 创建API蓝图
api_bp = Blueprint('api', __name__)

@api_bp.route('/api/visa-countries')
def api_visa_countries():
    """API: 获取签证国家列表"""
    try:
        from App_new.business.visa.models.Visamodels import VisaCountries, VisaTypes
        
        # 获取所有有签证类型的国家
        countries_with_visas = VisaCountries.query.join(VisaTypes).distinct().order_by(VisaCountries.country_name_CN).all()
        
        country_data = []
        for country in countries_with_visas:
            visa_count = VisaTypes.query.filter_by(country_id=country.id).count()
            country_data.append({
                'id': country.id,
                'name': country.country_name_CN,
                'name_en': country.country_name_EN,
                'code': country.country_code,
                'visa_count': visa_count
            })
        
        return jsonify({
            'success': True,
            'data': country_data
        })
    except Exception as e:
        current_app.logger.error(f"获取签证国家列表失败: {e}")
        return jsonify({
            'success': False,
            'message': '获取数据失败'
        }), 500

@api_bp.route('/api/visa-types/<int:country_id>')
def api_visa_types_by_country(country_id):
    """API: 获取指定国家的签证类型"""
    try:
        from App_new.business.visa.models.Visamodels import VisaTypes, VisaCountries
        
        # 获取国家信息
        country = VisaCountries.query.get(country_id)
        if not country:
            return jsonify({
                'success': False,
                'message': '国家不存在'
            }), 404
        
        # 获取该国家的签证类型
        visa_types = VisaTypes.query.filter_by(country_id=country_id).order_by(VisaTypes.visa_type).all()
        
        visa_type_data = []
        for visa_type in visa_types:
            visa_type_data.append({
                'id': visa_type.id,
                'name': visa_type.visa_type,
                'description': getattr(visa_type, 'description', ''),
                'fee': str(visa_type.fee) if hasattr(visa_type, 'fee') and visa_type.fee else None,
                'processing_time': getattr(visa_type, 'processing_time', ''),
                'validity': getattr(visa_type, 'validity', ''),
                'country_name': country.country_name_CN,
                'country_name_en': country.country_name_EN
            })
        
        return jsonify({
            'success': True,
            'data': visa_type_data,
            'country': {
                'id': country.id,
                'name': country.country_name_CN,
                'name_en': country.country_name_EN,
                'code': country.country_code
            }
        })
    except Exception as e:
        current_app.logger.error(f"获取签证类型失败: {e}")
        return jsonify({
            'success': False,
            'message': '获取数据失败'
        }), 500

@api_bp.route('/api/get_identity_options/<visa_type>')
def get_identity_options(visa_type):
    """获取签证类型的身份选项"""
    try:
        from App_new.business.visa.models.Visamodels import VisaTypes, VisaSingaporeIdentity, VisaDocuments
        
        # URL解码签证类型
        decoded_visa_type = unquote(visa_type)
        decoded_visa_type = html.unescape(decoded_visa_type)
        
        # 验证签证类型是否存在
        visa_type_record = VisaTypes.query.filter_by(visa_type=decoded_visa_type).first()
        if not visa_type_record:
            return jsonify({
                'success': False,
                'message': f'签证类型 {decoded_visa_type} 不存在',
                'identity_options': []
            }), 404
        
        # 从visa_type_identities表获取该签证类型关联的身份选项
        visa_type_identities = visa_type_record.identities
        identity_options = [identity.identity_zh for identity in visa_type_identities]
        
        # 确保SHARE在第一位（如果存在）
        if 'SHARE' in identity_options:
            identity_options.remove('SHARE')
            identity_options.insert(0, 'SHARE')
        
        return jsonify({
            'success': True,
            'identity_options': identity_options
        })
    except Exception as e:
        current_app.logger.error(f"获取身份选项失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e),
            'identity_options': []
        }), 500

@api_bp.route('/api/get_visa_documents/<visa_type>/<identity>')
def get_visa_documents(visa_type, identity):
    """获取指定签证类型和身份的文档资料"""
    try:
        from App_new.business.visa.models.Visamodels import VisaTypes, VisaSingaporeIdentity, VisaDocuments
        
        # URL解码参数
        decoded_visa_type = unquote(visa_type)
        decoded_visa_type = html.unescape(decoded_visa_type)
        decoded_identity = unquote(identity)
        decoded_identity = html.unescape(decoded_identity)
        
        # 获取签证类型
        visa_type_record = VisaTypes.query.filter_by(visa_type=decoded_visa_type).first()
        if not visa_type_record:
            return jsonify({
                'success': False,
                'message': '签证类型不存在'
            }), 404
        
        # 获取申请人准备的文档信息
        if decoded_identity == 'SHARE':
            identity_record = VisaSingaporeIdentity.query.filter_by(identity_zh='SHARE').first()
            if identity_record:
                documents_info = VisaDocuments.get_applicant_documents(visa_type_record.id, identity_record.id)
            else:
                documents_info = {'document_info': '暂无文件资料', 'additional_info': '暂无补充信息'}
        else:
            identity_record = VisaSingaporeIdentity.query.filter_by(identity_zh=decoded_identity).first()
            if identity_record:
                documents_info = VisaDocuments.get_applicant_documents(visa_type_record.id, identity_record.id)
            else:
                documents_info = {'document_info': '暂无文件资料', 'additional_info': '暂无补充信息'}
        
        return jsonify({
            'success': True,
            'document_info': documents_info.get('document_info', '暂无文件资料'),
            'additional_info': documents_info.get('additional_info', '暂无补充信息'),
            'applicant_additional_info': documents_info.get('applicant_additional_info', '暂无申请人补充信息')
        })
    except Exception as e:
        current_app.logger.error(f"获取签证文档失败: {e}")
        import traceback
        current_app.logger.error(f"详细错误信息: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'获取数据失败: {str(e)}'
        }), 500

@api_bp.route('/api/tour-packages')
def api_tour_packages():
    """API: 获取旅游配套列表"""
    try:
        # TODO: 从数据库获取真实数据
        packages = [
            {
                'id': 1,
                'name': '新马泰经典7日游',
                'price': 1280,
                'duration': 7,
                'destination': '新加坡-马来西亚-泰国'
            },
            {
                'id': 2,
                'name': '巴厘岛浪漫5日游',
                'price': 980,
                'duration': 5,
                'destination': '印尼巴厘岛'
            }
        ]
        
        return jsonify({
            'success': True,
            'data': packages
        })
    except Exception as e:
        current_app.logger.error(f"获取旅游配套列表失败: {e}")
        return jsonify({
            'success': False,
            'message': '获取数据失败'
        }), 500
