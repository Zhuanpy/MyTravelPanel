"""
旅游业务枚举定义
统一管理所有业务状态、类型等枚举值
"""

from enum import Enum


class ProjectStatus(str, Enum):
    """项目状态枚举"""
    DRAFT = 'draft'              # 草稿
    CONFIRMED = 'confirmed'      # 已确认
    IN_PROGRESS = 'in_progress'  # 进行中
    COMPLETED = 'completed'      # 已完成
    CANCELLED = 'cancelled'      # 已取消
    
    @property
    def display(self):
        """显示名称"""
        return {
            'draft': '草稿',
            'confirmed': '已确认',
            'in_progress': '进行中',
            'completed': '已完成',
            'cancelled': '已取消'
        }[self.value]
    
    @property
    def color(self):
        """Bootstrap颜色类"""
        return {
            'draft': 'secondary',
            'confirmed': 'primary',
            'in_progress': 'info',
            'completed': 'success',
            'cancelled': 'danger'
        }[self.value]
    
    @property
    def icon(self):
        """图标类"""
        return {
            'draft': 'fa-file-alt',
            'confirmed': 'fa-check-circle',
            'in_progress': 'fa-spinner',
            'completed': 'fa-check-double',
            'cancelled': 'fa-times-circle'
        }[self.value]


class GroupStatus(str, Enum):
    """团队状态枚举"""
    PLANNING = 'planning'        # 计划中
    READY = 'ready'             # 准备就绪
    DEPARTED = 'departed'       # 已出发
    IN_TOUR = 'in_tour'         # 行程中
    RETURNED = 'returned'       # 已返回
    CANCELLED = 'cancelled'     # 已取消
    
    @property
    def display(self):
        """显示名称"""
        return {
            'planning': '计划中',
            'ready': '准备就绪',
            'departed': '已出发',
            'in_tour': '行程中',
            'returned': '已返回',
            'cancelled': '已取消'
        }[self.value]
    
    @property
    def color(self):
        """Bootstrap颜色类"""
        return {
            'planning': 'secondary',
            'ready': 'primary',
            'departed': 'info',
            'in_tour': 'warning',
            'returned': 'success',
            'cancelled': 'danger'
        }[self.value]
    
    @property
    def icon(self):
        """图标类"""
        return {
            'planning': 'fa-clipboard-list',
            'ready': 'fa-check',
            'departed': 'fa-plane-departure',
            'in_tour': 'fa-route',
            'returned': 'fa-plane-arrival',
            'cancelled': 'fa-ban'
        }[self.value]


class ProductStatus(str, Enum):
    """产品状态枚举"""
    ACTIVE = 'active'           # 激活
    INACTIVE = 'inactive'       # 停用
    DRAFT = 'draft'             # 草稿
    ARCHIVED = 'archived'       # 归档
    
    @property
    def display(self):
        """显示名称"""
        return {
            'active': '激活',
            'inactive': '停用',
            'draft': '草稿',
            'archived': '归档'
        }[self.value]
    
    @property
    def color(self):
        """Bootstrap颜色类"""
        return {
            'active': 'success',
            'inactive': 'secondary',
            'draft': 'warning',
            'archived': 'dark'
        }[self.value]


class TemplateType(str, Enum):
    """展示模板类型枚举"""
    STANDARD = 'standard'         # 标准模板
    PROMOTION = 'promotion'       # 促销模板
    CUSTOMIZED = 'customized'     # 定制模板
    INTERNAL = 'internal'         # 内部使用
    
    @property
    def display(self):
        """显示名称"""
        return {
            'standard': '标准模板',
            'promotion': '促销模板',
            'customized': '定制模板',
            'internal': '内部使用'
        }[self.value]
    
    @property
    def color(self):
        """Bootstrap颜色类"""
        return {
            'standard': 'primary',
            'promotion': 'danger',
            'customized': 'warning',
            'internal': 'secondary'
        }[self.value]


class DocumentType(str, Enum):
    """文档类型枚举"""
    CONTRACT = 'contract'           # 合同
    INVOICE = 'invoice'             # 发票
    CONFIRMATION = 'confirmation'   # 确认函
    ITINERARY = 'itinerary'        # 行程单
    RECEIPT = 'receipt'            # 收据
    OTHER = 'other'                # 其他
    
    @property
    def display(self):
        """显示名称"""
        return {
            'contract': '合同',
            'invoice': '发票',
            'confirmation': '确认函',
            'itinerary': '行程单',
            'receipt': '收据',
            'other': '其他'
        }[self.value]
    
    @property
    def icon(self):
        """图标类"""
        return {
            'contract': 'fa-file-contract',
            'invoice': 'fa-file-invoice',
            'confirmation': 'fa-file-signature',
            'itinerary': 'fa-route',
            'receipt': 'fa-receipt',
            'other': 'fa-file'
        }[self.value]


class Season(str, Enum):
    """季节枚举（用于价格层级）"""
    PEAK = 'peak'           # 旺季
    LOW = 'low'             # 淡季
    SHOULDER = 'shoulder'   # 平季
    
    @property
    def display(self):
        """显示名称"""
        return {
            'peak': '旺季',
            'low': '淡季',
            'shoulder': '平季'
        }[self.value]


class AuditAction(str, Enum):
    """审计日志操作类型"""
    CREATE = 'create'       # 创建
    UPDATE = 'update'       # 更新
    DELETE = 'delete'       # 删除
    VIEW = 'view'           # 查看
    EXPORT = 'export'       # 导出
    IMPORT = 'import'       # 导入
    
    @property
    def display(self):
        """显示名称"""
        return {
            'create': '创建',
            'update': '更新',
            'delete': '删除',
            'view': '查看',
            'export': '导出',
            'import': '导入'
        }[self.value]
    
    @property
    def color(self):
        """Bootstrap颜色类"""
        return {
            'create': 'success',
            'update': 'primary',
            'delete': 'danger',
            'view': 'info',
            'export': 'warning',
            'import': 'warning'
        }[self.value]

