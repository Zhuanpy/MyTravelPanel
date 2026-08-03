import math
from datetime import datetime
from datetime import date
from App_new.exts import db  # 确保你已正确导入 db 对象
from sqlalchemy import Date
from flask_sqlalchemy import SQLAlchemy


class BudgetHeader(db.Model):
    __tablename__ = 'package_budget_header'

    id = db.Column(db.Integer, primary_key=True)
    package_name = db.Column(db.String(255), nullable=False)
    adult_count = db.Column(db.Integer, nullable=False)
    child_count = db.Column(db.Integer, nullable=False)
    currency = db.Column(db.String(10), default='SGD')  # 录入货币：明细价格所用货币
    # 最终统一货币 + 固定汇率（录入货币≠最终货币时按汇率换算）
    target_currency = db.Column(db.String(10), nullable=True)  # 最终统一货币；空=同录入货币
    exchange_rate = db.Column(db.Float, nullable=True)  # 固定汇率：1 SGD = exchange_rate CNY
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(50))
    remarks = db.Column(db.Text)
    status = db.Column(db.String(20), default='draft')
    is_template = db.Column(db.Boolean, default=False)
    
    # 关联项目ID
    project_id = db.Column(db.Integer, db.ForeignKey('tour_project.id'), nullable=True, index=True)
    project = db.relationship("TourProject", backref=db.backref("budgets", lazy="dynamic"))

    # 关联团组ID：用于多团组时按团组精确同步人数（为空表示未指定具体团组）
    group_id = db.Column(db.Integer, db.ForeignKey('tour_group.id'), nullable=True, index=True)

    items = db.relationship("BudgetItem", backref="header", cascade="all, delete-orphan")

    @property
    def active_items(self):
        """参与费用计算的明细（被临时禁用的不算）"""
        return [item for item in self.items if item.is_active]

    @property
    def disabled_item_count(self):
        """被临时禁用的明细条数"""
        return sum(1 for item in self.items if not item.is_active)

    @property
    def total_price(self):
        return sum(item.subtotal for item in self.items)

    @property
    def adult_unit_price(self):
        """成人人均价：各计入成人的预算项目成人单价之和"""
        return sum((item.adult_unit_price or 0) for item in self.items if item.count_adult_apply)

    @property
    def child_unit_price(self):
        """儿童人均价：各计入儿童的预算项目儿童单价之和"""
        return sum((item.child_unit_price or 0) for item in self.items if item.count_child_apply)

    # ===== 最终统一货币换算 =====
    @property
    def final_currency(self):
        """最终统一货币：未设置时同录入货币"""
        return self.target_currency or self.currency or 'SGD'

    @staticmethod
    def _round_up_int(amount):
        """换算取整规则：向上取整到 5 的倍数（末位凑成 0 或 5）。
        例：166→170，127→130，134.1→135，160→160。
        减 1e-6 消除浮点误差（如 165.0000001 不误进为 170）。
        """
        if amount is None:
            return amount
        return float(math.ceil((amount - 1e-6) / 5) * 5)

    @staticmethod
    def _fmt_money(v):
        """金额显示：整数不带小数，非整数保留两位。"""
        if v is None:
            return '0'
        return f'{v:.0f}' if abs(v - round(v)) < 1e-9 else f'{v:.2f}'

    def to_final(self, amount):
        """把录入货币金额换算为最终统一货币（换算结果向上取整）。

        汇率约定：exchange_rate = 1 SGD 兑多少 CNY。
        - 录入CNY→最终SGD：金额 / 汇率，再向上取整
        - 录入SGD→最终CNY：金额 * 汇率，再向上取整
        - 货币相同或未设汇率：原样返回（不取整）
        """
        if amount is None:
            return amount
        base = self.currency or 'SGD'
        tgt = self.final_currency
        if base == tgt:
            return amount
        rate = self.exchange_rate
        if not rate or rate <= 0:
            return amount  # 未设置有效汇率则不换算（避免误算）
        if base == 'CNY' and tgt == 'SGD':
            return self._round_up_int(amount / rate)
        if base == 'SGD' and tgt == 'CNY':
            return self._round_up_int(amount * rate)
        return amount

    @property
    def needs_conversion(self):
        """是否发生了货币换算（录入币≠最终币且有有效汇率）"""
        return (self.currency or 'SGD') != self.final_currency and bool(self.exchange_rate and self.exchange_rate > 0)

    @property
    def adult_unit_price_final(self):
        """成人人均价（最终统一货币）"""
        return self.to_final(self.adult_unit_price)

    @property
    def child_unit_price_final(self):
        """儿童人均价（最终统一货币）"""
        return self.to_final(self.child_unit_price)

    @property
    def total_price_final(self):
        """团总价（最终统一货币）"""
        return self.to_final(self.total_price)

    # 显示用字符串：换算后为整数则不带小数，未换算的原值保留两位
    @property
    def adult_unit_price_final_str(self):
        return self._fmt_money(self.adult_unit_price_final)

    @property
    def child_unit_price_final_str(self):
        return self._fmt_money(self.child_unit_price_final)

    @property
    def total_price_final_str(self):
        return self._fmt_money(self.total_price_final)

    def __repr__(self):
        return f'<BudgetHeader {self.package_name}>'


class BudgetItem(db.Model):
    __tablename__ = 'package_budget_items'

    id = db.Column(db.Integer, primary_key=True)
    header_id = db.Column(db.Integer, db.ForeignKey('package_budget_header.id'))
    category = db.Column(db.String(50))
    item_name = db.Column(db.String(255))
    item_details = db.Column(db.Text)  # 项目详细信息，如酒店入住日期、房型等
    
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
    # 临时不计入费用：价格原样保留，只是暂时不参与任何合计，随时可以开回来
    is_enabled = db.Column(db.Boolean, default=True, nullable=False, comment='是否计入费用计算')
    remarks = db.Column(db.Text)

    @property
    def is_active(self):
        """是否计入计算。老数据 is_enabled 为 NULL（迁移脚本没跑）时按启用处理，避免整单价格归零。"""
        return self.is_enabled is not False

    # ===== 对外的计算值：禁用的项目一律返回 0，让所有合计自动把它排除 =====
    @property
    def subtotal(self):
        return self.subtotal_raw if self.is_active else 0

    @property
    def adult_unit_price(self):
        return self.adult_unit_price_raw if self.is_active else 0

    @property
    def child_unit_price(self):
        return self.child_unit_price_raw if self.is_active else 0

    # ===== 原始计算值：不受禁用影响，页面上用来显示"停用前是多少钱" =====
    @property
    def subtotal_raw(self):
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
    def adult_unit_price_raw(self):
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
    def child_unit_price_raw(self):
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