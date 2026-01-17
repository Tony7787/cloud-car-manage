import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 頁面設定 ---
st.set_page_config(page_title="雲端資產管理系統", layout="centered")

# --- 建立 Google Sheets 連線 ---
# 注意：st.connection 的第一個參數是連線名稱(通常自訂為 "gsheets")
# 真正的試算表網址或 ID 應放在 Streamlit 的 .streamlit/secrets.toml 中
conn = st.connection("gsheets", type=GSheetsConnection)

# 定義分頁名稱變數，確保讀取與寫入完全一致
SHEET_STAFF = "staff"
SHEET_CARS = "cars"
SHEET_LOGS = "logs"

def load_all_data():
    """讀取雲端試算表的三個分頁"""
    # 這裡的 worksheet 名稱必須與 Google Sheets 標籤名稱一模一樣
    staff = conn.read(worksheet=SHEET_STAFF)
    cars = conn.read(worksheet=SHEET_CARS)
    logs = conn.read(worksheet=SHEET_LOGS)
    return staff, cars, logs

def sync_to_cloud(staff_df, cars_df, logs_df):
    """將更新後的 DataFrame 同步回雲端，確保更新正確的分頁"""
    conn.update(worksheet=SHEET_STAFF, data=staff_df)
    conn.update(worksheet=SHEET_CARS, data=cars_df)
    conn.update(worksheet=SHEET_LOGS, data=logs_df)

# --- 網頁邏輯 ---
if 'page' not in st.session_state:
    st.session_state.page = 'home'

# 讀取現有資料
# 提醒：在雲端環境，頻繁 load_data 可能影響速度，實務上可加入快取(ttl)
staff_df, cars_df, logs_df = load_all_data()

# 確保人員列表不為空，避免下拉選單錯誤
if not staff_df.empty:
    staff_list = staff_df['人員編號'].astype(str).tolist()
else:
    staff_list = ["(請先在 staff 分頁新增人員)"]

# --- UI 呈現 ---
if st.session_state.page == 'home':
    st.title("🌐 雲端資產運營中心")
    st.info("目前連線：Google Cloud 資料庫 (兩地即時同步)")
    cols = st.columns(4)
    if cols[0].button("新增"): st.session_state.page = '新增'; st.rerun()
    if cols[1].button("刪除"): st.session_state.page = '刪除'; st.rerun()
    if cols[2].button("更改"): st.session_state.page = '更改'; st.rerun()
    if cols[3].button("查詢"): st.session_state.page = '查詢'; st.rerun()

else:
    if st.sidebar.button("🔙 返回首頁"):
        st.session_state.page = 'home'; st.rerun()

    st.subheader(f"作業模式：{st.session_state.page}")
    p_in = st.text_input("車牌號碼")
    # 只有新增和更改需要輸入重量
    w_in = st.number_input("空車重量", min_value=0.0) if st.session_state.page in ['新增', '更改'] else 0.0
    s_in = st.selectbox("人員編號", staff_list)

    if st.button("確認執行並同步"):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 1. 紀錄 Log 並置頂 (操作列表)
        # 確保新的 DataFrame 欄位名稱與 logs_df 完全符合
        new_log = pd.DataFrame([[st.session_state.page, p_in, w_in, s_in, now]], 
                               columns=logs_df.columns)
        logs_df = pd.concat([new_log, logs_df], ignore_index=True)

        # 2. 處理車輛狀態更新
        if st.session_state.page == "新增" or st.session_state.page == "更改":
            # 移除舊車號紀錄並將新紀錄插在第一列
            cars_df = cars_df[cars_df['車牌號碼'] != p_in]
            new_car = pd.DataFrame([[p_in, w_in, now]], columns=cars_df.columns)
            cars_df = pd.concat([new_car, cars_df], ignore_index=True)
        
        elif st.session_state.page == "刪除":
            # 僅移除該車號
            cars_df = cars_df[cars_df['車牌號碼'] != p_in]

        # 3. 同步回 Google Sheets
        with st.spinner('正在同步全球資料庫...'):
            sync_to_cloud(staff_df, cars_df, logs_df)
        
        st.success(f"同步成功！兩地數據已更新。")
        st.write(f"【最新紀錄】時間：{now} | 車牌：{p_in}")
