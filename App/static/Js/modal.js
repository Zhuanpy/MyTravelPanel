// 通用的模态框功能
document.addEventListener('DOMContentLoaded', function() {
    // 初始化所有模态框
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        // 创建模态框实例
        const modalInstance = new bootstrap.Modal(modal, {
            backdrop: true,
            keyboard: true,
            focus: true
        });

        // 添加关闭按钮事件
        const closeButtons = modal.querySelectorAll('[data-bs-dismiss="modal"]');
        closeButtons.forEach(button => {
            button.addEventListener('click', () => {
                modalInstance.hide();
            });
        });

        // 添加模态框关闭事件
        modal.addEventListener('hidden.bs.modal', function() {
            // 重置表单
            const form = modal.querySelector('form');
            if (form) {
                form.reset();
            }
            // 移除背景遮罩层
            const backdrop = document.querySelector('.modal-backdrop');
            if (backdrop) {
                backdrop.remove();
            }
        });
    });

    // 密码显示/隐藏功能
    function togglePasswordVisibility(input, button) {
        if (input.type === 'password') {
            input.type = 'text';
            button.textContent = '隐藏密码';
        } else {
            input.type = 'password';
            button.textContent = '显示密码';
        }
    }

    // 复制密码功能
    async function copyPassword(password) {
        try {
            await navigator.clipboard.writeText(password);
            showAlert('密码已复制到剪贴板', true);
        } catch (err) {
            console.error('复制失败:', err);
            showAlert('复制失败', false);
        }
    }

    // 显示提示信息
    function showAlert(message, isSuccess = true) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${isSuccess ? 'success' : 'danger'} alert-dismissible fade show`;
        alertDiv.role = 'alert';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        const container = document.querySelector('.container');
        if (container) {
            container.insertBefore(alertDiv, container.firstChild);
        }
        
        // 3秒后自动消失
        setTimeout(() => {
            alertDiv.remove();
        }, 3000);
    }

    // 导出通用函数供其他模块使用
    window.togglePasswordVisibility = togglePasswordVisibility;
    window.copyPassword = copyPassword;
    window.showAlert = showAlert;
}); 