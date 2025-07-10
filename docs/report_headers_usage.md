# 报表表头配置使用指南

## 概述

本系统提供了统一的报表表头配置管理，支持多种报表类型，便于在不同模块中复用。

## 配置位置

表头配置位于 `App/config.py` 中的 `Config.REPORT_HEADERS` 字典。

## 支持的表头类型

### 1. 标准订单报表 (order_report)
16个字段，适用于完整的订单数据：
```python
[
    'order_id',           # 1. 订单ID
    'customer_type',      # 2. 客户类型
    'order_date',         # 3. 订单日期
    'passenger_name',     # 4. 乘客姓名
    'travel_date',        # 5. 旅行日期
    'product_name',       # 6. 产品名称
    'booking_type',       # 7. 预订类型
    'selling_price',      # 8. 销售价格
    'cost_price',         # 9. 成本价格
    'profit',             # 10. 利润
    'profit_margin',      # 11. 利润率
    'balance',            # 12. 余额
    'created_by',         # 13. 创建人
    'approved_by',        # 14. 审批人
    'pax_info',           # 15. 乘客信息
    'invoice_status'      # 16. 发票状态
]
```

### 2. 简化订单报表 (simple_order_report)
9个常用字段：
```python
[
    'order_id',
    'customer_type', 
    'order_date',
    'passenger_name',
    'product_name',
    'selling_price',
    'cost_price',
    'profit',
    'created_by'
]
```

### 3. 财务报表 (financial_report)
6个财务相关字段：
```python
[
    'date',
    'description',
    'amount',
    'type',
    'category',
    'reference'
]
```

### 4. 发票数据 (invoice_data)
11个发票相关字段，用于Invoice.py中的发票数据处理：
```python
[
    'hid',                # 0. HID编号
    'customer_name',      # 2. 客户姓名
    'order_date',         # 3. 订单日期
    'product_name',       # 4. 产品名称
    'travel_date',        # 5. 旅行日期
    'selling_price',      # 6. 销售价格
    'cost_price',         # 8. 成本价格
    'profit',             # 11. 利润
    'balance',            # 12. 余额
    'created_by',         # 13. 创建人
    'approved_by'         # 14. 审批人
]
```

### 5. HID数据 (hid_data)
10个HID相关字段，用于Invoice.py中的HID数据处理：
```python
[
    'hid',                # 0. HID编号
    'customer_name',      # 2. 客户姓名
    'order_date',         # 3. 订单日期
    'travel_date',        # 4. 旅行日期
    'product_name',       # 5. 产品名称
    'booking_type',       # 7. 预订类型
    'selling_price',      # 8. 销售价格
    'cost_price',         # 9. 成本价格
    'profit',             # 10. 利润
    'created_by'          # 11. 创建人
]
```

## 使用方法

### 1. 直接使用Config类

```python
from App.config import Config

# 获取表头列表
headers = Config.get_header_list('order_report')

# 获取表头字符串（用逗号分隔）
header_string = Config.get_header_string('order_report')
```

### 2. 使用工具函数（推荐）

```python
from App.utils.report_utils import (
    get_report_headers,
    get_report_headers_string,
    read_excel_file,
    read_csv_file,
    save_report_with_headers,
    compare_profit_columns,
    add_comparison_column
)

# 获取表头
headers = get_report_headers('order_report')
header_string = get_report_headers_string('order_report')

# 读取Excel文件并应用表头
df = read_excel_file('report.xlsx', 'order_report', has_header=False)

# 读取CSV文件并应用表头
df = read_csv_file('report.csv', 'order_report', has_header=False)

# 保存文件并确保正确表头
save_report_with_headers(df, 'output.xlsx', 'order_report')

# 对比两个报表的利润列
result = compare_profit_columns(df_a, df_b, 'profit')

# 为报表添加对比列
df_a_with_col, df_b_with_col = add_comparison_column(df_a, df_b, 'profit')
```

### 3. 在现有代码中的使用示例

#### 在statement.py中的使用：
```python
from App.config import Config

# 获取默认表头
custom_headers = Config.get_header_string('order_report')
```

#### 在其他模块中的使用：
```python
from App.utils.report_utils import read_excel_file

# 读取报表文件
df = read_excel_file('my_report.xls', 'order_report', has_header=False)
```

#### 在Invoice.py中的使用：
```python
from App.config import Config
from App.utils.report_utils import get_report_headers

class CountHid:
    def __init__(self, booking_path:str, name="Zz"):
        self._path = os.path.join(booking_path, name)
        
        # 获取表头配置
        self.invoice_headers = get_report_headers('invoice_data')
        self.hid_headers = get_report_headers('hid_data')
    
    def read_all_inv(self, complete_month=0):
        # 读取Excel文件并应用表头
        df = pd.read_excel(name, sheet_name='Sheet1', header=None)
        
        # 处理数据后应用表头
        if len(df.columns) == len(self.invoice_headers):
            df.columns = self.invoice_headers
        
        # 现在可以使用字段名称而不是列索引
        profits = df['profit'].sum()
        return df
```

## 添加新的表头类型

1. 在 `App/config.py` 的 `REPORT_HEADERS` 字典中添加新类型：

```python
REPORT_HEADERS = {
    # ... 现有类型 ...
    
    # 新增表头类型
    'new_report_type': [
        'field1',
        'field2',
        'field3',
        # ... 更多字段
    ]
}
```

2. 使用新表头：

```python
headers = Config.get_header_list('new_report_type')
```

## 最佳实践

1. **统一使用工具函数**：优先使用 `App.utils.report_utils` 中的函数
2. **明确指定表头类型**：避免使用默认值，明确指定表头类型
3. **错误处理**：使用try-catch处理可能的异常
4. **文档化**：在代码中添加注释说明使用的表头类型

## 注意事项

1. 表头字段数量必须与数据列数匹配
2. 修改表头配置后需要重启应用
3. 不同表头类型的字段数量可以不同
4. 表头字段名应该使用英文，避免特殊字符

## 故障排除

### 常见错误：

1. **字段数不匹配**：
   ```
   ValueError: 数据列数(15)与期望表头数(16)不匹配
   ```
   解决：检查数据文件的实际列数，或调整表头配置

2. **未知表头类型**：
   ```
   ValueError: 未知的表头类型: invalid_type
   ```
   解决：检查表头类型名称是否正确

3. **文件读取失败**：
   ```
   Exception: 读取Excel文件失败: ...
   ```
   解决：检查文件格式、路径和权限

4. **利润值转换错误**：
   ```
   ValueError: could not convert string to float: 'MAIN'
   ```
   解决：系统已自动处理，会跳过无法转换为数字的利润值，并在界面上显示处理信息

## 更新日志

### 2025-01-XX - 表头配置优化完成

#### 已完成的工作：

1. **配置集中化**：
   - 将表头配置从代码中提取到 `App/config.py`
   - 支持多种表头类型：`order_report`、`simple_order_report`、`financial_report`、`invoice_data`、`hid_data`
   - 提供便捷的获取方法：`get_header_list()` 和 `get_header_string()`

2. **工具函数创建**：
   - 创建了 `App/utils/report_utils.py` 工具模块
   - 提供完整的报表处理功能：读取、保存、对比、添加对比列
   - 支持Excel和CSV文件格式

3. **代码优化**：
   - 更新了 `App/routes/Utils/statement.py` 使用新的配置系统
   - 更新了 `App/code/Invoice.py` 使用表头配置，替换列索引为字段名称
   - 移除了硬编码的表头字符串
   - 简化了前端代码，自动使用配置中的表头

4. **测试和文档**：
   - 创建了测试脚本 `scripts/test_report_headers.py` 和 `scripts/test_invoice_headers.py`
   - 编写了详细的使用文档
   - 清理了调试和测试代码

5. **功能完善**：
   - 修复了CSRF保护导致的400错误
   - 优化了报表对比功能
   - 修复了利润值转换错误，支持处理包含非数字值的数据
   - 提供了完整的错误处理和数据验证

#### 优势：

- **维护性**：表头配置集中管理，修改只需改一个地方
- **复用性**：其他模块可以直接使用相同的表头配置
- **扩展性**：轻松添加新的表头类型
- **一致性**：确保所有模块使用相同的表头格式
- **文档化**：提供了完整的使用指南和示例

#### 使用建议：

1. 新功能开发时优先使用 `App.utils.report_utils` 中的工具函数
2. 需要新的表头类型时，在 `Config.REPORT_HEADERS` 中添加
3. 定期运行测试脚本确保配置正常工作
4. 参考文档中的最佳实践进行开发 