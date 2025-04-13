import os
import pandas as pd
import logging

pd.set_option('display.max_columns', None)


class OriginalStatement:

    def __init__(self, UOB_path:str):

        self.file_path = os.path.join(UOB_path)
        self.expense_category = ["个人消费" , "个人商用", "LG", "JE"]

    def read_original_file(self):

        original_path = os.path.join(self.file_path, "原始下载")

        files = os.listdir(original_path)

        original_files = [file for file in files if file.endswith('.xls')]

        data = pd.DataFrame()

        for f in original_files:
            file_path = os.path.join(original_path, f)
            df = pd.read_excel(file_path, sheet_name="Sheet0", skiprows=7, engine='xlrd')
            data = pd.concat([data, df])

        data = data.rename(columns={"Available Balance": "Balance",
                                    "Transaction Description": "Description",
                                    "Transaction Date": "T-Date"})

        data["T-Date"] = pd.to_datetime(data["T-Date"]).dt.date

        data["Id"] = data["Description"].astype(str) + data["Balance"].astype(str)
        data["Id"] = data["Id"].str.replace('[\s\.\\/]', '', regex=True).str[-20:].str.lower()

        # 去除重复数据
        data = data.drop_duplicates(subset=["Id"]).reset_index(drop=True)

        return data

    def read_key_word(self, fies: str):
        keyword_path = os.path.join(self.file_path, "原始下载", "Keywords")
        p = os.path.join(keyword_path, f"{fies}.txt")
        f = open(p, 'r')
        keys = []
        for line in f.readlines():
            line = line.replace('\n', '')
            keys.append(line)

        keys = list(set(keys))  # 去重复元素
        return keys

    def key_words_data(self, data):

        use_by_myself = self.read_key_word("keyword_use_by_myself")  # ["PAYNOW-FAST", "MIXUE", "BUS/MRT"]

        use_by_business = self.read_key_word("keyword_use_use_by_business")

        keywords = use_by_myself + use_by_business
        keywords = list(set(keywords))

        def extract_keywords(row):
            text = row["Description"]
            found_keywords = [keyword for keyword in keywords if keyword in text]
            return ', '.join(found_keywords) if found_keywords else None

        # 应用函数并创建新列 D
        data['Keyword'] = data.apply(extract_keywords, axis=1)

        data.loc[data['Keyword'].isin(use_by_myself), 'User'] = '个人消费'
        data.loc[data['Keyword'].isin(use_by_business), 'User'] = 'Business'

        return data

    def organized_statement_data(self):

        original = self.read_original_file()

        original["T-Date"] = pd.to_datetime(original["T-Date"])

        original = original.sort_values(by=["T-Date"])

        original[["Keyword", "User", "EO", "Credit date"]] = None

        columns = ["T-Date", "Withdrawal", 'Deposit', "EO", "Credit date", "Keyword", "User", "Id", "Description"]

        original = original[columns]

        # 筛选转入账单数据
        original = original[original["Withdrawal"] != 0]

        # 去除转入数据
        original = original.drop(columns=['Deposit'])  # .reset_index(drop=True)
        original = original.dropna(subset=['Description']).reset_index(drop=True)

        # 去除已经整理的日期
        checked_path = os.path.join(self.file_path, "原始下载", "Keywords", "checked_date.txt")
        with open(checked_path, 'r', encoding='utf-8') as file:
            checked_date = file.read()

        # 确保 checked_date 是有效日期（更改的地方）
        checked_date = pd.to_datetime(checked_date, errors='coerce')
        if pd.isna(checked_date):
            logging.error(f"Invalid checked_date value: {checked_date}")
            return None

        # 按日期筛选数据
        original = original[original["T-Date"] > checked_date]

        # 提取 & 添加关键字列
        original = self.key_words_data(original)

        """ 筛选数据 """
        previous_path = os.path.join(self.file_path, "整理区别分类", "整理下载.xls")
        previous = pd.read_excel(previous_path, sheet_name="Sheet1", engine='openpyxl')

        previous["T-Date"] = pd.to_datetime(previous["T-Date"]).dt.date
        previous["Credit date"] = pd.to_datetime(previous["Credit date"]).dt.date

        latest_statement = original[~original["Id"].isin(previous["Id"])]

        if latest_statement.empty:
            logging.warning("无最整理账单；")
            return latest_statement

        """ 找出已核查日期并 保存 """
        checked_date = latest_statement['T-Date'].drop_duplicates().tolist()

        if len(checked_date) >= 2:
            # 获取并保存 倒数第二个值
            checked_date = checked_date[-2]
            checked_date = checked_date.isoformat()

            checked_path = os.path.join(self.file_path, "原始下载", "Keywords", "checked_date.txt")
            with open(checked_path, 'w', encoding='utf-8') as file:
                file.write(checked_date)

        """ 保存最新的整理账单"""
        latest_statement = pd.concat([previous, latest_statement])
        latest_statement.to_excel(previous_path, index=False, engine='openpyxl')

        return latest_statement

    def latest_LG_statement(self):

        """ 读取 statement """
        latest_path = os.path.join(self.file_path, "整理区别分类", "整理下载.xls")
        statement = pd.read_excel(latest_path, sheet_name="Sheet1", engine='openpyxl')

        statement = statement[(statement["EO"] != "/") &
                              (statement["User"] == "LG") &
                              (~statement["EO"].isnull())]

        statement["T-Date"] = pd.to_datetime(statement["T-Date"]).dt.date
        statement["Credit date"] = pd.to_datetime(statement["Credit date"]).dt.date

        """ 以前数据 """
        previous_path = os.path.join(self.file_path, "最新账单", "全部分类", "LG.xls")
        previous = pd.read_excel(previous_path, sheet_name="Sheet1", engine='openpyxl')
        previous["T-Date"] = pd.to_datetime(previous["T-Date"]).dt.date
        previous["Credit date"] = pd.to_datetime(previous["Credit date"]).dt.date

        """ 最新 statement """
        latest_statement = statement[~statement["Id"].isin(previous["Id"])].sort_values(by=["T-Date"])

        if latest_statement.empty:
            logging.warning("LG无最新账单;")
            return latest_statement

        # 保存 Excel 文件之前设置选项
        latest_statement = pd.concat([previous, latest_statement])
        latest_statement.to_excel(previous_path, index=False, engine='openpyxl')
        logging.warning("LG最新账单已更新;")
        return latest_statement

    def latest_JE_statement(self):

        """ 读取 statement """
        latest_path = os.path.join(self.file_path, "整理区别分类", "整理下载.xls")
        statement = pd.read_excel(latest_path, sheet_name="Sheet1", engine='openpyxl')

        statement = statement[(statement["User"] == "JE")]

        statement["T-Date"] = pd.to_datetime(statement["T-Date"]).dt.date
        statement["Credit date"] = pd.to_datetime(statement["Credit date"]).dt.date

        """ 以前数据 """
        previous_path = os.path.join(self.file_path, "最新账单", "全部分类", "JE.xls")
        previous = pd.read_excel(previous_path, sheet_name="Sheet1", engine='openpyxl')
        previous["T-Date"] = pd.to_datetime(previous["T-Date"]).dt.date
        previous["Credit date"] = pd.to_datetime(previous["Credit date"]).dt.date

        """ 最新 statement """
        latest_statement = statement[~statement["Id"].isin(previous["Id"])]

        if latest_statement.empty:
            logging.warning("JE无最新账单;")
            return latest_statement

        # 保存 Excel 文件之前设置选项
        latest_statement = pd.concat([previous, latest_statement])
        latest_statement.to_excel(previous_path, index=False, engine='openpyxl')
        logging.warning("JE最新账单已更新;")
        return latest_statement

    def latest_personal_expense_statement(self):
        """ 读取 statement """
        latest_path = os.path.join(self.file_path, "整理区别分类", "整理下载.xls")

        statement = pd.read_excel(latest_path, sheet_name="Sheet1", engine='openpyxl')


        statement = statement[(statement["User"] == "个人消费")]

        statement["T-Date"] = pd.to_datetime(statement["T-Date"]).dt.date
        statement["Credit date"] = pd.to_datetime(statement["Credit date"]).dt.date

        """ 以前数据 """
        previous_path = os.path.join(self.file_path, "最新账单", "全部分类", "个人消费.xls")
        previous = pd.read_excel(previous_path, sheet_name="Sheet1", engine='openpyxl')
        previous["T-Date"] = pd.to_datetime(previous["T-Date"]).dt.date
        previous["Credit date"] = pd.to_datetime(previous["Credit date"]).dt.date

        """ 最新 statement """
        latest_statement = statement[~statement["Id"].isin(previous["Id"])]

        if latest_statement.empty:
            logging.warning("<个人消费>无最新账单;")
            return latest_statement

        # 保存 Excel 文件之前设置选项
        latest_statement = pd.concat([previous, latest_statement])
        latest_statement.to_excel(previous_path, index=False, engine='openpyxl')
        logging.warning("<个人消费>最新账单已更新;")
        return latest_statement

    def latest_personal_business(self):
        """ 读取 statement """
        latest_path = os.path.join(self.file_path, "整理区别分类", "整理下载.xls")

        statement = pd.read_excel(latest_path, sheet_name="Sheet1", engine='openpyxl')

        statement = statement[(statement["User"] == "个人商用")]

        statement["T-Date"] = pd.to_datetime(statement["T-Date"]).dt.date
        statement["Credit date"] = pd.to_datetime(statement["Credit date"]).dt.date

        """ 以前数据 """
        previous_path = os.path.join(self.file_path, "最新账单", "全部分类", "个人商用.xls")
        previous = pd.read_excel(previous_path, sheet_name="Sheet1", engine='openpyxl')
        previous["T-Date"] = pd.to_datetime(previous["T-Date"]).dt.date
        previous["Credit date"] = pd.to_datetime(previous["Credit date"]).dt.date

        """ 最新 statement """
        latest_statement = statement[~statement["Id"].isin(previous["Id"])]

        if latest_statement.empty:
            logging.warning("<个人商用>无最新账单;")
            return latest_statement

        # 保存 Excel 文件之前设置选项
        latest_statement = pd.concat([previous, latest_statement])
        latest_statement.to_excel(previous_path, index=False, engine='openpyxl')
        logging.warning("<个人商用>最新账单已更新;")
        return latest_statement

    def statement_to_company(self):
        latest_path = os.path.join(self.file_path, "最新账单", "全部分类", "LG.xls")
        latest_statement = pd.read_excel(latest_path, sheet_name="Sheet1", engine='openpyxl')

        to_path = os.path.join(self.file_path, "最新账单", "ToLG", "ToCompany.xls")

        # print(f"to_path: {to_path}")
        to_company_statement = pd.read_excel(to_path, sheet_name="Sheet1", engine='openpyxl')

        latest_statement = latest_statement[~latest_statement["EO"].isin(to_company_statement["EO"])]

        if latest_statement.empty:
            logging.warning("无最新<LG>账单;")

            return latest_statement

        latest_statement = latest_statement[["T-Date", "Credit date", "EO", "Withdrawal", "Description"]]
        latest_statement["status"] = "pending"
        latest_statement = pd.concat([to_company_statement, latest_statement])
        latest_statement["T-Date"] = latest_statement["T-Date"].dt.date
        latest_statement["Credit date"] = latest_statement["Credit date"].dt.date

        latest_statement.to_excel(to_path, index=False, engine='openpyxl')

        return latest_statement

    def statement_to_LG(self):

        """存储一份给老板"""
        load_path = os.path.join(self.file_path, "最新账单", "ToLG", "ToCompany.xls")

        statement = pd.read_excel(load_path, sheet_name="Sheet1", engine='openpyxl')

        statement = statement[statement["status"] == "pending"].reset_index(drop=True)

        if statement.empty:
            logging.warning("<ToLG> 无最新账单;")
            return statement

        statement["T-Date"] = statement["T-Date"].dt.date
        statement["Credit date"] = statement["Credit date"].dt.date

        last_date = statement.iloc[-1]["T-Date"]

        Withdrawal_sum = statement["Withdrawal"].sum()
        text = f"Grand Total SGD：{Withdrawal_sum}; "

        statement.loc[len(statement)] = pd.Series(dtype='object')  # 在 DataFrame 最后插入一个空白行
        statement.loc[len(statement), "EO"] = text  # 在空白行后插入说明文字

        # 保存文件
        file_name = f"ZHANG ZHUAN UOB_{last_date}.xls"
        path = os.path.join(self.file_path, "最新账单", "ToLG", file_name)
        statement.to_excel(path, index=False, engine='openpyxl')
        logging.warning("<ToLG>账单已更新;")

    def statement_process(self) -> None:

        self.organized_statement_data()  # 原始账单整理

        self.latest_LG_statement()  # 公司账单整理

        self.latest_JE_statement()  # 个人账单整理

        self.latest_personal_business()  # 个人账单整理

        self.latest_personal_expense_statement()  # 个人账单整理

        self.statement_to_company()  # 给公司账单

        self.statement_to_LG()  # 发送给老板账单


if __name__ == '__main__':
    path = "E:\Project\MyTravelPanel\App\static\资源\账单\ZHANG ZHUAN UOB MASTER"
    uob = OriginalStatement(path)
    uob.statement_process()