import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.title("🔌 雲端連線測試")

try:
    # 建立連線
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # 嘗試讀取第一個分頁 (不指定名稱，只用 ttl=0)
    df = conn.read(ttl=0) 
    
    st.success("✅ 連線成功！以下是您的資料內容：")
    st.dataframe(df) # 顯示讀取到的資料表

except Exception as e:
    st.error("❌ 連連看失敗了...")
    st.write(f"錯誤訊息：{e}")
