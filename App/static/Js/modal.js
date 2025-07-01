// 通用的模态框功能
document.addEventListener('DOMContentLoaded', function() {
    // 防抖函数
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // 模态框状态跟踪
    const modalStates = new Map();

    // 初始化所有模态框
    document.querySelectorAll('.modal').forEach(modal => {
        // 移除可能存在的旧实例
        const oldInstance = bootstrap.Modal.getInstance(modal);
        if (oldInstance) {
            oldInstance.dispose();
        }

        // 创建新的模态框实例
        const modalInstance = new bootstrap.Modal(modal, {
            backdrop: 'static',
            keyboard: false,
            focus: true
        });

        // 记录模态框状态
        modalStates.set(modal.id, {
            isOpen: false,
            instance: modalInstance
        });

        // 监听模态框事件
        modal.addEventListener('shown.bs.modal', () => {
            modalStates.get(modal.id).isOpen = true;
        });

        modal.addEventListener('hidden.bs.modal', () => {
            modalStates.get(modal.id).isOpen = false;
            // 重置表单
            const form = modal.querySelector('form');
            if (form) {
                form.reset();
            }
        });

        // 处理表单提交
        const form = modal.querySelector('form');
        if (form) {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                try {
                    const response = await fetch(form.action, {
                        method: 'POST',
                        body: new FormData(form)
                    });
                    
                    if (response.ok) {
                        modalInstance.hide();
                        // 延迟刷新页面，等待模态框完全关闭
                        setTimeout(() => {
                            window.location.reload();
                        }, 300);
                    } else {
                        showAlert('保存失败，请重试', 'error');
                    }
                } catch (error) {
                    console.error('提交表单时出错:', error);
                    showAlert('发生错误，请重试', 'error');
                }
            });
        }
    });

    // 处理编辑按钮点击
    const handleEditClick = (button) => {
        const modalId = button.getAttribute('data-bs-target');
        const modal = document.querySelector(modalId);
        
        if (!modal) {
            console.error('未找到模态框:', modalId);
            return;
        }

        const modalState = modalStates.get(modal.id);
        if (!modalState || modalState.isOpen) {
            return;
        }

        modalState.instance.show();
    };

    // 为编辑按钮添加防抖点击处理
    const debouncedHandleEdit = debounce(handleEditClick, 300);

    document.querySelectorAll('.edit-itinerary-btn').forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            const modalId = `#editItineraryModal-${button.dataset.itineraryId}`;
            button.setAttribute('data-bs-target', modalId);
            debouncedHandleEdit(button);
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
    function showAlert(message, type = 'info') {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
        alertDiv.role = 'alert';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        const container = document.querySelector('.container');
        if (container) {
            container.insertBefore(alertDiv, container.firstChild);
        }
        
        setTimeout(() => {
            alertDiv.remove();
        }, 3000);
    }

    // 导出通用函数
    window.showAlert = showAlert;
    window.togglePasswordVisibility = togglePasswordVisibility;
    window.copyPassword = copyPassword;
});

// 自定义模态框管理器
class CustomModalManager {
    constructor() {
        this.activeModal = null;
        this.isProcessing = false;
        this.init();
    }

    init() {
        // 使用事件委托处理所有模态框相关的点击事件
        document.addEventListener('click', (event) => {
            // 编辑按钮点击
            const editButton = event.target.closest('.edit-itinerary-btn');
            if (editButton && !this.isProcessing) {
                event.preventDefault();
                event.stopPropagation();
                const itineraryId = editButton.dataset.itineraryId;
                this.showModal(`editItineraryModal-${itineraryId}`);
            }

            // 关闭按钮点击
            if (event.target.closest('[data-action="close-modal"]')) {
                event.preventDefault();
                event.stopPropagation();
                this.hideActiveModal();
            }

            // 点击模态框外部区域关闭
            if (event.target.classList.contains('custom-modal') && !event.target.closest('.modal-content')) {
                this.hideActiveModal();
            }
        }, true);

        // 处理表单提交
        document.addEventListener('submit', async (event) => {
            const form = event.target.closest('.itinerary-edit-form');
            if (form) {
                event.preventDefault();
                await this.handleFormSubmit(form);
            }
        });

        // 处理ESC键
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape' && this.activeModal) {
                this.hideActiveModal();
            }
        });
    }

    showModal(modalId) {
        if (this.isProcessing) return;
        this.isProcessing = true;

        // 隐藏当前活动的模态框
        if (this.activeModal) {
            this.hideActiveModal();
        }

        const modal = document.getElementById(modalId);
        if (!modal) {
            console.error('Modal not found:', modalId);
            this.isProcessing = false;
            return;
        }

        // 显示模态框
        modal.style.display = 'block';
        document.body.classList.add('modal-open');

        // 使用 requestAnimationFrame 确保过渡效果正常工作
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                modal.classList.add('show');
                this.activeModal = modal;
                this.isProcessing = false;
            });
        });
    }

    hideActiveModal() {
        if (!this.activeModal || this.isProcessing) return;
        this.isProcessing = true;

        const modal = this.activeModal;
        modal.classList.remove('show');

        // 等待过渡效果完成
        setTimeout(() => {
            modal.style.display = 'none';
            document.body.classList.remove('modal-open');
            this.activeModal = null;
            this.isProcessing = false;

            // 重置表单
            const form = modal.querySelector('form');
            if (form) {
                form.reset();
            }
        }, 300); // 与CSS过渡时间相匹配
    }

    async handleFormSubmit(form) {
        if (this.isProcessing) return;
        this.isProcessing = true;

        try {
            const response = await fetch(form.action, {
                method: 'POST',
                body: new FormData(form),
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            const data = await response.json();
            
            if (data.success) {
                this.showMessage('保存成功', 'success');
                this.hideActiveModal();
                // 延迟刷新页面，等待模态框完全关闭
                setTimeout(() => window.location.reload(), 500);
            } else {
                this.showMessage(data.message || '保存失败', 'error');
            }
        } catch (error) {
            console.error('表单提交错误:', error);
            this.showMessage('提交表单时发生错误', 'error');
        } finally {
            this.isProcessing = false;
        }
    }

    showMessage(message, type) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `alert alert-${type} alert-dismissible fade show fixed-top w-50 mx-auto mt-3`;
        messageDiv.style.zIndex = '9999';
        messageDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        document.body.appendChild(messageDiv);
        setTimeout(() => messageDiv.remove(), 3000);
    }
}

// 创建单例实例
const modalManager = new CustomModalManager(); 