from flask import Blueprint, jsonify, request, render_template, send_file
from flask_login import login_required, current_user
from App_new.exts import db
from App_new.exts import csrf
from App_new.utils.decorators import staff_only
import logging
from sqlalchemy import case
from datetime import datetime
import pandas as pd
from io import BytesIO
from App_new.shared.models.account import (
    Account, 
    ACCESS_LEVEL_CHOICES,
    ACCESS_LEVEL_PRIVATE,
    ACCESS_LEVEL_LEVEL_1,
    ACCESS_LEVEL_LEVEL_2,
    ACCESS_LEVEL_PUBLIC
)
from App_new.shared.models.Suppliers import Supplier

# 创建蓝图
account_routes = Blueprint('account_routes', __name__)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def filter_accounts_by_access(query, user):
    """根据用户权限过滤账号查询"""
    from sqlalchemy import or_
    
    # 管理员可以看到所有账号
    if user.role and user.role.name in ['admin', 'super_admin']:
        return query
    
    # 获取用户的员工等级
    staff_level = 1  # 默认等级
    if user.profile:
        staff_level = user.profile.staff_level or 1
    
    # 构建权限过滤条件
    access_conditions = [
        Account.access_level == ACCESS_LEVEL_PUBLIC,  # 公开权限
        Account.access_level.is_(None),  # 空值视为公开
    ]
    
    # 私有权限：仅创建者可见
    access_conditions.append(
        db.and_(
            Account.access_level == ACCESS_LEVEL_PRIVATE,
            or_(
                Account.created_by == user.id,
                Account.owner == user.username
            )
        )
    )
    
    # 根据员工等级添加可见权限
    if staff_level >= 1:
        access_conditions.append(Account.access_level == ACCESS_LEVEL_LEVEL_1)
    if staff_level >= 2:
        access_conditions.append(Account.access_level == ACCESS_LEVEL_LEVEL_2)
    
    return query.filter(or_(*access_conditions))

def check_account_permissions(account, user):
    """
    检查用户对账号的编辑和删除权限
    返回: (can_edit, can_delete)
    """
    # 管理员可以编辑和删除所有账号
    is_admin = user.role and user.role.name in ['admin', 'super_admin']
    if is_admin:
        return True, True
    
    # 获取用户的员工等级
    staff_level = 1  # 默认等级
    if user.profile:
        staff_level = user.profile.staff_level or 1
    
    # 检查是否是账号的创建者或所有者
    is_owner = (account.created_by == user.id) or (account.owner == user.username)
    
    # 权限检查：
    # 1. 2级员工（最高权限）可以编辑和删除所有账号
    # 2. 1级员工只能编辑和删除自己创建的账号
    can_edit = False
    can_delete = False
    
    if staff_level == 2:
        # 2级员工可以编辑和删除所有账号
        can_edit = True
        can_delete = True
    elif is_owner:
        # 1级员工只能编辑和删除自己的账号
        can_edit = True
        can_delete = True
    
    return can_edit, can_delete

@account_routes.route('/accounts')
@login_required
@staff_only
def account_page():
    """账号管理页面路由"""
    return render_template('utils/account_manage.html')

@account_routes.route('/accounts/<int:account_id>')
@login_required
@staff_only
def account_detail(account_id):
    """账号详细页面路由"""
    try:
        account = Account.query.get(account_id)
        if not account:
            return render_template('errors/404.html'), 404
        
        # 使用新的权限检查方法
        if not account.can_access(current_user):
            from flask import flash, redirect, url_for
            flash('您没有权限访问此账户', 'error')
            return redirect(url_for('account_routes.account_page'))
        
        return render_template('utils/account_detail.html', account=account)
    except Exception as e:
        logger.error(f"Error fetching account detail: {str(e)}")
        return render_template('errors/404.html'), 404

@account_routes.route('/api/accounts/increment_click/<int:account_id>', methods=['POST'])
@csrf.exempt
@login_required
@staff_only
def increment_click(account_id):
    try:
        logger.info(f"Received click increment request for account_id: {account_id}")
        account = Account.query.get(account_id)
        if not account:
            return jsonify({'success': False, 'message': '账号不存在'}), 404
        
        # 使用新的权限检查方法
        if not account.can_access(current_user):
            return jsonify({
                'success': False,
                'message': '您没有权限访问此账户'
            }), 403
        
        # 增加点击次数
        if account.click_count is None:
            account.click_count = 0
        account.click_count += 1
        
        db.session.commit()
        logger.info(f"Successfully updated click count for account_id: {account_id}")
        return jsonify({
            'success': True,
            'message': '点击次数已更新',
            'click_count': account.click_count
        })

    except Exception as e:
        logger.error(f"Error updating click count: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@account_routes.route('/api/access_levels', methods=['GET'])
@login_required
@staff_only
def get_access_levels():
    """获取访问权限级别选项"""
    try:
        access_levels = [
            {'value': value, 'label': label}
            for value, label in ACCESS_LEVEL_CHOICES
        ]
        return jsonify({
            'success': True,
            'access_levels': access_levels
        })
    except Exception as e:
        logger.error(f"Error fetching access levels: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取访问权限级别失败: {str(e)}'
        }), 500

@account_routes.route('/api/categories', methods=['GET'])
def get_categories():
    try:
        # 从数据库中获取所有不重复的类别
        categories = db.session.query(Account.category)\
            .filter(Account.category.isnot(None))\
            .distinct()\
            .all()
        
        # 提取类别名称并排序
        category_list = sorted([cat[0] for cat in categories if cat[0]])
        
        # 如果没有类别，返回空列表
        if not category_list:
            category_list = []
        
        return jsonify({
            'success': True,
            'categories': category_list
        })
    except Exception as e:
        print('获取类别失败:', str(e))
        return jsonify({
            'success': False,
            'message': '获取类别失败: ' + str(e)
        }), 500

@account_routes.route('/api/accounts/popular', methods=['GET'])
@login_required
@staff_only
def get_popular_accounts():
    try:
        logger.info("Fetching popular accounts")
        
        # 构建基础查询
        base_query = Account.query
        
        # 使用新的权限过滤函数
        base_query = filter_accounts_by_access(base_query, current_user)
        
        # 修复 case 语句的语法
        popular_accounts = base_query.order_by(
            case(
                (Account.click_count == None, 0),
                else_=Account.click_count
            ).desc()
        ).limit(25).all()
        
        accounts_data = []
        for account in popular_accounts:
            # 检查编辑和删除权限
            can_edit, can_delete = check_account_permissions(account, current_user)
            
            accounts_data.append({
            'id': account.id,
            'platform': account.platform,
            'website_url': account.website_url,
                'click_count': account.click_count or 0,
                'can_edit': can_edit,
                'can_delete': can_delete
            })
        
        logger.info(f"Successfully fetched {len(accounts_data)} popular accounts")
        return jsonify({
            'success': True,
            'accounts': accounts_data
        })
    except Exception as e:
        logger.error(f"Error fetching popular accounts: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取热门账号失败: {str(e)}'
        }), 500

@account_routes.route('/api/accounts', methods=['GET'])
@login_required
@staff_only
def get_accounts():
    try:
        logger.info("Fetching all accounts")
        
        # 构建查询
        query = Account.query
        
        # 使用新的权限过滤函数
        query = filter_accounts_by_access(query, current_user)
        
        accounts = query.all()
        accounts_data = []
        for account in accounts:
            # 检查编辑和删除权限
            can_edit, can_delete = check_account_permissions(account, current_user)
            
            accounts_data.append({
            'id': account.id,
            'platform': account.platform,
            'website_url': account.website_url,
            'category': account.category,
            'owner': account.owner,
            'username': account.username,
            'password': account.password,
            'country': account.country,
            'region': account.region,
            'description': account.description,
            'notes': account.notes,
            'click_count': account.click_count or 0,
            'created_at': account.created_at.isoformat() if account.created_at else None,
            'updated_at': account.updated_at.isoformat() if account.updated_at else None,
            'supplier_id': account.supplier_id,
            'supplier_name': account.supplier.name if account.supplier else None,
            'access_level': account.access_level or ACCESS_LEVEL_PRIVATE,
                'access_level_display': dict(ACCESS_LEVEL_CHOICES).get(account.access_level, '仅自己可见'),
                'can_edit': can_edit,
                'can_delete': can_delete
            })
        
        logger.info(f"Successfully fetched {len(accounts_data)} accounts")
        return jsonify({
            'success': True,
            'accounts': accounts_data
        })
    except Exception as e:
        logger.error(f"Error fetching accounts: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取账号列表失败: {str(e)}'
        }), 500

@account_routes.route('/api/accounts/<int:account_id>', methods=['GET'])
@login_required
@staff_only
def get_account(account_id):
    """获取单个账号信息"""
    try:
        account = Account.query.get_or_404(account_id)
        
        # 使用新的权限检查方法
        if not account.can_access(current_user):
            return jsonify({
                'success': False,
                'message': '您没有权限访问此账户'
            }), 403
        
        # 检查编辑和删除权限
        can_edit, can_delete = check_account_permissions(account, current_user)
            
        return jsonify({
            'success': True,
            'account': {
                'id': account.id,
                'platform': account.platform,
                'website_url': account.website_url,
                'category': account.category,
                'owner': account.owner,
                'username': account.username,
                'password': account.password,
                'country': account.country,
                'region': account.region,
                'description': account.description,
                'notes': account.notes,
                'click_count': account.click_count or 0,
                'created_at': account.created_at.isoformat() if account.created_at else None,
                'updated_at': account.updated_at.isoformat() if account.updated_at else None,
                'supplier_id': account.supplier_id,
                'supplier_name': account.supplier.name if account.supplier else None,
                'access_level': account.access_level or ACCESS_LEVEL_PRIVATE,
                'access_level_display': dict(ACCESS_LEVEL_CHOICES).get(account.access_level, '仅自己可见'),
                'can_edit': can_edit,
                'can_delete': can_delete
            }
        })
    except Exception as e:
        logger.error(f"Error fetching account {account_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取账号信息失败: {str(e)}'
        }), 500

@csrf.exempt
@account_routes.route('/api/accounts', methods=['POST'])
@login_required
@staff_only
def create_account():
    """创建新账号"""
    try:
        logger.info("Creating new account")
        data = request.get_json()
        
        # 验证必填字段
        required_fields = ['platform', 'category', 'username', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'缺少必填字段: {field}'
                }), 400

        # 验证供应商ID（如果提供）
        supplier_id = data.get('supplier_id')
        # 处理空字符串和 null
        if supplier_id == '' or supplier_id == 'null':
            supplier_id = None
        
        if supplier_id is not None:
            try:
                supplier_id = int(supplier_id)
                supplier = Supplier.query.get(supplier_id)
                if not supplier:
                    return jsonify({
                        'success': False,
                        'message': f'供应商ID {supplier_id} 不存在'
                    }), 400
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'message': '供应商ID格式错误'
                }), 400
        
        # 处理访问权限
        access_level = data.get('access_level', ACCESS_LEVEL_PRIVATE)
        if access_level not in [ACCESS_LEVEL_PRIVATE, ACCESS_LEVEL_LEVEL_1, ACCESS_LEVEL_LEVEL_2, ACCESS_LEVEL_PUBLIC]:
            access_level = ACCESS_LEVEL_PRIVATE
        
        # 创建新账号
        new_account = Account(
            platform=data['platform'],
            website_url=data.get('website_url'),
            category=data['category'],
            owner=data.get('owner'),
            username=data['username'],
            password=data['password'],
            country=data.get('country'),
            region=data.get('region'),
            description=data.get('description'),
            notes=data.get('notes'),
            supplier_id=supplier_id,
            access_level=access_level,
            created_by=current_user.id  # 记录创建者
        )

        db.session.add(new_account)
        db.session.commit()
        
        logger.info(f"Successfully created new account: {new_account.platform}")
        return jsonify({
            'success': True,
            'message': '账号创建成功',
            'account': {
                'id': new_account.id,
                'platform': new_account.platform,
                'category': new_account.category,
                'username': new_account.username,
                'access_level': new_account.access_level
            }
        })
    except Exception as e:
        logger.error(f"Error creating account: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'创建账号失败: {str(e)}'
        }), 500

@csrf.exempt
@account_routes.route('/api/accounts/<int:account_id>', methods=['PUT'])
@login_required
@staff_only
def update_account(account_id):
    """更新账号信息"""
    try:
        logger.info(f"Updating account {account_id}")
        account = Account.query.get(account_id)
        if not account:
            logger.warning(f"Account {account_id} not found")
            return jsonify({
                'success': False,
                'message': '账号不存在'
            }), 404

        # 检查用户是否有权限访问此账号（查看权限）
        if not account.can_access(current_user):
            return jsonify({
                'success': False,
                'message': '您没有权限访问此账户'
            }), 403

        # 检查编辑权限：最高权限员工（2级）可以编辑所有账号，或者只能编辑自己的账号
        # 管理员可以编辑所有账号
        is_admin = current_user.role and current_user.role.name in ['admin', 'super_admin']
        
        # 获取用户的员工等级
        staff_level = 1  # 默认等级
        if current_user.profile:
            staff_level = current_user.profile.staff_level or 1
        
        # 检查是否是账号的创建者或所有者
        is_owner = (account.created_by == current_user.id) or (account.owner == current_user.username)
        
        # 编辑权限检查：
        # 1. 管理员可以编辑所有账号
        # 2. 2级员工（最高权限）可以编辑所有账号
        # 3. 1级员工只能编辑自己创建的账号
        can_edit = False
        if is_admin:
            can_edit = True
        elif staff_level == 2:
            # 2级员工可以编辑所有账号
            can_edit = True
        elif is_owner:
            # 1级员工只能编辑自己的账号
            can_edit = True
        
        if not can_edit:
            return jsonify({
                'success': False,
                'message': '您没有权限编辑此账户。只有最高权限员工（2级）可以编辑所有账户，或者您只能编辑自己创建的账户。'
            }), 403

        data = request.get_json()
        logger.info(f"Update data received: {data}")

        # 验证并更新供应商ID
        if 'supplier_id' in data:
            supplier_id = data.get('supplier_id')
            # 处理空字符串和 null
            if supplier_id == '' or supplier_id == 'null':
                supplier_id = None
            
            if supplier_id is not None:
                # 验证供应商是否存在
                try:
                    supplier_id = int(supplier_id)
                    supplier = Supplier.query.get(supplier_id)
                    if not supplier:
                        return jsonify({
                            'success': False,
                            'message': f'供应商ID {supplier_id} 不存在'
                        }), 400
                except (ValueError, TypeError):
                    return jsonify({
                        'success': False,
                        'message': '供应商ID格式错误'
                    }), 400
            
            account.supplier_id = supplier_id
            logger.info(f"Updated supplier_id to: {supplier_id}")

        # 更新账号信息
        account.platform = data.get('platform', account.platform)
        account.website_url = data.get('website_url', account.website_url)
        account.category = data.get('category', account.category)
        account.owner = data.get('owner', account.owner)
        account.username = data.get('username', account.username)
        account.country = data.get('country', account.country)
        account.region = data.get('region', account.region)
        account.description = data.get('description', account.description)
        account.notes = data.get('notes', account.notes)
        
        # 更新访问权限
        if 'access_level' in data:
            access_level = data.get('access_level')
            if access_level in [ACCESS_LEVEL_PRIVATE, ACCESS_LEVEL_LEVEL_1, ACCESS_LEVEL_LEVEL_2, ACCESS_LEVEL_PUBLIC]:
                account.access_level = access_level
                logger.info(f"Updated access_level to: {access_level}")

        # 如果提供了新密码，则更新密码
        if 'password' in data and data['password']:
            account.password = data['password']

        # 更新时间戳
        account.updated_at = datetime.utcnow()

        # 保存更改
        db.session.commit()
        logger.info(f"Successfully updated account {account_id}")

        return jsonify({
            'success': True,
            'message': '账号更新成功'
        })
    except Exception as e:
        logger.error(f"Error updating account {account_id}: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'更新账号失败: {str(e)}'
        }), 500

@csrf.exempt
@account_routes.route('/api/accounts/<int:account_id>', methods=['DELETE'])
@login_required
@staff_only
def delete_account(account_id):
    try:
        logger.info(f"Deleting account with id: {account_id}")
        account = Account.query.get_or_404(account_id)
        
        # 检查用户是否有权限访问此账号（查看权限）
        if not account.can_access(current_user):
            return jsonify({
                'success': False,
                'message': '您没有权限访问此账户'
            }), 403
        
        # 检查删除权限：最高权限员工（2级）可以删除所有账号，或者只能删除自己的账号
        # 管理员可以删除所有账号
        is_admin = current_user.role and current_user.role.name in ['admin', 'super_admin']
        
        # 获取用户的员工等级
        staff_level = 1  # 默认等级
        if current_user.profile:
            staff_level = current_user.profile.staff_level or 1
        
        # 检查是否是账号的创建者或所有者
        is_owner = (account.created_by == current_user.id) or (account.owner == current_user.username)
        
        # 删除权限检查：
        # 1. 管理员可以删除所有账号
        # 2. 2级员工（最高权限）可以删除所有账号
        # 3. 1级员工只能删除自己创建的账号
        can_delete = False
        if is_admin:
            can_delete = True
        elif staff_level == 2:
            # 2级员工可以删除所有账号
            can_delete = True
        elif is_owner:
            # 1级员工只能删除自己的账号
            can_delete = True
        
        if not can_delete:
            return jsonify({
                'success': False,
                'message': '您没有权限删除此账户。只有最高权限员工（2级）可以删除所有账户，或者您只能删除自己创建的账户。'
            }), 403
        
        # 记录要删除的账号信息
        logger.info(f"Found account: {account.platform} - {account.username}")
        
        db.session.delete(account)
        db.session.commit()
        
        logger.info(f"Successfully deleted account: {account_id}")
        return jsonify({
            'success': True,
            'message': '账号删除成功'
        })
    except Exception as e:
        logger.error(f"Error deleting account: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'删除账号失败: {str(e)}'
        }), 500

@csrf.exempt
@account_routes.route('/api/accounts/import', methods=['POST'])
def import_accounts():
    """批量导入账号"""
    try:
        logger.info("Starting account import")
        
        # 检查用户是否已登录
        if not current_user.is_authenticated:
            logger.warning("User not authenticated")
            return jsonify({
                'success': False,
                'message': '用户未登录'
            }), 401
        
        if 'file' not in request.files:
            logger.warning("No file in request")
            return jsonify({
                'success': False,
                'message': '未找到上传的文件'
            }), 400

        file = request.files['file']
        if file.filename == '':
            logger.warning("Empty filename")
            return jsonify({
                'success': False,
                'message': '未选择文件'
            }), 400

        if not file.filename.endswith(('.xlsx', '.xls')):
            logger.warning(f"Invalid file type: {file.filename}")
            return jsonify({
                'success': False,
                'message': '只支持 Excel 文件 (.xlsx, .xls)'
            }), 400

        # 读取 Excel 文件
        try:
            df = pd.read_excel(file, engine='openpyxl')
            logger.info(f"Successfully read Excel file with {len(df)} rows")
            logger.info(f"Columns found: {list(df.columns)}")
        except Exception as e:
            logger.error(f"Excel file parsing failed: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Excel 文件解析失败: {str(e)}'
            }), 400

        # 验证必填字段
        required_fields = ['platform', 'category', 'username', 'password']
        missing_fields = [field for field in required_fields if field not in df.columns]
        if missing_fields:
            logger.warning(f"Missing required fields: {missing_fields}")
            return jsonify({
                'success': False,
                'message': f'Excel 文件缺少必填字段: {", ".join(missing_fields)}'
            }), 400

        # 数据预处理和验证 - 处理nan值
        df = df.fillna('')  # 将NaN值替换为空字符串
        logger.info("Data preprocessing completed")
        
        # 验证数据不为空
        validation_errors = []
        for field in required_fields:
            empty_rows = df[df[field].astype(str).str.strip() == ''].index.tolist()
            if empty_rows:
                error_msg = f'必填字段 "{field}" 在第 {[i+2 for i in empty_rows]} 行为空'
                validation_errors.append(error_msg)
                logger.warning(f"Empty values found in field '{field}' at rows: {empty_rows}")
        
        # 如果有验证错误，返回所有错误信息
        if validation_errors:
            return jsonify({
                'success': False,
                'message': '数据验证失败，请检查以下问题：',
                'validation_errors': validation_errors
            }), 400

        # 导入账号
        imported_count = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                # 数据清理 - 确保没有nan值
                platform = str(row['platform']).strip()
                category = str(row['category']).strip()
                username = str(row['username']).strip()
                password = str(row['password']).strip()
                
                logger.info(f"Processing row {index + 2}: platform={platform}, username={username}")
                
                # 验证数据长度
                if len(platform) > 100:
                    error_msg = f'第 {index + 2} 行: 平台名称过长（最大100字符）'
                    errors.append(error_msg)
                    logger.warning(error_msg)
                    continue
                if len(username) > 100:
                    error_msg = f'第 {index + 2} 行: 用户名过长（最大100字符）'
                    errors.append(error_msg)
                    logger.warning(error_msg)
                    continue
                if len(password) > 100:  # Account模型中的password字段限制是100
                    error_msg = f'第 {index + 2} 行: 密码过长（最大100字符）'
                    errors.append(error_msg)
                    logger.warning(error_msg)
                    continue
                
                # 安全地处理可选字段，确保没有nan值
                def safe_str(value):
                    """安全地转换值为字符串，处理nan值"""
                    if pd.isna(value) or value == '' or value is None:
                        return None
                    return str(value).strip()
                
                # 创建新账号 - 注意这里不需要user_id，因为Account模型没有这个字段
                new_account = Account(
                    platform=platform,
                    website_url=safe_str(row.get('website_url')),
                    category=category,
                    owner=safe_str(row.get('owner')),
                    username=username,
                    password=password,
                    country=safe_str(row.get('country')),
                    region=safe_str(row.get('region')),
                    description=safe_str(row.get('description')),
                    notes=safe_str(row.get('notes'))
                )
                db.session.add(new_account)
                imported_count += 1
                logger.info(f"Successfully added account: {username} for platform: {platform}")
                
            except Exception as e:
                error_msg = f'第 {index + 2} 行导入失败: {str(e)}'
                errors.append(error_msg)
                logger.error(error_msg)

        # 提交所有更改
        if imported_count > 0:
            try:
                db.session.commit()
                logger.info(f"Successfully imported {imported_count} accounts")
            except Exception as e:
                logger.error(f"Database commit failed: {str(e)}")
                db.session.rollback()
                return jsonify({
                    'success': False,
                    'message': f'数据库提交失败: {str(e)}'
                }), 500
        else:
            logger.warning("No accounts were imported")
            return jsonify({
                'success': False,
                'message': '没有成功导入任何账号，请检查数据格式'
            }), 400

        return jsonify({
            'success': True,
            'message': f'导入完成，成功导入 {imported_count} 个账号',
            'imported_count': imported_count,
            'errors': errors
        })
    except Exception as e:
        logger.error(f"Error importing accounts: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'导入账号失败: {str(e)}'
        }), 500

@account_routes.route('/api/accounts/download_template')
def download_template():
    """下载账号导入模板"""
    try:
        # 创建一个示例数据 - 确保字段与Account模型匹配
        data = {
            'platform': ['示例平台'],
            'website_url': ['https://example.com'],
            'category': ['示例类别'],
            'owner': ['示例所有者'],
            'username': ['示例用户名'],
            'password': ['示例密码'],
            'country': ['示例国家'],
            'region': ['示例地区'],
            'description': ['示例描述'],
            'notes': ['示例备注']
        }
        
        # 创建DataFrame
        df = pd.DataFrame(data)
        
        # 创建Excel文件 - 使用openpyxl引擎
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='账号导入模板')
            
            # 获取worksheet对象
            worksheet = writer.sheets['账号导入模板']
            
            # 设置列宽
            column_widths = [15, 25, 15, 15, 15, 15, 15, 15, 20, 20]
            for idx, width in enumerate(column_widths):
                col_letter = chr(65 + idx)  # A, B, C, D...
                worksheet.column_dimensions[col_letter].width = width
            
            # 添加说明 - 使用openpyxl的方式
            worksheet['A12'] = '必填字段：平台、分类、用户名、密码'
            worksheet['A13'] = '可选字段：网站链接、所有者、国家、地区、描述、备注'
            worksheet['A14'] = '注意：第一行必须是字段名称，请勿修改'
            worksheet['A15'] = '密码长度限制：最大100个字符'
        
        # 将指针移到开始位置
        output.seek(0)
        
        # 返回文件
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='账号导入模板.xlsx'
        )
    except Exception as e:
        logger.error(f"Error generating template: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'生成模板失败: {str(e)}'
        }), 500

@account_routes.route('/api/suppliers', methods=['GET'])
@login_required
@staff_only
def get_suppliers():
    """获取供应商列表，用于账号管理页面的下拉选择"""
    try:
        logger.info("Fetching suppliers for account management")
        
        # 获取所有活跃的供应商
        suppliers = Supplier.query.filter_by(status='active').order_by(Supplier.name).all()
        logger.info(f"Found {len(suppliers)} active suppliers")
        
        suppliers_data = [{
            'supplier_id': supplier.supplier_id,
            'name': supplier.name,
            'supplier_type': supplier.supplier_type_code,
            'supplier_type_display': supplier.supplier_type_display,
            'country': supplier.country
        } for supplier in suppliers]
        
        logger.info(f"Returning {len(suppliers_data)} suppliers to frontend")
        return jsonify({
            'success': True,
            'suppliers': suppliers_data
        })
    except Exception as e:
        logger.error(f"Error fetching suppliers: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'获取供应商列表失败: {str(e)}'
        }), 500 