// 封装AJAX请求逻辑
function sendPostRequest(url, successMessage) {
    // 获取CSRF令牌
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    
    fetch(url, {
        method: 'POST',  // 指定HTTP请求方法为POST，用于发送数据到服务器
        headers: {
            'Content-Type': 'application/json', // 设置请求头，指定发送的数据类型为JSON
            'X-CSRFToken': csrfToken, // 添加CSRF令牌
            'X-Requested-With': 'XMLHttpRequest' // 添加AJAX标识
        },
        body: JSON.stringify({})  // 请求体内容，这里是空的JSON对象，视具体需求可修改
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.status === 'success' || data.success) {  // 检查响应数据中是否包含"status"字段，并且值为"success"
            console.log(successMessage); // 如果成功，打印自定义的成功消息到控制台
            // 创建临时提示元素
            const alertDiv = document.createElement('div');
            alertDiv.className = 'alert alert-success';
            alertDiv.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999; padding: 10px 20px; border-radius: 4px;';
            alertDiv.textContent = successMessage;
            document.body.appendChild(alertDiv);
            
            // 1秒后移除提示
            setTimeout(() => {
                alertDiv.remove();
            }, 1000);
        } else {
            throw new Error(data.message || '操作失败');
        }
    })
    .catch(error => {
        console.error('请求失败: ', error); // 捕获并处理请求过程中发生的错误，打印到控制台
        // 创建临时错误提示元素
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-danger';
        alertDiv.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999; padding: 10px 20px; border-radius: 4px;';
        alertDiv.textContent = '操作失败: ' + error.message;
        document.body.appendChild(alertDiv);
        
        // 1秒后移除提示
        setTimeout(() => {
            alertDiv.remove();
        }, 1000);
    });
}