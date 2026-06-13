/**
 * 邮件正文富文本编辑器（基于 Quill）
 * 在模板编辑页和各发送邮件弹窗复用，输出内联样式 HTML（可在邮件客户端正常渲染）。
 *
 * 用法：
 *   var q = initEmailEditor('#emailBodyQuill', 'emailBody');
 *   q.setEmailBody(htmlOrText);   // 设置正文（纯文本会自动转换换行）
 * 编辑器内容会实时同步到隐藏的 textarea(#emailBody)，发送/提交时直接读取该 textarea。
 */
(function (global) {
    'use strict';

    // 字号、对齐改用内联样式（默认是 class，邮件里没有 Quill 的 CSS 会失效）
    function registerInlineStyles() {
        if (global.__emailQuillRegistered) return;
        var SizeStyle = Quill.import('attributors/style/size');
        SizeStyle.whitelist = ['12px', '14px', '16px', '18px', '24px', '32px'];
        Quill.register(SizeStyle, true);
        var AlignStyle = Quill.import('attributors/style/align');
        Quill.register(AlignStyle, true);
        global.__emailQuillRegistered = true;
    }

    function injectStyle() {
        if (document.getElementById('email-quill-style')) return;
        var st = document.createElement('style');
        st.id = 'email-quill-style';
        st.textContent =
            '.ql-editor{min-height:180px;font-family:Arial,sans-serif;font-size:14px;line-height:1.6;}' +
            '.ql-container{font-size:14px;}';
        document.head.appendChild(st);
    }

    function hasHtml(s) {
        return /<[a-z][\s\S]*>/i.test(s || '');
    }

    function toHtml(s) {
        if (!s) return '';
        return hasHtml(s) ? s : String(s).replace(/\n/g, '<br>');
    }

    global.initEmailEditor = function (editorSelector, textareaId) {
        if (typeof Quill === 'undefined') {
            // CDN 未加载：回退为可见的纯文本框，保证仍能编辑
            console.error('Quill 未加载，邮件正文回退为纯文本框');
            var taFallback = document.getElementById(textareaId);
            if (taFallback) {
                taFallback.classList.remove('d-none');
                if (!taFallback.getAttribute('rows')) taFallback.setAttribute('rows', '12');
                if (!taFallback.classList.contains('form-control')) taFallback.classList.add('form-control');
            }
            var editorEl = document.querySelector(editorSelector);
            if (editorEl) editorEl.style.display = 'none';
            return null;
        }
        registerInlineStyles();
        injectStyle();

        var ta = document.getElementById(textareaId);

        var quill = new Quill(editorSelector, {
            theme: 'snow',
            placeholder: '请输入邮件内容...',
            modules: {
                toolbar: [
                    [{ 'size': ['12px', '14px', false, '18px', '24px', '32px'] }],
                    ['bold', 'italic', 'underline'],
                    [{ 'color': [] }, { 'background': [] }],
                    [{ 'align': [] }],
                    [{ 'list': 'ordered' }, { 'list': 'bullet' }],
                    ['link', 'clean']
                ]
            }
        });

        // 用初始 textarea 内容做种子
        if (ta && ta.value) {
            quill.clipboard.dangerouslyPasteHTML(toHtml(ta.value));
        }

        // 编辑器 -> textarea 实时同步（空内容写入空串，避免 <p><br></p> 误判为有内容）
        function sync() {
            if (!ta) return;
            ta.value = quill.getText().trim() ? quill.root.innerHTML : '';
        }
        sync();
        quill.on('text-change', sync);

        // 对外提供设置正文的方法（替换变量、应用模板时调用）
        quill.setEmailBody = function (html) {
            quill.setText('');
            if (html) quill.clipboard.dangerouslyPasteHTML(toHtml(html));
            sync();
        };

        return quill;
    };
})(window);
