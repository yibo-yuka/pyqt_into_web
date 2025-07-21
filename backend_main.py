# region 套件載入區
from PyQt5 import QtCore,QtWidgets,QtGui
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, 
                             QVBoxLayout, QHBoxLayout, QLabel, QListWidget, 
                             QListWidgetItem, QTableWidget, QTableWidgetItem,
                             QPushButton, QHeaderView, QMessageBox)
from FinMind.data import DataLoader
import talib
import pandas as pd
import matplotlib.pyplot as plt
import mplfinance as mpf
import re
import datetime
from datetime import datetime as DT
from datetime import timedelta
import time
import sys
import calendar
import os
import json
from pathlib import Path

# endregion


# --- 設定 JSON 檔案路徑 ---
SETTINGS_FILE = Path("all_time_settings.json")
class BackTesting(QtWidgets.QWidget):
    def find_pos(self,df:pd.DataFrame)->pd.DataFrame:
        global top_ck,top_stop_ck,bot_ck,bot_stop_ck,positive_top_ck,negative_bot_ck,osc_ratio_limit
        """
        依照OSC起伏找出波峰、波谷,並記錄波峰時最高價、波谷時最低價
        20250321細節補充：
        是在20240325偵測到20240322是OSC波峰，0326進場(做空)

        Args:
            df (pd.DataFrame): 有OSC的日k資料

        Returns:
            df (pd.DataFrame): 加了波峰波谷資料的日k資料
        """
        #df.reset_index(inplace=True)
        
        pos_ls = ["" for i in range(len(df))]
        high_ls = []
        low_ls = []
        max_high_ls = []
        min_low_ls = []
        for i in range(len(df)):
            if i > 1 and i != len(df)-1:
            #if i > 2:
                val_minus1 = df.loc[i-2,"OSC"]# 波峰波谷候選 前一個點
                val = df.loc[i-1,"OSC"]# 波峰波谷候選 
                val_add1 = df.loc[i,"OSC"]# 波峰波谷候選 後一個點
                #print(val_minus1,val,val_add1)
                
                if osc_ratio_limit:
                    if (max([abs(val_minus1),abs(val),abs(val_add1)])/min([abs(val_minus1),abs(val),abs(val_add1)]))<=self.osc_ratio_set:
                        continue #只要最大值跟最小值比例沒有超過某值，不辨識是否為波峰波谷
                
                if top_ck:
                    if val>val_minus1 and val>val_add1:
                        pos_ls[i] = "波峰"
                    
                if positive_top_ck:
                    all_positive_bool_ls = [v>0 for v in [val_minus1,val,val_add1]]
                    positive_check = all(all_positive_bool_ls)
                    if val>val_minus1 and val>val_add1 and positive_check:
                        pos_ls[i] = "波峰"
                        
                if bot_ck:
                    if val<val_minus1 and val<val_add1:
                        pos_ls[i] = "波谷"
                
                if negative_bot_ck:
                    all_negative_bool_ls = [v<0 for v in [val_minus1,val,val_add1]]
                    negative_check = all(all_negative_bool_ls)
                    if val<val_minus1 and val<val_add1 and negative_check:
                        pos_ls[i] = "波谷"
                
        max_high = lambda v1,v2,v3:max([v1,v2,v3])
        min_low = lambda v1,v2,v3:min([v1,v2,v3])
        max_high_ls = [max_high(df.loc[i-2,"High"],df.loc[i-1,"High"],df.loc[i,"High"]) if pos_ls[i] == "波峰" else "" for i in range(len(df))]
        min_low_ls = [min_low(df.loc[i-2,"Low"],df.loc[i-1,"Low"],df.loc[i,"Low"]) if pos_ls[i] == "波谷" else "" for i in range(len(df))]
        high_ls = [df.loc[i-1,"High"] if pos_ls[i] == "波峰" else "" for i in range(len(df))]
        low_ls = [df.loc[i-1,"Low"] if pos_ls[i] == "波谷" else "" for i in range(len(df))]
        pos_ls.append("") # 平移後index = len(df)-1
        high_ls.append("") # 平移後index = len(df)-1
        low_ls.append("") # 平移後index = len(df)-1
        max_high_ls.append("") # 平移後index = len(df)-1
        min_low_ls.append("") # 平移後index = len(df)-1
        #在找到波峰/波谷時，已經是下一天，所以波峰/波谷要往前平移一天
        #最高價與最低價已經是抓前一天的值，一起平移就好
        df["OSC波峰波谷"] = pos_ls[1:]
        df["波峰最高價"] = high_ls[1:]
        df["波谷最低價"] = low_ls[1:]
        df["3根k棒波峰最高價"] = max_high_ls[1:]
        df["3根k棒波谷最低價"] = min_low_ls[1:]
        return df
        
    def read_position(self,df:pd.DataFrame)->pd.DataFrame:
        global top_ck,top_stop_ck,bot_ck,bot_stop_ck,positive_top_ck,negative_bot_ck,skip_reverse_check,no_inverse_in_mid_check
        
        """
        判斷背離與止損

        Args:
            df (pd.DataFrame): 有OSC波峰波谷的日k資料

        Returns:
            df (pd.DataFrame): 判斷背離與止損的資料
        """
        #先設置背離欄位
        df["訊號"] = ["" for i in range(len(df))]
        #OSC波峰資料index df_t
        df_t = df[df["3根k棒波峰最高價"] != ""]
        top_ind_ls = df_t.index.tolist()
        #OSC波谷資料index df_b
        df_b = df[df["3根k棒波谷最低價"] != ""]
        bot_ind_ls = df_b.index.tolist()
        #讀取df_t每個row"OSC波峰波谷"，如果OSC跟最高價趨勢相反，紀錄頂背離訊號在df
        for i in range(len(top_ind_ls)-1):
            if top_ck:
                
                if no_inverse_in_mid_check:
                    temp_bool = [df.loc[temp_i,"OSC"]>=0 for temp_i in range(top_ind_ls[i],top_ind_ls[i+1]+1)]
                    if not all(temp_bool):
                        continue #如果中間翻負，不做以下的背離判斷
                
                pre_high = df.loc[top_ind_ls[i],"3根k棒波峰最高價"]
                now_high = df.loc[top_ind_ls[i+1],"3根k棒波峰最高價"]
                
                if self.top_def_ck1:
                    if df.loc[top_ind_ls[i],"OSC"]>df.loc[top_ind_ls[i+1],"OSC"] and pre_high<now_high:
                        df.loc[top_ind_ls[i+1],"訊號"] += "(不分正負)頂背離＆"
                if self.top_def_ck2:
                    if df.loc[top_ind_ls[i],"OSC"]<df.loc[top_ind_ls[i+1],"OSC"] and pre_high>now_high:
                        df.loc[top_ind_ls[i+1],"訊號"] += "(不分正負)頂背離＆"
                
                if skip_reverse_check and i!=len(top_ind_ls)-2:
                    if no_inverse_in_mid_check:
                        temp_bool = [df.loc[temp_i,"OSC"]>=0 for temp_i in range(top_ind_ls[i],top_ind_ls[i+2]+1)]
                        if not all(temp_bool):
                            continue #如果中間翻負，不做以下的背離判斷
                    pre_high = df.loc[top_ind_ls[i],"3根k棒波峰最高價"]
                    now_high = df.loc[top_ind_ls[i+2],"3根k棒波峰最高價"]
                    if self.top_def_ck1:
                        if df.loc[top_ind_ls[i],"OSC"]>df.loc[top_ind_ls[i+2],"OSC"] and pre_high<now_high:
                            df.loc[top_ind_ls[i+2],"訊號"] += "(不分正負)頂背離＆"
                    if self.top_def_ck2:
                        if df.loc[top_ind_ls[i],"OSC"]<df.loc[top_ind_ls[i+2],"OSC"] and pre_high>now_high:
                            df.loc[top_ind_ls[i+2],"訊號"] += "(不分正負)頂背離＆"
            else:
                break
        #讀取df_b每個row"OSC波峰波谷"，如果OSC跟最低價趨勢相反，紀錄底背離訊號在df
        for i in range(len(bot_ind_ls)-1):
            if bot_ck:
                
                if no_inverse_in_mid_check:
                    temp_bool = [df.loc[temp_i,"OSC"]<=0 for temp_i in range(bot_ind_ls[i],bot_ind_ls[i+1]+1)]
                    if not all(temp_bool):
                        continue #如果中間翻正，不做以下的背離判斷
                
                pre_low = df.loc[bot_ind_ls[i],"3根k棒波谷最低價"]
                now_low = df.loc[bot_ind_ls[i+1],"3根k棒波谷最低價"]

                if self.bot_def_ck1:
                    if df.loc[bot_ind_ls[i],"OSC"]<df.loc[bot_ind_ls[i+1],"OSC"] and pre_low>now_low:
                        df.loc[bot_ind_ls[i+1],"訊號"] += "(不分正負)底背離＆"
                if self.bot_def_ck2:
                    if df.loc[bot_ind_ls[i],"OSC"]>df.loc[bot_ind_ls[i+1],"OSC"] and pre_low<now_low:
                        df.loc[bot_ind_ls[i+1],"訊號"] += "(不分正負)底背離＆"
                if skip_reverse_check and i!=len(bot_ind_ls)-2:
                    
                    if no_inverse_in_mid_check:
                        temp_bool = [df.loc[temp_i,"OSC"]<=0 for temp_i in range(bot_ind_ls[i],bot_ind_ls[i+2]+1)]
                        if not all(temp_bool):
                            continue #如果中間翻正，不做以下的背離判斷
                    
                    pre_low = df.loc[bot_ind_ls[i],"3根k棒波谷最低價"]
                    now_low = df.loc[bot_ind_ls[i+2],"3根k棒波谷最低價"]
                    if self.bot_def_ck1:
                        if df.loc[bot_ind_ls[i],"OSC"]<df.loc[bot_ind_ls[i+2],"OSC"] and pre_low>now_low:
                            df.loc[bot_ind_ls[i+2],"訊號"] += "(不分正負)底背離＆"
                    if self.bot_def_ck2:
                        if df.loc[bot_ind_ls[i],"OSC"]>df.loc[bot_ind_ls[i+2],"OSC"] and pre_low<now_low:
                            df.loc[bot_ind_ls[i+2],"訊號"] += "(不分正負)底背離＆"
            else:
                break
            
        if positive_top_ck:
            positive_top_ls = [False for i in range(len(df))]
            osc_ls = df["OSC"].tolist()
            position_ls = df["OSC波峰波谷"].tolist()
            for i in range(1,len(position_ls)-1):
                p = position_ls[i]
                all_positive = all([osc_ls[i-1]>0,osc_ls[i]>0,osc_ls[i+1]>0])
                if p == "波峰" and all_positive:
                    positive_top_ls[i] = True
            df["正向頂背離"] = positive_top_ls
            
            temp_df = df[df["正向頂背離"]]
            posi_top_ind_ls = temp_df.index.tolist()
            for i in range(len(posi_top_ind_ls)-1):
                
                if no_inverse_in_mid_check:
                    temp_bool = [df.loc[temp_i,"OSC"]>=0 for temp_i in range(posi_top_ind_ls[i],posi_top_ind_ls[i+1]+1)]
                    if not all(temp_bool):
                        continue #如果中間翻負，不做以下的背離判斷
                
                pre_high = df.loc[posi_top_ind_ls[i],"3根k棒波峰最高價"]
                now_high = df.loc[posi_top_ind_ls[i+1],"3根k棒波峰最高價"]
                
                if self.posi_top_def_ck1:
                    if df.loc[posi_top_ind_ls[i],"OSC"]>df.loc[posi_top_ind_ls[i+1],"OSC"] and pre_high<now_high:
                            df.loc[posi_top_ind_ls[i+1],"訊號"] += "頂背離＆"
                if self.posi_top_def_ck2:
                    if df.loc[posi_top_ind_ls[i],"OSC"]<df.loc[posi_top_ind_ls[i+1],"OSC"] and pre_high>now_high:
                            df.loc[posi_top_ind_ls[i+1],"訊號"] += "頂背離＆"
                if skip_reverse_check and i!=len(posi_top_ind_ls)-2:
                    if no_inverse_in_mid_check:
                        temp_bool = [df.loc[temp_i,"OSC"]>=0 for temp_i in range(posi_top_ind_ls[i],posi_top_ind_ls[i+2]+1)]
                        if not all(temp_bool):
                            continue #如果中間翻負，不做以下的背離判斷
                    pre_high = df.loc[posi_top_ind_ls[i],"3根k棒波峰最高價"]
                    now_high = df.loc[posi_top_ind_ls[i+2],"3根k棒波峰最高價"]
                    if self.top_def_ck1:
                        if df.loc[posi_top_ind_ls[i],"OSC"]>df.loc[posi_top_ind_ls[i+2],"OSC"] and pre_high<now_high:
                            df.loc[posi_top_ind_ls[i+2],"訊號"] += "頂背離＆"
                    if self.top_def_ck2:
                        if df.loc[posi_top_ind_ls[i],"OSC"]<df.loc[posi_top_ind_ls[i+2],"OSC"] and pre_high>now_high:
                            df.loc[posi_top_ind_ls[i+2],"訊號"] += "頂背離＆"
            df.drop("正向頂背離",axis=1,inplace=True)
            
        if negative_bot_ck:
            negative_bot_ls = [False for i in range(len(df))]
            osc_ls = df["OSC"].tolist()
            position_ls = df["OSC波峰波谷"].tolist()
            for i in range(1,len(position_ls)-1):
                p = position_ls[i]
                all_negative = all([osc_ls[i-1]<0,osc_ls[i]<0,osc_ls[i+1]<0])
                if p == "波谷" and all_negative:
                    negative_bot_ls[i] = True
            df["負向底背離"] = negative_bot_ls
            
            temp_df = df[df["負向底背離"]]
            nega_bot_ind_ls = temp_df.index.tolist()
            for i in range(len(nega_bot_ind_ls)-1):
                if no_inverse_in_mid_check:
                        temp_bool = [df.loc[temp_i,"OSC"]<=0 for temp_i in range(nega_bot_ind_ls[i],nega_bot_ind_ls[i+1]+1)]
                        if not all(temp_bool):
                            continue #如果中間翻正，不做以下的背離判斷
                pre_low = df.loc[nega_bot_ind_ls[i],"3根k棒波谷最低價"]
                now_low = df.loc[nega_bot_ind_ls[i+1],"3根k棒波谷最低價"]
                
                if self.nega_bot_def_ck1:
                    if df.loc[nega_bot_ind_ls[i],"OSC"]<df.loc[nega_bot_ind_ls[i+1],"OSC"] and pre_low>now_low:
                            df.loc[nega_bot_ind_ls[i+1],"訊號"] += "底背離＆"
                if self.nega_bot_def_ck2:
                    if df.loc[nega_bot_ind_ls[i],"OSC"]>df.loc[nega_bot_ind_ls[i+1],"OSC"] and pre_low<now_low:
                            df.loc[nega_bot_ind_ls[i+1],"訊號"] += "底背離＆"
                if skip_reverse_check and i!=len(nega_bot_ind_ls)-2:
                    if no_inverse_in_mid_check:
                        temp_bool = [df.loc[temp_i,"OSC"]<=0 for temp_i in range(nega_bot_ind_ls[i],nega_bot_ind_ls[i+2]+1)]
                        if not all(temp_bool):
                            continue #如果中間翻正，不做以下的背離判斷
                    pre_low = df.loc[nega_bot_ind_ls[i],"3根k棒波谷最低價"]
                    now_low = df.loc[nega_bot_ind_ls[i+2],"3根k棒波谷最低價"]
                    if self.bot_def_ck1:
                        if df.loc[nega_bot_ind_ls[i],"OSC"]<df.loc[nega_bot_ind_ls[i+2],"OSC"] and pre_low>now_low:
                            df.loc[nega_bot_ind_ls[i+2],"訊號"] += "底背離＆"
                    if self.bot_def_ck2:
                        if df.loc[nega_bot_ind_ls[i],"OSC"]>df.loc[nega_bot_ind_ls[i+2],"OSC"] and pre_low<now_low:
                            df.loc[nega_bot_ind_ls[i+2],"訊號"] += "底背離＆"
            df.drop("負向底背離",axis=1,inplace=True)
            
        # 20250324 要先把背離的訊號往後移一天，再判斷止損
        # 這些訊號出現時，是在波峰波谷出現的後一天
        # 所以這裡的訊號要往後移一天
        temp_signal_ls = df["訊號"].tolist()
        temp_signal_ls.insert(0,"")
        df["訊號"] = temp_signal_ls[:-1]
        
        # 判斷止損
        state = ""
        high_stop = 0
        low_stop = 0    
        for i in range(1,len(df)):
            if top_stop_ck:
                if  "頂背離" in df.loc[i,"訊號"]:
                    state = "做空"
                    high_stop = df.loc[i-1,"3根k棒波峰最高價"] #因為訊號是後一天出現，所以抓前一天波峰最高價
                    continue
                if high_stop and state == "做空":
                    #temp_high = df.loc[i,"High"]
                    temp_close = df.loc[i,"Close"]
                    if temp_close>high_stop:
                        df.loc[i,"訊號"] = "頂背離止損"
                        state = ""
                        high_stop = 0
                        low_stop = 0
            if bot_stop_ck:
                if  "底背離" in df.loc[i,"訊號"]:
                    state = "做多"
                    low_stop = df.loc[i-1,"3根k棒波谷最低價"] #因為訊號是後一天出現，所以抓前一天波谷最低價
                    continue
                if low_stop and state == "做多":
                    #temp_low = df.loc[i,"Low"]
                    temp_close = df.loc[i,"Close"]
                    if temp_close<low_stop:
                        df.loc[i,"訊號"] = "底背離止損"
                        state = ""
                        high_stop = 0
                        low_stop = 0
        
        #回傳df
        return df
    
    def is_time_in_allowed_periods(self,time_str):
        """
        檢查給定的日期時間是否在允許的時間段內
        
        參數:
        date_str (str): 日期字符串，格式為 'YYYY/MM/DD'
        time_str (str): 時間字符串，格式為 'HH:MM:SS'
        
        返回:
        bool: 如果時間在允許的時間段內，則返回True，否則返回False
        """
        # 提取時間部分
        hour, minute, second = map(int, time_str.split(':'))
        
        # 將時間轉換為分鐘，便於比較
        time_in_minutes = hour * 60 + minute
        
        # 定義允許的時間段（以分鐘為單位）
        period1_start = 8 * 60 + 45   # 08:45
        period1_end = 11 * 60         # 11:00
        
        period2_start = 15 * 60       # 15:00
        period2_end = 17 * 60    # 17:00
        
        period3_start = 19 * 60 + 30  # 19:30
        period3_end = 24 * 60    # 00:00 第二天，轉換為分鐘是 24*60
        
        # 檢查時間是否在任一允許的時間段內
        if period1_start <= time_in_minutes <= period1_end:
            return True
        elif period2_start <= time_in_minutes <= period2_end:
            return True
        elif period3_start <= time_in_minutes or time_in_minutes <= (period3_end - 24 * 60):
            # 特殊處理跨午夜的情況
            # 如果時間 >= 19:30 或 時間 <= 00:00，則在第三個時間段內
            return True
        else:
            return False

    def checkTimeInSlots(self,time_str,allowed_ranges=[]):
        if not allowed_ranges:
            allowed_ranges = [
                {"start": "08:30:00", "end": "11:05:00"},
                {"start": "14:45:00", "end": "17:05:00"},
                {"start": "19:30:00", "end": "01:30:00"}  # 跨午夜的時間段
            ]
        
        temp_allowed_ranges = []
        for slot in allowed_ranges:
            if slot["end"]<slot["start"]:
                temp_allowed_ranges.append({"start": slot["start"], "end": "23:59:59"})
                temp_allowed_ranges.append({"start": "00:00:00", "end": slot["end"]})
            else:
                temp_allowed_ranges.append(slot)
        for slot in temp_allowed_ranges:
            if time_str >= slot["start"] and time_str <= slot["end"]:
                return True
        return False

    def readCertainTimeLimit(self,limitType = ""):
        allowed_ranges = []
        if not limitType:
            allowed_ranges = [
                {"start": "08:30:00", "end": "11:05:00"},
                {"start": "14:45:00", "end": "17:05:00"},
                {"start": "19:30:00", "end": "01:30:00"}  # 跨午夜的時間段
            ]
        else:
            #with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                #settings = json.load(f)
            allowed_ranges = self.all_time_settings[limitType]
        return allowed_ranges

    # --- 輔助函式：讀取和寫入 JSON ---
    def load_all_settings(self):
        """從 JSON 檔案載入所有設定。如果檔案不存在或無效，則返回包含預設結構的字典。
        如果檔案不存在，會創建一個帶有預設時間的 JSON 檔案。
        """
        # 定義所有四組的統一預設時間段
        unified_default_times = [
            {"start": "08:30:00", "end": "11:05:00"},
            {"start": "14:45:00", "end": "17:05:00"},
            {"start": "19:30:00", "end": "01:30:00"} # This slot crosses midnight
        ]

        default_settings = {
            "15分K - 做多": unified_default_times,
            "15分K - 做空": unified_default_times,
            "小時K - 做多": unified_default_times,
            "小時K - 做空": unified_default_times
        }

        if not SETTINGS_FILE.exists():
            # 如果檔案不存在，則創建它並寫入預設設定
            print(f"'{SETTINGS_FILE}' 不存在，創建並寫入預設設定。")
            self.save_all_settings(default_settings)
            return default_settings
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                # 合併，確保載入的設定包含所有預期的鍵，如果缺少則用預設值填充
                # 這會保留已存在的設定，並為新加入的鍵提供預設值
                return {**default_settings, **settings}
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading settings from JSON: {e}. Returning default settings.")
            # 載入失敗時也返回預設結構，並寫入檔案以修復潛在的錯誤
            self.save_all_settings(default_settings)
            return default_settings

    def save_all_settings(self,all_settings):
        """將所有設定儲存到 JSON 檔案中。"""
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(all_settings, f, indent=4)
        except IOError as e:
            print(f"Error saving settings to JSON: {e}")

    def decide_position(self,df:pd.DataFrame)->pd.DataFrame:
        """
        依照背離與止損決定部位(做多、做空、平倉)

        Args:
            df (pd.DataFrame): 判斷背離與止損的資料

        Returns:
            df (pd.DataFrame): 判斷部位的資料
        """
        pos = 0
        pos_ls = []
        open_record = []
        for i in df.index.tolist():
            
            if df.loc[i,"訊號"] == "頂背離止損" or df.loc[i,"訊號"] == "底背離止損":
                if pos != 0:#為了避免因為不在可進場時段，該進場沒進場，所以用當前部位判斷做多做空
                    if pos<0 and df.loc[i,"訊號"] == "頂背離止損": 
                        pos = 0
                        pos_ls.append(pos)
                        open_record.append(True)
                    elif pos>0 and df.loc[i,"訊號"] == "底背離止損":
                        pos = 0
                        pos_ls.append(pos)
                        open_record.append(True)
                    else:
                        pos_ls.append(pos)
                        open_record.append(False)
                else:
                    pos_ls.append(pos)
                    open_record.append(False)
                continue
            elif "頂背離" in df.loc[i,"訊號"]:
                if enter_time_check and not self.checkTimeInSlots(df.loc[i+1,"時間區間"].split('~')[0],self.readCertainTimeLimit(f"{timelevel} - 做空")):
                    pos_ls.append(pos)
                    open_record.append(False)
                    continue
                if pos > 0:
                    pos = -1*pos
                elif pos == 0:
                    pos -= 1
                pos_ls.append(pos)
                open_record.append(True)
            elif "底背離" in df.loc[i,"訊號"]:
                if enter_time_check and not self.checkTimeInSlots(df.loc[i+1,"時間區間"].split('~')[0],self.readCertainTimeLimit(f"{timelevel} - 做多")):
                    pos_ls.append(pos)
                    open_record.append(False)
                    continue
                if pos < 0:
                    pos = -1*pos
                elif pos == 0:
                    pos += 1
                pos_ls.append(pos)
                open_record.append(True)
            else:
                pos_ls.append(pos)
                open_record.append(False)
        #因為接觸到訊號隔天才會變化，所以最前面插入原始部位
        pos_ls.insert(0,0)
        pos_ls = pos_ls[:-1]
        open_record.insert(0,False)
        open_record = open_record[:-1]
        #儲存部位
        df["position"] = pos_ls
        df["當時開盤價"] = open_record
        open_record = [df.loc[i,"Open"] if df.loc[i,"當時開盤價"] else pd.NA for i in df.index.tolist()]
        df["當時開盤價"] = open_record
        #回傳df
        return df

    def getIncome(self,df:pd.DataFrame):
        temp_df = df[["日期","時間區間","position","當時開盤價"]]
        temp_df = temp_df.dropna(how="any",axis=0)
        #部位變高->(後Open-前Open)*-1(買回做空的期貨)
        #部位變低->(後Open-前Open)(賣出做多的期貨)
        #做多變做空中間經過平倉，所以是算做多後平倉賣的賺多少
        #做空變做多中間經過平倉，所以是算做空後平倉買回的差價為賺的錢
        income_ls = []
        ind_ls = temp_df.index.tolist()
        for i in range(len(temp_df)):
            if (temp_df.loc[ind_ls[i],"position"]!=0) and (i+1 < len(temp_df)):
                if (temp_df.loc[ind_ls[i],"position"] < temp_df.loc[ind_ls[i+1],"position"]):#部位變高
                    temp_income = (temp_df.loc[ind_ls[i+1],"當時開盤價"]-temp_df.loc[ind_ls[i],"當時開盤價"])*(-1)
                    income_ls.append(temp_income*200)
                elif (temp_df.loc[ind_ls[i],"position"] > temp_df.loc[ind_ls[i+1],"position"]):#部位變低
                    temp_income = (temp_df.loc[ind_ls[i+1],"當時開盤價"]-temp_df.loc[ind_ls[i],"當時開盤價"])
                    income_ls.append(temp_income*200)
                else:
                    income_ls.append(pd.NA)
            else:
                income_ls.append(pd.NA)
                continue
        #income是算在後面那天    
        income_ls.insert(0,pd.NA)
        income_ls = income_ls[:-1]
        temp_df["income($)"] = income_ls
        temp_df = temp_df[["日期","時間區間","income($)"]]
        df = df.merge(temp_df,on=["日期","時間區間"],how="left")
        
        return df

    def getNetIncome(self,df:pd.DataFrame):
        net_income_in_cash = df["income($)"].sum()
        return round(net_income_in_cash)

    def getSumOfCertainCondition(self,val_ls,state:str):
        right_state_ls = []
        for val in val_ls:
            if val is not pd.NA:
                if state == "+" and val>0:
                    right_state_ls.append(val)
                if state == "-" and val<=0:
                    right_state_ls.append(val)
            else:
                continue
        return right_state_ls
    
    def getIncomeRatio(self,df:pd.DataFrame):
        income_ls = df["income($)"].tolist()
        pos_income_ls = self.getSumOfCertainCondition(income_ls,state="+")
        neg_income_ls = self.getSumOfCertainCondition(income_ls,state="-")
        pos_income = sum(pos_income_ls)
        neg_income = sum(neg_income_ls)
        income_ratio = 0
        if neg_income != 0:
            income_ratio = abs(pos_income/neg_income)
        else:
            income_ratio = "-"
            return income_ratio
        return round(income_ratio,2)
    
    def getSignalDetail(self,df:pd.DataFrame):
        signal_data = []
        ind_ls = df.index.tolist()
        for i in ind_ls[:-1]:
            if df.loc[i,"訊號"]:
                next_i = ind_ls[ind_ls.index(i)+1]
                actionStr = ""
                if df.loc[next_i,'position']-df.loc[i,'position'] < 0:
                    actionStr = "賣出"
                elif df.loc[next_i,'position']-df.loc[i,'position'] > 0:
                    actionStr = "買進"
                #交易指令
                signal_content = df.loc[i,"訊號"][:-1] if df.loc[i,"訊號"][-1] == "＆" else df.loc[i,"訊號"]
                #先用split將＆相連的字串分開
                signal_content_strlist = signal_content.split("＆")
                #將重複的字串只留下一個
                signal_content = ""
                for content in signal_content_strlist:
                    if content not in signal_content:
                        signal_content += content + "＆"
                signal_content = signal_content[:-1]
                signal_data.append([f"{str(datetime.datetime.now()).split(' ')[1][:-3]}","台股指數近月","交易指令",
                                    f"實際部位:{df.loc[i,'position']} 目標部位:{df.loc[next_i,'position']} 價格：市價 (訊號：{signal_content})"])
                #回測成交
                amount = abs(df.loc[next_i,'position']-df.loc[i,'position'])
                if amount != 0:
                    signal_data.append([f"{str(datetime.datetime.now()).split(' ')[1][:-3]}","台股指數近月","回測成交",
                                        f"成交時間:{str(df.loc[next_i,'日期']).split(' ')[0]} {str(df.loc[next_i,'時間區間']).split('~')[0]}({actionStr}) 數量:{amount} 價格:{df.loc[next_i,'當時開盤價']}"])
        signal_df = pd.DataFrame(signal_data,columns=["時間","商品","動作","內容"])
        
        return signal_df

    def getTradeDetail(self,df:pd.DataFrame,principal:float):
        ind_ls = df.index.tolist()
        temp_df = df[["日期","時間區間","position","當時開盤價","income($)"]]
        temp_df = temp_df.dropna(subset=["當時開盤價"],axis=0)
        temp_ind_ls = temp_df.index.tolist()
        trade_data = []
        for i in temp_ind_ls[1:]:
            pre_i = temp_ind_ls[temp_ind_ls.index(i)-1]
            trade_amount = temp_df.loc[i,"position"] - temp_df.loc[pre_i,"position"]
            action1 = ""
            action2 = ""
            if trade_amount<0:
                action1 = "買進"
                action2 = "賣出"
            elif trade_amount>0:
                action1 = "賣出"
                action2 = "買進"
            #act_time_1 = str(df.loc[ind_ls[ind_ls.index(pre_i)-1],"日期"]).split(" ")[0]
            #act_time_2 = str(df.loc[ind_ls[ind_ls.index(i)-1],"日期"]).split(" ")[0]
            #20250322 只要是"當時開盤價"有值的那一行，那行日期就是入場/出場日期
            act_time_date_1 = str(df.loc[ind_ls[ind_ls.index(pre_i)],"日期"]).split(" ")[0]
            act_time_start_1 = str(df.loc[ind_ls[ind_ls.index(pre_i)],"時間區間"]).split("~")[0]
            act_time_date_2 = str(df.loc[ind_ls[ind_ls.index(i)],"日期"]).split(" ")[0]
            act_time_start_2 = str(df.loc[ind_ls[ind_ls.index(i)],"時間區間"]).split("~")[0]
            pre_i_ind_inList = ind_ls.index(pre_i)
            i_ind_inList = ind_ls.index(i)
            
            if temp_df.loc[i,"income($)"] is not pd.NA:
                temp_trade_data = ["台股指數近月(FITXN*1.TF)",f"{i_ind_inList-pre_i_ind_inList}",f"{act_time_date_1} {act_time_start_1}",f"{action1} {temp_df.loc[pre_i,'當時開盤價']}",
                                f"{act_time_date_2} {act_time_start_2}",f"{action2} {temp_df.loc[i,'當時開盤價']}",abs(trade_amount),temp_df.loc[i,"income($)"]]
                trade_data.append(temp_trade_data)
        trade_df = pd.DataFrame(trade_data,columns=["商品名稱","持有區間","進場時間","進場價格","出場時間","出場價格","交易數量","獲利金額"])
        temp_income_ls = []
        income_in_percent_ls = []
        acc_income_ls = []
        acc_income_in_precent_ls = []
        for income in trade_df["獲利金額"]:
            temp_income_ls.append(income)
            acc_income_ls.append(sum(temp_income_ls))
            income_in_percent_ls.append(round((income/principal)*100,2))
            acc_income_in_precent_ls.append(round((sum(temp_income_ls)/principal)*100,2))
        trade_df["累計獲利金額"] = acc_income_ls
        trade_df["報酬率(%)"] = income_in_percent_ls
        trade_df["累計報酬率(%)"] = acc_income_in_precent_ls
        trade_df["序號"] = [i+1 for i in range(len(trade_df))]
        new_cols = ["商品名稱","序號","進場時間","進場價格","出場時間","出場價格","持有區間","報酬率(%)","交易數量","獲利金額","累計獲利金額","累計報酬率(%)"]
        trade_df = trade_df[new_cols]
        return trade_df
    
    def getNetIncomePercent(self,trade_df:pd.DataFrame):
        net_income_in_percent = trade_df["報酬率(%)"].sum()
        return round(net_income_in_percent,2)
    
    def getIncomePercentRatio(self,trade_df:pd.DataFrame):
        income_ls = trade_df["報酬率(%)"].tolist()
        pos_income_ls = self.getSumOfCertainCondition(income_ls,state="+")
        neg_income_ls = self.getSumOfCertainCondition(income_ls,state="-")
        pos_income = sum(pos_income_ls)
        neg_income = sum(neg_income_ls)
        income_perc_ratio = 0
        if neg_income != 0:
            income_perc_ratio = abs(pos_income/neg_income)
        else:
            income_perc_ratio = "-"
            return income_perc_ratio
        return round(income_perc_ratio,2)
    
    def getIntervalDebt(self,trade_df:pd.DataFrame):
        # 先將所有累積損益取出來存成acc_income_ls
        acc_income_ls = trade_df["累計獲利金額"].tolist()
        # 掃描acc_income_ls，如果遇到正數就先取為暫時波峰，
        temp_peak = 0
        debt_ls = []
        for val in acc_income_ls:
            if temp_peak==0:
                if val>0: #取得回測區間第一個正數
                    temp_peak = val
                    continue
                elif val<=0: #負數不管
                    continue
            # 如果後面一個值比波峰大，後面一個值變成新暫時波峰，
            if val >= temp_peak:
                temp_peak = val
            else:# 如果後面一個值比波峰小，儲存區間虧損->[後面一個值-暫時波峰]*-1存到debt_ls
                temp_interval_debt = (val-temp_peak)*-1
                debt_ls.append(temp_interval_debt)
        
        if temp_peak == 0: #如果從頭到尾沒有獲利，回報最大區虧為未知["-"]
            return "-"
        
        if not debt_ls:
            return "-"
        
        # 回傳debt_ls的最大值
        return round(max(debt_ls),2)
    
    def getIntervalPercentDebt(self,trade_df:pd.DataFrame):
        # 先將所有累積損益取出來存成acc_income_ls
        acc_income_ls = trade_df["累計報酬率(%)"].tolist()
        # 掃描acc_income_ls，如果遇到正數就先取為暫時波峰，
        temp_peak = 0
        debt_ls = []
        for val in acc_income_ls:
            if temp_peak==0:
                if val>0: #取得回測區間第一個正數
                    temp_peak = val
                    continue
                elif val<=0: #負數不管
                    continue
            # 如果後面一個值比波峰大，後面一個值變成新暫時波峰，
            if val >= temp_peak:
                temp_peak = val
            else:# 如果後面一個值比波峰小，儲存區間虧損->[後面一個值-暫時波峰]*-1存到debt_ls
                temp_interval_debt = (val-temp_peak)*-1
                debt_ls.append(temp_interval_debt)
        
        if temp_peak == 0: #如果從頭到尾沒有獲利，回報最大區虧為未知["-"]
            return "-"
        
        if not debt_ls:
            return "-"
        
        # 回傳debt_ls的最大值
        return round(max(debt_ls),2)
    
    def checkParam(self):
        Warning_ls = []
        start_date = self.date_val_1.date()
        end_date = self.date_val_2.date()
        now_date = QtCore.QDate.currentDate()
        principal = float(self.principal_val.text()) 
        
        if start_date.toString(QtCore.Qt.ISODate) < "2022-01-01":
            Warning_ls.append("開始日期應在2022-01-01後(含2022-01-01)!!\n")
        if end_date.toString(QtCore.Qt.ISODate) > self.last_date_of_data.strftime("%Y-%m-%d"):
            Warning_ls.append(f"結束日期應在{self.last_date_of_data.strftime('%Y-%m-%d')}以前(含{self.last_date_of_data.strftime('%Y-%m-%d')})!!\n")
        if start_date >= end_date :
            Warning_ls.append("開始日期須早於結束日期!!\n")
        if start_date>now_date and end_date>now_date:
            Warning_ls.append("開始與結束日期須包含已交易的日期!!\n")
        if not principal:
            Warning_ls.append("請填寫本金!!\n")
        if principal<0:
            Warning_ls.append("本金請填寫正數!!\n")
        
        return Warning_ls
    
    def one_hour_backtest(self):
        global top_ck,top_stop_ck,bot_ck,bot_stop_ck,positive_top_ck,negative_bot_ck,osc_ratio_limit,skip_reverse_check,no_inverse_in_mid_check,enter_time_check,timelevel
        df = pd.read_excel('小時k.xlsx') #TODO 之後df需要在回測前更新沒有的資料
        warning_ls = self.checkParam()
        if warning_ls:
            warning_str = ""
            for s in warning_ls: warning_str+=s
            self._info = QtWidgets.QMessageBox(self)
            self._info.information(self,"警告",warning_str)
            return
        start_date = self.date_val_1.date().toString(QtCore.Qt.ISODate)
        end_date = self.date_val_2.date().toString(QtCore.Qt.ISODate)
        #這次也不需要往前抓，因為往前抓是為了算OSC，資料已經計算好OSC了。
        #data_start_date = self.date_val_1.date().addDays(-3).toString(QtCore.Qt.ISODate)
        #這次不往後抓，因為osc是往前抓資料算出來的
        #data_end_date = self.date_val_2.date().addMonths(3).toString(QtCore.Qt.ISODate)
        #data_end_date = end_date #TODO 之後UI的結束日期預設要改成資料最晚日期
        top_ck = self.tacticCheckbtn1.isChecked()
        top_stop_ck = self.tacticCheckbtn2.isChecked()
        bot_ck = self.tacticCheckbtn3.isChecked()
        bot_stop_ck = self.tacticCheckbtn4.isChecked()
        positive_top_ck = self.tacticCheckbtn5.isChecked()
        negative_bot_ck = self.tacticCheckbtn6.isChecked()
        osc_ratio_limit = self.tacticCheckbtn7.isChecked()
        skip_reverse_check = self.skip_reverse.isChecked()
        no_inverse_in_mid_check = self.no_inverse_in_middle.isChecked()
        enter_time_check = self.enter_time_limits.isChecked()
        timelevel = "小時K"
        
        # 這裡需要提醒什麼都沒勾，但沒勾照樣是可以測
        reply = ""
        if  not any([top_ck,top_stop_ck,bot_ck,bot_stop_ck,positive_top_ck,negative_bot_ck,osc_ratio_limit,skip_reverse_check,no_inverse_in_mid_check,enter_time_check]) :
            self._info = QtWidgets.QMessageBox(self)
            reply = self._info.question(self,"提醒","未設定任何策略，確定進行回測?",
                                        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, 
                                        QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.No:
            return
        #小時k資料已經整理為近月、小時k資料
        #df = self.get_TX_data(data_start_date,data_end_date,"TX")
        #df = self.clean_Constract_Date(df)
        #df = self.get_1TF(df)
        #df = self.get_daliy_k_bar_range(df,data_start_date,data_end_date)
        #df = self.getMACD_OSC(df)
        #原先日k是要多少取多少資料，現在是要從三年資料裡取用資料段
        #因為回測是要從開始投資那天開始計算
        df = df[(df["日期"]>pd.to_datetime(start_date)) & (df["日期"]<pd.to_datetime(end_date))]
        df.reset_index(inplace=True,drop=True)
        df = self.find_pos(df)
        df = self.read_position(df)
        df = self.decide_position(df)
        df = self.getIncome(df)
        df["訊號"] = [s[:-1] if s and s[-1] == "＆" else s for s in df["訊號"]]
        df = df[(df["日期"]>pd.to_datetime(start_date)) & (df["日期"]<pd.to_datetime(end_date))]
        
        self._info = QtWidgets.QMessageBox(self)
        self._info.information(self,"訊息",f'已完成 小時k 回測 !!!')
        
        signal_df,trade_df = self.getReportTable(df)
        
        self.RecordTable_1 = QtWidgets.QTableWidget(self)
        self.RecordTable_1.setColumnCount(len(signal_df.columns.tolist()))
        self.RecordTable_1.setHorizontalHeaderLabels(signal_df.columns.tolist())
        columns = signal_df.columns.tolist()
        for r in range(len(signal_df)):
            temp_row = self.RecordTable_1.rowCount()
            self.RecordTable_1.insertRow(temp_row)
            for c in columns:
                tempItem = QtWidgets.QTableWidgetItem(str(signal_df.loc[r,c]))
                self.RecordTable_1.setItem(temp_row,columns.index(c),tempItem)
        #self.putDfToTableUI(signal_df)
        #self.tabwid = QtWidgets.QTabWidget(self)
        self.tab_signal_df_wid = QtWidgets.QWidget(self)
        self.tab_layout_1 = QtWidgets.QVBoxLayout(self.tab_signal_df_wid)
        self.tab_layout_1.addWidget(self.RecordTable_1)
        #self.tabwid.addTab(self.tab_signal_df_wid,"策略交易明細")
        
        self.RecordTable_2 = QtWidgets.QTableWidget(self)
        self.RecordTable_2.setColumnCount(len(trade_df.columns.tolist()))
        self.RecordTable_2.setHorizontalHeaderLabels(trade_df.columns.tolist())
        columns = trade_df.columns.tolist()
        for r in range(len(trade_df)):
            temp_row = self.RecordTable_2.rowCount()
            self.RecordTable_2.insertRow(temp_row)
            for c in columns:
                tempItem = QtWidgets.QTableWidgetItem(str(trade_df.loc[r,c]))
                self.RecordTable_2.setItem(temp_row,columns.index(c),tempItem)
        #self.putDfToTableUI(trade_df)
        #self.tabwid = QtWidgets.QTabWidget(self)
        self.tab_trade_df_wid = QtWidgets.QWidget(self)
        self.tab_layout_2 = QtWidgets.QVBoxLayout(self.tab_trade_df_wid)
        self.tab_layout_2.addWidget(self.RecordTable_2)
        #self.tabwid.addTab(self.tab_trade_df_wid,"買賣交易明細")
        
        self.RecordTable_3 = QtWidgets.QTableWidget(self)
        self.RecordTable_3.setColumnCount(len(df.columns.tolist()))
        self.RecordTable_3.setHorizontalHeaderLabels(df.columns.tolist())
        columns = df.columns.tolist()
        for r in df.index.tolist():
            temp_row = self.RecordTable_3.rowCount()
            self.RecordTable_3.insertRow(temp_row)
            for c in columns:
                tempItem = QtWidgets.QTableWidgetItem(str(df.loc[r,c]))
                self.RecordTable_3.setItem(temp_row,columns.index(c),tempItem)
        #self.putDfToTableUI(trade_df)
        #self.tabwid = QtWidgets.QTabWidget(self)
        self.df_wid = QtWidgets.QWidget(self)
        self.tab_layout_3 = QtWidgets.QVBoxLayout(self.df_wid)
        self.tab_layout_3.addWidget(self.RecordTable_3)
        #self.tabwid.addTab(self.df_wid,"總表")
        
        time_now = datetime.datetime.now()
        
        sample_texts = [f"小時k_策略交易明細{str(time_now)[11:19]}",f"小時k_買賣交易明細{str(time_now)[11:19]}",f"小時k_總表{str(time_now)[11:19]}"]
        for text in sample_texts:
            self.text_list.addItem(text)
        
        # 連接列表的點擊信號
        self.text_list.itemClicked.connect(self.add_new_table_tab)
        self.df_dict[f"小時k_策略交易明細{str(time_now)[11:19]}"] = signal_df
        self.df_dict[f"小時k_買賣交易明細{str(time_now)[11:19]}"] = trade_df
        self.df_dict[f"小時k_總表{str(time_now)[11:19]}"] = df
        #損益歷史加入表格
        cols = ["時間級別","淨利($)","淨利(%)","平均獲利\n虧損比($)","平均獲利\n虧損比(%)","最大區間虧損($)","最大區間虧損(%)"]
        vals = ["小時k",self.getNetIncome(df),self.getNetIncomePercent(trade_df),self.getIncomeRatio(df),self.getIncomePercentRatio(trade_df),self.getIntervalDebt(trade_df),self.getIntervalPercentDebt(trade_df)]
        temp_row = self.RecordTable.rowCount()
        self.RecordTable.insertRow(temp_row)
        for i in range(len(cols)):
            tempItem = QtWidgets.QTableWidgetItem(str(vals[i]))
            self.RecordTable.setItem(temp_row,i,tempItem)
        
        if self.his_df.loc[0,"淨利($)"] != "":
            self.his_df.loc[len(self.his_df)] = vals
        else:
            self.his_df = pd.DataFrame(data = [vals],columns=cols)
        self.df_dict["損益歷史紀錄"] = self.his_df
    
    def quanter_backtest(self):
        global top_ck,top_stop_ck,bot_ck,bot_stop_ck,positive_top_ck,negative_bot_ck,osc_ratio_limit,skip_reverse_check,no_inverse_in_mid_check,enter_time_check,timelevel
        df = pd.read_excel('15分k.xlsx') #TODO 之後df需要在回測前更新沒有的資料
        warning_ls = self.checkParam()
        if warning_ls:
            warning_str = ""
            for s in warning_ls: warning_str+=s
            self._info = QtWidgets.QMessageBox(self)
            self._info.information(self,"警告",warning_str)
            return
        start_date = self.date_val_1.date().toString(QtCore.Qt.ISODate)
        end_date = self.date_val_2.date().toString(QtCore.Qt.ISODate)
        #這次也不需要往前抓，因為往前抓是為了算OSC，資料已經計算好OSC了。
        #data_start_date = self.date_val_1.date().addDays(-3).toString(QtCore.Qt.ISODate)
        #這次不往後抓，因為osc是往前抓資料算出來的
        #data_end_date = self.date_val_2.date().addMonths(3).toString(QtCore.Qt.ISODate)
        #data_end_date = end_date #TODO 之後UI的結束日期預設要改成資料最晚日期
        top_ck = self.tacticCheckbtn1.isChecked()
        top_stop_ck = self.tacticCheckbtn2.isChecked()
        bot_ck = self.tacticCheckbtn3.isChecked()
        bot_stop_ck = self.tacticCheckbtn4.isChecked()
        positive_top_ck = self.tacticCheckbtn5.isChecked()
        negative_bot_ck = self.tacticCheckbtn6.isChecked()
        osc_ratio_limit = self.tacticCheckbtn7.isChecked()
        skip_reverse_check = self.skip_reverse.isChecked()
        no_inverse_in_mid_check = self.no_inverse_in_middle.isChecked()
        enter_time_check = self.enter_time_limits.isChecked()
        timelevel = "15分K"
        
        # 這裡需要提醒什麼都沒勾，但沒勾照樣是可以測
        reply = ""
        if  not any([top_ck,top_stop_ck,bot_ck,bot_stop_ck,positive_top_ck,negative_bot_ck,osc_ratio_limit,skip_reverse_check,no_inverse_in_mid_check,enter_time_check]) :
            self._info = QtWidgets.QMessageBox(self)
            reply = self._info.question(self,"提醒","未設定任何策略，確定進行回測?",
                                        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, 
                                        QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.No:
            return
        #小時k資料已經整理為近月、小時k資料
        #df = self.get_TX_data(data_start_date,data_end_date,"TX")
        #df = self.clean_Constract_Date(df)
        #df = self.get_1TF(df)
        #df = self.get_daliy_k_bar_range(df,data_start_date,data_end_date)
        #df = self.getMACD_OSC(df)
        #原先日k是要多少取多少資料，現在是要從三年資料裡取用資料段
        #因為回測是要從開始投資那天開始計算
        df = df[(df["日期"]>pd.to_datetime(start_date)) & (df["日期"]<pd.to_datetime(end_date))]
        df.reset_index(inplace=True,drop=True)
        df = self.find_pos(df)
        df = self.read_position(df)
        df = self.decide_position(df)
        df = self.getIncome(df)
        df["訊號"] = [s[:-1] if s and s[-1] == "＆" else s for s in df["訊號"]]
        df = df[(df["日期"]>pd.to_datetime(start_date)) & (df["日期"]<pd.to_datetime(end_date))]
        
        self._info = QtWidgets.QMessageBox(self)
        self._info.information(self,"訊息",f'已完成 15分k 回測 !!!')
        
        signal_df,trade_df = self.getReportTable(df)
        
        self.RecordTable_1 = QtWidgets.QTableWidget(self)
        self.RecordTable_1.setColumnCount(len(signal_df.columns.tolist()))
        self.RecordTable_1.setHorizontalHeaderLabels(signal_df.columns.tolist())
        columns = signal_df.columns.tolist()
        for r in range(len(signal_df)):
            temp_row = self.RecordTable_1.rowCount()
            self.RecordTable_1.insertRow(temp_row)
            for c in columns:
                tempItem = QtWidgets.QTableWidgetItem(str(signal_df.loc[r,c]))
                self.RecordTable_1.setItem(temp_row,columns.index(c),tempItem)
        #self.putDfToTableUI(signal_df)
        #self.tabwid = QtWidgets.QTabWidget(self)
        self.tab_signal_df_wid = QtWidgets.QWidget(self)
        self.tab_layout_1 = QtWidgets.QVBoxLayout(self.tab_signal_df_wid)
        self.tab_layout_1.addWidget(self.RecordTable_1)
        #self.tabwid.addTab(self.tab_signal_df_wid,"策略交易明細")
        
        self.RecordTable_2 = QtWidgets.QTableWidget(self)
        self.RecordTable_2.setColumnCount(len(trade_df.columns.tolist()))
        self.RecordTable_2.setHorizontalHeaderLabels(trade_df.columns.tolist())
        columns = trade_df.columns.tolist()
        for r in range(len(trade_df)):
            temp_row = self.RecordTable_2.rowCount()
            self.RecordTable_2.insertRow(temp_row)
            for c in columns:
                tempItem = QtWidgets.QTableWidgetItem(str(trade_df.loc[r,c]))
                self.RecordTable_2.setItem(temp_row,columns.index(c),tempItem)
        #self.putDfToTableUI(trade_df)
        #self.tabwid = QtWidgets.QTabWidget(self)
        self.tab_trade_df_wid = QtWidgets.QWidget(self)
        self.tab_layout_2 = QtWidgets.QVBoxLayout(self.tab_trade_df_wid)
        self.tab_layout_2.addWidget(self.RecordTable_2)
        #self.tabwid.addTab(self.tab_trade_df_wid,"買賣交易明細")
        
        self.RecordTable_3 = QtWidgets.QTableWidget(self)
        self.RecordTable_3.setColumnCount(len(df.columns.tolist()))
        self.RecordTable_3.setHorizontalHeaderLabels(df.columns.tolist())
        columns = df.columns.tolist()
        for r in df.index.tolist():
            temp_row = self.RecordTable_3.rowCount()
            self.RecordTable_3.insertRow(temp_row)
            for c in columns:
                tempItem = QtWidgets.QTableWidgetItem(str(df.loc[r,c]))
                self.RecordTable_3.setItem(temp_row,columns.index(c),tempItem)
        #self.putDfToTableUI(trade_df)
        #self.tabwid = QtWidgets.QTabWidget(self)
        self.df_wid = QtWidgets.QWidget(self)
        self.tab_layout_3 = QtWidgets.QVBoxLayout(self.df_wid)
        self.tab_layout_3.addWidget(self.RecordTable_3)
        #self.tabwid.addTab(self.df_wid,"總表")
        
        time_now = datetime.datetime.now()
        
        sample_texts = [f"15分k_策略交易明細{str(time_now)[11:19]}",f"15分k_買賣交易明細{str(time_now)[11:19]}",f"15分k_總表{str(time_now)[11:19]}"]
        for text in sample_texts:
            self.text_list.addItem(text)
        
        # 連接列表的點擊信號
        self.text_list.itemClicked.connect(self.add_new_table_tab)
        self.df_dict[f"15分k_策略交易明細{str(time_now)[11:19]}"] = signal_df
        self.df_dict[f"15分k_買賣交易明細{str(time_now)[11:19]}"] = trade_df
        self.df_dict[f"15分k_總表{str(time_now)[11:19]}"] = df
        #損益歷史加入表格
        cols = ["時間級別","淨利($)","淨利(%)","平均獲利\n虧損比($)","平均獲利\n虧損比(%)","最大區間虧損($)","最大區間虧損(%)"]
        vals = ["15分k",self.getNetIncome(df),self.getNetIncomePercent(trade_df),self.getIncomeRatio(df),self.getIncomePercentRatio(trade_df),self.getIntervalDebt(trade_df),self.getIntervalPercentDebt(trade_df)]
        temp_row = self.RecordTable.rowCount()
        self.RecordTable.insertRow(temp_row)
        for i in range(len(cols)):
            tempItem = QtWidgets.QTableWidgetItem(str(vals[i]))
            self.RecordTable.setItem(temp_row,i,tempItem)
        
        if self.his_df.loc[0,"淨利($)"] != "":
            self.his_df.loc[len(self.his_df)] = vals
        else:
            self.his_df = pd.DataFrame(data = [vals],columns=cols)
        self.df_dict["損益歷史紀錄"] = self.his_df
    
    def backTesting(self):
        
        if not self.hr_1_kbar_cb.isChecked() and not self.min_15_kbar_cb.isChecked():
            self._info = QtWidgets.QMessageBox(self)
            self._info.information(self,"訊息",'請至少選一個時間級別!!!')
        
        if self.hr_1_kbar_cb.isChecked():
            self.one_hour_backtest()
            
        if self.min_15_kbar_cb.isChecked():
            self.quanter_backtest()
    
    def getReportTable(self,df:pd.DataFrame):
        signal_df = self.getSignalDetail(df)
        principal = float(self.principal_val.text()) 
        trade_df = self.getTradeDetail(df,principal)
        return signal_df,trade_df
    