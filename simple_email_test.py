# -*- coding: utf-8 -*-
"""简单邮件发送测试脚本"""

import os
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def test_email_sending():
    """测试邮件发送"""
    print("=" * 60)
    print("简单邮件发送测试")
    print("=" * 60)
    
    # 1. 检查环境变量
    print("\n1. 检查环境变量...")
    mail_server = os.environ.get('MAIL_SERVER')
    mail_port = os.environ.get('MAIL_PORT')
    mail_username = os.environ.get('MAIL_USERNAME')
    mail_password = os.environ.get('MAIL_PASSWORD')
    default_recipients = os.environ.get('DEFAULT_EMAIL_RECIPIENTS')
    
    print(f"   MAIL_SERVER: {mail_server}")
    print(f"   MAIL_PORT: {mail_port}")
    print(f"   MAIL_USERNAME: {mail_username}")
    print(f"   MAIL_PASSWORD: {'已设置' if mail_password else '未设置'}")
    print(f"   DEFAULT_EMAIL_RECIPIENTS: {default_recipients}")
    
    if not all([mail_server, mail_username, mail_password]):
        print("   ❌ 邮件配置不完整")
        return False
    
    # 2. 解析收件人
    print("\n2. 解析收件人...")
    if default_recipients:
        recipients = [email.strip() for email in default_recipients.split(',') if email.strip()]
    else:
        recipients = [mail_username]  # 如果没有配置收件人，发送给自己
    
    print(f"   收件人列表: {recipients}")
    
    # 3. 测试邮件连接
    print("\n3. 测试邮件连接...")
    try:
        server = smtplib.SMTP(mail_server, int(mail_port))
        server.starttls()
        server.login(mail_username, mail_password)
        print("   ✅ 邮件服务器连接成功")
        server.quit()
    except Exception as e:
        print(f"   ❌ 邮件服务器连接失败: {e}")
        return False
    
    # 4. 发送测试邮件
    print("\n4. 发送测试邮件...")
    success_count = 0
    failed_recipients = []
    
    for recipient in recipients:
        print(f"   发送到: {recipient}")
        try:
            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = mail_username
            msg['To'] = recipient
            msg['Subject'] = "MyTravelPanel 邮件功能测试"
            
            # 邮件正文
            body = f"""
尊敬的收件人，

这是一封来自 MyTravelPanel 系统的测试邮件。

测试时间: {os.popen('date').read().strip()}
发件人: {mail_username}
收件人: {recipient}

如果您收到这封邮件，说明邮件功能配置正确！

此邮件由系统自动发送，请勿回复。

---
MyTravelPanel 系统
            """
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # 发送邮件
            server = smtplib.SMTP(mail_server, int(mail_port))
            server.starttls()
            server.login(mail_username, mail_password)
            text = msg.as_string()
            server.sendmail(mail_username, recipient, text)
            server.quit()
            
            print(f"   ✅ 发送成功: {recipient}")
            success_count += 1
            
        except Exception as e:
            print(f"   ❌ 发送失败: {recipient} - {e}")
            failed_recipients.append(recipient)
    
    # 5. 测试结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    print(f"总收件人数: {len(recipients)}")
    print(f"发送成功: {success_count}")
    print(f"发送失败: {len(failed_recipients)}")
    
    if failed_recipients:
        print(f"失败的收件人: {', '.join(failed_recipients)}")
    
    if success_count > 0:
        print("\n🎉 邮件发送测试成功！")
        print("请检查您的邮箱（包括垃圾邮件文件夹）")
        return True
    else:
        print("\n❌ 邮件发送测试失败！")
        return False

def main():
    """主函数"""
    print("开始简单邮件发送测试...")
    
    try:
        success = test_email_sending()
        
        if success:
            print("\n✅ 测试完成！邮件功能正常工作")
        else:
            print("\n❌ 测试失败！请检查配置")
            
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()



