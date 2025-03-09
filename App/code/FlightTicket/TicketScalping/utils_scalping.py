from pymouse import *
from pykeyboard import PyKeyboard
import time
import smtplib
from email.message import Message
import cv2
import pyautogui

flight_dic = {"SQ": ["*", "A@#1"],
              "CZ": ["*", "A@#1"],
              "HO": ["*", "A@#1"],
              "MU": ["*", "A@#1"],
              "BG": ["/", "A@#1"],
              }


def screen_shot(name: str, path: str, size_=(0, 0, 1366, 768)):
    img = pyautogui.screenshot(region=[size_[0], size_[1], size_[2], size_[3]])  # x,y,w,h
    img.save(f'{path}/{name}')


def return_location(temp: str, path_='img'):
    target = 'shot.jpg'

    num = 0
    max_ = 0
    while num < 12:

        screen_shot(name=target, path=path_)
        target_ = f"{path_}/{target}"
        template_ = f"{path_}/{temp}"

        tar = cv2.imread(target_)
        temp_ = cv2.imread(template_)

        res = cv2.matchTemplate(tar, temp_, cv2.TM_CCORR_NORMED)

        min_, max_, min_loc, max_loc = cv2.minMaxLoc(res)

        if max_ < 0.99:
            num += 1
            time.sleep(0.25)

        if max_ >= 0.99:
            break

    return max_


def sent_email(title, content):
    smtpserver = 'smtp.gmail.com'
    username = 'legendtravel004@gmail.com'
    password = 'duooevejgywtaoka'
    from_addr = 'legendtravel004@gmail.com'
    # toAddr = ['legend.ticketing@gmail.com']
    toAddr = ['651748264@qq.com']
    # ccAddr = ['zhangzhuan516@gmail.com', 'legendtravel006@gmail.com', 'legend.ticking@gmail.com']
    # ccAddr = ['zhangzhuan516@gmail.com', 'legend.ticking@gmail.com', '']
    ccAddr = ['zhangzhuan516@gmail.com']
    message = Message()
    message['Subject'] = f'抓到票：{title}'  # 邮件标题
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


def key_inform(inf: str, s=0.1):
    pyk = PyKeyboard()
    pyk.type_string(inf)
    time.sleep(s)
    pyk.tap_key(pyk.enter_key)
    time.sleep(s)


def pause_times(pause):
    time.sleep(pause)
    mouse = PyMouse()
    (x, y) = mouse.position()

    if x < 30 and y < 30:

        val = input('输入continue继续: ')

        if val == 'continue' or 'CONTINUE':
            pass


def confirm_booking(author: str, date: str):
    # 输入F2，输入预定人名
    pyk = PyKeyboard()
    # mouse = PyMouse()
    pause_times(2)

    pyk.tap_key(pyk.function_keys[2])
    return_location('KeyAuthor.png')
    key_inform(author)
    pause_times(0.5)

    # 输入今天日期 例如：02SEP
    pyk.tap_key(pyk.function_keys[3])
    return_location('KeyDate.png')
    key_inform(date)

    # 确认订单 R.ZH; ER;
    key_inform('R.ZH')
    key_inform('ER')
    pause_times(0.5)
    key_inform('ER')


class MouseKeyBoard:
    stp = 0.1
    mouse = PyMouse()
    pyk = PyKeyboard()

    @classmethod
    def page_move(cls, star_x, star_y, end_x, end_y):  # 上下拖动网页功能
        cls.mouse.move(star_x, star_y)

        time.sleep(cls.stp)
        cls.mouse.press(star_x, star_y)
        time.sleep(cls.stp)

        cls.mouse.move(end_x, end_y)
        time.sleep(cls.stp)

        cls.mouse.click(end_x, end_y)
        time.sleep(cls.stp)

    @classmethod
    def click_page(cls, x, y):
        cls.mouse.click(x, y)
        time.sleep(cls.stp)

    @classmethod
    def click_homePage(cls):
        cls.click_page(146, 223)

    @classmethod
    def ctrlW(cls,):
        cls.pyk.press_key(cls.pyk.control_key)
        time.sleep(cls.stp)

        cls.pyk.tap_key('w')
        time.sleep(cls.stp)

        cls.pyk.release_key(cls.pyk.control_key)
        time.sleep(cls.stp)

    @classmethod
    def ctrlC(cls):
        cls.pyk.press_key(cls.pyk.control_key)
        time.sleep(cls.stp)

        cls.pyk.tap_key('c')
        time.sleep(cls.stp)

        cls.pyk.release_key(cls.pyk.control_key)
        time.sleep(cls.stp)

    @classmethod
    def ctrlV(cls):
        cls.pyk.press_key(cls.pyk.control_key)
        time.sleep(cls.stp)

        cls.pyk.tap_key('v')
        time.sleep(cls.stp)

        cls.pyk.release_key(cls.pyk.control_key)
        time.sleep(cls.stp)

    @classmethod
    def ctrlA(cls):
        cls.pyk.press_key(cls.pyk.control_key)
        time.sleep(cls.stp)

        cls.pyk.tap_key('a')
        time.sleep(cls.stp)

        cls.pyk.release_key(cls.pyk.control_key)
        time.sleep(cls.stp)

    @classmethod
    def pause_times(cls, pause):
        time.sleep(cls.stp)
        time.sleep(pause)
        (x, y) = cls.mouse.position()
        if x < 30 and y < 30:
            val = input('输入continue继续: ')

            if val == 'continue' or 'CONTINUE':
                pass

    @classmethod
    def clipboard_get(cls, ):
        time.sleep(cls.stp)
        try:  # 获取剪贴板数据

            import win32clipboard

            win32clipboard.OpenClipboard()

            try:
                text = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)

            except (TypeError, win32clipboard.error):

                try:
                    import py3compat
                    text = win32clipboard.GetClipboardData(win32clipboard.CF_TEXT)
                    text = py3compat.encode_filename(text)

                except (TypeError, win32clipboard.error):
                    text = None
                    pass

            finally:
                win32clipboard.CloseClipboard()

            return text

        except Exception as ex:
            print(f''' Getting text from the clipboard requires the pywin32,
                    extensions: http://sourceforge.net/projects/pywin32/;\nError:{ex}''')


if __name__ == '__main__':
    MouseKeyBoard.stp = 1
    MouseKeyBoard.ctrlA()
    pass
