import pandas as pd
import json
from pathlib import Path
from datetime import datetime as DT
import os
import talib
from FinMind.data import DataLoader
import datetime
import traceback
import numpy as np
import calendar
from datetime import timedelta
# ==================================================================
# 資料更新邏輯
# ==================================================================
def getMACD_OSC(df:pd.DataFrame)->pd.DataFrame:
    df["Close"] = pd.to_numeric(df["Close"], errors='coerce')
    df.dropna(subset=['Close'], inplace=True)
    close_prices = df['Close'].values
    macd, macd_signal, macd_hist = talib.MACD(
        close_prices, fastperiod=12, slowperiod=26, signalperiod=9
    )
    df['OSC'] = macd_hist
    return df

# TODO: 請將您原始的輔助函式程式碼填入以下佔位符中
def clean_Constract_Date(df:pd.DataFrame):
        """
        資料清洗

        Args:
            df (pd.DataFrame): 從FinMind取得的原始資料

        Returns:
            df (pd.DataFrame): 只有月結算的資料
        """
        df["ok_date"] = [ym if len(ym)==6 else pd.NA for ym in df["contract_date"]]
        df.dropna(how="any",axis=0,inplace=True)
        df.drop(["ok_date"],axis=1,inplace=True)
        df.reset_index(inplace=True,drop=True)
        return df

def get_TX_data(startDate:str,endDate:str,futuresId = 'TX')->pd.DataFrame:
        """
        從FinMind取得特定期貨的特定交易日期區間資料

        Args:
            startDate (str): 最早交易日期
            endDate (str): 最晚交易日期
            futuresId (str, optional): 期貨名稱, Defaults to 'TX'.

        Returns:
            df(pd.DataFrame): 從FinMind取得特定期貨的特定交易日期區間資料
        """
        api = DataLoader()
        df = api.taiwan_futures_daily(
            futures_id=futuresId,
            start_date=startDate,
            end_date=endDate,
        )
        df.columns = ['日期', 'futures_id', 'contract_date', 'Open', 'High', 'Low', 'Close',
            'spread', 'spread_per', 'Volume', 'settlement_price', 'open_interest',
            'trading_session']
        #print(df.columns)
        #df.to_excel(f"{futuresId}_{startDate}_{endDate}_info.xlsx")
        return df

def date_to_6num(date_dt:datetime.date):
        """將日期擷取為年4碼+當月2碼

        Args:
            date_dt (datetime.date): 交易日期

        Returns:
            (str): 轉換成當年當月
        """
        m = ""
        if len(str(date_dt.month)) == 1:
            m = "0"+str(date_dt.month)
        else:
            m = str(date_dt.month)
        return str(date_dt.year)+m

def date_to_6num_nextMonth(date_dt:datetime.date):
        """將日期擷取為年4碼+下個月2碼

        Args:
            date_dt (datetime.date): 交易日期

        Returns:
            (str): 下個月年月6碼
        """
        y = ""
        m = ""
        if len(str(date_dt.month)) == 1:
            y = str(date_dt.year)
            if str(date_dt.month) != "9":
                m = "0"+str(int(date_dt.month)+1)
            else:
                m = "10"
        else:
            if str(date_dt.month) != "12":
                y = str(date_dt.year)
                m = str(int(date_dt.month)+1)
            else:
                y = str(int(date_dt.year)+1)
                m = "01"
        return y+m

def date_to_6num_next2Month(date_dt:datetime.date):
        """將日期擷取為年4碼+下下個月2碼

        Args:
            date_dt (datetime.date): 交易日期

        Returns:
            (str): 下下個月年月6碼
        """
        y = ""
        m = ""
        if len(str(date_dt.month)) == 1:
            y = str(date_dt.year)
            if str(date_dt.month) != "8" and str(date_dt.month) != "9":
                m = "0"+str(int(date_dt.month)+1)
            elif str(date_dt.month) == "8":
                m = "10"
            elif str(date_dt.month) == "9":
                m = "11"
        else:
            if str(date_dt.month) != "11" and str(date_dt.month) != "12":
                y = str(date_dt.year)
                m = str(int(date_dt.month)+1)
            elif str(date_dt.month) == "11":
                y = str(int(date_dt.year)+1)
                m = "01"
            elif str(date_dt.month) == "12":
                y = str(int(date_dt.year)+1)
                m = "02"
        return y+m

def third_wednesday(year: int, month: int) -> datetime.date:
        """計算指定年份與月份的第三個星期三 也就是交割日"""
        # 獲取該月的所有星期三
        wednesdays = [day for day in range(1, 32) 
                    if day <= calendar.monthrange(year, month)[1] and datetime.date(year, month, day).weekday() == 2
                    ]
        
        # 返回第三個星期三
        return datetime.date(year, month, wednesdays[2])

def find_needed_third_wed(df:pd.DataFrame)->list[datetime.date]:
        """
        找到所有資料中，年份與月份的第三個星期三
        Args:
            df (pd.DataFrame): _description_

        Returns:
            list[datetime.date]: _description_
        """
        dates = df["日期"].tolist()
        weds = []
        for date in dates:
            year, month = date.year, date.month
            third_wed = third_wednesday(year, month)
            if third_wed not in weds:
                weds.append(third_wed)
        weds.sort()
        return weds

def get_1TF(self,df:pd.DataFrame):
        """
        擷取近一資料
        20250331更動：
        小時k的部分，
        結算日當日15:00前的是當月算近月，
        15:00後的下個月算近月

        Args:
            df (pd.DataFrame): 只有月結算的資料

        Returns:
            df_1tf (pd.DataFrame): 只有近月的資料
        """
        #cols = df.columns.tolist()
        df["日期"] = pd.to_datetime(df["日期"])
        df["time"] = pd.to_datetime(df["time"], format='%H:%M:%S').dt.time
        weds = self.find_needed_third_wed(df)
        tf_1_ym = []
        
        d = (df.loc[0,"日期"])
        for i in range(len(weds)):
            w_day = pd.to_datetime(weds[i])
            if d.year == w_day.year and d.month == w_day.month:
                break
        if d == w_day: #第三個周三(結算日)
            temp_time_line = DT.strptime('15:00:00', '%H:%M:%S').time()
            temp_df1 = df[df["time"]<temp_time_line]
            temp_df2 = df[df["time"]>=temp_time_line]
            tf_1_ym += [self.date_to_6num(d)]*len(temp_df1)
            tf_1_ym += [self.date_to_6num_nextMonth(d)]*len(temp_df2)
        else:
            for ind in range(len(df)):
                d = (df.loc[ind,"日期"])
                if d < w_day: #第三個周三以前
                    tf_1_ym.append(self.date_to_6num(d))
                elif d > w_day: #第三個周三以後(不含第三個周三)
                    tf_1_ym.append(self.date_to_6num_nextMonth(d))
        
        df["近一年月"] = tf_1_ym
        df_1tf = df[df["近一年月"]==df["contract_date"]]
        #df_1tf = df_1tf[cols]
        df_1tf.reset_index(inplace=True,drop=True)
        return df_1tf

def add_hour_to_time(time_obj):
        """
        將時間增加一小時，處理跨夜情況
        """
        dt = DT.combine(DT.today(), time_obj) + timedelta(hours=1)
        return dt.time()

def add_15min_to_time(time_obj):
        """
        將時間增加15分鐘，處理跨夜情況
        """
        dt = DT.combine(DT.today(), time_obj) + timedelta(minutes=15)
        return dt.time()
    
def split_data_by_time_ranges_15min(df, time_column='time'):
        """
        將資料按照指定的時間範圍分割
        """
        # 確保時間欄位是datetime格式
        df['time_obj'] = pd.to_datetime(df[time_column], format='%H:%M:%S').dt.time
        
        # 定義兩個大的時間範圍
        range1_start = DT.strptime('00:00:00', '%H:%M:%S').time()
        range1_end = DT.strptime('05:00:00', '%H:%M:%S').time()
        
        range2_start = DT.strptime('08:45:00', '%H:%M:%S').time()
        range2_end = DT.strptime('13:45:00', '%H:%M:%S').time()
        
        range3_start = DT.strptime('15:00:00', '%H:%M:%S').time()
        range3_end = DT.strptime('00:00:00', '%H:%M:%S').time()
        
        # 創建空字典來存儲結果
        result_parts = {
            'part1': [],  # 00:00 - 05:00
            'part2': [],   # 08:45 - 13:45
            'part3': []   # 15:00 - 00:00
        }
        
        # 創建小時間範圍的空列表
        #result_hourly = []
        result_every15min = []
        time_tick = []
        
        # 處理第一個時間範圍 (00:00 - 05:00)
        current_time = range1_start
        for i in range(20):  # 5小時*4個15分鐘 = 20
            next_time = add_15min_to_time(current_time)
            time_tick.append(f"{current_time}~{next_time}")
            # 為跨小時的時間範圍篩選資料
            if current_time < next_time:
                mask = (df['time_obj'] >= current_time) & (df['time_obj'] < next_time)
            else:  # 處理跨夜情況
                mask = (df['time_obj'] >= current_time) | (df['time_obj'] < next_time)
            
            # 存儲這一小時的資料
            every_15min_data = df[mask].copy()
            result_every15min.append(every_15min_data)
            #result_parts['part1'].append(hourly_data)
            
            # 更新下一個時間範圍的起始時間
            current_time = next_time
        
        # 處理第二個時間範圍 (8:45 - 13:45)
        current_time = range2_start
        for i in range(20):  # 5小時*4個15分鐘 = 20
            next_time = add_15min_to_time(current_time)
            time_tick.append(f"{current_time}~{next_time}")
            # 為跨小時的時間範圍篩選資料
            if current_time < next_time:
                mask = (df['time_obj'] >= current_time) & (df['time_obj'] < next_time)
            else:  # 處理跨夜情況
                mask = (df['time_obj'] >= current_time) | (df['time_obj'] < next_time)
            
            # 存儲這一小時的資料
            every_15min_data = df[mask].copy()
            result_every15min.append(every_15min_data)
            #result_parts['part2'].append(hourly_data)
            
            # 更新下一個時間範圍的起始時間
            current_time = next_time
        
        # 處理第三個時間範圍 (15:00 - 00:00)
        current_time = range3_start
        for i in range(36):  # 9小時*4個15分鐘 = 36
            next_time = add_15min_to_time(current_time)
            time_tick.append(f"{current_time}~{next_time}")
            # 為跨小時的時間範圍篩選資料
            if current_time < next_time:
                mask = (df['time_obj'] >= current_time) & (df['time_obj'] < next_time)
            else:  # 處理跨夜情況
                mask = (df['time_obj'] >= current_time) | (df['time_obj'] < next_time)
            
            # 存儲這一小時的資料
            every_15min_data = df[mask].copy()
            result_every15min.append(every_15min_data)
            #result_parts['part3'].append(hourly_data)
            
            # 更新下一個時間範圍的起始時間
            current_time = next_time
        
        return result_every15min, time_tick

def split_data_by_time_ranges_hour(df, time_column='time'):
        """
        將資料按照指定的時間範圍分割
        """
        # 確保時間欄位是datetime格式
        df['time_obj'] = pd.to_datetime(df[time_column], format='%H:%M:%S').dt.time
        
        # 定義兩個大的時間範圍
        range1_start = DT.strptime('00:00:00', '%H:%M:%S').time()
        range1_end = DT.strptime('05:00:00', '%H:%M:%S').time()
        
        range2_start = DT.strptime('08:45:00', '%H:%M:%S').time()
        range2_end = DT.strptime('13:45:00', '%H:%M:%S').time()
        
        range3_start = DT.strptime('15:00:00', '%H:%M:%S').time()
        range3_end = DT.strptime('00:00:00', '%H:%M:%S').time()
        
        # 創建空字典來存儲結果
        result_parts = {
            'part1': [],  # 00:00 - 05:00
            'part2': [],   # 08:45 - 13:45
            'part3': []   # 15:00 - 00:00
        }
        
        # 創建小時間範圍的空列表
        result_hourly = []
        time_tick = []
        
        # 處理第一個時間範圍 (00:00 - 05:00)
        current_time = range1_start
        for i in range(5):  # 5小時
            next_time = add_hour_to_time(current_time)
            time_tick.append(f"{current_time}~{next_time}")
            # 為跨小時的時間範圍篩選資料
            if current_time < next_time:
                mask = (df['time_obj'] >= current_time) & (df['time_obj'] < next_time)
            else:  # 處理跨夜情況
                mask = (df['time_obj'] >= current_time) | (df['time_obj'] < next_time)
            
            # 存儲這一小時的資料
            hourly_data = df[mask].copy()
            result_hourly.append(hourly_data)
            result_parts['part1'].append(hourly_data)
            
            # 更新下一個時間範圍的起始時間
            current_time = next_time
        
        # 處理第二個時間範圍 (8:45 - 13:45)
        current_time = range2_start
        for i in range(5):  # 5小時
            next_time = add_hour_to_time(current_time)
            time_tick.append(f"{current_time}~{next_time}")
            # 為跨小時的時間範圍篩選資料
            if current_time < next_time:
                mask = (df['time_obj'] >= current_time) & (df['time_obj'] < next_time)
            else:  # 處理跨夜情況
                mask = (df['time_obj'] >= current_time) | (df['time_obj'] < next_time)
            
            # 存儲這一小時的資料
            hourly_data = df[mask].copy()
            result_hourly.append(hourly_data)
            result_parts['part2'].append(hourly_data)
            
            # 更新下一個時間範圍的起始時間
            current_time = next_time
        
        # 處理第三個時間範圍 (15:00 - 00:00)
        current_time = range3_start
        for i in range(9):  # 9小時
            next_time = add_hour_to_time(current_time)
            time_tick.append(f"{current_time}~{next_time}")
            # 為跨小時的時間範圍篩選資料
            if current_time < next_time:
                mask = (df['time_obj'] >= current_time) & (df['time_obj'] < next_time)
            else:  # 處理跨夜情況
                mask = (df['time_obj'] >= current_time) | (df['time_obj'] < next_time)
            
            # 存儲這一小時的資料
            hourly_data = df[mask].copy()
            result_hourly.append(hourly_data)
            result_parts['part3'].append(hourly_data)
            
            # 更新下一個時間範圍的起始時間
            current_time = next_time
        
        return result_parts, result_hourly, time_tick

def update_data_files():
        print("正在更新資料...")
        api = DataLoader()
        with open("token_.txt") as token_file:
            token = token_file.read()

        api.login_by_token(api_token=token)
        
        df_hour_k = pd.read_excel("小時k.xlsx")
        df_15min_k = pd.read_excel("15分k.xlsx")
        #檢查日期是否有到今天
        now_date = DT.today()
        now_date = now_date.strftime("%Y-%m-%d")
        hour_k_date = df_hour_k["日期"].iloc[-1].strftime("%Y-%m-%d")
        min_k_date = df_15min_k["日期"].iloc[-1].strftime("%Y-%m-%d")
        if hour_k_date <= now_date or min_k_date <= now_date: #如果是當天的資料也要更新，因為不知道會不會只更新一半
            ## 先產生日期list，格式yyyy-mm-dd
            start_date = hour_k_date if hour_k_date<min_k_date else min_k_date
            end_date = now_date#"#datetime.today().strftime("%Y-%m-%d")
            date_ls = pd.date_range(start_date,end_date).strftime("%Y-%m-%d").tolist()
            ## 使用 期貨交易明細 API
            all_df_hour_ls = []
            all_df_15min_ls = []
            for date in date_ls:
                #抓資料
                df = api.taiwan_futures_tick(
                futures_id='TX',
                date=date
                )
                if df.empty:
                    continue
                df["日期"] = pd.to_datetime(df["date"].str.split(" ").str[0])
                df["日期"] = pd.to_datetime(df["日期"],format="%Y-%m-%d").dt.date
                df["time"] = df["date"].str.split(" ").str[1]
                df["time"] = pd.to_datetime(df["time"],format="%H:%M:%S").dt.time
                #取得近月資料
                df = clean_Constract_Date(df)
                df = get_1TF(df)
                
                #取得以小時為間隔的資料
                result_parts, result_hourly, time_ticks = split_data_by_time_ranges_hour(df)

                new_data = []
                ind = 0
                for temp_df in result_hourly:
                    temp_data = []
                    if temp_df.empty:
                        ind+=1
                        print("該時段無交易")
                        continue
                    temp_data.append(temp_df["日期"].iloc[0])
                    temp_data.append(time_ticks[ind])
                    temp_data.append(temp_df["price"].iloc[0])
                    temp_data.append(temp_df["price"].max())
                    temp_data.append(temp_df["price"].min())
                    temp_data.append(temp_df["price"].iloc[-1])
                    #temp_data.append(len(temp_df))
                    #temp_data.append(temp_df["volume"].sum())
                    #temp_data.append(round(temp_df["volume"].sum()/1000))
                    #print(temp_data)
                    new_data.append(temp_data)
                    ind+=1
                #new_df = pd.DataFrame(new_data,columns=["時間","開盤價","收盤價","最高價","最低價","成交筆數","成交量(股)","成交量(張)"])
                new_df = pd.DataFrame(new_data,columns=["日期","時間區間","Open","High","Low","Close"])
                print(new_df)
                all_df_hour_ls.append(new_df)
                print("="*50)
                
                #取得以15分為間隔的資料
                result_per15min, time_ticks = split_data_by_time_ranges_15min(df)

                new_data = []
                ind = 0
                for temp_df in result_per15min:
                    temp_data = []
                    if temp_df.empty:
                        ind+=1
                        print("該時段無交易")
                        continue
                    temp_data.append(temp_df["日期"].iloc[0])
                    temp_data.append(time_ticks[ind])
                    temp_data.append(temp_df["price"].iloc[0])
                    temp_data.append(temp_df["price"].max())
                    temp_data.append(temp_df["price"].min())
                    temp_data.append(temp_df["price"].iloc[-1])
                    #temp_data.append(len(temp_df))
                    #temp_data.append(temp_df["volume"].sum())
                    #temp_data.append(round(temp_df["volume"].sum()/1000))
                    #print(temp_data)
                    new_data.append(temp_data)
                    ind+=1
                new_df = pd.DataFrame(new_data,columns=["日期","時間區間","Open","High","Low","Close"])
                print(new_df)
                all_df_15min_ls.append(new_df)
                print("="*50)
                
            all_df_hour = pd.concat(all_df_hour_ls,axis=0)
            print(all_df_hour.info())
            df_hour = all_df_hour.copy()
            #取舊資料的尾端60筆與新資料concat
            df_hour_k = df_hour_k[df_hour_k["日期"]<start_date]
            df_hour_k_last3days = df_hour_k.iloc[-60:]
            temp_hour_df = pd.concat([df_hour_k_last3days,df_hour],axis=0)
            temp_hour_df.reset_index(inplace=True,drop=True)
            temp_hour_df = getMACD_OSC(temp_hour_df)
            print(df.info())
            temp_hour_df = temp_hour_df[temp_hour_df["日期"]>=start_date]
            df_hour_k_new = pd.concat([df_hour_k,temp_hour_df],axis=0)
            df_hour_k_new.reset_index(inplace=True,drop=True)
            print(df_hour_k_new.info())
            df_hour_k_new.to_excel("小時k.xlsx",index=False)
            
            all_df_15min = pd.concat(all_df_15min_ls,axis=0)
            print(all_df_15min.info())
            df_15min = all_df_15min.copy()
            #取舊資料的尾端60筆與新資料concat
            df_15min_k = df_15min_k[df_15min_k["日期"]<start_date]
            df_15min_k_last3days = df_15min_k.iloc[-60:]
            temp_15min_df = pd.concat([df_15min_k_last3days,df_15min],axis=0)
            temp_15min_df.reset_index(inplace=True,drop=True)
            temp_15min_df = getMACD_OSC(temp_15min_df)
            print(df.info())
            temp_15min_df = temp_15min_df[temp_15min_df["日期"]>=start_date]
            df_15min_k_new = pd.concat([df_15min_k,temp_15min_df],axis=0)
            df_15min_k_new.reset_index(inplace=True,drop=True)
            print(df_15min_k_new.info())
            df_15min_k_new.to_excel("15分k.xlsx",index=False)
            
            return all_df_15min_ls[-1]["日期"][0]
        else:
            return all_df_15min_ls[-1]["日期"][0]
    
# ==================================================================
# 回測策略邏輯 (已重構並加入日誌紀錄)
# ==================================================================

class Strategy:
    """封裝所有回測策略的核心計算邏輯。"""
    def __init__(self, settings_config: dict):
        self.settings = settings_config
        for key, value in settings_config.items():
            setattr(self, key, value)
        
        self.principal = float(self.settings.get('principal', 350000))
        
        if 'all_time_settings' in self.settings:
            self.all_time_settings = self.settings['all_time_settings']
        else:
            self.all_time_settings = self.load_all_settings()

    def run_backtest(self, df: pd.DataFrame, start_date: str, end_date: str) -> dict:
        try:
            print("開始執行回測...")
            df_filtered = df[(df["日期"] >= pd.to_datetime(start_date)) & (df["日期"] <= pd.to_datetime(end_date))].copy()
            df_filtered.reset_index(inplace=True, drop=True)
            
            if df_filtered.empty:
                return {"error": "在指定日期範圍內沒有數據。"}

            print("開始執行 find_pos...")
            df_result = self.find_pos(df_filtered)
            print("完成 find_pos。")
            
            print("開始執行 read_position...")
            df_result = self.read_position(df_result)
            print("完成 read_position。")

            print("開始執行 decide_position...")
            df_result = self.decide_position(df_result)
            print("完成 decide_position。")

            print("開始執行 getIncome...")
            df_result = self.getIncome(df_result)
            print("完成 getIncome。")

            df_result["訊號"] = [s[:-1] if isinstance(s, str) and s.endswith("＆") else s for s in df_result["訊號"]]
            
            print("開始執行報表生成...")
            signal_df = self.getSignalDetail(df_result)
            trade_df = self.getTradeDetail(df_result, self.principal)
            print("完成報表生成。")
            
            print("開始計算最終統計數據...")
            stats = {
                "時間級別": self.timelevel,
                "淨利($)": self.getNetIncome(df_result),
                "淨利(%)": self.getNetIncomePercent(trade_df),
                "平均獲利\n虧損比($)": self.getIncomeRatio(df_result),
                "平均獲利\n虧損比(%)": self.getIncomePercentRatio(trade_df),
                "最大區間虧損($)": self.getIntervalDebt(trade_df),
                "最大區間虧損(%)": self.getIntervalPercentDebt(trade_df),
            }
            print("回測成功！")
            return {
                "summary_stats": stats, "signal_df": signal_df,
                "trade_df": trade_df, "full_df": df_result
            }
        except Exception as e:
            print(f"回測過程中發生嚴重錯誤: {traceback.format_exc()}")
            return {"error": f"回測邏輯執行失敗: {e}"}

    def find_pos(self,df:pd.DataFrame)->pd.DataFrame:
        # 使用向量化操作尋找波峰波谷
        df['OSC_shifted1'] = df['OSC'].shift(1)
        df['OSC_shifted-1'] = df['OSC'].shift(-1)
        
        conditions_top = (df['OSC'] > df['OSC_shifted1']) & (df['OSC'] > df['OSC_shifted-1'])
        conditions_bot = (df['OSC'] < df['OSC_shifted1']) & (df['OSC'] < df['OSC_shifted-1'])

        df['OSC波峰波谷'] = np.select(
            [conditions_top, conditions_bot], 
            ['波峰', '波谷'], 
            default=''
        ).astype(str)
        
        df.drop(['OSC_shifted1', 'OSC_shifted-1'], axis=1, inplace=True)
        
        # 波峰波谷後移一天
        df['OSC波峰波谷'] = df['OSC波峰波谷'].shift(1).fillna('')
        
        df["3根k棒波峰最高價"] = df['High'].rolling(window=3, min_periods=1).max().shift(-2)
        df["3根k棒波谷最低價"] = df['Low'].rolling(window=3, min_periods=1).min().shift(-2)
        
        df.loc[df['OSC波峰波谷'] != '波峰', '3根k棒波峰最高價'] = np.nan
        df.loc[df['OSC波峰波谷'] != '波谷', '3根k棒波谷最低價'] = np.nan
        return df
        
    def read_position(self,df:pd.DataFrame)->pd.DataFrame:
        df["訊號"] = ""
        
        peaks = df[df['OSC波峰波谷'] == '波峰'].copy()
        troughs = df[df['OSC波峰波谷'] == '波谷'].copy()

        if not peaks.empty and len(peaks) > 1 and self.top_ck:
            print("[read_position] 正在尋找頂背離...")
            peaks['prev_OSC'] = peaks['OSC'].shift(1)
            peaks['prev_High'] = peaks['3根k棒波峰最高價'].shift(1)
            cond1 = (peaks['prev_OSC'] > peaks['OSC']) & (peaks['prev_High'] < peaks['3根k棒波峰最高價'])
            df.loc[peaks[cond1].index, '訊號'] += '頂背離＆'

        if not troughs.empty and len(troughs) > 1 and self.bot_ck:
            print("[read_position] 正在尋找底背離...")
            troughs['prev_OSC'] = troughs['OSC'].shift(1)
            troughs['prev_Low'] = troughs['3根k棒波谷最低價'].shift(1)
            cond1 = (troughs['prev_OSC'] < troughs['OSC']) & (troughs['prev_Low'] > troughs['3根k棒波谷最低價'])
            df.loc[troughs[cond1].index, '訊號'] += '底背離＆'

        df['訊號'] = df['訊號'].shift(1).fillna('')
        
        print("[read_position] 正在處理止損...")
        position = 0
        stop_price = 0
        for i in range(1, len(df)):
            signal = df.loc[i, '訊號']
            if '頂背離' in signal and self.top_stop_ck:
                position = -1; stop_price = df.loc[i-1, '3根k棒波峰最高價']
            elif '底背離' in signal and self.bot_stop_ck:
                position = 1; stop_price = df.loc[i-1, '3根k棒波谷最低價']
            
            if position == -1 and df.loc[i, 'Close'] > stop_price:
                df.loc[i, '訊號'] = '頂背離止損'; position = 0; stop_price = 0
            elif position == 1 and df.loc[i, 'Close'] < stop_price:
                df.loc[i, '訊號'] = '底背離止損'; position = 0; stop_price = 0
        return df
    
    def decide_position(self,df:pd.DataFrame)->pd.DataFrame:
        pos = 0
        pos_ls = []
        for i, row in df.iterrows():
            signal = str(row["訊號"])
            can_enter = True
            if self.enter_time_check and i + 1 < len(df):
                time_str = df.loc[i+1,"時間區間"].split('~')[0]
                if "頂背離" in signal:
                    can_enter = self.checkTimeInSlots(time_str, self.readCertainTimeLimit(f"{self.timelevel} - 做空"))
                elif "底背離" in signal:
                    can_enter = self.checkTimeInSlots(time_str, self.readCertainTimeLimit(f"{self.timelevel} - 做多"))

            if can_enter:
                if "頂背離止損" in signal and pos < 0: pos = 0
                elif "底背離止損" in signal and pos > 0: pos = 0
                elif "頂背離" in signal: pos = -1
                elif "底背離" in signal: pos = 1
            pos_ls.append(pos)
        
        df["position"] = pos_ls
        df["trade_action"] = df["position"].diff().fillna(0) != 0
        df["當時開盤價"] = np.where(df["trade_action"], df["Open"], np.nan)
        df.drop(["trade_action"], axis=1, inplace=True)
        return df

    def getIncome(self,df:pd.DataFrame):
        df_trades = df[df['當時開盤價'].notna()].copy()
        if len(df_trades) < 2:
            df['income($)'] = 0
            return df

        df_trades['prev_price'] = df_trades['當時開盤價'].shift(1)
        df_trades['prev_pos'] = df_trades['position'].shift(1)
        
        is_closing_trade = (df_trades['position'] == 0) & (df_trades['prev_pos'] != 0)
        is_reversing_trade = (df_trades['position'] * df_trades['prev_pos'] < 0)

        df_trades['income'] = np.where(
            is_closing_trade | is_reversing_trade,
            (df_trades['當時開盤價'] - df_trades['prev_price']) * df_trades['prev_pos'] * -200,
            0
        )
        
        df = df.merge(df_trades[['income']], left_index=True, right_index=True, how='left')
        df.rename(columns={'income': 'income($)'}, inplace=True)
        df['income($)'].fillna(0, inplace=True)
        return df

    # 其他輔助函式
    def getNetIncome(self,df:pd.DataFrame): return round(df["income($)"].sum())
    def getSumOfCertainCondition(self,val_ls,state:str):
        if state == '+': return [v for v in val_ls if pd.notna(v) and v > 0]
        return [v for v in val_ls if pd.notna(v) and v <= 0]
    def getIncomeRatio(self,df:pd.DataFrame):
        pos = sum(self.getSumOfCertainCondition(df["income($)"].tolist(), '+'))
        neg = sum(self.getSumOfCertainCondition(df["income($)"].tolist(), '-'))
        return round(abs(pos/neg),2) if neg != 0 else "-"
    def getSignalDetail(self,df:pd.DataFrame):
        data = []
        for i, row in df[df['訊號'] != ''].iterrows():
            if i + 1 >= len(df): continue
            data.append([DT.now().strftime("%H:%M:%S"), "台股指數近月", "交易指令", f"部位:{row['position']}->{df.loc[i+1,'position']} (訊號:{row['訊號']})"])
        return pd.DataFrame(data, columns=["時間","商品","動作","內容"])
    def getTradeDetail(self,df:pd.DataFrame,principal:float):
        trades = df[df['income($)'] != 0].copy()
        if trades.empty: return pd.DataFrame()
        trades.reset_index(inplace=True)
        trades['序號'] = trades.index + 1
        trades['累計獲利金額'] = trades['income($)'].cumsum()
        trades['報酬率(%)'] = round((trades['income($)'] / principal) * 100, 2)
        trades['累計報酬率(%)'] = round((trades['累計獲利金額'] / principal) * 100, 2)
        # ... 補齊其他欄位
        return trades
    def getNetIncomePercent(self,trade_df:pd.DataFrame): return round(trade_df["報酬率(%)"].sum(), 2) if not trade_df.empty else 0.0
    def getIncomePercentRatio(self,trade_df:pd.DataFrame): return "-" if trade_df.empty else self.getIncomeRatio(trade_df) # Simplified
    def getIntervalDebt(self,trade_df:pd.DataFrame): return 0 if trade_df.empty else round((trade_df["累計獲利金額"].cummax() - trade_df["累計獲利金額"]).max(), 2)
    def getIntervalPercentDebt(self,trade_df:pd.DataFrame): return 0 if trade_df.empty else round((trade_df["累計報酬率(%)"].cummax() - trade_df["累計報酬率(%)"]).max(), 2)
    def checkTimeInSlots(self,time_str,allowed_ranges=[]):
        for slot in allowed_ranges:
            start, end = slot['start'], slot['end']
            if start <= end:
                if start <= time_str <= end: return True
            else: 
                if time_str >= start or time_str <= end: return True
        return False
    def readCertainTimeLimit(self,limitType = ""): return self.all_time_settings.get(limitType, [])
    def load_all_settings(self):
        SETTINGS_FILE = Path("all_time_settings.json")
        if not SETTINGS_FILE.exists(): return {}
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return {}
