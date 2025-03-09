from utils_scalping import MouseKeyBoard, confirm_booking, key_inform, pause_times, flight_dic
import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 5000)

ult = MouseKeyBoard()


def book_waiting_list():
    waitnum = 1

    while waitnum:

        waitinglist = pd.read_excel('WaitingList.xls')

        waitinglist['start'] = pd.to_datetime(waitinglist['start']).dt.date

        waitinglist['end'] = pd.to_datetime(waitinglist['end']).dt.date

        dup = ['ID', 'ResClass', 'Itinerary', 'start', 'end']
        waiting = waitinglist[(waitinglist['waitinglist'] == 0) &
                              (waitinglist['Paxs'] != 'Swipe Date Range')].drop_duplicates(subset=dup)

        calendars = pd.read_excel('FlightCalendar.xls')
        calendars['Date'] = pd.to_datetime(calendars['Date']).dt.date

        for x, waiting_row in waiting.iterrows():
            id_ = waiting_row['ID']
            start = waiting_row['start']
            end = waiting_row['end']
            itinerary = waiting_row['Itinerary']
            class_ = waiting_row['ResClass']  # 'ResClass'

            res_pax = waitinglist[(waitinglist['ID'] == id_) &
                                  (waitinglist['Itinerary'] == itinerary) &
                                  (waitinglist['ResClass'] == class_)]

            num_seat = res_pax.shape[0]

            calendar_ = calendars[(calendars['Itinerary'] == itinerary) &
                                  (calendars['Date'] >= start) &
                                  (calendars['Date'] <= end)]
            print(calendar_)
            pause_times(0.1)

            for i, calendar_row in calendar_.index:
                airline = calendar_row['Airline']
                date_ = calendar_row['Date'].strftime('%d%b')

                air_select = flight_dic[airline][0]
                keyItn = f'A{date_}{itinerary}{air_select}{airline}'  # A 21 AUG SIN SZX * SQ
                keySeat = f'0{num_seat}{class_}1'  # 01Y1

                ult.click_homePage()
                key_inform('I')
                pause_times(0.5)
                ult.ctrlW()
                pause_times(0.5)

                key_inform(keyItn, s=1)  # A21 AUG SIN SZX*SQ
                key_inform(keySeat)  # 02Y1

                """ key name """
                for k in res_pax.index:
                    paxname = res_pax.loc[k, 'Paxs']
                    keyName = f'N.{paxname}'  # N.LI/SI
                    key_inform(keyName)  # N.LI/SI

                """ confirm booking """
                author = 'ZHUAN'

                keyDate = pd.Timestamp('today').strftime('%d%b')
                confirm_booking(author, keyDate)

                key_inform('I')
                pause_times(1)
                ult.ctrlW()

            """ 更改 pending 状态"""
            con1 = (waitinglist['ID'] == id_)
            con2 = (waitinglist['Itinerary'] == itinerary)
            con3 = (waitinglist['ResClass'] == class_)
            waitinglist.loc[con1 & con2 & con3, 'waitinglist'] = 1

            """ 从新保存数据"""
            waitinglist.to_excel('WaitingList.xls', sheet_name='Sheet1', index=False)

        new = waitinglist[(~waitinglist['ID'].isnull()) & (waitinglist['waitinglist'] == 0)]
        waitnum = new.shape[0]


if __name__ == '__main__':
    book_waiting_list()
