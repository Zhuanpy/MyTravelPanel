from flask import current_app
from flask_mail import Mail, Message

def send_email(subject, body):
    """
    发送邮件的通用函数
    使用配置文件中的邮件设置
    """
    try:
        mail = Mail(current_app)
        mail_config = current_app.config['MAIL_CONFIG']
        
        # 从配置中获取发件人信息
        sender = mail_config['DEFAULT_SENDER']
        sender_str = f"{sender['name']} <{sender['email']}>"
        
        # 从配置中获取收件人列表
        recipients = [r['email'] for r in mail_config['DEFAULT_RECIPIENTS'] if r['email']]
        cc = mail_config['CC_LIST']
        bcc = mail_config['BCC_LIST']
        
        if not recipients:
            print("没有配置收件人，无法发送邮件")
            return
        
        msg = Message(
            subject=subject,
            sender=sender_str,
            recipients=recipients,
            cc=cc,
            bcc=bcc,
            body=body
        )
        
        mail.send(msg)
        print(f"邮件发送成功: {subject}")
        
    except Exception as e:
        print(f"发送邮件时出错: {str(e)}")
        raise 