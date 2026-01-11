# -*- coding: utf-8 -*-
"""
共享模型包 - 统一导入所有模型

注意：Supplier 表已合并到 CustomerCompany 表
Supplier 别名保留用于向后兼容
"""

# 基础模型
from .account import Account
from .business_types import BusinessType

# Supplier 兼容层 - 实际指向 CustomerCompany
from .Suppliers import (
    Supplier,  # CustomerCompany 的别名
    get_suppliers,
    get_supplier_by_id
)

from .Utilsmodels import Todo, TodoChecklist, TodoChecklistItem

# 注意：project, ref, eo 模型在 business.projects 模块中
# 注意：flight 模型在 business.flight 模块中
# 这里只导入真正属于 shared 模块的模型

__all__ = [
    # 基础模型
    'Account',
    'BusinessType',
    # 供应商兼容层（实际是 CustomerCompany）
    'Supplier',
    'get_suppliers',
    'get_supplier_by_id',
    # 待办事项
    'Todo',
    'TodoChecklist',
    'TodoChecklistItem',
]
