from flask import Blueprint, jsonify, request, render_template, send_file
from flask_login import login_required, current_user
from App.exts import db
from App.exts import csrf
from App.utils.decorators import staff_only
import logging
from sqlalchemy import case
from datetime import datetime
import pandas as pd
from io import BytesIO
from App.models.account import Account

# 创建蓝图
account_routes = Blueprint('account_routes', __name__)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        
        return render_template('utils/account_detail.html', account=account)
    except Exception as e:
        logger.error(f"Error fetching account detail: {str(e)}")
        return render_template('errors/404.html'), 404

@account_routes.route('/api/accounts/increment_click/<int:account_id>', methods=['POST'])
@csrf.exempt
def increment_click(account_id):
    try:
        logger.info(f"Received click increment request for account_id: {account_id}")
        account = Account.query.get(account_id)
        if not account:
            return jsonify({'success': False, 'message': '账号不存在'}), 404
        
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
def get_popular_accounts():
    try:
        logger.info("Fetching popular accounts")
        # 修复 case 语句的语法
        popular_accounts = Account.query.order_by(
            case(
                (Account.click_count == None, 0),
                else_=Account.click_count
            ).desc()
        ).limit(25).all()
        
        accounts_data = [{
            'id': account.id,
            'platform': account.platform,
            'website_url': account.website_url,
            'click_count': account.click_count or 0
        } for account in popular_accounts]
        
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
        accounts = Account.query.all()
        accounts_data = [{
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
            'click_count': account.click_count or 0
        } for account in accounts]
        
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
def get_account(account_id):
    """获取单个账号信息"""
    try:
        account = Account.query.get_or_404(account_id)
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
                'click_count': account.click_count or 0
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
            notes=data.get('notes')
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
                'username': new_account.username
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

        data = request.get_json()
        logger.info(f"Update data received: {data}")

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
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': '未找到上传的文件'
            }), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': '未选择文件'
            }), 400

        if not file.filename.endswith(('.xlsx', '.xls')):
            return jsonify({
                'success': False,
                'message': '只支持 Excel 文件 (.xlsx, .xls)'
            }), 400

        # 读取 Excel 文件
        try:
            df = pd.read_excel(file)
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Excel 文件解析失败: {str(e)}'
            }), 400

        # 验证必填字段
        required_fields = ['platform', 'category', 'username', 'password']
        missing_fields = [field for field in required_fields if field not in df.columns]
        if missing_fields:
            return jsonify({
                'success': False,
                'message': f'Excel 文件缺少必填字段: {", ".join(missing_fields)}'
            }), 400

        # 导入账号
        imported_count = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                # 创建新账号
                new_account = Account(
                    platform=row['platform'],
                    website_url=row.get('website_url'),
                    category=row['category'],
                    owner=row.get('owner'),
                    username=row['username'],
                    password=row['password'],
                    country=row.get('country'),
                    region=row.get('region'),
                    description=row.get('description'),
                    notes=row.get('notes')
                )
                db.session.add(new_account)
                imported_count += 1
            except Exception as e:
                errors.append(f'第 {index + 2} 行导入失败: {str(e)}')

        # 提交所有更改
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '导入完成',
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
        # 创建一个示例数据
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
        
        # 创建Excel文件
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='账号导入模板')
            
            # 获取workbook和worksheet对象
            workbook = writer.book
            worksheet = writer.sheets['账号导入模板']
            
            # 设置列宽
            for idx, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).apply(len).max(),
                    len(col)
                )
                worksheet.set_column(idx, idx, max_length + 2)
            
            # 添加说明
            worksheet.write('A12', '必填字段：平台/网址、分类、用户名、密码')
            worksheet.write('A13', '可选字段：网站链接、所有者、国家、地区、描述、备注')
            worksheet.write('A14', '注意：第一行必须是字段名称，请勿修改')
        
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