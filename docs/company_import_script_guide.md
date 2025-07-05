# 公司信息自动导入脚本使用指南

## 功能概述

本脚本可以从文件夹名称中自动提取公司信息，并通过网络搜索获取更详细的公司资料，然后批量导入到数据库中。

## 脚本文件

### 基础版本
- `scripts/import_companies_from_folders.py` - 基础版本，支持从文件夹名称导入

### 增强版本
- `scripts/enhanced_company_importer.py` - 增强版本，集成网络搜索功能

## 功能特点

### 基础版本功能
- 从文件夹名称解析公司信息
- 自动生成公司代码
- 根据公司名称猜测行业和规模
- 检查重复公司
- 批量导入数据库

### 增强版本功能
- 包含基础版本所有功能
- 集成Google搜索获取公司信息
- 集成ACRA搜索获取注册信息
- 搜索缓存功能
- 生成Excel导入报告
- 更详细的行业和规模判断

## 使用方法

### 1. 基础版本使用

```bash
# 预览模式（不实际导入）
python scripts/import_companies_from_folders.py --dry-run

# 实际导入
python scripts/import_companies_from_folders.py

# 指定自定义路径
python scripts/import_companies_from_folders.py --path "E:\自定义路径\公司文件夹"
```

### 2. 增强版本使用

```bash
# 预览模式
python scripts/enhanced_company_importer.py --dry-run

# 实际导入
python scripts/enhanced_company_importer.py

# 不生成Excel报告
python scripts/enhanced_company_importer.py --no-report

# 指定自定义路径
python scripts/enhanced_company_importer.py --path "E:\自定义路径\公司文件夹"
```

## 参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `--dry-run` | 预览模式，不实际导入数据库 | `--dry-run` |
| `--path` | 指定公司文件夹路径 | `--path "E:\公司文件夹"` |
| `--no-report` | 不生成Excel报告（仅增强版） | `--no-report` |

## 脚本功能详解

### 1. 文件夹名称解析

脚本会自动处理以下常见的公司后缀：
- `PTE. LTD`
- `PTE LTD`
- `CO PTE LTD`
- `LIMITED`
- `LTD`

**示例：**
- `FU XIANG CONSTRUCTION PTE LTD` → `FU XIANG CONSTRUCTION`
- `CHINA HARBOUR (SINGAPORE) ENGINEERING COMPANY PTE. LTD` → `CHINA HARBOUR (SINGAPORE) ENGINEERING COMPANY`

### 2. 公司代码生成

自动生成格式：`首字母缩写 + 月日时间戳`

**示例：**
- `FU XIANG CONSTRUCTION` → `FXC0703`
- `CHINA HARBOUR ENGINEERING` → `CHE0703`

### 3. 行业判断

根据公司名称关键词自动判断行业：

| 关键词 | 行业 |
|--------|------|
| construction, engineering, builder, maintenance | 制造业 |
| development, group, property, real estate | 房地产 |
| trading, import, export, logistics, transport | 零售 |
| technology, tech, software, digital | 科技 |
| finance, financial, banking, investment | 金融 |
| consulting, consultant, advisory | 咨询 |
| education, school, training | 教育 |
| healthcare, medical, hospital, clinic | 医疗健康 |

### 4. 规模判断

根据公司名称特征判断规模：

| 特征 | 规模 |
|------|------|
| international, group, development, global | 大型公司 |
| construction, engineering, trading | 中型公司 |
| pte, ltd, private | 小型公司 |

### 5. 网络搜索功能（增强版）

#### Google搜索
- 搜索公司官网和联系信息
- 获取电话号码、邮箱、地址等

#### ACRA搜索
- 获取公司注册信息
- 获取注册地址和业务活动

#### 搜索缓存
- 自动缓存搜索结果
- 避免重复搜索相同公司

### 6. Excel报告生成（增强版）

生成的报告包含以下字段：
- 公司名称
- 公司代码
- 行业
- 规模
- 联系电话
- 邮箱
- 地址
- 网站
- ACRA编号
- 导入状态
- 备注

## 输出示例

### 预览模式输出
```
=== 公司信息自动导入脚本 ===
扫描路径: E:\Project\MyTravelPanel\资源\账单\Company
模式: 预览模式

找到 13 个公司文件夹:
  - BAONENG ENGINEERING PTE. LTD
  - CHINA HARBOUR (SINGAPORE) ENGINEERING COMPANY PTE. LTD
  - CHYE THIAM MAINTENANCE PTE LTD
  ...

[1/13] 处理: BAONENG ENGINEERING PTE. LTD
  📋 公司代码: BEP0703
  📋 行业: 制造业
  📋 规模: 中型公司
  ✅ 预览完成

=== 导入结果 ===
总计: 13 个公司
成功: 13 个
失败: 0 个
跳过: 0 个

📋 预览完成，可以运行实际导入
```

### 实际导入输出
```
[1/13] 处理: BAONENG ENGINEERING PTE. LTD
  📋 公司代码: BEP0703
  📋 行业: 制造业
  📋 规模: 中型公司
  💾 导入数据库...
  ✅ 导入成功

=== 导入结果 ===
总计: 13 个公司
成功: 13 个
失败: 0 个
跳过: 0 个

📊 导入报告已生成: company_import_report_20250703_192030.xlsx

✅ 成功导入 13 个公司到数据库
```

## 注意事项

### 1. 依赖要求
```bash
pip install requests pandas openpyxl
```

### 2. 数据库连接
- 确保数据库连接正常
- 确保有写入权限

### 3. 网络连接（增强版）
- 需要网络连接进行搜索
- 搜索可能有延迟，请耐心等待

### 4. 文件权限
- 确保脚本有读取文件夹的权限
- 确保有写入Excel报告的权限

### 5. 重复检查
- 脚本会自动检查公司是否已存在
- 已存在的公司会被跳过

## 故障排除

### 常见问题

1. **ImportError: No module named 'requests'**
   ```bash
   pip install requests
   ```

2. **ImportError: No module named 'pandas'**
   ```bash
   pip install pandas openpyxl
   ```

3. **路径不存在错误**
   - 检查文件夹路径是否正确
   - 使用 `--path` 参数指定正确路径

4. **数据库连接失败**
   - 检查数据库配置
   - 确保数据库服务正在运行

5. **网络搜索失败**
   - 检查网络连接
   - 脚本会自动使用默认值

### 日志查看

如果遇到问题，可以查看详细错误信息：
```bash
python scripts/enhanced_company_importer.py 2>&1 | tee import.log
```

## 扩展功能

### 1. 自定义行业映射
可以修改脚本中的 `industry_keywords` 字典来添加更多行业映射。

### 2. 集成其他API
可以在 `search_google` 和 `search_acra` 方法中集成真实的API调用。

### 3. 自定义报告格式
可以修改 `generate_excel_report` 方法来自定义报告格式。

## 更新日志

- v1.0.0: 基础版本，支持从文件夹名称导入
- v2.0.0: 增强版本，集成网络搜索和报告生成
- v2.1.0: 添加搜索缓存功能
- v2.2.0: 改进行业和规模判断逻辑 