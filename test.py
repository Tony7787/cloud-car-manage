import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 頁面設定 ---
st.set_page_config(page_title="雲端資產管理系統", layout="centered")

# --- 建立 Google Sheets 連線 ---
# 在 Streamlit Cloud 部署時，需在 Secrets 設定中貼上 Google Sheet 網址
conn = st.connection("1w2Fl2nc7ptfrSGTa4yARI_Opl7CWvcVFjfNu1Q2Wzus", type=GSheetsConnection)

def load_all_data():
    """讀取雲端試算表的三個分頁"""
    staff = conn.read(worksheet="staff")
    cars = conn.read(worksheet="cars")
    logs = conn.read(worksheet="logs")
    return staff, cars, logs

def sync_to_cloud(staff_df, cars_df, logs_df):
    """將更新後的 DataFrame 同步回雲端"""
    # 此處邏輯會更新對應的工作表
    conn.update(worksheet="人員列表", data=staff_df)
    conn.update(worksheet="車輛列表", data=cars_df)
    conn.update(worksheet="操作列表", data=logs_df)

# --- 網頁邏輯 ---
if 'page' not in st.session_state:
    st.session_state.page = 'home'

staff_df, cars_df, logs_df = load_all_data()
staff_list = staff_df['人員編號'].astype(str).tolist()

if st.session_state.page == 'home':
    st.title("🌐 雲端資產運營中心")
    st.info("目前連線：Google Cloud 資料庫 (兩地即時同步)")
    cols = st.columns(4)
    if cols[0].button("新增"): st.session_state.page = 'add'; st.rerun()
    if cols[1].button("刪除"): st.session_state.page = 'delete'; st.rerun()
    if cols[2].button("更改"): st.session_state.page = 'update'; st.rerun()
    if cols[3].button("查詢"): st.session_state.page = 'query'; st.rerun()

else:
    if st.sidebar.button("🔙 返回首頁"):
        st.session_state.page = 'home'; st.rerun()

    p_in = st.text_input("車牌號碼")
    w_in = st.number_input("空車重量", min_value=0.0) if st.session_state.page in ['add', 'update'] else 0.0
    s_in = st.selectbox("人員編號", staff_list)

    if st.button("確認執行並同步"):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 紀錄 Log 並置頂 (操作列表)
        new_log = pd.DataFrame([[st.session_state.page, p_in, w_in, s_in, now]], 
                               columns=logs_df.columns)
        logs_df = pd.concat([new_log, logs_df], ignore_index=True)

        if st.session_state.page == "新增" or st.session_state.page == "更改":
            cars_df = cars_df[cars_df['車牌號碼'] != p_in]
            new_car = pd.DataFrame([[p_in, w_in, now]], columns=cars_df.columns)
            cars_df = pd.concat([new_car, cars_df], ignore_index=True)
        
        elif st.session_state.page == "刪除":
            cars_df = cars_df[cars_df['車牌號碼'] != p_in]

        # 同步回 Google Sheets
        sync_to_cloud(staff_df, cars_df, logs_df)
        st.success(f"同步成功！兩地數據已更新。時間：{now}")