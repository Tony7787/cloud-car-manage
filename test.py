import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, timezone

# --- 頁面設定 ---
st.set_page_config(page_title="雲端資產管理系統", layout="wide")

# --- 建立連線 ---
# 注意：這會自動讀取您在 Secrets 設定的 service_account 資訊
conn = st.connection("gsheets", type=GSheetsConnection)

# 定義分頁變數 (需與 Google Sheets 下方標籤名稱一致)
SHEET_STAFF = "staff"
SHEET_CARS = "cars"
SHEET_LOGS = "logs"

def load_all_data():
    """使用 GID 強制讀取特定分頁，確保公開連結下不會報 400 錯誤"""
    try:
        base_url = "https://docs.google.com/spreadsheets/d/1w2Fl2nc7ptfrSGTa4yARI_Opl7CWvcVFjfNu1Q2Wzus"
        
        # 讀取三個分頁 (請確認您的 GID 是否與網址一致)
        staff_url = f"{base_url}/export?format=csv&gid=1036077614" 
        staff = pd.read_csv(staff_url)
        
        cars_url = f"{base_url}/export?format=csv&gid=735260252" 
        cars = pd.read_csv(cars_url)
        
        logs_url = f"{base_url}/export?format=csv&gid=1334291441"
        logs = pd.read_csv(logs_url)
        
        return staff, cars, logs
    except Exception as e:
        st.error(f"⚠️ 資料讀取失敗")
        st.write(f"錯誤訊息：{e}")
        st.stop()

def sync_to_cloud(staff_df, cars_df, logs_df):
    """利用服務帳號權限將資料同步回雲端"""
    try:
        conn.update(worksheet=SHEET_STAFF, data=staff_df)
        conn.update(worksheet=SHEET_CARS, data=cars_df)
        conn.update(worksheet=SHEET_LOGS, data=logs_df)
    except Exception as e:
        st.error("❌ 同步至雲端失敗，請確認是否已將試算表「共用」給服務帳號 Email")
        st.write(e)

# --- 數據準備 ---
if 'page' not in st.session_state:
    st.session_state.page = 'home'

staff_df, cars_df, logs_df = load_all_data()
staff_list = staff_df['人員編號'].astype(str).tolist() if not staff_df.empty else ["無人員資料"]

# --- 介面呈現 ---
if st.session_state.page == 'home':
    st.title("🌐 雲端資產運營中心")
    st.info("目前時區：台北 (GMT+8)")
    
    # 財務統計看板
    m1, m2 = st.columns(2)
    m1.metric("車輛總數", len(cars_df))
    m2.metric("操作紀錄", len(logs_df))

    st.write("---")
    cols = st.columns(4)
    if cols[0].button("新增車輛"): st.session_state.page = '新增'; st.rerun()
    if cols[1].button("刪除車輛"): st.session_state.page = '刪除'; st.rerun()
    if cols[2].button("更改資訊"): st.session_state.page = '更改'; st.rerun()
    if cols[3].button("紀錄查詢"): st.session_state.page = '查詢'; st.rerun()

    # 置頂顯示最新動態
    st.write("### 🕒 最近操作紀錄 (置頂)")
    st.dataframe(logs_df.head(10), use_container_width=True)

else:
    if st.sidebar.button("🔙 返回首頁"):
        st.session_state.page = 'home'; st.rerun()

    st.subheader(f"進行作業：{st.session_state.page}")
    
    # 輸入介面
    with st.form("data_form"):
        p_in = st.text_input("輸入車牌號碼")
        w_in = st.number_input("空車重量", min_value=0.0, format="%.2f") if st.session_state.page in ['新增', '更改'] else 0.0
        s_in = st.selectbox("操作人員", staff_list)
        submit = st.form_submit_button(f"確認執行{st.session_state.page}")

    if submit:
        # --- 修正時間問題 (GMT+8) ---
        tw_tz = timezone(timedelta(hours=8))
        now = datetime.now(tw_tz).strftime("%Y-%m-%d %H:%M:%S")
        
        # 1. 更新 Logs (置頂邏輯)
        new_log = pd.DataFrame([[st.session_state.page, p_in, w_in, s_in, now]], columns=logs_df.columns)
        logs_df = pd.concat([new_log, logs_df], ignore_index=True)

        # 2. 更新 Cars (置頂邏輯)
        if st.session_state.page in ["新增", "更改"]:
            cars_df = cars_df[cars_df['車牌號碼'] != p_in]
            new_car = pd.DataFrame([[p_in, w_in, now]], columns=cars_df.columns)
            cars_df = pd.concat([new_car, cars_df], ignore_index=True)
        elif st.session_state.page == "刪除":
            cars_df = cars_df[cars_df['車牌號碼'] != p_in]

        # 3. 同步回雲端
        with st.spinner('同步雲端中...'):
            sync_to_cloud(staff_df, cars_df, logs_df)
        
        st.success(f"✅ 操作成功！時間：{now}")
        st.balloons()







