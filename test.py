import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- 自動抓取程式所在的資料夾路徑 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_PATH = os.path.join(BASE_DIR, 'test.xlsx')

def load_data():
    """載入資料並檢查檔案是否存在"""
    if not os.path.exists(FILE_PATH):
        st.error(f"❌ 找不到檔案：{FILE_PATH}")
        st.info("請確保 test.xlsx 檔案與 test.py 放在同一個資料夾。")
        return None
    try:
        return {
            "staff": pd.read_excel(FILE_PATH, sheet_name="staff"),
            "cars": pd.read_excel(FILE_PATH, sheet_name="cars"),
            "logs": pd.read_excel(FILE_PATH, sheet_name="logs")
        }
    except Exception as e:
        st.error(f"讀取 Sheet 失敗，請確認分頁名稱正確。錯誤：{e}")
        return None

def update_excel(action, plate, weight, staff, data):
    """執行操作並將新紀錄插入到 Excel 的第一列 (Index 0)"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. 操作列表 (Sheet 3) - 永遠置頂
    new_log = pd.DataFrame([[action, plate, weight, staff, now]], 
                           columns=['動作', '車牌號碼', '空車重量', '操作人員', '時間'])
    data['logs'] = pd.concat([new_log, data['logs']], ignore_index=True)
    
    # 2. 車輛列表 (Sheet 2)
    if action in ["新增", "更改"]:
        # 移除舊紀錄並將新紀錄插在最上方
        data['cars'] = data['cars'][data['cars']['車牌號碼'] != plate]
        new_car = pd.DataFrame([[plate, weight, now]], columns=['車牌號碼', '空車重量', '更新時間'])
        data['cars'] = pd.concat([new_car, data['cars']], ignore_index=True)
    elif action == "刪除":
        data['cars'] = data['cars'][data['cars']['車牌號碼'] != plate]

    # 3. 寫回 Excel
    with pd.ExcelWriter(FILE_PATH, engine='openpyxl') as writer:
        for name, df in data.items():
            df.to_excel(writer, sheet_name=name, index=False)
    return now

# --- 網頁介面 ---
st.set_page_config(page_title="車輛管理系統", layout="centered")

if 'menu' not in st.session_state:
    st.session_state.menu = 'home'

data = load_data()

if data is not None:
    staff_options = data['staff']['人員編號'].astype(str).tolist()

    if st.session_state.menu == 'home':
        st.title("🚜 車輛管理系統")
        st.write("請選擇作業項目：")
        cols = st.columns(4)
        if cols[0].button("新增"): st.session_state.menu = 'add'; st.rerun()
        if cols[1].button("刪除"): st.session_state.menu = 'delete'; st.rerun()
        if cols[2].button("更改"): st.session_state.menu = 'update'; st.rerun()
        if cols[3].button("查詢"): st.session_state.menu = 'query'; st.rerun()
    else:
        if st.sidebar.button("🔙 返回起始畫面"):
            st.session_state.menu = 'home'; st.rerun()

        # 輸入區域
        p = st.text_input("輸入車牌號碼")
        w = st.number_input("空車重量", min_value=0.0) if st.session_state.menu != 'delete' else 0.0
        s = st.selectbox("人員編號 (連動列表)", staff_options)

        if st.session_state.menu == 'add':
            if st.button("確認"):
                t = update_excel("新增", p, w, s, data)
                st.write(f"【網頁顯示】 車牌: {p} | 重量: {w} | 人員: {s} | 時間: {t}")
                st.success("紀錄已成功置於 Excel 第一列")

        elif st.session_state.menu == 'delete':
            if st.button("刪除"):
                st.session_state.confirm = True
            if st.session_state.get('confirm'):
                st.warning(f"⚠️ 確定刪除車牌 {p}？")
                if st.button("確定刪除"):
                    t = update_excel("刪除", p, 0, s, data)
                    st.write(f"【網頁顯示】 車牌: {p} | 人員: {s} | 時間: {t}")
                    st.session_state.confirm = False
                    st.success("資料已移除並更新日誌")

        elif st.session_state.menu == 'update':
            if st.button("確認"):
                t = update_excel("更改", p, w, s, data)
                st.write(f"【網頁顯示】 車牌: {p} | 重量: {w} | 人員: {s} | 時間: {t}")
                st.success("車輛狀態已更新並置頂")

        elif st.session_state.menu == 'query':
            if st.button("確認"):
                car_info = data['cars'][data['cars']['車牌號碼'] == p]
                weight = car_info['空車重量'].values[0] if not car_info.empty else "無紀錄"
                t = update_excel("查詢", p, weight, s, data)
                st.write(f"【網頁顯示】 車牌: {p} | 重量: {weight} | 人員: {s} | 時間: {t}")
                if not car_info.empty: st.table(car_info)