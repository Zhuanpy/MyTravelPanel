import sys
import time

import pandas as pd
from pykeyboard import PyKeyboard

from utils_scalping import MouseKeyBoard, sent_email, key_inform, confirm_booking
from utils_scalping import flight_dic

pd.set_option('display.width', 5000)
pd.set_option('display.max_columns', None)

ult = MouseKeyBoard()
board = PyKeyboard()


def copyDataByPd():
    ult.click_page(146, 223)
    ult.ctrlA()
    ult.ctrlC()
    ult.click_page(146, 223)
    ult.pause_times(0.1)
    df = pd.read_clipboard()
    return df


def get_copy_data():
    ult.pause_times(1)
    ult.click_page(146, 223)

    ult.ctrlA()
    time.sleep(0.1)

    ult.ctrlC()
    time.sleep(0.1)

    ult.click_page(160, 240)
    seats = {}

    try:
        data = pd.read_clipboard()
        data = data.reset_index()
        li = data.values.tolist()

        if len(li) == 4 or len(li) == 5:

            for i in range(len(li)):

                l = li[i]

                for s in l:

                    try:
                        if len(s) == 2:
                            key_ = s[0]
                            value_ = int(s[1])

                            if value_ != 0:
                                seats[key_] = value_

                    except TypeError:
                        pass

                    except ValueError:
                        pass

    except Exception as ex:
        print(ex)
        pass

    return seats


class TravelSport:

    def __init__(self, ):

        try:
            with open('doc.txt') as f:
                lines = f.readlines()

            self.author = lines[0].split(':')[1]

        except FileNotFoundError:
            self.author = 'ZHUAN'

        self.data = None
        self.paxData = None  # self.data[self.data['additional'] == self.add]

        self.pause = 0
        self.sleeps = 0

        self.res_class = None  # 'Y'

        self.loc_num = None  # key 01Y1
        self.location = None  # key A@#1
        self.select = None
        #
        self.get_seats_num = 0
        self.copy_data = None
        self.key_name = False
        self.num_pending = 0
        self.book_num = 0
        self.airline = None

        self.departure = None  # pending.loc[i, 'Departure']
        self.date_ = None

        self.add = None  # pending.loc[i, 'additional']
        self.itinerary = None  # pending.loc[i, 'Itinerary']

    def paxs_docs(self, name, air, order):

        li = name.split('/')

        last = li[0]
        first = li[1]

        country = None
        p_num = None
        birth_date = None
        sex = None
        expire = None

        if len(li) == 7:
            country = li[2]
            p_num = li[3]
            birth_date = li[4]
            sex = li[5]
            expire = li[6]

        key_inform('>*R')
        key_inform(f'N.{last}/{first}')
        ult.pause_times(2)

        if p_num:
            key_inform('*R')
            ult.pause_times(1)

            inf = f'SI.P{order}/SSRDOCS{air[1:]}HK1/P/{country}/{p_num}/{country}/' \
                  f'{birth_date}/{sex}/{expire}/{last}/{first}'

            key_inform(inf)
            ult.pause_times(2)

    # 窗口1位置(255 188),window01;
    def check_action(self):
        ult.click_page(146, 223)
        ult.ctrlW()

        ult.pause_times(1)
        key_inform('I')

        ult.click_page(146, 223)
        ult.ctrlW()

        # key A27JUL SIN PVG*SQ
        itinerary = f'A{self.departure}{self.itinerary}{self.select}{self.airline}'  # A27JUL SIN PVG*SQ
        key_inform(itinerary)

        # key A@#1
        key_inform(self.location)
        ult.pause_times(0.5)

        seats = get_copy_data()

        return seats

    def book_action(self):

        if self.get_seats_num > self.num_pending:
            self.book_num = self.num_pending

        else:
            self.book_num = self.get_seats_num

        books = f'>0{self.book_num}{self.res_class}{self.loc_num}'  # 06Y1

        ult.click_homePage()
        ult.pause_times(0.1)
        key_inform(books)
        ult.pause_times(1)
        key_inform('*R')
        ult.pause_times(1)

    def key_name_action(self):

        confirms = []  # booked name list
        self.paxData = self.paxData.head(self.book_num)
        order = 1  # 输入名字
        for index in self.paxData.index:
            name = self.paxData.loc[index, 'Paxs']
            airline = self.paxData.loc[index, 'Airline']

            self.paxs_docs(name=name, air=airline, order=order)

            self.data.loc[index, 'Status'] = 'CONFIRM'

            order += 1

            confirms.append(name)

        author = 'ZHUAN'
        date_ = pd.Timestamp('today').strftime('%d%b')
        confirm_booking(author, date_)

        # Sent_email
        key_inform('*R')
        ult.pause_times(1)

        titles = f'Itinerary: {self.departure}, {self.itinerary}, {self.res_class},{self.get_seats_num}'.encode(
            'utf-8').strip()

        contents = f'{titles}\n\n{confirms}'

        sent_email(titles, contents)

        return confirms

    def windows_check_ticket(self):

        # 读取整理CSV数据
        waiting = pd.read_excel('WaitingList.xls')

        waiting['start'] = waiting['start'].dt.date
        waiting['end'] = waiting['end'].dt.date

        swipe_date = waiting[(waiting['Paxs'] == 'Swipe Date Range') & (waiting['Complete'] == 0)]

        flight_calendar = pd.read_excel('FlightCalendar.xls')

        pax_waiting = waiting[(waiting['Paxs'] != 'Swipe Date Range') & (waiting['Complete'] == 0)]
        # print(pax_waiting)
        # exit()
        print(swipe_date)
        # print(flight_calendar)
        exit()
        cal = pd.DataFrame()

        pending_data = pd.DataFrame()

        for index in swipe_date.index:
            swipe_itinerary = swipe_date.loc[index, 'Itinerary']
            swipe_start = pd.to_datetime(swipe_date.loc[index, 'start'])
            swipe_end = pd.to_datetime(swipe_date.loc[index, 'end'])
            swipe_class = swipe_date.loc[index, 'ResClass']
            swipe_loc = swipe_date.loc[index, 'Remark']

            """ 整理等待人数数据 """
            df = waiting[(waiting['Itinerary'] == swipe_itinerary) &
                         (waiting['start'] <= swipe_end) &
                         (waiting['end'] >= swipe_start) &
                         (waiting['Paxs'] != 'Swipe Date Range') &
                         (waiting['Complete'] == 0)]

            if not df.shape[0]:
                waiting.loc[index, 'Complete'] = 1
                waiting.to_excel('WaitingList.xls', sheet_name='Sheet1', index=False)
                continue

            df = df.sort_values(by=['Urgent'], ascending=False)
            pending_data = pd.concat([df, pending_data])

            """ 整理航班日历 """
            cal1 = flight_calendar[(flight_calendar['Itinerary'] == swipe_itinerary) &
                                   (flight_calendar['Date'] >= swipe_start) &
                                   (flight_calendar['Date'] <= swipe_end)].reset_index(drop=True)

            cal1.loc[:, 'ResClass'] = swipe_class
            cal1.loc[:, 'LocClass'] = swipe_loc

            cal = pd.concat([cal, cal1], ignore_index=True)

        if not cal.shape[0]:
            sys.exit()

        cal.loc[:, 'Date_'] = pd.to_datetime(cal['Date']).dt.strftime('%d%b')

        for i in cal.index:

            self.date_ = cal.loc[i, 'Date']  # 2022-07-09
            self.departure = cal.loc[i, 'Date_']  # 09JUL

            self.itinerary = cal.loc[i, 'Itinerary']
            self.airline = cal.loc[i, 'Airline']
            self.select = flight_dic[self.airline][0]
            self.location = flight_dic[self.airline][1]  # key A@#1

            self.loc_num = self.location[-1]  # key 01Y1

            self.res_class = cal.loc[i, 'ResClass']  # 'Y'

            # 判断是否需要输入名字

            seat_dic = self.check_action()

            pending_pax = pending_data[(pending_data['Itinerary'] == self.itinerary) &
                                       (pending_data['start'] <= self.date_) &
                                       (pending_data['end'] >= self.date_)]

            self.num_pending = pending_pax.shape[0]

            try:
                self.get_seats_num = seat_dic[self.res_class]
                print(f'Get Seats Number: {self.get_seats_num}')

            except KeyError:
                pass

            # 抓取舱位大于0 继续，否则退出
            if not self.get_seats_num:
                continue  # break & continue

            """ 订位 """
            self.book_action()  # 订位

            """ 查看 订位状态是 'HS' or 'LL', 抢位时 可能出现 LL 状态 """
            hs = copyDataByPd()
            hs = hs.columns[6][:2]

            if hs != 'HS':
                continue

            """ # 输入名字信息 """
            # names = self.key_name_action()
            confirms = []  # booked name list
            self.paxData = pending_pax.head(self.book_num)

            order = 1  # 输入名字
            for index in self.paxData.index:
                name = self.paxData.loc[index, 'Paxs']
                airline = self.paxData.loc[index, 'Airline']
                self.paxs_docs(name=name, air=airline, order=order)
                order += 1
                confirms.append(name)

            author = 'ZHUAN'
            date_ = pd.Timestamp('today').strftime('%d%b')
            confirm_booking(author, date_)

            """ Sent_email """
            key_inform('*R')
            ult.pause_times(1)

            titles = f'Itinerary: {self.departure}, {self.itinerary}, ' \
                     f'{self.res_class},{self.get_seats_num}'.encode('utf-8').strip()

            contents = f'{titles}\n\n{confirms}'

            sent_email(titles, contents)

            """ 保存数据 """
            con1 = waiting['Paxs'].isin(confirms)
            waiting.loc[con1, 'Complete'] = 1
            waiting.to_excel('WaitingList.xls', sheet_name='Sheet1', index=False)

            # 不输入名字 暂停15分钟
            if not self.key_name:
                time.sleep(1500)

            # 退出booking
            key_inform('I')

            break  # 退出当前循环,重新刷票

        ult.pause_times(self.pause)


if __name__ == '__main__':
    nums = 100

    # while nums:
    #
    # if nums == 100:
    #     time.sleep(5)

    run = TravelSport()
    run.windows_check_ticket()

    waiting = pd.read_excel('WaitingList.xls')
    waiting = waiting[(waiting['Paxs'] == 'Swipe Date Range') & (waiting['Complete'] == 0)]

    # nums = waiting.shape[0]

# 打包 pyinstaller -F E:\Python\Project\Air_ticket\Galilue_System\GALILUE_SYSTEM.py
# pyinstaller -F E:\Python\Project\Stock\Project_01\code\Dl_Strategy\Stock_RNN\code\FlightTicket\GALILUE_SYSTEM.py
