# -*- coding: utf-8 -*-
"""
访问统计调试路由
"""

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from App_new.utils.decorators import staff_only
from App_new.utils.csrf import csrf

debug_stats = Blueprint('debug_stats', __name__)

@debug_stats.route('/debug_visit_stats')
@login_required
@staff_only
def debug_visit_stats():
    """访问统计调试页面"""
    return render_template('business/visa/访问统计/debug_visit_stats.html')

@debug_stats.route('/test_visit_stats', methods=['POST'])
@login_required
@staff_only
@csrf.exempt
def test_visit_stats():
    """测试访问统计功能"""
    try:
        from App_new.shared.services.visit_stats_service import VisitStatsService
        
        # 测试记录访问
        result = VisitStatsService.record_visa_visit(
            visa_type_id=999,  # 测试ID
            visa_type_name="测试签证",
            country_name="测试国家"
        )
        
        return jsonify({
            'success': True,
            'message': '测试访问记录成功',
            'result': result
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'message': f'测试失败: {str(e)}',
            'traceback': traceback.format_exc()
        })
