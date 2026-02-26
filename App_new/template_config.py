# -*- coding: utf-8 -*-
"""
Flask模板配置
"""

import os

class TemplateConfig:
    """模板配置类"""
    
    # 应用级别模板目录
    TEMPLATE_FOLDER = os.path.join(os.path.dirname(__file__), 'templates')
    
    # 静态文件目录
    STATIC_FOLDER = os.path.join(os.path.dirname(__file__), 'static')
    
    # 模板配置
    TEMPLATES_AUTO_RELOAD = True
    
    # 静态文件浏览器缓存（秒）：图片/CSS/JS 缓存1天
    SEND_FILE_MAX_AGE_DEFAULT = 86400

# 导出配置
template_config = TemplateConfig()
