from datetime import datetime
from datetime import date
from App.exts import db  # 确保你已正确导入 db 对象
from sqlalchemy import Date
from flask_sqlalchemy import SQLAlchemy


class BudgetHeader(db.Model):
    __tablename__ = 'package_budget_header'

    id = db.Column(db.Integer, primary_key=True)
    package_name = db.Column(db.String(255), nullable=False)
    adult_count = db.Column(db.Integer, nullable=False)
    child_count = db.Column(db.Integer, nullable=False)
    currency = db.Column(db.String(10), default='SGD')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(50))
    remarks = db.Column(db.Text)
    status = db.Column(db.String(20), default='draft')
    is_template = db.Column(db.Boolean, default=False)

    items = db.relationship("BudgetItem", backref="header", cascade="all, delete-orphan")

    @property
    def total_price(self):
        return sum(item.subtotal for item in self.items)

    def __repr__(self):
        return f'<BudgetHeader {self.package_name}>'


class BudgetItem(db.Model):
    __tablename__ = 'package_budget_items'

    id = db.Column(db.Integer, primary_key=True)
    header_id = db.Column(db.Integer, db.ForeignKey('package_budget_header.id'))
    category = db.Column(db.String(50))
    item_type = db.Column(db.String(50))  # 如住宿/交通/门票等
    item_name = db.Column(db.String(255))
    
    # 计价方式：'item_based' 或 'person_based'
    pricing_method = db.Column(db.String(20), default='person_based')
    
    # 模板1：物品计价方式
    item_unit_price = db.Column(db.Numeric(10, 2), nullable=True)  # 物品单价
    item_quantity = db.Column(db.Integer, default=1)  # 物品件数
    
    # 模板2：人均计价方式
    adult_price = db.Column(db.Numeric(10, 2))  # 成人单价
    child_price = db.Column(db.Numeric(10, 2))  # 儿童单价
    
    # 人数设置
    count_adult_apply = db.Column(db.Boolean, default=True)
    count_child_apply = db.Column(db.Boolean, default=True)
    adult_count_override = db.Column(db.Integer, nullable=True)
    child_count_override = db.Column(db.Integer, nullable=True)
    
    # 总价覆盖
    total_override = db.Column(db.Numeric(10, 2), nullable=True)
    sort_order = db.Column(db.Integer, default=0)
    tax_rate = db.Column(db.Float, default=0)
    tax_amount = db.Column(db.Numeric(10, 2), nullable=True)
    is_optional = db.Column(db.Boolean, default=False)
    remarks = db.Column(db.Text)

    @property
    def subtotal(self):
        if self.total_override is not None:
            return float(self.total_override)
        
        if self.pricing_method == 'item_based':
            # 模板1：物品计价方式
            if self.item_unit_price and self.item_quantity:
                total_item_cost = float(self.item_unit_price) * self.item_quantity
                return total_item_cost
            else:
                return 0
        else:
            # 模板2：人均计价方式
            adult_count = self.adult_count_override if self.adult_count_override is not None else (self.header.adult_count if self.header else 0)
            child_count = self.child_count_override if self.child_count_override is not None else (self.header.child_count if self.header else 0)
            subtotal = 0
            if self.count_adult_apply:
                subtotal += float(self.adult_price or 0) * adult_count
            if self.count_child_apply:
                subtotal += float(self.child_price or 0) * child_count
            return subtotal

    @property
    def adult_unit_price(self):
        """计算成人人均单价"""
        if self.total_override is not None:
            adult_count = self.adult_count_override if self.adult_count_override is not None else (self.header.adult_count if self.header else 0)
            return float(self.total_override) / adult_count if adult_count > 0 else 0
        
        if self.pricing_method == 'item_based':
            # 模板1：按物品总价分摊给成人
            if self.item_unit_price and self.item_quantity:
                total_item_cost = float(self.item_unit_price) * self.item_quantity
                adult_count = self.adult_count_override if self.adult_count_override is not None else (self.header.adult_count if self.header else 0)
                child_count = self.child_count_override if self.child_count_override is not None else (self.header.child_count if self.header else 0)
                
                total_persons = 0
                if self.count_adult_apply:
                    total_persons += adult_count
                if self.count_child_apply:
                    total_persons += child_count
                
                if total_persons > 0 and self.count_adult_apply:
                    return total_item_cost / total_persons
                else:
                    return 0
            else:
                return 0
        else:
            # 模板2：直接返回成人单价
            return float(self.adult_price or 0)

    @property
    def child_unit_price(self):
        """计算儿童人均单价"""
        if self.total_override is not None:
            child_count = self.child_count_override if self.child_count_override is not None else (self.header.child_count if self.header else 0)
            return float(self.total_override) / child_count if child_count > 0 else 0
        
        if self.pricing_method == 'item_based':
            # 模板1：按物品总价分摊给儿童
            if self.item_unit_price and self.item_quantity:
                total_item_cost = float(self.item_unit_price) * self.item_quantity
                adult_count = self.adult_count_override if self.adult_count_override is not None else (self.header.adult_count if self.header else 0)
                child_count = self.child_count_override if self.child_count_override is not None else (self.header.child_count if self.header else 0)
                
                total_persons = 0
                if self.count_adult_apply:
                    total_persons += adult_count
                if self.count_child_apply:
                    total_persons += child_count
                
                if total_persons > 0 and self.count_child_apply:
                    return total_item_cost / total_persons
                else:
                    return 0
            else:
                return 0
        else:
            # 模板2：直接返回儿童单价
            return float(self.child_price or 0)

    @property
    def total_item_cost(self):
        """计算物品总价（仅模板1）"""
        if self.pricing_method == 'item_based' and self.item_unit_price and self.item_quantity:
            return float(self.item_unit_price) * self.item_quantity
        return 0

    def __repr__(self):
        return f'<BudgetItem {self.item_name}>'