import pandas as pd
from flask import Flask, request, jsonify, render_template
from flask.json.provider import JSONProvider
from strategy import Strategy, update_data_files
import os
import threading
import json
import traceback
import numpy as np
import datetime

# ==================================================================
# 自定義 JSON Provider 來處理特殊資料型別
# ==================================================================

class CustomJSONProvider(JSONProvider):
    """
    自定義的 JSON Provider，用於處理 NumPy 和 Pandas 的特殊資料型別。
    這是 Flask 2.3+ 建議的作法。
    """
    def dumps(self, obj, **kwargs):
        return json.dumps(obj, **kwargs, cls=NpEncoder)

    def loads(self, s, **kwargs):
        return json.loads(s, **kwargs)

class NpEncoder(json.JSONEncoder):
    """ 
    自定義的 JSON Encoder，將特殊型別轉換為可序列化的格式。
    """
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (pd.Timestamp, datetime.datetime, datetime.date)):
            return obj.isoformat()
        return super(NpEncoder, self).default(obj)

# --- Flask App 初始化 ---
app = Flask(__name__)
# 應用新的 JSON Provider
app.json = CustomJSONProvider(app)


# --- 全域設定 ---
data_lock = threading.Lock()
DATA_MAP = {"小時K": pd.DataFrame(), "15分K": pd.DataFrame()}
SETTINGS_FILE_PATH = "all_time_settings.json"


# ==================================================================
# 後端函式
# ==================================================================

def load_data_from_disk():
    """從硬碟載入 Excel 檔案到記憶體中"""
    global DATA_MAP
    try:
        with data_lock:
            print("正在從硬碟載入資料...")
            df_1h = pd.read_excel('小時k.xlsx')
            df_15m = pd.read_excel('15分k.xlsx')
            df_1h['日期'] = pd.to_datetime(df_1h['日期'])
            df_15m['日期'] = pd.to_datetime(df_15m['日期'])
            DATA_MAP = {"小時K": df_1h, "15分K": df_15m}
            print("資料載入成功。")
    except FileNotFoundError as e:
        print(f"錯誤：找不到資料檔案: {e}。請確保檔案與 app.py 在同一目錄下。")
    except Exception as e:
        print(f"載入資料時發生錯誤: {e}")

# ==================================================================
# API 端點 (Routes)
# ==================================================================

@app.route('/')
def index():
    """渲染主頁面"""
    return render_template('index.html')

@app.route('/api/time_settings', methods=['GET', 'POST'])
def handle_time_settings():
    """處理進場時間設定的讀取與儲存"""
    if request.method == 'GET':
        try:
            with open(SETTINGS_FILE_PATH, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                return jsonify(settings)
        except FileNotFoundError:
            return jsonify({"error": f"找不到設定檔: {SETTINGS_FILE_PATH}"}), 404
        except Exception as e:
            return jsonify({"error": f"讀取設定檔時發生錯誤: {e}"}), 500

    if request.method == 'POST':
        try:
            new_settings = request.json
            with open(SETTINGS_FILE_PATH, 'w', encoding='utf-8') as f:
                json.dump(new_settings, f, indent=4, ensure_ascii=False)
            return jsonify({"message": "設定已成功儲存"}), 200
        except Exception as e:
            return jsonify({"error": f"儲存設定檔時發生錯誤: {e}"}), 500


@app.route('/update_data', methods=['POST'])
def update_data_endpoint():
    """觸發資料更新的 API 端點"""
    try:
        message = update_data_files()
        load_data_from_disk()
        return jsonify({"message": message}), 200
    except Exception as e:
        print(f"資料更新過程中發生錯誤: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

@app.route('/run_backtest', methods=['POST'])
def run_backtest_endpoint():
    """執行回測的 API 端點"""
    try:
        settings = request.json
        time_levels = settings.get('time_levels', [])
        if not time_levels:
            return jsonify({"error": "請至少選擇一個時間級別。"}), 400

        final_response = {
            "historical_summary": {"columns": [], "data": []},
            "new_reports": {}
        }
        
        summary_data = []
        summary_cols = []

        with data_lock: 
            for level in time_levels:
                df = DATA_MAP.get(level)
                if df is None or df.empty:
                    continue
                
                settings['timelevel'] = level 
                strategy_engine = Strategy(settings)
                result = strategy_engine.run_backtest(df.copy(), settings['start_date'], settings['end_date'])
                
                if result.get("error"):
                    return jsonify(result), 400

                def format_df_for_json(df_to_format):
                    if df_to_format is None or df_to_format.empty: return {"columns": [], "data": []}
                    df_copy = df_to_format.copy()
                    # 主動將日期時間相關欄位轉為字串，作為備用方案
                    for col in df_copy.select_dtypes(include=['datetime', 'datetimetz']).columns:
                        df_copy[col] = df_copy[col].astype(str)
                    df_reset = df_copy.reset_index(drop=True)
                    data = df_reset.where(pd.notnull(df_reset), None).to_dict(orient='split')['data']
                    return {"columns": df_reset.columns.tolist(), "data": data}

                time_suffix = pd.Timestamp.now().strftime('%H:%M:%S')
                
                final_response["new_reports"][f'{level}_策略交易明細 {time_suffix}'] = format_df_for_json(result.get("signal_df"))
                final_response["new_reports"][f'{level}_買賣交易明細 {time_suffix}'] = format_df_for_json(result.get("trade_df"))
                final_response["new_reports"][f'{level}_總表 {time_suffix}'] = format_df_for_json(result.get("full_df"))
                
                if result.get("summary_stats"):
                    summary_data.append(list(result["summary_stats"].values()))
                    if not summary_cols:
                        summary_cols = list(result["summary_stats"].keys())

        if summary_data:
            final_response['historical_summary'] = {"columns": summary_cols, "data": summary_data}
            
        return jsonify(final_response)

    except Exception as e:
        print(f"執行回測時發生未預期的伺服器錯誤: {traceback.format_exc()}")
        return jsonify({"error": f"伺服器內部錯誤: {e}"}), 500

if __name__ == '__main__':
    load_data_from_disk()
    print("Flask 應用程式準備就緒，正在啟動伺服器...")
    print("請在瀏覽器中開啟 http://您的本機IP:5001")
    app.run(host="0.0.0.0", port=5001, debug=False)

