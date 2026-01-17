import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 頁面設定 ---
st.set_page_config(page_title="雲端資產管理系統", layout="centered")

# --- 建立連線 ---
conn = st.connection("gsheets", type=GSheetsConnection)

# 定義分頁變數 (請務必確認 Google Sheets 下方標籤名稱與此一致)
SHEET_STAFF = "staff"
SHEET_CARS = "cars"
SHEET_LOGS = "logs"

def load_all_data():
    try:
        # 改成不指定 worksheet，先看看能不能讀到「預設第一頁」
        st.write("正在測試讀取預設第一頁...")
        df_test = conn.read(ttl=0) 
        st.write("✅ 成功讀到第一頁！標題為：", df_test.columns.tolist())
        
        # 如果上面成功，再讀取特定頁面
        staff = conn.read(worksheet=SHEET_STAFF, ttl=0)
        cars = conn.read(worksheet=SHEET_CARS, ttl=0)
        logs = conn.read(worksheet=SHEET_LOGS, ttl=0)
        return staff, cars, logs
    except Exception as e:
        st.error(f"技術錯誤訊息：{e}")
        st.stop()

def sync_to_cloud(staff_df, cars_df, logs_df):
    """將資料同步回雲端"""
    conn.update(worksheet=SHEET_STAFF, data=staff_df)
    conn.update(worksheet=SHEET_CARS, data=cars_df)
    conn.update(worksheet=SHEET_LOGS, data=logs_df)

# --- 初始載入 ---
if 'page' not in st.session_state:
    st.session_state.page = 'home'

staff_df, cars_df, logs_df = load_all_data()
staff_list = staff_df['人員編號'].astype(str).tolist() if not staff_df.empty else ["無人員資料"]

# --- 介面 ---
if st.session_state.page == 'home':
    st.title("🌐 雲端資產運營中心")
    st.success("連線狀態：正常 (兩地即時同步)")
    
    # 顯示目前統計 (財務儀表板概念)
    cols_info = st.columns(2)
    cols_info[0].metric("目前車輛總數", len(cars_df))
    cols_info[1].metric("今日操作次數", len(logs_df))

    st.write("---")
    cols = st.columns(4)
    if cols[0].button("新增"): st.session_state.page = '新增'; st.rerun()
    if cols[1].button("刪除"): st.session_state.page = '刪除'; st.rerun()
    if cols[2].button("更改"): st.session_state.page = '更改'; st.rerun()
    if cols[3].button("查詢"): st.session_state.page = '查詢'; st.rerun()

else:
    if st.sidebar.button("🔙 返回首頁"):
        st.session_state.page = 'home'; st.rerun()

    st.subheader(f"目前作業：{st.session_state.page}")
    
    p_in = st.text_input("輸入車牌號碼")
    w_in = st.number_input("空車重量", min_value=0.0) if st.session_state.page in ['新增', '更改'] else 0.0
    s_in = st.selectbox("操作人員編號", staff_list)

    if st.button(f"確認{st.session_state.page}"):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 1. 操作列表 (Logs) - 永遠將新紀錄置頂
        new_log = pd.DataFrame([[st.session_state.page, p_in, w_in, s_in, now]], columns=logs_df.columns)
        logs_df = pd.concat([new_log, logs_df], ignore_index=True)

        # 2. 車輛列表 (Cars) 處理
        if st.session_state.page in ["新增", "更改"]:
            # 先移除舊紀錄，再把新紀錄插到第一列 (Index 0)
            cars_df = cars_df[cars_df['車牌號碼'] != p_in]
            new_car = pd.DataFrame([[p_in, w_in, now]], columns=cars_df.columns)
            cars_df = pd.concat([new_car, cars_df], ignore_index=True)
        elif st.session_state.page == "刪除":
            cars_df = cars_df[cars_df['車牌號碼'] != p_in]

        # 3. 同步回雲端
        with st.spinner('正在同步數據至雲端...'):
            sync_to_cloud(staff_df, cars_df, logs_df)
        
        st.success(f"操作已完成！資料已同步。")
        st.write(f"時間：{now}")

# 頁尾顯示最新 5 筆紀錄，方便核對
st.write("---")
st.write("🔍 **最新 5 筆操作動態：**")
st.table(logs_df.head(5))



