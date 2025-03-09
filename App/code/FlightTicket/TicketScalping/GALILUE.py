import sys
import time
import pandas as pd
from pykeyboard import PyKeyboard
from utils_scalping import sent_email, key_inform, confirm_booking
from utils_scalping import flight_dic
from utils_scalping import MouseKeyBoard as mkb

pd.set_option('display.width', 5000)
pd.set_option('display.max_columns', None)

board = PyKeyboard()


def copyDataByPd():
    mkb.click_page(146, 223)
    mkb.ctrlA()
    mkb.ctrlC()
    mkb.click_page(146, 223)
    mkb.pause_times(0.1)
    df = pd.read_clipboard()
    return df


def get_copy_data():
    mkb.pause_times(1)
    mkb.click_page(146, 223)

    mkb.ctrlA()
    time.sleep(0.1)

    mkb.ctrlC()
    time.sleep(0.1)

    mkb.click_page(160, 240)
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
        mkb.pause_times(2)

        if p_num:
            key_inform('*R')
            mkb.pause_times(1)

            inf = f'SI.P{order}/SSRDOCS{air[1:]}HK1/P/{country}/{p_num}' \
                  f'/{country}/{birth_date}/{sex}/{expire}/{last}/{first}'

            key_inform(inf)
            mkb.pause_times(2)

        return True

    # 窗口1位置(255 188),window01;
    def check_action(self):

        mkb.click_page(146, 223)
        mkb.ctrlW()

        mkb.pause_times(1)
        key_inform('I')

        mkb.click_page(146, 223)
        mkb.ctrlW()

        # key A27JUL SIN PVG*SQ
        itinerary = f'A{self.departure}{self.itinerary}{self.select}{self.airline}'  # A27JUL SIN PVG*SQ
        key_inform(itinerary)

        # key A@#1
        key_inform(self.location)
        mkb.pause_times(0.5)

        seats = get_copy_data()

        return seats

    def book_action(self):

        if self.get_seats_num > self.num_pending:
            self.book_num = self.num_pending

        else:
            self.book_num = self.get_seats_num

        books = f'>0{self.book_num}{self.res_class}{self.loc_num}'  # 06Y1

        mkb.click_homePage()
        mkb.pause_times(0.1)
        key_inform(books)
        mkb.pause_times(1)
        key_inform('*R')
        mkb.pause_times(1)

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
        date_ = pd.Timestamp.today().strftime('%d%b')

        # Sent_email
        key_inform('*R')
        mkb.pause_times(1)

        titles = f'Itinerary: {self.departure}, {self.itinerary}, {self.res_class},{self.get_seats_num}'.encode(
            'utf-8').strip()

        contents = f'{titles}\n\n{confirms}'

        sent_email(titles, contents)

        return confirms

    def windows_check_ticket(self):

        """ 整理数据 """
        # 读取整理CSV数据
        waiting = pd.read_excel('WaitingList.xls')

        waiting['start'] = waiting['start'].dt.date
        waiting['end'] = waiting['end'].dt.date

        """
        1 读取航班日历信息
        2 筛选日期，筛选出选定范围的日期
        """

        calendars = pd.read_excel('FlightCalendar.xls').dropna(subset=['Itinerary'])
        calendars['Date'] = calendars['Date'].dt.date
        range_date = waiting[(waiting['Paxs'] == 'Swipe Date Range') & (waiting['Complete'] == 0)]
        print(range_date)
        exit()
        for r in range_date.index:
            itin = range_date.loc[r, 'Itinerary']
            start_ = range_date.loc[r, 'start']
            end_ = range_date.loc[r, 'end']

            # pandas 删除特定条件下的行
            con1 = (calendars['Itinerary'] == itin)
            con2 = (calendars['Date'] < start_)
            con3 = (calendars['Date'] > end_)
            calendars = calendars.drop(calendars.loc[con1 & con2].index)
            calendars = calendars.drop(calendars.loc[con1 & con3].index)

        pax_waiting = waiting[(waiting['Paxs'] != 'Swipe Date Range') &
                              (waiting['Complete'] == 0)].dropna(subset=['Paxs'])
        cal = pd.DataFrame()

        for index in pax_waiting.index:

            itinerary_ = pax_waiting.loc[index, 'Itinerary']

            start_ = pd.to_datetime(pax_waiting.loc[index, 'start'])
            end_ = pd.to_datetime(pax_waiting.loc[index, 'end'])
            class_ = pax_waiting.loc[index, 'ResClass']

            """ 整理航班日历 """
            cal1 = calendars[(calendars['Itinerary'] == itinerary_) &
                             (calendars['Date'] >= start_) &
                             (calendars['Date'] <= end_)].reset_index(drop=True)

            if not cal1.shape[0]:
                continue
            cal1.loc[:, 'ResClass'] = class_
            cal = pd.concat([cal, cal1], ignore_index=True)

        if not cal.shape[0]:
            sys.exit()

        cal = cal.drop_duplicates(subset=['Itinerary', 'Date', 'ResClass']).reset_index(drop=True)
        cal['Date_'] = pd.to_datetime(cal['Date']).dt.strftime('%d%b')

        for i, row in cal.iterrows():
            self.date_ = row['Date']  # 2022-07-09
            self.departure = row['Date_']  # 09JUL
            self.itinerary = row['Itinerary']
            self.airline = row['Airline']

            self.select = flight_dic[self.airline][0]
            self.location = flight_dic[self.airline][1]  # key A@#1

            self.loc_num = self.location[-1]  # key 01Y1

            self.res_class = row['ResClass']  # 'Y'

            """判断是否需要输入名字"""
            seat_dic = self.check_action()

            pending_pax = waiting[(waiting['Itinerary'] == self.itinerary) &
                                  (waiting['start'] <= self.date_) &
                                  (waiting['end'] >= self.date_) &
                                  (waiting['Complete'] == 0) &
                                  (waiting['Paxs'] != 'Swipe Date Range')]

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
            confirms = []  # booked name list
            self.paxData = pending_pax.head(self.book_num)

            order = 1  # 输入名字
            for index, row_ in self.paxData.iterrows():
                name = row_['Paxs']
                airline = row_['Airline']
                self.paxs_docs(name=name, air=airline, order=order)
                order += 1
                confirms.append(name)

            author = 'ZHUAN'
            date_ = pd.Timestamp.today().strftime('%d%b')
            confirm_booking(author, date_)

            """ Sent_email """
            key_inform('*R')
            mkb.pause_times(1)

            titles = f'Itinerary: {self.departure}, {self.itinerary}, ' \
                     f'{self.res_class},{self.get_seats_num}'.encode('utf-8').strip()

            contents = f'{titles}\n\n{confirms}'

            sent_email(titles, contents)

            """ 保存数据 """
            con1 = waiting['Paxs'].isin(confirms)
            waiting.loc[con1, 'Complete'] = 1
            waiting.to_excel('WaitingList.xls', sheet_name='Sheet1', index=False)

            # 退出booking
            key_inform('I')

            break  # 退出当前循环,重新刷票

        mkb.pause_times(self.pause)


if __name__ == '__main__':

    nums = 100

    while nums:

        if nums == 100:
            time.sleep(5)

        run = TravelSport()
        run.windows_check_ticket()

        waiting = pd.read_excel('WaitingList.xls')
        waiting = waiting[(waiting['Paxs'] != 'Swipe Date Range') & (waiting['Complete'] == 0)]
        print(waiting)
        exit()
        nums = waiting.shape[0]

# 打包 pyinstaller -F E:\Python\Project\Air_ticket\Galilue_System\GALILUE_SYSTEM.py
# pyinstaller -F E:\Python\Project\Stock\Project_01\code\Dl_Strategy\Stock_RNN\code\FlightTicket\GALILUE_SYSTEM.py
