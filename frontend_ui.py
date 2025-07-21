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

class mainwin(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("FITXN_1TF")
        self.setWindowTitle("台指期近一 回測分析")
        self.setWindowIcon(QtGui.QIcon('Frank_TXicon_24x24.ico')) #TODO
        self.resize(2400,1200)
        #先更新資料 #TODO 記得打開
        self.last_date_of_data = self.updateData()
        # 在 MainWindow 初始化時載入所有設定
        self.all_time_settings = self.load_all_settings()
        
        self.top_def_ck1 = True
        self.top_def_ck2 = False
        self.bot_def_ck1 = True
        self.bot_def_ck2 = False
        self.posi_top_def_ck1 = True
        self.posi_top_def_ck2 = False
        self.nega_bot_def_ck1 = True
        self.nega_bot_def_ck2 = False
        self.osc_ratio_set = 1.1
        
        self.Hlayout = QtWidgets.QHBoxLayout(self)
        # 創建分割器
        #self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        #self.Hlayout.addWidget(self.splitter)
        
        self.right_wid = QtWidgets.QWidget()
        self.left_wid = QtWidgets.QWidget()
        self.left_wid.setGeometry(0,0,500,1200)
        self.right_part = QtWidgets.QHBoxLayout(self.right_wid)
        self.left_part = QtWidgets.QVBoxLayout(self.left_wid)
        self.strategy_ui()
        self.ReportTablet_ui()
        self.Hlayout.addWidget(self.left_wid)
        self.Hlayout.addWidget(self.right_wid)
        self.Hlayout.setStretchFactor(self.left_wid,1)
        self.Hlayout.setStretchFactor(self.right_wid,3)
        #self.splitter.addWidget(self.left_wid)
        #self.splitter.addWidget(self.right_wid)
        # 存儲已打開的標籤頁
        self.opened_tabs = ["損益歷史紀錄"]
        self.settings_saved = False
        
    def receive_checkbox_states(self, states):
        # 接收子視窗傳來的 checkbox 狀態
        self.checkbox_states = states
    
    def strategy_ui(self):
        
        self.strategy_wid = QtWidgets.QWidget(self)
        
        self.strategy_wid_V = QtWidgets.QVBoxLayout(self.strategy_wid)
        self.strategyLb = QtWidgets.QLabel(self)
        self.strategyLb.setObjectName("StrategyLabel")
        self.strategyLb.setText("策略設定")
        self.strategyLb.setStyleSheet("""
                                      QLabel {
                                          font-family: 微軟正黑體;
                                          font-size: 50px;
                                          color: blue;
                                          font-weight: bold;
                                      }
                                      """)
        
        #self.strategyLb.move(50,20)
        self.strategy_wid_V.addWidget(self.strategyLb)
        self.left_wid_1 = QtWidgets.QWidget()
        self.left_wid_2 = QtWidgets.QWidget()
        self.left_wid_3 = QtWidgets.QWidget()
        self.left_wid_4 = QtWidgets.QWidget()
        self.left_wid_5 = QtWidgets.QWidget()
        self.left_wid_6 = QtWidgets.QWidget()
        self.left_wid_7 = QtWidgets.QWidget()
        self.left_wid_8 = QtWidgets.QWidget()
        self.left_wid_9 = QtWidgets.QWidget()
        self.left_wid_10 = QtWidgets.QWidget()
        self.left_Vlayout1 = QtWidgets.QHBoxLayout(self.left_wid_1)
        self.left_Vlayout2 = QtWidgets.QHBoxLayout(self.left_wid_2)
        self.left_Vlayout3 = QtWidgets.QHBoxLayout(self.left_wid_3)
        self.left_Vlayout4 = QtWidgets.QHBoxLayout(self.left_wid_4)
        self.left_Vlayout5 = QtWidgets.QHBoxLayout(self.left_wid_5)
        self.left_Vlayout6 = QtWidgets.QHBoxLayout(self.left_wid_6)
        self.left_Vlayout7 = QtWidgets.QHBoxLayout(self.left_wid_7)
        self.left_Vlayout8 = QtWidgets.QHBoxLayout(self.left_wid_8)
        self.left_Vlayout9 = QtWidgets.QHBoxLayout(self.left_wid_9)
        self.left_Vlayout10 = QtWidgets.QHBoxLayout(self.left_wid_10)
        
        self.tacticCheckbtn1 = QtWidgets.QCheckBox("(不分正負)\n頂背離",self)
        #self.tacticCheckbtn1.move(50,100)
        self.tacticCheckbtn1.setChecked(True)
        self.left_Vlayout1.addWidget(self.tacticCheckbtn1)
        self.tacticCheckbtn3 = QtWidgets.QCheckBox("(不分正負)\n底背離",self)
        #self.tacticCheckbtn3.move(50,220)
        self.tacticCheckbtn3.setChecked(True)
        self.left_Vlayout3.addWidget(self.tacticCheckbtn3)
        self.tacticCheckbtn5 = QtWidgets.QCheckBox("頂背離",self)
        #self.tacticCheckbtn4.move(50,280)
        self.tacticCheckbtn5.setChecked(True)
        self.left_Vlayout5.addWidget(self.tacticCheckbtn5)
        self.tacticCheckbtn6 = QtWidgets.QCheckBox("底背離",self)
        #self.tacticCheckbtn4.move(50,280)
        self.tacticCheckbtn6.setChecked(True)
        self.left_Vlayout6.addWidget(self.tacticCheckbtn6)
        self.tacticCheckbtn2 = QtWidgets.QCheckBox("頂背離止損",self)
        #self.tacticCheckbtn2.move(50,160)
        self.tacticCheckbtn2.setChecked(True)
        self.left_Vlayout2.addWidget(self.tacticCheckbtn2)
        self.tacticCheckbtn4 = QtWidgets.QCheckBox("底背離止損",self)
        #self.tacticCheckbtn4.move(50,280)
        self.tacticCheckbtn4.setChecked(True)
        self.left_Vlayout4.addWidget(self.tacticCheckbtn4)
        
        self.adjustBtn1 = QtWidgets.QPushButton("調整定義",self)
        self.adjustBtn1.clicked.connect(self.open_top_define_setting)
        self.left_Vlayout1.addWidget(self.adjustBtn1)
        self.adjustBtn2 = QtWidgets.QPushButton("不可調整",self)
        self.adjustBtn2.setDisabled(True)
        self.left_Vlayout2.addWidget(self.adjustBtn2)
        self.adjustBtn3 = QtWidgets.QPushButton("調整定義",self)
        self.adjustBtn3.clicked.connect(self.open_bot_define_setting)
        self.left_Vlayout3.addWidget(self.adjustBtn3)
        self.adjustBtn4 = QtWidgets.QPushButton("不可調整",self)
        self.adjustBtn4.setDisabled(True)
        #self.adjustBtn4.move(250,270)
        self.left_Vlayout4.addWidget(self.adjustBtn4)
        self.adjustBtn5 = QtWidgets.QPushButton("調整定義",self)
        self.adjustBtn5.clicked.connect(self.open_posi_top_define_setting)
        #self.adjustBtn5.setDisabled(True)
        #self.adjustBtn4.move(250,270)
        self.left_Vlayout5.addWidget(self.adjustBtn5)
        self.adjustBtn6 = QtWidgets.QPushButton("調整定義",self)
        self.adjustBtn6.clicked.connect(self.open_nega_bot_define_setting)
        #self.adjustBtn6.setDisabled(True)
        #self.adjustBtn4.move(250,270)
        self.left_Vlayout6.addWidget(self.adjustBtn6)
        
        self.tacticCheckbtn7 = QtWidgets.QCheckBox("OSC絕對值比例",self)
        self.tacticCheckbtn7.setChecked(True)
        self.left_Vlayout7.addWidget(self.tacticCheckbtn7)
        self.adjustBtn7 = QtWidgets.QPushButton("調整定義",self)
        self.adjustBtn7.clicked.connect(self.open_osc_ratio_setting)
        self.left_Vlayout7.addWidget(self.adjustBtn7)
        
        self.skip_reverse = QtWidgets.QCheckBox("與上上一個波峰/波谷\n判斷背離",self)
        self.skip_reverse.setChecked(True)
        self.left_Vlayout8.addWidget(self.skip_reverse)
        self.adjustBtn8 = QtWidgets.QPushButton("不可調整",self)
        self.adjustBtn8.setDisabled(True)
        self.left_Vlayout8.addWidget(self.adjustBtn8)
        
        self.no_inverse_in_middle = QtWidgets.QCheckBox("中途不可翻正/翻負\n才可以判斷背離",self)
        self.no_inverse_in_middle.setChecked(True)
        self.left_Vlayout9.addWidget(self.no_inverse_in_middle)
        self.adjustBtn9 = QtWidgets.QPushButton("不可調整",self)
        self.adjustBtn9.setDisabled(True)
        self.left_Vlayout9.addWidget(self.adjustBtn9)
        
        self.enter_time_limits = QtWidgets.QCheckBox("進場時間限制",self)
        self.enter_time_limits.setChecked(True)
        self.left_Vlayout10.addWidget(self.enter_time_limits)
        self.adjustBtn10 = QPushButton("調整進場時間")
        self.adjustBtn10.clicked.connect(self.open_entry_time_settings)
        self.left_Vlayout10.addWidget(self.adjustBtn10)
        
        self.strategy_wid_V.addWidget(self.left_wid_1)
        self.strategy_wid_V.addWidget(self.left_wid_2)
        self.strategy_wid_V.addWidget(self.left_wid_3)
        self.strategy_wid_V.addWidget(self.left_wid_4)
        self.strategy_wid_V.addWidget(self.left_wid_5)
        self.strategy_wid_V.addWidget(self.left_wid_6)
        self.strategy_wid_V.addWidget(self.left_wid_7)
        self.strategy_wid_V.addWidget(self.left_wid_8)
        self.strategy_wid_V.addWidget(self.left_wid_9)
        self.strategy_wid_V.addWidget(self.left_wid_10)
        
        self.left_part.addWidget(self.strategy_wid)
        
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setMinimumSize(500,600)
        self.scroll_area.setWidget(self.strategy_wid)
        self.left_part.addWidget(self.scroll_area)
        
        self.settingLb = QtWidgets.QLabel(self)
        self.settingLb.setObjectName("BackTestSettingLabel")
        self.settingLb.setText("回測報告設定")
        self.settingLb.setStyleSheet("""
                                      QLabel {
                                          font-family: 微軟正黑體;
                                          font-size: 50px;
                                          color: blue;
                                          font-weight: bold;
                                      }
                                      """)
        self.left_part.addWidget(self.settingLb)
        
        self.left_wid_5 = QtWidgets.QWidget()
        self.left_Vlayout5 = QtWidgets.QHBoxLayout(self.left_wid_5)
        
        self.date_Lb_st = QtWidgets.QLabel(self)
        self.date_Lb_st.setObjectName("DateLabel_start")
        self.date_Lb_st.setText("開始日期")
        self.left_Vlayout5.addWidget(self.date_Lb_st)
        #self.date_Lb.move(50,50)
        
        self.left_wid_7 = QtWidgets.QWidget()
        self.left_Vlayout7 = QtWidgets.QHBoxLayout(self.left_wid_7)
        
        self.min_15_kbar_cb = QtWidgets.QCheckBox("15分K",self)
        self.min_15_kbar_cb.setEnabled(True)
        self.hr_1_kbar_cb = QtWidgets.QCheckBox("小時K",self)
        self.hr_1_kbar_cb.setEnabled(True)
        self.hr_1_kbar_cb.setChecked(True)
        self.left_Vlayout7.addWidget(self.min_15_kbar_cb)
        self.left_Vlayout7.addWidget(self.hr_1_kbar_cb)
        self.left_part.addWidget(self.left_wid_7)
        
        self.date_val_1 = QtWidgets.QDateEdit(self)
        #self.date_val.setGeometry(110,50,150,30)
        self.date_val_1.setDisplayFormat("yyyy/MM/dd")
        self.date_val_1.setDate(QtCore.QDate().currentDate())
        self.left_Vlayout5.addWidget(self.date_val_1)
        
        self.date_Lb_end = QtWidgets.QLabel(self)
        self.date_Lb_end.setObjectName("DateLabel_end")
        self.date_Lb_end.setText("結束日期")
        self.left_Vlayout5.addWidget(self.date_Lb_end)
        #self.date_Lb.move(50,50)
        self.date_val_2 = QtWidgets.QDateEdit(self)
        #self.date_val.setGeometry(110,50,150,30)
        self.date_val_2.setDisplayFormat("yyyy/MM/dd")
        self.date_val_2.setDate(QtCore.QDate().currentDate())
        self.left_Vlayout5.addWidget(self.date_val_2)
        
        self.left_part.addWidget(self.left_wid_5)
        
        self.left_wid_6 = QtWidgets.QWidget()
        self.left_Vlayout6 = QtWidgets.QHBoxLayout(self.left_wid_6)
        self.principal_Lb = QtWidgets.QLabel(self)
        self.principal_Lb.setText("本金")
        self.left_Vlayout6.addWidget(self.principal_Lb)
        self.principal_val = QtWidgets.QLineEdit(self)
        #self.principal_val.setWidth(500)
        self.left_Vlayout6.addWidget(self.principal_val)
        self.left_part.addWidget(self.left_wid_6)
        
        self.backtestBtn = QtWidgets.QPushButton("開始回測",self)
        self.backtestBtn.setObjectName("BacktestBtn")
        self.backtestBtn.setStyleSheet("""
                                      QPushButton {
                                          font-family: 微軟正黑體;
                                          font-size: 30px;
                                          color: blue;
                                          font-weight: bold;
                                      }
                                      """)
        #self.backtestBtn.move(50,400)
        self.backtestBtn.clicked.connect(self.backTesting)
        self.left_part.addWidget(self.backtestBtn)
        
        self.ReportBtn = QtWidgets.QPushButton("匯出報表",self)
        self.ReportBtn.setStyleSheet("""
                                      QPushButton {
                                          font-family: 微軟正黑體;
                                          font-size: 30px;
                                          color: black;
                                          font-weight: bold;
                                      }
                                      """)
        #self.ReportBtn.move(50,520)
        #self.ReportBtn.clicked.connect(self.saveReportToExcel)
        self.ReportBtn.clicked.connect(self.open_selector)
        self.left_part.addWidget(self.ReportBtn)
    
    def ReportTablet_ui(self):
        '''
        self.ReadReportBtn = QtWidgets.QPushButton("匯入報表")
        self.ReadReportBtn.setStyleSheet("""
                                      QPushButton {
                                          font-family: 微軟正黑體;
                                          font-size: 30px;
                                          color: blue;
                                          font-weight: bold;
                                      }
                                      """)
        #self.ReadReportBtn.move(600,20)
        self.right_part.addWidget(self.ReadReportBtn)
        '''
        self.RecordTable = QtWidgets.QTableWidget(self)
        #self.RecordTable.setGeometry(QtCore.QRect(600,100,1200,1000))
        self.RecordTable.setObjectName("RecordTable")
        self.RecordTable.setColumnCount(7)
        self.RecordTable.setHorizontalHeaderLabels(["時間級別","淨利($)","淨利(%)","平均獲利\n虧損比($)","平均獲利\n虧損比(%)","最大區間虧損($)","最大區間虧損(%)"])
        
        self.tabwid = QtWidgets.QTabWidget(self)
        self.tabwid.setTabsClosable(True)
        self.tabwid.tabCloseRequested.connect(self.close_tab_func)
        self.tab1 = QtWidgets.QWidget(self)
        self.tab1_layout = QtWidgets.QVBoxLayout(self.tab1)
        self.tab1_layout.addWidget(self.RecordTable)
        self.tabwid.addTab(self.tab1,"損益歷史紀錄")
        self.right_part.addWidget(self.tabwid)
        self.his_df = pd.DataFrame([["","","","","","",""]],columns=["時間級別","淨利($)","淨利(%)","平均獲利\n虧損比($)","平均獲利\n虧損比(%)","最大區間虧損($)","最大區間虧損(%)"])
        self.df_dict = {}
        self.df_dict["損益歷史紀錄"] = self.his_df
        self.text_list = QtWidgets.QListWidget(self)
        self.text_list.setMaximumWidth(300)  # 限制列表寬度
        self.text_list.addItem("損益歷史紀錄")
        self.right_part.addWidget(self.text_list)
    
    def close_tab_func(self,index):
        self.tabwid.removeTab(index)
    
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

    def open_selector(self):
        dialog = DataFrameSelector(self.df_dict, self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            selected = dialog.get_selected_dataframes()
            self.save_dataframes(selected)
    
    def save_dataframes(self, selected_df_names):
        # 實際儲存DataFrame的邏輯
        saveFolder = QtWidgets.QFileDialog.getExistingDirectory(self,"儲存位置")
        saveFileName,_ok = QtWidgets.QInputDialog.getText(self,"匯出設定","請輸入檔名：")
        if _ok and (not saveFileName):
            self._info = QtWidgets.QMessageBox(self)
            self._info.information(self,"提醒",f'檔名不可空白!!!')
            return 
        savepath = os.path.join(saveFolder,saveFileName+".xlsx")
        if _ok:
            with pd.ExcelWriter(savepath) as wt:
                for df_name in selected_df_names:
                    df = self.df_dict[df_name]
                    temp_sheetName = re.sub(r":","",df_name)
                    df.to_excel(wt,sheet_name=temp_sheetName,index=False)
        else:
            return 
            
        # 顯示儲存成功的訊息
        self._info = QtWidgets.QMessageBox(self)
        self._info.information(self,"訊息",f'已將報表儲存為 {saveFileName}.xlsx !!!')
   
    def putDfToTableUI(self,df:pd.DataFrame):
        columns = df.columns.tolist()
        for r in range(len(df)):
            temp_row = r+1
            self.temp_RecordTable.insertRow(temp_row)
            for c in columns:
                tempItem = QtWidgets.QTableWidgetItem(str(df.loc[r,c]))
                self.temp_RecordTable.setItem(temp_row,columns.index(c),tempItem)
                
    def dataframe_to_table(self, df, table):
        """將 DataFrame 轉換為 QTableWidget"""
        # 設置表格行數和列數
        table.setRowCount(df.shape[0])
        table.setColumnCount(df.shape[1])
        
        # 設置表格的標題行
        table.setHorizontalHeaderLabels(df.columns)
        
        # 填充表格數據
        for row in range(df.shape[0]):
            for col in range(df.shape[1]):
                item = QTableWidgetItem(str(df.iloc[row, col]))
                table.setItem(row, col, item)
        
        return table
    
    def add_new_table_tab(self, item):
        df_name = item.text()
        
        # 檢查是否已經打開了這個標籤頁
        if df_name in self.opened_tabs:
            # 如果已經打開，就切換到該標籤頁
            for i in range(self.tabwid.count()):
                if self.tabwid.tabText(i) == df_name:
                    self.tabwid.setCurrentIndex(i)
                    return
        
        # 獲取相應的 DataFrame
        df = self.df_dict.get(df_name)
        if df is None:
            return
        
        # 創建新的標籤頁
        new_tab = QWidget()
        tab_layout = QVBoxLayout()
        
        # 創建 QTableWidget
        table = QTableWidget()
        
        # 將 DataFrame 轉換為表格
        self.dataframe_to_table(df, table)
        
        # 添加表格到標籤頁
        tab_layout.addWidget(table)
        new_tab.setLayout(tab_layout)
        
        # 添加新標籤頁
        index = self.tabwid.addTab(new_tab, df_name)
        self.tabwid.setCurrentIndex(index)
        
        # 記錄已打開的標籤頁
        self.opened_tabs.append(df_name)
    
    def close_tab(self, index):
        # 獲取標籤頁文字
        tab_text = self.tabwid.tabText(index)
        
        # 移除標籤頁
        self.tabwid.removeTab(index)
        
        # 從已打開列表中移除
        if tab_text in self.opened_tabs:
            self.opened_tabs.remove(tab_text)
    
    def open_top_define_setting(self):
        dialog = AdjustTopReverseDefination_ui(self.top_def_ck1,self.top_def_ck2, self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.top_def_ck1,self.top_def_ck2 = dialog.getDefineState()
    
    def open_bot_define_setting(self):
        dialog = AdjustBotReverseDefination_ui(self.bot_def_ck1,self.bot_def_ck2, self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.bot_def_ck1,self.bot_def_ck2 = dialog.getDefineState()
            
    def open_posi_top_define_setting(self):
        dialog = PositiveAdjustTopReverseDefination_ui(self.posi_top_def_ck1,self.posi_top_def_ck2, self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.posi_top_def_ck1,self.posi_top_def_ck2 = dialog.getDefineState()
    
    def open_nega_bot_define_setting(self):
        dialog = NegativeAdjustBotReverseDefination_ui(self.nega_bot_def_ck1,self.nega_bot_def_ck2, self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.nega_bot_def_ck1,self.nega_bot_def_ck2 = dialog.getDefineState()
       
    def open_osc_ratio_setting(self):
        dialog = RatioOfOSCs(osc_ratio=self.osc_ratio_set,parent=self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.osc_ratio_set = dialog.get_new_osc_ratio()
    
    def open_entry_time_settings(self):
        """Opens the main entry time settings window."""
        # 將所有設定傳遞給 EntryTimeSettingsWindow
        settings_window = EntryTimeSettingsWindow(self, all_settings_data=self.all_time_settings)
        
        # 顯示為模態對話框，並檢查回傳結果
        if settings_window.exec_() == QtWidgets.QDialog.Accepted:
            # 如果 EntryTimeSettingsWindow 被關閉，則獲取其內部更新後的設定
            self.all_time_settings = settings_window.get_all_settings()
            # 統一由 MainWindow 將所有設定儲存回 JSON
            self.save_all_settings(self.all_time_settings)
            QMessageBox.information(self, "設定更新", "所有進場時間設定已更新並儲存。")
            print(f"MainWindow 統一儲存所有設定: {self.all_time_settings}")
class DetailedTimeSettingsWindow(QtWidgets.QDialog):
    def __init__(self, parent=None, setting_type="未知設定", initial_data=None):
        super().__init__(parent)
        self.setWindowTitle(f"進場時間設定 - {setting_type}")
        self.setGeometry(300, 300, 400, 300)

        self.setting_type = setting_type
        # 接收傳入的初始資料，如果沒有則為空列表
        self.initial_data = initial_data if initial_data is not None else []
        self.time_slots = [] # To store QTimeEdit pairs and their layouts
        self.init_ui()
        self.load_initial_times() # Load times from the passed initial_data

        # 這個變數將用於儲存介面關閉時的回傳值
        self.saved_ranges = []

    def init_ui(self):
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        self.time_slots_layout = QVBoxLayout()
        main_layout.addLayout(self.time_slots_layout)

        button_layout = QHBoxLayout()
        self.add_period_button = QPushButton("新增時段")
        self.save_settings_button = QPushButton("儲存設定")

        # 使用 lambda 確保 add_time_slot_row 在被點擊時，不接收任何信號的參數
        self.add_period_button.clicked.connect(lambda: self.add_time_slot_row())
        self.save_settings_button.clicked.connect(self.save_settings)

        button_layout.addWidget(self.add_period_button)
        button_layout.addWidget(self.save_settings_button)

        main_layout.addLayout(button_layout)
        main_layout.addStretch()

    def load_initial_times(self):
        """根據傳入的 initial_data 初始化 QTimeEdit。"""
        if self.initial_data:
            for slot in self.initial_data:
                start_str = slot.get("start", "00:00:00")
                end_str = slot.get("end", "00:00:00")
                self.add_time_slot_row(start_str[:5], end_str[:5]) # 載入時只取 HH:mm
        else:
            # 如果沒有傳入數據，則不預設添加時段，因為現在預設值由 JSON 管理
            pass 

    def add_time_slot_row(self, start_time_str="00:00", end_time_str="00:00"):
        row_layout = QHBoxLayout()
        
        slot_number = len(self.time_slots) + 1
        label = QLabel(f"時段 {slot_number} :")
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        row_layout.addWidget(label)

        start_time_edit = QtWidgets.QTimeEdit(self)
        start_time_edit.setDisplayFormat("HH:mm")
        start_time_edit.setTime(QtCore.QTime.fromString(start_time_str, "HH:mm"))
        row_layout.addWidget(start_time_edit)

        dash_label = QLabel("~")
        row_layout.addWidget(dash_label)

        end_time_edit = QtWidgets.QTimeEdit(self)
        end_time_edit.setDisplayFormat("HH:mm")
        end_time_edit.setTime(QtCore.QTime.fromString(end_time_str, "HH:mm"))
        row_layout.addWidget(end_time_edit)

        delete_button = QPushButton("X")
        delete_button.setFixedSize(20, 20)
        delete_button.clicked.connect(lambda _, rl=row_layout, tse=(start_time_edit, end_time_edit, row_layout): self.remove_time_slot_row(rl, tse))
        row_layout.addWidget(delete_button)

        self.time_slots_layout.addLayout(row_layout)
        self.time_slots.append((start_time_edit, end_time_edit, row_layout))

    def remove_time_slot_row(self, row_layout_to_remove, time_slot_tuple_to_remove):
        self.time_slots.remove(time_slot_tuple_to_remove)

        while row_layout_to_remove.count():
            item = row_layout_to_remove.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.time_slots_layout.removeItem(row_layout_to_remove)
        row_layout_to_remove.deleteLater()

        self.update_slot_numbers()

    def update_slot_numbers(self):
        for i, (_, _, row_layout) in enumerate(self.time_slots):
            label = row_layout.itemAt(0).widget()
            if isinstance(label, QLabel):
                label.setText(f"時段 {i + 1} :")

    def save_settings(self):
        # 收集當前介面中的時間段
        current_edited_ranges = []
        for i, (start_edit, end_edit, _) in enumerate(self.time_slots):
            start_time = start_edit.time().toString("HH:mm:ss")
            end_time = end_edit.time().toString("HH:mm:ss")
            current_edited_ranges.append({"start": start_time, "end": end_time})
        
        # 將結果儲存到 self.saved_ranges，以便父視窗可以獲取
        self.saved_ranges = current_edited_ranges
        
        #QMessageBox.information(self, "設定已儲存", f"已儲存以下時間段設定到 '{self.setting_type}'：\n{current_edited_ranges}")
        #print(f"從 DetailedTimeSettingsWindow 儲存的設定 ({self.setting_type}): {current_edited_ranges}")

        # 這裡不直接儲存到 JSON，而是讓父視窗 (MainWindow) 處理
        # 關閉視窗，並以 QDialog.Accepted 狀態回傳
        self.accept() 

    def get_saved_ranges(self):
        """提供一個方法讓父視窗獲取儲存的數據"""
        return self.saved_ranges

class EntryTimeSettingsWindow(QtWidgets.QDialog):
    def __init__(self, parent=None, all_settings_data=None):
        super().__init__(parent)
        self.setWindowTitle("調整進場時間設定")
        self.setGeometry(200, 200, 450, 300)

        self.all_settings = all_settings_data if all_settings_data is not None else {}
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # 15分K Group
        group_15min_k = QtWidgets.QGroupBox("15分K")
        layout_15min_k = QVBoxLayout()
        
        # 15分K - 做多
        layout_15min_long = QHBoxLayout()
        label_15min_long = QLabel("做多")
        btn_15min_long = QPushButton("調整進場時間")
        btn_15min_long.clicked.connect(lambda: self.open_detailed_settings("15分K - 做多"))
        layout_15min_long.addWidget(label_15min_long)
        layout_15min_long.addStretch()
        layout_15min_long.addWidget(btn_15min_long)
        layout_15min_k.addLayout(layout_15min_long)

        # 15分K - 做空
        layout_15min_short = QHBoxLayout()
        label_15min_short = QLabel("做空")
        btn_15min_short = QPushButton("調整進場時間")
        btn_15min_short.clicked.connect(lambda: self.open_detailed_settings("15分K - 做空"))
        layout_15min_short.addWidget(label_15min_short)
        layout_15min_short.addStretch()
        layout_15min_short.addWidget(btn_15min_short)
        layout_15min_k.addLayout(layout_15min_short)

        group_15min_k.setLayout(layout_15min_k)
        main_layout.addWidget(group_15min_k)

        # 小時K Group
        group_hour_k = QtWidgets.QGroupBox("小時K")
        layout_hour_k = QVBoxLayout()

        # 小時K - 做多
        layout_hour_long = QHBoxLayout()
        label_hour_long = QLabel("做多")
        btn_hour_long = QPushButton("調整進場時間")
        btn_hour_long.clicked.connect(lambda: self.open_detailed_settings("小時K - 做多"))
        layout_hour_long.addWidget(label_hour_long)
        layout_hour_long.addStretch()
        layout_hour_long.addWidget(btn_hour_long)
        layout_hour_k.addLayout(layout_hour_long)

        # 小時K - 做空
        layout_hour_short = QHBoxLayout()
        label_hour_short = QLabel("做空")
        btn_hour_short = QPushButton("調整進場時間")
        btn_hour_short.clicked.connect(lambda: self.open_detailed_settings("小時K - 做空"))
        layout_hour_short.addWidget(label_hour_short)
        layout_hour_short.addStretch()
        layout_hour_short.addWidget(btn_hour_short)
        layout_hour_k.addLayout(layout_hour_short)

        group_hour_k.setLayout(layout_hour_k)
        main_layout.addWidget(group_hour_k)
        
        main_layout.addStretch()

    def open_detailed_settings(self, setting_type):
        """Opens the detailed time settings window for a specific type."""
        # 從總設定中獲取當前設定類型對應的數據
        current_type_data = self.all_settings.get(setting_type, [])
        detailed_window = DetailedTimeSettingsWindow(self, setting_type, initial_data=current_type_data)
        
        # 顯示為模態對話框，並檢查回傳結果
        if detailed_window.exec_() == QtWidgets.QDialog.Accepted:
            # 如果使用者點擊了 "儲存設定" 並關閉了視窗
            updated_ranges = detailed_window.get_saved_ranges()
            self.all_settings[setting_type] = updated_ranges
            #print(f"從 DetailedTimeSettingsWindow 回傳的設定 ({setting_type}): {updated_ranges}")
            # 這裡不直接儲存到 JSON，而是等待 EntryTimeSettingsWindow 關閉時由 MainWindow 統一處理

    def get_all_settings(self):
        """提供一個方法讓父視窗獲取所有修改後的設定"""
        return self.all_settings
          
class AdjustTopReverseDefination_ui(QtWidgets.QDialog):
    def __init__(self, top_def_ck1, top_def_ck2, parent=None):
        super().__init__(parent)
        #self.parent_widget = parent #可能不需要這一行也可以稱為子視窗
        self.o_top_def_ck1 = top_def_ck1
        self.o_top_def_ck2 = top_def_ck2
        self.setObjectName("TopReverseDefine")
        self.setWindowTitle("頂背離 定義設定")
        self.resize(550,300)
        self.Layout_V = QtWidgets.QVBoxLayout(self)
        
        self.define1_ckb = QtWidgets.QCheckBox(self)
        self.define1_ckb.setText("過去OSC>當前OSC 但 過去最高價<現在最高價")
        self.define1_ckb.setChecked(self.o_top_def_ck1)
        self.Layout_V.addWidget(self.define1_ckb)
        self.define2_ckb = QtWidgets.QCheckBox(self)
        self.define2_ckb.setText("過去OSC<當前OSC 但 過去最高價>現在最高價")
        self.define2_ckb.setChecked(self.o_top_def_ck2)
        self.Layout_V.addWidget(self.define2_ckb)
        
         # 建立按鈕 (確定/取消)
        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Cancel | QtWidgets.QDialogButtonBox.Ok,self)
        button_box.accepted.connect(self.accept_check)
        button_box.rejected.connect(self.reject)
        self.Layout_V.addWidget(button_box)
    
    def accept_check(self):
        if (not self.define1_ckb.isChecked()) and (not self.define2_ckb.isChecked()):
            self._info = QtWidgets.QMessageBox(self)
            self._info.information(self,"警告","請至少勾選一項!!!")
            return
        else:
            self.accept()
    
    def getDefineState(self):
        return self.define1_ckb.isChecked(),self.define2_ckb.isChecked()
    
class AdjustBotReverseDefination_ui(QtWidgets.QDialog):
    def __init__(self, bot_def_ck1, bot_def_ck2, parent=None):
        super().__init__(parent)
        #self.parent_widget = parent #可能不需要這一行也可以稱為子視窗
        self.o_bot_def_ck1 = bot_def_ck1
        self.o_bot_def_ck2 = bot_def_ck2
        self.setObjectName("BottomReverseDefine")
        self.setWindowTitle("底背離 定義設定")
        self.resize(550,300)
        self.init_ui()
    
    def init_ui(self):
        self.Layout_V = QtWidgets.QVBoxLayout(self)
        self.define1_ckb = QtWidgets.QCheckBox(self)
        self.define1_ckb.setText("過去OSC<當前OSC 但 過去最低價>現在最低價")
        self.define1_ckb.setChecked(self.o_bot_def_ck1)
        self.Layout_V.addWidget(self.define1_ckb)
        self.define2_ckb = QtWidgets.QCheckBox(self)
        self.define2_ckb.setText("過去OSC>當前OSC 但 過去最低價<現在最低價")
        self.define2_ckb.setChecked(self.o_bot_def_ck2)
        self.Layout_V.addWidget(self.define2_ckb)
        # 建立按鈕 (確定/取消)
        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Cancel | QtWidgets.QDialogButtonBox.Ok,self)
        button_box.accepted.connect(self.accept_check)
        button_box.rejected.connect(self.reject)
        self.Layout_V.addWidget(button_box)
        # 標記是否已保存設定
        #self.settings_saved = False
    
    def accept_check(self):
        if (not self.define1_ckb.isChecked()) and (not self.define2_ckb.isChecked()):
            self._info = QtWidgets.QMessageBox(self)
            self._info.information(self,"警告","請至少勾選一項!!!")
            return
        else:
            self.accept()
    
    def getDefineState(self):
        return self.define1_ckb.isChecked(),self.define2_ckb.isChecked()

class PositiveAdjustTopReverseDefination_ui(QtWidgets.QDialog):
    def __init__(self, posi_top_def_ck1, posi_top_def_ck2, parent=None):
        super().__init__(parent)
        #self.parent_widget = parent #可能不需要這一行也可以稱為子視窗
        self.o_top_def_ck1 = posi_top_def_ck1
        self.o_top_def_ck2 = posi_top_def_ck2
        #self.setObjectName("TopReverseDefine")
        self.setWindowTitle("頂背離 定義設定")
        self.resize(550,300)
        self.Layout_V = QtWidgets.QVBoxLayout(self)
        
        self.define1_ckb = QtWidgets.QCheckBox(self)
        self.define1_ckb.setText("過去OSC>當前OSC 但 過去最高價<現在最高價")
        self.define1_ckb.setChecked(self.o_top_def_ck1)
        self.Layout_V.addWidget(self.define1_ckb)
        self.define2_ckb = QtWidgets.QCheckBox(self)
        self.define2_ckb.setText("過去OSC<當前OSC 但 過去最高價>現在最高價")
        self.define2_ckb.setChecked(self.o_top_def_ck2)
        self.Layout_V.addWidget(self.define2_ckb)
         # 建立按鈕 (確定/取消)
        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Cancel | QtWidgets.QDialogButtonBox.Ok,self)
        button_box.accepted.connect(self.accept_check)
        button_box.rejected.connect(self.reject)
        self.Layout_V.addWidget(button_box)
    
    def accept_check(self):
        if (not self.define1_ckb.isChecked()) and (not self.define2_ckb.isChecked()):
            self._info = QtWidgets.QMessageBox(self)
            self._info.information(self,"警告","請至少勾選一項!!!")
            return
        else:
            self.accept()
    
    def getDefineState(self):
        return self.define1_ckb.isChecked(),self.define2_ckb.isChecked()

class NegativeAdjustBotReverseDefination_ui(QtWidgets.QDialog):
    def __init__(self, nega_bot_def_ck1, nega_bot_def_ck2, parent=None):
        super().__init__(parent)
        #self.parent_widget = parent #可能不需要這一行也可以稱為子視窗
        self.o_bot_def_ck1 = nega_bot_def_ck1
        self.o_bot_def_ck2 = nega_bot_def_ck2
        self.setObjectName("BottomReverseDefine")
        self.setWindowTitle("底背離 定義設定")
        self.resize(550,300)
        self.init_ui()
    
    def init_ui(self):
        self.Layout_V = QtWidgets.QVBoxLayout(self)
        self.define1_ckb = QtWidgets.QCheckBox(self)
        self.define1_ckb.setText("過去OSC<當前OSC 但 過去最低價>現在最低價")
        self.define1_ckb.setChecked(self.o_bot_def_ck1)
        self.Layout_V.addWidget(self.define1_ckb)
        self.define2_ckb = QtWidgets.QCheckBox(self)
        self.define2_ckb.setText("過去OSC>當前OSC 但 過去最低價<現在最低價")
        self.define2_ckb.setChecked(self.o_bot_def_ck2)
        self.Layout_V.addWidget(self.define2_ckb)
        # 建立按鈕 (確定/取消)
        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Cancel | QtWidgets.QDialogButtonBox.Ok,self)
        button_box.accepted.connect(self.accept_check)
        button_box.rejected.connect(self.reject)
        self.Layout_V.addWidget(button_box)
        # 標記是否已保存設定
        #self.settings_saved = False
    
    def accept_check(self):
        if (not self.define1_ckb.isChecked()) and (not self.define2_ckb.isChecked()):
            self._info = QtWidgets.QMessageBox(self)
            self._info.information(self,"警告","請至少勾選一項!!!")
            return
        else:
            self.accept()
    
    def getDefineState(self):
        return self.define1_ckb.isChecked(),self.define2_ckb.isChecked()

class DataFrameSelector(QtWidgets.QDialog):
    def __init__(self, dataframes, parent=None):
        super().__init__(parent)
        self.dataframes = dataframes
        self.selected_dataframes = []
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle('選擇要儲存的報表')
        self.setMinimumWidth(400)
        
        # 創建捲動區域以容納大量的DataFrame
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        scroll_layout = QVBoxLayout(content_widget)
        
        # 顯示說明文字
        info_label = QLabel('請勾選您想要儲存的報表:')
        scroll_layout.addWidget(info_label)
        
        # 建立所有DataFrame的核取方塊
        self.checkboxes = {}
        for df_name in self.dataframes:
            checkbox = QtWidgets.QCheckBox(df_name)
            self.checkboxes[df_name] = checkbox
            scroll_layout.addWidget(checkbox)
        
        scroll.setWidget(content_widget)
        
        # 建立按鈕 (確定/取消)
        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept_selection)
        button_box.rejected.connect(self.reject)
        
        # 主佈局
        main_layout = QVBoxLayout()
        main_layout.addWidget(scroll)
        main_layout.addWidget(button_box)
        self.setLayout(main_layout)
    
    def accept_selection(self):
        # 收集所有被勾選的DataFrame
        self.selected_dataframes = [df_name for df_name, checkbox in self.checkboxes.items() 
                                  if checkbox.isChecked()]
        
        if not self.selected_dataframes:
            QMessageBox.warning(self, "警告", "您沒有選擇任何報表")
            return
            
        self.accept()
        
    def get_selected_dataframes(self):
        return self.selected_dataframes

class RatioOfOSCs(QtWidgets.QDialog):
    def __init__(self, osc_ratio ,parent=None):
        super().__init__(parent)
        self.osc_ratio = osc_ratio
        self.resize(200,300)
        self.InitUI()
    
    def InitUI(self):
        self.Layout_V = QtWidgets.QVBoxLayout(self)
        self.defination_wid = QtWidgets.QWidget(self)
        self.setWindowTitle("OSC絕對值比例設定")
        self.layout_h = QtWidgets.QHBoxLayout(self.defination_wid)
        self.defination_label = QtWidgets.QLabel(self)
        self.defination_label.setText("(三個OSC絕對值最大值)/(三個OSC絕對值最小值) > ")
        self.layout_h.addWidget(self.defination_label)
        self.val_entry = QtWidgets.QLineEdit(self)
        self.val_entry.setText(str(self.osc_ratio))
        self.layout_h.addWidget(self.val_entry)
        self.Layout_V.addWidget(self.defination_wid)
        # 建立按鈕 (確定/取消)
        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Cancel | QtWidgets.QDialogButtonBox.Ok,self)
        button_box.accepted.connect(self.accept_check)
        button_box.rejected.connect(self.reject)
        self.Layout_V.addWidget(button_box)
    
    def accept_check(self):
        try:
            float(self.val_entry.text())
        except:
            QMessageBox.warning(self, "警告", "OSC絕對值比例請填寫數值!!!")
            return
        
        if not self.val_entry.text():
            QMessageBox.warning(self, "警告", "請填寫OSC絕對值比例!!!")
            return
        elif float(self.val_entry.text()) <= 0:
            QMessageBox.warning(self, "警告", "OSC絕對值比例請填寫正數!!!")
            return
        else:
            self.accept()
    
    def get_new_osc_ratio(self):
        return float(self.val_entry.text())
    