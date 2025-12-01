import streamlit as st
import pandas as pd
import io
import smtplib
import os  # <--- Thêm thư viện này
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CẤU HÌNH TRANG WEB ---
st.set_page_config(page_title="My Schedule Pro", page_icon="✅", layout="wide")
st.title(" Quản Lý Lịch Học ")

# --- 1. HÀM GỬI EMAIL (ĐÃ NÂNG CẤP) ---
def get_secret(key):
    """Hàm thông minh: Tìm trong secrets.toml trước, nếu không có thì tìm trong biến môi trường"""
    if key in st.secrets:
        return st.secrets[key]
    return os.environ.get(key)

def send_email_reminder(to_email, subject, df_schedule, personal_plans):
    try:
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        
        # --- Lấy mật khẩu theo cách mới ---
        sender_email = get_secret("EMAIL_USER")
        sender_password = get_secret("EMAIL_PASSWORD")

        if not sender_email or not sender_password:
            return False, "Thiếu thông tin đăng nhập! Hãy kiểm tra lại cấu hình."

        # Tạo nội dung email
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject

        html_body = f"""
        <h2>📅 Lịch Trình Của Bạn</h2>
        <p>Xin chào, đây là danh sách các việc cần làm bạn đã chọn:</p>
        
        <h3>🏫 Lịch Học</h3>
        {df_schedule.to_html(index=False) if not df_schedule.empty else "<p>Không có lịch học.</p>"}
        
        <h3>🎉 Lịch Cá Nhân</h3>
        {pd.DataFrame(personal_plans).to_html(index=False) if personal_plans else "<p>Không có lịch cá nhân.</p>"}
        
        <p><i>Được gửi từ hệ thống Streamlit của bạn.</i></p>
        """
        
        msg.attach(MIMEText(html_body, 'html'))

        # Kết nối và gửi
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
        return True, "Đã gửi email thành công!"
    except Exception as e:
        return False, f"Lỗi gửi email: {e}"

# --- 2. CÁC HÀM XỬ LÝ DỮ LIỆU (GIỮ NGUYÊN) ---
def check_week_in_string(week_str, current_week):
    try:
        if pd.isna(week_str): return False
        week_str = str(week_str)
        parts = week_str.split(',')
        for part in parts:
            if '-' in part: 
                start, end = part.split('-')
                if int(start) <= current_week <= int(end):
                    return True
            else: 
                if int(part) == current_week:
                    return True
        return False
    except:
        return False

@st.cache_data
def load_data(file):
    try:
        df = pd.read_excel(file, header=2)
        if 'Tên_HP' in df.columns and 'Mã_lớp' in df.columns:
            df['Label_MonHoc'] = df['Tên_HP'] + " (" + df['Mã_lớp'].astype(str) + ")"
        return df
    except Exception as e:
        return None

# --- 3. KHỞI TẠO BỘ NHỚ ---
if 'personal_schedule' not in st.session_state:
    st.session_state['personal_schedule'] = []
if 'selected_classes' not in st.session_state:
    st.session_state['selected_classes'] = []

# ================= GIAO DIỆN CHÍNH =================

with st.sidebar:
    st.header("1. Nhập liệu")
    uploaded_file = st.file_uploader("Tải lịch toàn trường (xlsx)", type=['xlsx'])
    
    st.divider()
    st.header("2. Chọn thời gian")
    selected_week = st.number_input("Chọn Tuần", min_value=1, max_value=50, value=1)

if uploaded_file:
    df = load_data(uploaded_file)
    if df is not None:
        required_cols = ['Tuần', 'Thứ', 'Thời_gian', 'Label_MonHoc']
        if not all(col in df.columns for col in required_cols):
             st.error("File thiếu cột quan trọng!")
        else:
            # === BƯỚC 1: CHỌN MÔN ===
            st.subheader("✅ Bước 1: Chọn môn học")
            unique_classes = df['Label_MonHoc'].unique()
            my_classes = st.multiselect("Môn của tôi:", unique_classes, default=st.session_state['selected_classes'])
            st.session_state['selected_classes'] = my_classes

            if my_classes:
                df_my_schedule = df[df['Label_MonHoc'].isin(my_classes)].copy()
                df_my_schedule['Hoc_Tuan_Nay'] = df_my_schedule['Tuần'].apply(lambda x: check_week_in_string(x, selected_week))
                df_weekly_view = df_my_schedule[df_my_schedule['Hoc_Tuan_Nay'] == True].copy()
                
                df_weekly_view['Thứ'] = df_weekly_view['Thứ'].astype(str)
                df_weekly_view = df_weekly_view.sort_values(by=['Thứ', 'Thời_gian'])

                if 'Xong' not in df_weekly_view.columns:
                    df_weekly_view.insert(0, "Xong", False)

                st.divider()
                st.subheader(f"📅 Checklist Tuần {selected_week}")
                
                edited_df = st.data_editor(
                    df_weekly_view[['Xong', 'Thứ', 'Thời_gian', 'Tên_HP', 'Phòng', 'Ghi_chú']],
                    column_config={
                        "Xong": st.column_config.CheckboxColumn("Đã làm?", default=False)
                    },
                    disabled=["Thứ", "Thời_gian", "Tên_HP", "Phòng", "Ghi_chú"],
                    hide_index=True,
                    use_container_width=True,
                    key="editor"
                )

                st.divider()
                st.subheader("📧 Gửi Email Nhắc Nhở")
                
                with st.form("email_form"):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        user_email = st.text_input("Nhập Gmail của bạn:", placeholder="example@gmail.com")
                    with col2:
                        submit_email = st.form_submit_button("Gửi Ngay 🚀")
                    
                    if submit_email and user_email:
                        tasks_to_do = edited_df[edited_df['Xong'] == False]
                        my_plans = [p for p in st.session_state['personal_schedule'] if p['week'] == selected_week]
                        
                        with st.spinner("Đang gửi mail..."):
                            success, msg = send_email_reminder(
                                user_email, 
                                f"Nhắc nhở lịch học Tuần {selected_week}", 
                                tasks_to_do[['Thứ', 'Thời_gian', 'Tên_HP', 'Phòng']], 
                                my_plans
                            )
                            if success: st.success(msg)
                            else: st.error(msg)
    else:
        st.error("Không đọc được file.")
else:
    st.info("👈 Hãy tải file Excel lên để bắt đầu.")