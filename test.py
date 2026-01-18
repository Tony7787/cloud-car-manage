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

# --- 4. 效能優化：帶有緩存的讀取函數 ---
@st.cache_data(ttl=300)  # 資料緩存 5 分鐘，這期間切換頁面不重新下載
def load_all_data():
    try:
        base_url = "https://docs.google.com/spreadsheets/d/1w2Fl2nc7ptfrSGTa4yARI_Opl7CWvcVFjfNu1Q2Wzus"
        # 使用 GID 讀取，避免公開連結的 400 錯誤
        staff = pd.read_csv(f"{base_url}/export?format=csv&gid=1036077614")
        cars = pd.read_csv(f"{base_url}/export?format=csv&gid=735260252")
        logs = pd.read_csv(f"{base_url}/export?format=csv&gid=1334291441")
        return staff, cars, logs
    except Exception as e:
        st.error(f"❌ 資料載入失敗：{e}")
        st.stop()

def save_and_refresh(staff_df, cars_df, logs_df):
    """同步寫入並清除快取，確保下次讀取到最新資料"""
    try:
        conn.update(worksheet=SHEET_STAFF, data=staff_df)
        conn.update(worksheet=SHEET_CARS, data=cars_df)
        conn.update(worksheet=SHEET_LOGS, data=logs_df)
        # 關鍵：寫入成功後清除快取，迫使下一次 load_all_data 抓取新資料
        st.cache_data.clear()
    except Exception as e:
        st.error(f"❌ 雲端同步失敗：{e}")

# --- 5. 數據初始化 ---
staff_df, cars_df, logs_df = load_all_data()
STAFF_LIST = staff_df['人員編號'].astype(str).tolist() if not staff_df.empty else ["無人員資料"]

# --- 6. 導覽邏輯 ---
if 'menu' not in st.session_state:
    st.session_state.menu = 'home'

if st.session_state.menu != 'home':
    if st.sidebar.button("🔙 回首頁"):
        st.session_state.menu = 'home'
        st.rerun()

st.title("🚗 車輛作業紀錄系統")

# --- 7. 各功能畫面 ---
if st.session_state.menu == 'home':
    st.info(f"系統狀態：已啟動 | 時間：{datetime.now(TW_TZ).strftime('%H:%M:%S')}")
    
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
    # 這裡使用靜態 table 渲染最快
    st.table(logs_df.head(5))

elif st.session_state.menu == 'add':
    st.subheader("➕ 新增車輛紀錄")
    with st.form("add_form", clear_on_submit=True):
        plate = st.text_input("輸入車牌號碼")
        weight = st.number_input("輸入空車重量", min_value=0.0, format="%.0f")
        staff = st.selectbox("選擇人員編號", STAFF_LIST)
        submit = st.form_submit_button("確認提交")
    
    if submit and plate:
        now_str = datetime.now(TW_TZ).strftime("%Y-%m-%d %H:%M:%S")
        # 更新邏輯
        cars_df = cars_df[cars_df['車牌號碼'] != plate]
        new_car = pd.DataFrame([[plate, weight, now_str]], columns=cars_df.columns)
        cars_df = pd.concat([new_car, cars_df], ignore_index=True)
        
        new_log = pd.DataFrame([["新增", plate, weight, staff, now_str]], columns=logs_df.columns)
        logs_df = pd.concat([new_log, logs_df], ignore_index=True)
        
        with st.spinner("同步中..."):
            save_and_refresh(staff_df, cars_df, logs_df)
        st.success("✅ 紀錄已更新！")
        #st.balloons()
        # --- 新增完後即時顯示該筆資料 ---
        st.write("📋 **剛剛新增的資料內容：**")
        st.info(f"車牌號碼：**{plate}** | 空車重量：**{weight}** | 時間：**{now_str}**")

elif st.session_state.menu == 'query':
    st.subheader("🔍 查詢所有紀錄")
    # 使用快取中的資料進行搜尋
    search_q = st.text_input("💡 輸入車牌搜尋過濾", "")
    
    tab1, tab2 = st.tabs(["目前車輛清單", "歷史操作紀錄"])
    with tab1:
        display_cars = cars_df[cars_df['車牌號碼'].str.contains(search_q, na=False)] if search_q else cars_df
        st.dataframe(display_cars, use_container_width=True)
    with tab2:
        st.dataframe(logs_df.head(100), use_container_width=True) # 限制顯示前100筆提高效能

elif st.session_state.menu == 'delete':
    st.subheader("🗑️ 刪除紀錄")
    target_plate = st.selectbox("選擇欲刪除的車牌", [""] + list(cars_df['車牌號碼'].unique()))
    staff = st.selectbox("操作人員", STAFF_LIST)
    
    if st.button("執行刪除", type="primary") and target_plate != "":
        now_str = datetime.now(TW_TZ).strftime("%Y-%m-%d %H:%M:%S")
        old_weight = cars_df[cars_df['車牌號碼'] == target_plate]['空車重量'].values[0]
        
        cars_df = cars_df[cars_df['車牌號碼'] != target_plate]
        new_log = pd.DataFrame([["刪除", target_plate, old_weight, staff, now_str]], columns=logs_df.columns)
        logs_df = pd.concat([new_log, logs_df], ignore_index=True)
        
        with st.spinner("同步中..."):
            save_and_refresh(staff_df, cars_df, logs_df)
        st.warning(f"⚠️ 車牌 {target_plate} 已移除")

elif st.session_state.menu == 'update':
    st.subheader("📝 變更紀錄內容")
    if not cars_df.empty:
        target_plate = st.selectbox("選擇欲變更的車牌", cars_df['車牌號碼'].unique())
        new_weight = st.number_input("修正空車重量", min_value=0.0, format="%.0f")
        new_staff = st.selectbox("修正人員編號", STAFF_LIST)
        
        if st.button("儲存變更"):
            now_str = datetime.now(TW_TZ).strftime("%Y-%m-%d %H:%M:%S")
            idx = cars_df[cars_df['車牌號碼'] == target_plate].index
            cars_df.loc[idx, '空車重量'] = new_weight
            cars_df.loc[idx, '更新時間'] = now_str
            
            new_log = pd.DataFrame([["變更", target_plate, new_weight, new_staff, now_str]], columns=logs_df.columns)
            logs_df = pd.concat([new_log, logs_df], ignore_index=True)
            
            with st.spinner("同步中..."):
                save_and_refresh(staff_df, cars_df, logs_df)
            st.success("✅ 變更成功")
            # --- 修改完後即時顯示該筆資料 ---
            st.write("📋 **變更後的最新資訊：**")
            st.info(f"車牌號碼：**{target_plate}** | 空車重量：**{new_weight}** | 時間：**{now_str}**")














