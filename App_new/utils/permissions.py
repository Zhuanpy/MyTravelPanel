"""
权限定义和权限检查工具
"""

# 权限常量定义
PERMISSIONS = {
    # 管理员权限
    'manage_all_data': '管理全站数据',
    'manage_users': '用户管理',
    'manage_roles': '权限管理',
    'manage_orders': '订单管理',
    'publish_content': '内容发布',
    'view_analytics': '查看统计',
    'system_config': '系统配置',
    
    # 员工权限
    'manage_own_projects': '管理所属项目',
    'create_quotes': '新增报价',
    'edit_quotes': '修改报价',
    'upload_files': '上传文件',
    'update_progress': '更新项目进度',
    'view_own_orders': '查看相关订单',
    
    # 会员权限
    'place_orders': '下单',
    'view_quotes': '查看报价',
    'view_invoices': '查看发票',
    'edit_profile': '编辑个人资料',
    
    # 访客权限
    'view_public_info': '浏览公开信息',
    'view_visa_services': '查看签证服务',
    'view_tour_packages': '查看旅游配套'
}

# 角色权限分配
ROLE_PERMISSIONS = {
    'admin': [
        'manage_all_data',      # 管理全站数据
        'manage_users',         # 用户管理
        'manage_roles',         # 权限管理
        'manage_orders',        # 订单管理
        'publish_content',      # 内容发布
        'view_analytics',       # 查看统计
        'system_config'         # 系统配置
    ],
    'staff': [
        'manage_own_projects',  # 管理所属项目
        'create_quotes',        # 新增报价
        'edit_quotes',          # 修改报价
        'upload_files',         # 上传文件
        'update_progress',      # 更新项目进度
        'view_own_orders'       # 查看相关订单
    ],
    'member': [
        'view_own_orders',      # 查看自己的订单
        'place_orders',         # 下单
        'view_quotes',          # 查看报价
        'view_invoices',        # 查看发票
        'edit_profile'          # 编辑个人资料
    ],
    'guest': [
        'view_public_info',     # 浏览公开信息
        'view_visa_services',   # 查看签证服务
        'view_tour_packages'    # 查看旅游配套
    ]
}

def has_permission(user, permission):
    """
    检查用户是否有指定权限
    
    Args:
        user: 用户对象
        permission: 权限名称
    
    Returns:
        bool: 是否有权限
    """
    if not user or not user.is_authenticated:
        return False
    
    # 管理员拥有所有权限
    if user.role and user.role.name == 'admin':
        return True
    
    # 检查用户角色是否有指定权限
    if user.role and user.role.permissions:
        return permission in user.role.permissions
    
    return False

def has_role(user, role_name):
    """
    检查用户是否有指定角色
    
    Args:
        user: 用户对象
        role_name: 角色名称
    
    Returns:
        bool: 是否有角色
    """
    if not user or not user.is_authenticated:
        return False
    
    if user.role:
        return user.role.name == role_name
    
    return False

def get_user_permissions(user):
    """
    获取用户的所有权限
    
    Args:
        user: 用户对象
    
    Returns:
        list: 权限列表
    """
    if not user or not user.is_authenticated:
        return []
    
    if user.role and user.role.permissions:
        return user.role.permissions
    
    return []

def get_permission_description(permission):
    """
    获取权限描述
    
    Args:
        permission: 权限名称
    
    Returns:
        str: 权限描述
    """
    return PERMISSIONS.get(permission, '未知权限')

def get_role_permissions(role_name):
    """
    获取角色的所有权限
    
    Args:
        role_name: 角色名称
    
    Returns:
        list: 权限列表
    """
    return ROLE_PERMISSIONS.get(role_name, [])

def get_all_permissions():
    """
    获取所有权限列表
    
    Returns:
        dict: 权限字典
    """
    return PERMISSIONS

def get_all_roles():
    """
    获取所有角色列表
    
    Returns:
        dict: 角色权限字典
    """
    return ROLE_PERMISSIONS 