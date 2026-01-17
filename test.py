import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, timezone

# --- 1. 網頁頁面配置 ---
st.set_page_config(page_title="車輛管理系統", layout="centered")

# --- 2. 建立雲端連線 ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 3. 基礎設定與時區處理 ---
SHEET_STAFF = "staff"
SHEET_CARS = "cars"
SHEET_LOGS = "logs"
TW_TZ = timezone(timedelta(hours=8))  # 台灣時區

def load_all_data():
    """使用 GID 確保在公開連結下也能精準讀取各個分頁"""
    try:
        base_url = "https://docs.google.com/spreadsheets/d/1w2Fl2nc7ptfrSGTa4yARI_Opl7CWvcVFjfNu1Q2Wzus"
        # 讀取三個分頁 (依據您之前提供的 GID)
        staff = pd.read_csv(f"{base_url}/export?format=csv&gid=1036077614")
        cars = pd.read_csv(f"{base_url}/export?format=csv&gid=735260252")
        logs = pd.read_csv(f"{base_url}/export?format=csv&gid=1334291441")
        return staff, cars, logs
    except Exception as e:
        st.error(f"❌ 資料載入失敗：{e}")
        st.stop()

def save_to_cloud(staff_df, cars_df, logs_df):
    """將資料同步寫入雲端 (需 Secrets 內有 Service Account 資訊)"""
    try:
        conn.update(worksheet=SHEET_STAFF, data=staff_df)
        conn.update(worksheet=SHEET_CARS, data=cars_df)
        conn.update(worksheet=SHEET_LOGS, data=logs_df)
    except Exception as e:
        st.error(f"❌ 雲端同步失敗，請檢查權限設定：{e}")

# --- 4. 數據初始化 ---
staff_df, cars_df, logs_df = load_all_data()
STAFF_LIST = staff_df['人員編號'].astype(str).tolist() if not staff_df.empty else ["無人員資料"]

# --- 5. 導覽邏輯 (Menu Control) ---
if 'menu' not in st.session_state:
    st.session_state.menu = 'home'

if st.session_state.menu != 'home':
    if st.sidebar.button("🔙 回首頁"):
        st.session_state.menu = 'home'
        st.rerun()

# --- 6. 各功能畫面 ---
st.title("🚗 車輛作業紀錄系統")

if st.session_state.menu == 'home':
    st.info(f"當前連線狀態：正常 | 台北時間：{datetime.now(TW_TZ).strftime('%H:%M')}")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ 新增紀錄", use_container_width=True):
            st.session_state.menu = 'add'; st.rerun()
        if st.button("🗑️ 刪除紀錄", use_container_width=True):
            st.session_state.menu = 'delete'; st.rerun()
    with col2:
        if st.button("🔍 查詢紀錄", use_container_width=True):
            st.session_state.menu = 'query'; st.rerun()
        if st.button("📝 變更紀錄", use_container_width=True):
            st.session_state.menu = 'update'; st.rerun()
    
    st.write("---")
    st.subheader("🕒 最近 5 筆操作動態")
    st.table(logs_df.head(5))

elif st.session_state.menu == 'add':
    st.subheader("➕ 新增車輛紀錄")
    plate = st.text_input("輸入車牌號碼")
    weight = st.number_input("輸入空車重量", min_value=0.0, format="%.2f")
    staff = st.selectbox("選擇人員編號", STAFF_LIST)
    
    if st.button("確認提交"):
        now_str = datetime.now(TW_TZ).strftime("%Y-%m-%d %H:%M:%S")
        # 更新 Cars 表 (置頂新資料)
        cars_df = cars_df[cars_df['車牌號碼'] != plate]
        new_car = pd.DataFrame([[plate, weight, now_str]], columns=cars_df.columns)
        cars_df = pd.concat([new_car, cars_df], ignore_index=True)
        # 更新 Logs 表 (置頂)
        new_log = pd.DataFrame([["新增", plate, weight, staff, now_str]], columns=logs_df.columns)
        logs_df = pd.concat([new_log, logs_df], ignore_index=True)
        
        with st.spinner("同步至雲端..."):
            save_to_cloud(staff_df, cars_df, logs_df)
        st.success("✅ 紀錄已成功更新至雲端！")
        st.balloons()

elif st.session_state.menu == 'query':
    st.subheader("🔍 查詢所有紀錄")
    tab1, tab2 = st.tabs(["目前車輛清單", "歷史操作紀錄"])
    with tab1:
        st.dataframe(cars_df, use_container_width=True)
    with tab2:
        st.dataframe(logs_df, use_container_width=True)

elif st.session_state.menu == 'delete':
    st.subheader("🗑️ 刪除紀錄")
    target_plate = st.text_input("輸入欲刪除的車牌號碼")
    staff = st.selectbox("操作人員", STAFF_LIST)
    
    if st.button("執行刪除", type="primary"):
        if target_plate in cars_df['車牌號碼'].values:
            now_str = datetime.now(TW_TZ).strftime("%Y-%m-%d %H:%M:%S")
            # 取得該車最後紀錄的重量 (紀錄進 logs 用)
            old_weight = cars_df[cars_df['車牌號碼'] == target_plate]['空車重量'].values[0]
            # 刪除
            cars_df = cars_df[cars_df['車牌號碼'] != target_plate]
            # 紀錄動作
            new_log = pd.DataFrame([["刪除", target_plate, old_weight, staff, now_str]], columns=logs_df.columns)
            logs_df = pd.concat([new_log, logs_df], ignore_index=True)
            
            save_to_cloud(staff_df, cars_df, logs_df)
            st.warning(f"⚠️ 車牌 {target_plate} 的相關紀錄已移除")
        else:
            st.error("❌ 找不到該車牌紀錄")

elif st.session_state.menu == 'update':
    st.subheader("📝 變更紀錄內容")
    if not cars_df.empty:
        target_plate = st.selectbox("選擇欲變更的車牌", cars_df['車牌號碼'].unique())
        new_weight = st.number_input("修正空車重量", min_value=0.0, format="%.2f")
        new_staff = st.selectbox("修正人員編號", STAFF_LIST)
        
        if st.button("儲存變更"):
            now_str = datetime.now(TW_TZ).strftime("%Y-%m-%d %H:%M:%S")
            # 更新 Cars 表
            idx = cars_df[cars_df['車牌號碼'] == target_plate].index
            cars_df.loc[idx, '空車重量'] = new_weight
            cars_df.loc[idx, '更新時間'] = now_str
            # 紀錄動作
            new_log = pd.DataFrame([["變更", target_plate, new_weight, new_staff, now_str]], columns=logs_df.columns)
            logs_df = pd.concat([new_log, logs_df], ignore_index=True)
            
            save_to_cloud(staff_df, cars_df, logs_df)
            st.success("✅ 變更成功")
    else:
        st.info("目前無車輛紀錄可供變更")





