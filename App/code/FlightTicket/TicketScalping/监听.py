import smtplib
from email.message import Message
from pynput import mouse
import time
import os


def sent_email(title, content):
    smtpserver = 'smtp.gmail.com'
    username = 'legendtravel004@gmail.com'
    password = 'duooevejgywtaoka'
    from_addr = 'legendtravel004@gmail.com'
    toAddr = ['651748264@qq.com']
    ccAddr = ['zhangzhuan516@gmail.com']
    message = Message()
    message['Subject'] = f'my computer：{title}'  # 邮件标题
    message['From'] = from_addr
    message['To'] = ','.join(toAddr)
    message['Cc'] = ','.join(ccAddr)

    message.set_payload(content)  # 邮件正文
    msg = message.as_string().encode('utf-8')

    sm = smtplib.SMTP(smtpserver, port=587, timeout=20)
    sm.set_debuglevel(1)  # 开启debug模式
    sm.ehlo()
    sm.starttls()  # 使用安全连接
    sm.ehlo()
    sm.login(username, password)
    sm.sendmail(from_addr, (toAddr + ccAddr), msg)
    time.sleep(2)  # 避免邮件没有发送完成就调用了quit()
    sm.quit()


# 鼠标点击次数计数
click_count = 0


# 鼠标点击事件回调函数
def on_click(x, y, button, pressed):
    global click_count

    if pressed:
        click_count += 1

        print(f"当前点击次数: {click_count}")
        titles = f"当前点击次数: {click_count}"
        content = f"当前点击次数: {click_count}"
        # 如果点击次数在 5-9 次之间，发送提醒邮件
        if 5 <= click_count <= 9:
            sent_email(titles, content)
        # 如果点击次数超过 10 次，自动关机
        elif click_count >= 10:
            print("点击次数超过10次，电脑即将关机...")
            os.system("shutdown /s /t 1")  # Windows关机命令
            # os.system("sudo shutdown -h now")  # macOS/Linux关机命令


# 使用 pynput 监测鼠标事件
with mouse.Listener(on_click=on_click) as listener:
    listener.join()
