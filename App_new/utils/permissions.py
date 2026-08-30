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


def is_project_owner(header, user):
    """
    检查用户是否是项目的创建者/所有者

    主要通过 staff_id 外键匹配，staff_name 作为兼容回退

    Args:
        header: ProjectHeader 对象
        user: 当前用户对象

    Returns:
        bool: 是否是项目所有者
    """
    if not header or not user:
        return False

    # 主要判断：staff_id 外键匹配
    if header.staff_id is not None:
        try:
            if int(header.staff_id) == int(user.id):
                return True
        except (ValueError, TypeError):
            pass

    # 兼容回退：staff_name 匹配（历史数据可能 staff_id 为空）
    if header.staff_name:
        staff_name_lower = header.staff_name.lower()

        # 匹配用户名
        if user.username and staff_name_lower == user.username.lower():
            return True

        # 匹配用户全名
        if hasattr(user, 'profile') and user.profile:
            user_full_name = user.profile.get_full_name()
            if user_full_name and user_full_name != "未设置姓名":
                if staff_name_lower == user_full_name.lower():
                    return True

    return False


def can_access_project(header, user):
    """
    检查用户是否有权限访问项目
    
    权限规则：
    1. 管理员可以访问所有项目
    2. 2级员工可以访问所有项目
    3. 1级员工只能访问自己创建的项目
    
    Args:
        header: ProjectHeader 对象
        user: 当前用户对象
    
    Returns:
        bool: 是否有权限访问
    """
    if not header or not user:
        return False
    
    # 获取用户角色名称
    role_name = user.role.name if user.role else None
    
    # 管理员可以访问所有项目
    if role_name in ['admin', 'super_admin']:
        return True
    
    # 获取员工等级（适用于所有登录用户）
    staff_level = 1  # 默认等级
    if hasattr(user, 'profile') and user.profile:
        staff_level = user.profile.staff_level or 1
    
    # 2级员工可以访问所有项目
    if staff_level >= 2:
        return True
    
    # 1级员工/其他用户只能访问自己的项目
    return is_project_owner(header, user)


def block_if_settled(header):
    """已结算项目禁止改动资金：返回错误消息，可结算则返回 None

    收款/退款都会改变项目余额，而余额是结算条件之一。已结算项目再动钱，
    会让结算时算出的利润分成和实际对不上（分成可能已经发出去了）。
    页面上按钮已隐藏，这里挡住直接敲 URL 的情况。
    """
    if header is not None and getattr(header, 'is_settled', False):
        return f'项目 {header.hid} 已结算，不能再新增或修改收款/退款；如需调整请先取消结算'
    return None
