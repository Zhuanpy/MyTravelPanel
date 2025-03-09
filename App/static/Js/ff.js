// 封装AJAX请求逻辑
function sendPostRequest(url, successMessage) {
    fetch(url, {
        method: 'POST',  // 指定HTTP请求方法为POST，用于发送数据到服务器
        headers: {
            'Content-Type': 'application/json', // 设置请求头，指定发送的数据类型为JSON
        },
        body: JSON.stringify({})  // 请求体内容，这里是空的JSON对象，视具体需求可修改
    })
    .then(response => response.json())  // 解析服务器返回的响应数据为JSON格式
    .then(data => {
        if (data.status === 'success') {  // 检查响应数据中是否包含"status"字段，并且值为"success"
            console.log(successMessage); // 如果成功，打印自定义的成功消息到控制台
        }
    })
    .catch(error => {
        console.error('请求失败: ', error); // 捕获并处理请求过程中发生的错误，打印到控制台
    });
}