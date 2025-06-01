@app.route('/open_bill_project_folder', methods=['GET', 'POST'])
def open_bill_project_folder():
    try:
        # 获取项目根目录
        project_root = Path(__file__).resolve().parent
        folder_path = project_root / "static" / "资源" / "Bill"
        
        if not folder_path.exists():
            return jsonify({
                'status': 'error',
                'message': f'账单项目文件夹 {folder_path} 不存在'
            }), 404

        # 打开文件夹
        if platform.system() == "Windows":
            os.startfile(folder_path)
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["open", folder_path])
        else:  # Linux and other Unix-based systems
            subprocess.run(["xdg-open", folder_path])

        return jsonify({
            'status': 'success',
            'message': '文件夹已打开',
            'path': str(folder_path)
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'无法打开文件夹: {str(e)}'
        }), 500 