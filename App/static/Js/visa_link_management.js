function confirmDelete() {
    return confirm('Are you sure you want to delete this link?');
}

// 添加表单验证
document.addEventListener('DOMContentLoaded', function() {
    const visaForm = document.getElementById('visaForm');
    if (visaForm) {
        visaForm.addEventListener('submit', function(e) {
            const visaType = document.getElementById('visa_type').value.trim();
            const name = document.getElementById('name').value.trim();
            const link = document.getElementById('link').value.trim();

            if (!visaType || !name || !link) {
                e.preventDefault();
                alert('Please fill in all fields');
                return false;
            }

            if (!isValidUrl(link)) {
                e.preventDefault();
                alert('Please enter a valid URL');
                return false;
            }
        });
    }
});

// URL验证函数
function isValidUrl(url) {
    try {
        new URL(url);
        return true;
    } catch {
        return false;
    }
} 