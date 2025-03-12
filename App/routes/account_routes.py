from flask import Blueprint, jsonify, request,render_template
from ..models.account import Account
from ..exts import db
from sqlalchemy.exc import SQLAlchemyError
import pandas as pd
from werkzeug.utils import secure_filename
import os
import json

account_routes = Blueprint('account_routes', __name__)

# 确保上传目录存在
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@account_routes.route('/api/accounts', methods=['GET'])
def get_accounts():
    try:
        accounts = db.session.query(
            Account.id,
            Account.platform,
            Account.website_url,
            Account.username,
            Account.password,
            Account.category,
            Account.owner,
            Account.country,
            Account.region,
            Account.description,
            Account.notes,
            Account.file_materials,
            Account.additional_info,
            Account.created_at,
            Account.updated_at
        ).all()
        
        return jsonify([{
            'id': account.id,
            'platform': account.platform,
            'website_url': account.website_url,
            'username': account.username,
            'password': account.password,
            'category': account.category,
            'owner': account.owner,
            'country': account.country,
            'region': account.region,
            'description': account.description,
            'notes': account.notes,
            'file_materials': json.loads(account.file_materials) if account.file_materials else [],
            'additional_info': json.loads(account.additional_info) if account.additional_info else [],
            'created_at': account.created_at.strftime('%Y-%m-%d %H:%M:%S') if account.created_at else None,
            'updated_at': account.updated_at.strftime('%Y-%m-%d %H:%M:%S') if account.updated_at else None
        } for account in accounts])
    except Exception as e:
        print(f"Error in get_accounts: {str(e)}")  # 打印详细错误信息
        import traceback
        traceback.print_exc()  # 打印完整的错误堆栈
        return jsonify({'error': str(e)}), 500

@account_routes.route('/api/categories', methods=['GET'])
def get_categories():
    """获取所有账号类别"""
    return jsonify(Account.CATEGORIES)

@account_routes.route('/api/accounts', methods=['POST'])
def create_account():
    try:
        data = request.get_json()
        new_account = Account(
            platform=data['platform'],
            username=data['username'],
            password=data['password'],
            website_url=data.get('website_url'),
            category=data.get('category'),
            owner=data.get('owner'),
            country=data.get('country'),
            region=data.get('region'),
            description=data.get('description'),
            notes=data.get('notes'),
            file_materials=json.dumps(data.get('file_materials', [])),
            additional_info=json.dumps(data.get('additional_info', []))
        )
        db.session.add(new_account)
        db.session.commit()
        return jsonify({'message': '账号创建成功', 'account': new_account.to_dict()}), 201
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': '数据库错误'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@account_routes.route('/api/accounts/<int:id>', methods=['GET'])
def get_account(id):
    try:
        account = Account.query.get_or_404(id)
        return jsonify({
            'id': account.id,
            'platform': account.platform,
            'website_url': account.website_url,
            'username': account.username,
            'password': account.password,
            'category': account.category,
            'owner': account.owner,
            'country': account.country,
            'region': account.region,
            'description': account.description,
            'notes': account.notes,
            'created_at': account.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': account.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@account_routes.route('/api/accounts/<int:id>', methods=['PUT'])
def update_account(id):
    try:
        print(f"Updating account {id}")
        account = Account.query.get_or_404(id)
        data = request.get_json()
        print(f"Received data: {data}")
        
        # 更新基本字段
        allowed_fields = [
            'platform', 
            'website_url', 
            'username', 
            'category', 
            'owner', 
            'country', 
            'region', 
            'description', 
            'notes'
        ]
        
        # 更新提供的字段
        for field in allowed_fields:
            if field in data:
                value = data[field]
                print(f"Updating field {field} with value {value}")
                setattr(account, field, value)
        
        # 只在提供新密码时更新密码
        if 'password' in data and data['password']:
            print("Updating password")
            account.password = data['password']
        
        db.session.commit()
        print("Account updated successfully")
        return jsonify({'message': '账号更新成功'})
    except SQLAlchemyError as e:
        db.session.rollback()
        print(f"Database error: {str(e)}")
        return jsonify({'error': f'数据库错误: {str(e)}'}), 500
    except Exception as e:
        print(f"General error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400

@account_routes.route('/api/accounts/<int:id>', methods=['DELETE'])
def delete_account(id):
    try:
        account = Account.query.get_or_404(id)
        db.session.delete(account)
        db.session.commit()
        return jsonify({'message': '账号删除成功'})
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': '数据库错误'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# 页面路由
@account_routes.route('/accounts')
def account_page():
    return render_template('files/账号管理.html')

@account_routes.route('/api/accounts/import', methods=['POST'])
def import_accounts():
    if 'file' not in request.files:
        return jsonify({'message': '没有上传文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': '没有选择文件'}), 400
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        return jsonify({'message': '只支持Excel文件'}), 400
    
    try:
        # 保存上传的文件
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        # 读取Excel文件
        df = pd.read_excel(filepath)
        
        # 验证必要的列是否存在
        required_columns = ['platform', 'username', 'password', 'category']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return jsonify({'message': f'缺少必要的列: {", ".join(missing_columns)}'}), 400
        
        imported_count = 0
        errors = []
        
        # 遍历数据行
        for index, row in df.iterrows():
            try:
                # 检查必要字段是否为空
                if pd.isna(row['platform']) or pd.isna(row['username']) or pd.isna(row['password']) or pd.isna(row['category']):
                    errors.append(f'第 {index + 2} 行: 必要字段不能为空')
                    continue

                # 将密码转换为字符串并去除首尾空格
                password = str(row['password']).strip()
                
                # 创建账号对象
                account = Account(
                    platform=row['platform'],
                    username=row['username'],
                    password=password,  # 直接存储原始密码
                    category=row['category'],
                    website_url=row['website_url'] if 'website_url' in df.columns and not pd.isna(row['website_url']) else None,
                    owner=row['owner'] if 'owner' in df.columns and not pd.isna(row['owner']) else None,
                    country=row['country'] if 'country' in df.columns and not pd.isna(row['country']) else None,
                    region=row['region'] if 'region' in df.columns and not pd.isna(row['region']) else None,
                    description=row['description'] if 'description' in df.columns and not pd.isna(row['description']) else None,
                    notes=row['notes'] if 'notes' in df.columns and not pd.isna(row['notes']) else None
                )
                
                db.session.add(account)
                imported_count += 1
            except Exception as e:
                errors.append(f'第 {index + 2} 行: {str(e)}')
        
        # 提交事务
        db.session.commit()
        
        # 删除上传的文件
        os.remove(filepath)
        
        return jsonify({
            'message': '导入完成',
            'imported_count': imported_count,
            'errors': errors
        })
        
    except Exception as e:
        if os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({'message': f'导入失败: {str(e)}'}), 400