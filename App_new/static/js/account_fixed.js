// 账号管理系统 API 测试脚本
console.log('测试脚本已加载 - 版本 20250414-1');

// 测试API路径
async function testApiPath() {
    console.log('开始测试API路径...');
    
    try {
        // 测试正确的API路径
        console.log('测试 /account/api/accounts 路径');
        const response = await fetch('/account/api/accounts');
        console.log('API响应状态:', response.status);
        
        if (response.ok) {
            const data = await response.json();
            console.log('API响应成功:', data);
            
            // 如果成功，显示一个成功消息
            const body = document.querySelector('body');
            const alert = document.createElement('div');
            alert.style.position = 'fixed';
            alert.style.top = '20px';
            alert.style.left = '50%';
            alert.style.transform = 'translateX(-50%)';
            alert.style.padding = '15px 20px';
            alert.style.backgroundColor = '#4CAF50';
            alert.style.color = 'white';
            alert.style.borderRadius = '5px';
            alert.style.boxShadow = '0 4px 8px rgba(0,0,0,0.2)';
            alert.style.zIndex = '9999';
            alert.innerHTML = '✅ API测试成功! 正确路径 /account/api/accounts 可以访问!';
            body.appendChild(alert);
            
            setTimeout(() => {
                alert.remove();
            }, 5000);
        } else {
            console.error('API请求失败:', response.status);
        }
    } catch (error) {
        console.error('测试API路径出错:', error);
    }
}

// 页面加载后执行测试
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM已加载，开始测试');
    testApiPath();
}); 