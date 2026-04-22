/**
 * 项目详情页面JavaScript模块
 * 提供内联编辑、备注管理、状态更新等功能
 */
class ProjectDetailManager {
    constructor() {
        this.csrfToken = this.getCSRFToken();
        this.apiEndpoints = {
            updateDesc: '/projects/header/update_desc',
            updateCompany: '/projects/header/update_company',
            syncInvoiceCompany: '/projects/header/sync_invoice_company',
            updateStatus: '/projects/header/update_status',
            updateContact: '/projects/header/update_contact',
            updateRemarks: '/projects/header/update_remarks',
            updateRefStatus: '/projects/ref/update_status',
            quickCreateEO: '/projects/eo/quick_create',
            reminder: '/projects/detail/header'
        };
        
        this.init();
    }

    /**
     * 初始化所有功能
     */
    init() {
        this.setupKeyboardNavigation();
        this.setupInlineEditors();
        this.setupRemarksManager();
        this.setupRefStatusEditors();
        this.setupReminderManager();
        this.setupEventDelegation();
        this.cleanupFlashMessages();
    }

    /**
     * 获取CSRF Token
     */
    getCSRFToken() {
        const token = document.querySelector('meta[name="csrf-token"]');
        return token ? token.getAttribute('content') : '';
    }

    /**
     * 设置键盘导航
     */
    setupKeyboardNavigation() {
        const prevUrl = window.prevHeaderUrl;
        const nextUrl = window.nextHeaderUrl;
        const listUrl = window.listUrl;

        document.addEventListener('keydown', (event) => {
            if (this.isInputFocused(event.target)) return;

            switch(event.key) {
                case 'ArrowLeft':
                    if (prevUrl) {
                        event.preventDefault();
                        window.location.href = prevUrl;
                    }
                    break;
                case 'ArrowRight':
                    if (nextUrl) {
                        event.preventDefault();
                        window.location.href = nextUrl;
                    }
                    break;
                case 'l':
                case 'L':
                    if (listUrl) {
                        event.preventDefault();
                        window.location.href = listUrl;
                    }
                    break;
            }
        });

        // 5秒后自动隐藏键盘提示
        setTimeout(() => {
            const alert = document.querySelector('.alert');
            if (alert) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        }, 5000);
    }

    /**
     * 检查是否在输入框中
     */
    isInputFocused(element) {
        return ['INPUT', 'TEXTAREA', 'SELECT'].includes(element.tagName);
    }

    /**
     * 设置内联编辑器
     */
    setupInlineEditors() {
        // 使用事件委托处理所有内联编辑
        document.addEventListener('click', (event) => {
            const target = event.target;
            
            // 状态编辑
            if (target.id === 'status-span') {
                this.toggleInlineEdit(target, 'status-select');
            }
            // 公司编辑
            else if (target.id === 'company-name-span') {
                this.toggleInlineEdit(target, 'company-select');
            }
            // 联系人编辑
            else if (target.id === 'contact-span') {
                this.toggleInlineEdit(target, 'contact-input');
            }
        });

        // 处理选择框和输入框的变化
        document.addEventListener('change', (event) => {
            const target = event.target;
            
            if (target.id === 'status-select') {
                this.saveInlineEdit('status', target);
            } else if (target.id === 'company-select') {
                this.saveInlineEdit('company', target);
            }
        });

        // 处理输入框的保存
        document.addEventListener('blur', (event) => {
            const target = event.target;
            
            if (target.id === 'contact-input') {
                this.saveInlineEdit('contact', target);
            }
        });

        // 处理键盘事件
        document.addEventListener('keydown', (event) => {
            const target = event.target;
            
            if (target.id === 'contact-input') {
                if (event.key === 'Enter') {
                    event.preventDefault();
                    this.saveInlineEdit('contact', target);
                } else if (event.key === 'Escape') {
                    this.cancelInlineEdit(target);
                }
            }
        });
    }

    /**
     * 检查结算状态，如果已结算则阻止编辑
     */
    checkSettledStatus() {
        if (window.isSettled) {
            this.showMessage('该项目已结算，无法进行编辑操作。如需修改，请先取消结算。', 'error');
            return false;
        }
        return true;
    }

    /**
     * 切换内联编辑状态
     */
    toggleInlineEdit(displayElement, inputElementId) {
        // 检查结算状态
        if (!this.checkSettledStatus()) return;

        const inputElement = document.getElementById(inputElementId);
        if (!inputElement) return;

        // 隐藏显示元素，显示输入元素
        displayElement.style.display = 'none';
        inputElement.style.display = 'inline-block';
        
        // 设置输入元素样式
        if (inputElementId.includes('select')) {
            inputElement.style.width = inputElementId === 'status-select' ? '90%' : '70%';
        } else {
            inputElement.style.width = '60%';
            inputElement.value = displayElement.textContent.trim() === '未设置' ? '' : displayElement.textContent.trim();
        }
        
        inputElement.focus();
        if (inputElement.select) inputElement.select();
    }

    /**
     * 保存内联编辑
     */
    async saveInlineEdit(type, inputElement) {
        const displayElement = this.getDisplayElement(inputElement);
        if (!displayElement) return;

        const value = inputElement.value.trim();
        const headerId = displayElement.getAttribute('data-header-id');
        
        if (!headerId) return;

        try {
            const endpoint = this.apiEndpoints[`update${type.charAt(0).toUpperCase() + type.slice(1)}`];
            const response = await this.makeRequest(endpoint, {
                header_id: headerId,
                [type]: value
            });

            if (response.success) {
                // 更新显示文本
                if (type === 'company') {
                    displayElement.textContent = inputElement.options[inputElement.selectedIndex].text;
                } else if (type === 'status') {
                    displayElement.textContent = inputElement.options[inputElement.selectedIndex].text;
                    displayElement.className = `status-badge status-${value}`;
                } else {
                    displayElement.textContent = value || '未设置';
                }

                this.showMessage('保存成功', 'success');

                // 公司变更后，若存在抬头快照不一致的未付款发票，提示是否同步
                if (type === 'company' && response.unsynced_invoices && response.unsynced_invoices.count > 0) {
                    this.confirmSyncInvoiceCompany(headerId, response.unsynced_invoices);
                }
            } else {
                this.showMessage(response.message || '保存失败', 'error');
            }
        } catch (error) {
            this.showMessage('网络错误，保存失败', 'error');
        } finally {
            this.cancelInlineEdit(inputElement);
        }
    }

    /**
     * 公司变更后，询问是否把项目下未付款发票的抬头一并同步到新公司
     */
    async confirmSyncInvoiceCompany(headerId, info) {
        const preview = (info.invoice_numbers || []).slice(0, 5).join(', ');
        const more = info.count > 5 ? ` 等共 ${info.count} 张` : '';
        const confirmed = window.confirm(
            `该项目下有 ${info.count} 张 "Confirmed + 未付款" 的发票抬头与新公司不一致：\n`
            + `${preview}${more}\n\n`
            + `是否将这些发票的客户公司同步为 "${info.new_company_name}"？\n`
            + `（不会改动已付款或已作废的发票）`
        );
        if (!confirmed) return;

        try {
            const resp = await this.makeRequest(this.apiEndpoints.syncInvoiceCompany, {
                header_id: headerId
            });
            if (resp.success) {
                this.showMessage(`已同步 ${resp.updated} 张发票抬头`, 'success');
            } else {
                this.showMessage(resp.message || '同步失败', 'error');
            }
        } catch (e) {
            this.showMessage('网络错误，同步失败', 'error');
        }
    }

    /**
     * 取消内联编辑
     */
    cancelInlineEdit(inputElement) {
        const displayElement = this.getDisplayElement(inputElement);
        if (displayElement) {
            displayElement.style.display = '';
            inputElement.style.display = 'none';
        }
    }

    /**
     * 获取对应的显示元素
     */
    getDisplayElement(inputElement) {
        const inputId = inputElement.id;
        if (inputId.includes('status')) {
            return document.getElementById('status-span');
        } else if (inputId.includes('company')) {
            return document.getElementById('company-name-span');
        } else if (inputId.includes('contact')) {
            return document.getElementById('contact-span');
        }
        return null;
    }

    /**
     * 设置备注管理器
     */
    setupRemarksManager() {
        // 新增备注按钮
        const addBtn = document.getElementById('add-remarks-btn');
        if (addBtn) {
            addBtn.addEventListener('click', () => this.showNewRemarksInput());
        }

        // 新增备注输入框的按钮事件
        document.addEventListener('click', (event) => {
            if (event.target.id === 'cancel-remarks-btn') {
                this.cancelNewRemarks();
            } else if (event.target.id === 'submit-remarks-btn') {
                this.submitNewRemarks();
            }
        });
    }

    /**
     * 显示新增备注输入框
     */
    showNewRemarksInput() {
        // 检查结算状态
        if (!this.checkSettledStatus()) return;

        const section = document.getElementById('new-remarks-section');
        const input = document.getElementById('new-remarks-input');

        if (section && input) {
            section.style.display = 'block';
            setTimeout(() => section.classList.add('show'), 10);
            input.focus();
        }
    }

    /**
     * 取消新增备注
     */
    cancelNewRemarks() {
        const section = document.getElementById('new-remarks-section');
        const input = document.getElementById('new-remarks-input');
        
        if (section) {
            section.classList.remove('show');
            setTimeout(() => section.style.display = 'none', 300);
        }
        
        if (input) {
            input.value = '';
        }
    }

    /**
     * 提交新增备注
     */
    async submitNewRemarks() {
        const input = document.getElementById('new-remarks-input');
        const newRemarks = input.value.trim();
        
        if (!newRemarks) {
            this.showMessage('请输入备注信息', 'error');
            return;
        }

        try {
            const timestamp = this.getCurrentTimestamp();
            const existingRemarks = this.getExistingRemarks();
            const combinedRemarks = this.combineRemarks(existingRemarks, newRemarks, timestamp);

            const response = await this.makeRequest(this.apiEndpoints.updateRemarks, {
                header_id: window.headerId,
                remarks: combinedRemarks
            });

            if (response.success) {
                this.showMessage('备注保存成功', 'success');
                setTimeout(() => window.location.reload(), 1000);
            } else {
                this.showMessage(response.message || '备注保存失败', 'error');
            }
        } catch (error) {
            this.showMessage('网络错误，备注保存失败', 'error');
        }
    }

    /**
     * 获取当前时间戳
     */
    getCurrentTimestamp() {
        const now = new Date();
        return now.getFullYear() + '-' + 
               String(now.getMonth() + 1).padStart(2, '0') + '-' + 
               String(now.getDate()).padStart(2, '0') + ' ' + 
               String(now.getHours()).padStart(2, '0') + ':' + 
               String(now.getMinutes()).padStart(2, '0') + ':' + 
               String(now.getSeconds()).padStart(2, '0');
    }

    /**
     * 获取现有备注
     */
    getExistingRemarks() {
        const remarksElement = document.getElementById('remarks-display');
        if (!remarksElement) return '';
        
        return remarksElement.textContent || remarksElement.innerText || '';
    }

    /**
     * 合并备注
     */
    combineRemarks(existing, newRemarks, timestamp) {
        // 清理现有备注，只保留有时间戳的
        let cleanedRemarks = '';
        if (existing) {
            const lines = existing.split('\n');
            const validLines = lines.filter(line => 
                line.trim().match(/^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]/)
            );
            cleanedRemarks = validLines
                .filter(line => line.trim() !== '')
                .map(line => line.trim())
                .join('\n');
        }
        
        // 组合备注
        let combined = cleanedRemarks ? 
            cleanedRemarks + '\n\n[' + timestamp + '] ' + newRemarks : 
            '[' + timestamp + '] ' + newRemarks;
        
        // 清理格式
        return combined
            .replace(/\r\n/g, '\n')
            .replace(/\r/g, '\n')
            .split('\n')
            .map(line => line.trim())
            .filter(line => line !== '')
            .join('\n')
            .replace(/\n\s*\n/g, '\n')
            .replace(/^\s+|\s+$/g, '')
            .trim();
    }

    /**
     * 设置REF状态编辑器
     */
    setupRefStatusEditors() {
        document.addEventListener('click', (event) => {
            const target = event.target;
            if (target.classList.contains('status-badge') && target.id.startsWith('ref-status-')) {
                const refId = target.getAttribute('data-ref-id');
                this.editRefStatus(refId);
            }
        });

        document.addEventListener('change', (event) => {
            const target = event.target;
            if (target.classList.contains('ref-status-select')) {
                const refId = target.id.replace('ref-status-select-', '');
                this.saveRefStatus(refId, target);
            }
        });
    }

    /**
     * 编辑REF状态
     */
    editRefStatus(refId) {
        // 检查结算状态
        if (!this.checkSettledStatus()) return;

        const statusSpan = document.getElementById(`ref-status-${refId}`);
        const statusSelect = document.getElementById(`ref-status-select-${refId}`);
        
        if (statusSpan && statusSelect) {
            statusSpan.style.display = 'none';
            statusSelect.style.display = 'inline-block';
            statusSelect.focus();
        }
    }

    /**
     * 保存REF状态
     */
    async saveRefStatus(refId, selectElement) {
        const statusSpan = document.getElementById(`ref-status-${refId}`);
        if (!statusSpan) return;

        const newStatus = selectElement.value;
        const statusText = selectElement.options[selectElement.selectedIndex].text;

        try {
            const response = await this.makeRequest(this.apiEndpoints.updateRefStatus, {
                ref_id: refId,
                status: newStatus
            });

            if (response.success) {
                statusSpan.textContent = statusText;
                statusSpan.className = `status-badge status-${newStatus}`;
                statusSpan.style.display = 'inline-block';
                selectElement.style.display = 'none';
                this.showMessage('状态更新成功', 'success');
            } else {
                this.showMessage(response.message || '保存失败', 'error');
                this.cancelRefStatusEdit(refId);
            }
        } catch (error) {
            this.showMessage('网络错误，保存失败', 'error');
            this.cancelRefStatusEdit(refId);
        }
    }

    /**
     * 取消REF状态编辑
     */
    cancelRefStatusEdit(refId) {
        const statusSpan = document.getElementById(`ref-status-${refId}`);
        const statusSelect = document.getElementById(`ref-status-select-${refId}`);
        
        if (statusSpan && statusSelect) {
            statusSpan.style.display = 'inline-block';
            statusSelect.style.display = 'none';
        }
    }

    /**
     * 设置提醒管理器
     */
    setupReminderManager() {
        document.addEventListener('click', (event) => {
            // 向上查找最近的带有 data-action 的元素
            const target = event.target.closest('[data-action]');
            if (!target) return;
            
            const action = target.getAttribute('data-action');
            
            switch(action) {
                case 'add-reminder':
                    this.addReminder();
                    break;
                case 'edit-reminder':
                    this.editReminder();
                    break;
                case 'delete-reminder':
                    this.deleteReminder();
                    break;
                case 'close-reminder-modal':
                    this.closeReminderModal();
                    break;
                case 'save-reminder':
                    this.saveReminder();
                    break;
            }
        });
    }

    /**
     * 添加提醒
     */
    addReminder() {
        // 检查结算状态
        if (!this.checkSettledStatus()) return;

        document.getElementById('reminderEvent').value = '';
        document.getElementById('reminderDate').value = '';
        document.getElementById('reminderModalTitle').textContent = '添加提醒';
        document.getElementById('reminderForm').setAttribute('data-action', 'add');
        document.getElementById('reminderModal').style.display = 'block';
    }

    /**
     * 编辑提醒
     */
    editReminder() {
        // 检查结算状态
        if (!this.checkSettledStatus()) return;

        const event = window.headerReminderEvent || '';
        const date = window.headerReminderDate || '';

        document.getElementById('reminderEvent').value = event;
        document.getElementById('reminderDate').value = date;
        document.getElementById('reminderModalTitle').textContent = '编辑提醒';
        document.getElementById('reminderForm').setAttribute('data-action', 'edit');
        document.getElementById('reminderModal').style.display = 'block';
    }

    /**
     * 删除提醒
     */
    async deleteReminder() {
        // 检查结算状态
        if (!this.checkSettledStatus()) return;

        if (!confirm('确定要删除这个提醒吗？')) return;

        try {
            const response = await this.makeRequest(
                `${this.apiEndpoints.reminder}/${window.headerId}/reminder`,
                {},
                'DELETE'
            );

            if (response.success) {
                this.showMessage('提醒删除成功', 'success');
                setTimeout(() => window.location.reload(), 1000);
            } else {
                this.showMessage('删除失败: ' + response.message, 'error');
            }
        } catch (error) {
            this.showMessage('删除失败，请重试', 'error');
        }
    }

    /**
     * 关闭提醒模态框
     */
    closeReminderModal() {
        document.getElementById('reminderModal').style.display = 'none';
    }

    /**
     * 保存提醒
     */
    async saveReminder() {
        const action = document.getElementById('reminderForm').getAttribute('data-action');
        const reminderEvent = document.getElementById('reminderEvent').value.trim();
        const reminderDate = document.getElementById('reminderDate').value;
        
        if (!reminderEvent) {
            this.showMessage('请输入提醒事件', 'error');
            return;
        }
        
        if (!reminderDate) {
            this.showMessage('请选择提醒日期时间', 'error');
            return;
        }

        // 检查日期时间不能早于当前
        const now = new Date();
        const selectedDate = new Date(reminderDate);
        if (selectedDate < now) {
            this.showMessage('提醒时间不能早于当前时间', 'error');
            return;
        }
        
        try {
            const method = action === 'add' ? 'POST' : 'PUT';
            const response = await this.makeRequest(
                `${this.apiEndpoints.reminder}/${window.headerId}/reminder`,
                {
                    reminder_event: reminderEvent,
                    reminder_date: reminderDate
                },
                method
            );

            if (response.success) {
                this.showMessage(response.message, 'success');
                this.closeReminderModal();
                setTimeout(() => window.location.reload(), 1000);
            } else {
                this.showMessage('保存失败: ' + response.message, 'error');
            }
        } catch (error) {
            this.showMessage('保存失败，请重试', 'error');
        }
    }

    /**
     * 设置事件委托
     */
    setupEventDelegation() {
        // 快速创建EO
        document.addEventListener('click', (event) => {
            // 向上查找最近的带有 data-action 的元素
            const target = event.target.closest('[data-action]');
            if (!target) return;

            const action = target.getAttribute('data-action');

            if (action === 'quick-create-eo') {
                // 防止重复点击：检查按钮是否已禁用
                if (target.disabled || target.classList.contains('is-loading')) {
                    return;
                }
                const refId = target.getAttribute('data-ref-id');
                this.quickCreateEO(refId);
            }
        });

        // 模态框外部点击关闭
        document.addEventListener('click', (event) => {
            const modal = document.getElementById('reminderModal');
            if (event.target === modal) {
                this.closeReminderModal();
            }
        });
    }

    /**
     * 快速创建EO
     */
    async quickCreateEO(refId) {
        // 检查结算状态
        if (!this.checkSettledStatus()) return;

        // 找到对应的按钮
        const button = document.querySelector(`[data-action="quick-create-eo"][data-ref-id="${refId}"]`);
        if (!button) return;

        // 防止重复点击：检查是否正在处理中
        if (button.disabled || button.classList.contains('is-loading')) {
            return;
        }

        // 显示加载状态
        const originalHTML = button.innerHTML;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        button.disabled = true;
        button.classList.add('is-loading');

        try {
            const response = await this.makeRequest(
                this.apiEndpoints.quickCreateEO + '/' + refId,
                {},
                'POST'
            );

            if (response.success) {
                this.showMessage('EO编号生成成功', 'success');

                // 先获取行引用（在替换按钮之前）
                const row = button.closest('tr');

                // 局部更新：将按钮替换为EO编号链接
                if (response.eo_number && response.eo_id) {
                    const eoUrl = `/projects/eo/${response.eo_id}`;
                    const td = button.closest('td');
                    if (td) {
                        td.innerHTML = `
                            <a href="${eoUrl}" class="eo-number-link" title="点击查看EO详情">
                                <span class="badge bg-info">${response.eo_number}</span>
                            </a>
                        `;
                    }
                }

                // 隐藏该REF的删除按钮（生成EO后不能删除）
                if (row) {
                    const deleteBtn = row.querySelector('a.btn-danger[title="删除REF"]');
                    if (deleteBtn) {
                        deleteBtn.style.display = 'none';
                    }
                }
            } else {
                this.showMessage(response.message || '生成EO编号失败', 'error');
                // 恢复按钮状态
                button.innerHTML = originalHTML;
                button.disabled = false;
                button.classList.remove('is-loading');
            }
        } catch (error) {
            this.showMessage('网络错误，生成EO编号失败', 'error');
            // 恢复按钮状态
            button.innerHTML = originalHTML;
            button.disabled = false;
            button.classList.remove('is-loading');
        }
    }

    /**
     * 清理Flash消息
     */
    cleanupFlashMessages() {
        const flashMessages = document.querySelectorAll('.alert');
        flashMessages.forEach(alert => {
            const messageText = alert.textContent || alert.innerText;
            if (messageText.includes('机票REF保存成功')) {
                alert.style.display = 'none';
            }
        });
    }

    /**
     * 发送HTTP请求
     */
    async makeRequest(url, data = {}, method = 'POST') {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.csrfToken
            }
        };

        if (method !== 'GET' && Object.keys(data).length > 0) {
            options.body = JSON.stringify(data);
        }

        const response = await fetch(url, options);
        return await response.json();
    }

    /**
     * 显示消息提示
     */
    showMessage(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
        toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        toast.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(toast);
        
        // 3秒后自动消失
        setTimeout(() => {
            if (toast.parentNode) {
                toast.remove();
            }
        }, 3000);
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 设置全局变量供模板使用
    window.prevHeaderUrl = window.prevHeaderUrl || null;
    window.nextHeaderUrl = window.nextHeaderUrl || null;
    window.listUrl = window.listUrl || null;
    window.headerId = window.headerId || null;
    window.headerReminderEvent = window.headerReminderEvent || '';
    window.headerReminderDate = window.headerReminderDate || '';

    // 初始化项目管理器
    new ProjectDetailManager();
});
