import streamlit as st
import pandas as pd
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CẤU HÌNH TRANG WEB ---
st.set_page_config(page_title="My Schedule Pro", page_icon="✅", layout="wide")
st.title(" Quản Lý Lịch Học ")

# --- 1. HÀM GỬI EMAIL ---
def send_email_reminder(to_email, subject, df_schedule, personal_plans):
    # Lấy thông tin từ Secret (Bảo mật)
    try:
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        sender_email = st.secrets["EMAIL_USER"]
        sender_password = st.secrets["EMAIL_PASSWORD"]

        # Tạo nội dung email (HTML cho đẹp)
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
        return False, f"Lỗi gửi email: {e}. \nHãy kiểm tra lại Mật khẩu ứng dụng (App Password)."

# --- 2. CÁC HÀM XỬ LÝ DỮ LIỆU ---
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
        # Header=2 để đọc đúng định dạng file của bạn
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
                # Lọc dữ liệu
                df_my_schedule = df[df['Label_MonHoc'].isin(my_classes)].copy()
                df_my_schedule['Hoc_Tuan_Nay'] = df_my_schedule['Tuần'].apply(lambda x: check_week_in_string(x, selected_week))
                df_weekly_view = df_my_schedule[df_my_schedule['Hoc_Tuan_Nay'] == True].copy()
                
                # Sắp xếp
                df_weekly_view['Thứ'] = df_weekly_view['Thứ'].astype(str)
                df_weekly_view = df_weekly_view.sort_values(by=['Thứ', 'Thời_gian'])

                # Thêm cột Checklist 'Xong' mặc định là False
                if 'Xong' not in df_weekly_view.columns:
                    df_weekly_view.insert(0, "Xong", False)

                # === BƯỚC 2: HIỂN THỊ CHECKLIST ===
                st.divider()
                st.subheader(f"📅 Checklist Tuần {selected_week}")
                
                # Hiển thị bảng dạng Data Editor (Cho phép tích chọn)
                edited_df = st.data_editor(
                    df_weekly_view[['Xong', 'Thứ', 'Thời_gian', 'Tên_HP', 'Phòng', 'Ghi_chú']],
                    column_config={
                        "Xong": st.column_config.CheckboxColumn("Đã làm?", help="Tích vào khi đã học xong", default=False)
                    },
                    disabled=["Thứ", "Thời_gian", "Tên_HP", "Phòng", "Ghi_chú"], # Chỉ cho sửa cột Xong
                    hide_index=True,
                    use_container_width=True,
                    key="editor"
                )

                # Hiển thị tiến độ
                if not edited_df.empty:
                    so_mon_da_hoc = edited_df['Xong'].sum()
                    tong_so_mon = len(edited_df)
                    st.progress(so_mon_da_hoc / tong_so_mon)
                    st.caption(f"Đã hoàn thành: {so_mon_da_hoc}/{tong_so_mon} môn học.")

                # === BƯỚC 3: GỬI EMAIL NHẮC NHỞ ===
                st.divider()
                st.subheader("📧 Gửi Email Nhắc Nhở")
                
                with st.form("email_form"):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        user_email = st.text_input("Nhập Gmail của bạn:", placeholder="example@gmail.com")
                    with col2:
                        submit_email = st.form_submit_button("Gửi Ngay 🚀")
                    
                    if submit_email and user_email:
                        # Lọc ra những môn CHƯA XONG để nhắc nhở
                        tasks_to_do = edited_df[edited_df['Xong'] == False]
                        my_plans = [p for p in st.session_state['personal_schedule'] if p['week'] == selected_week]
                        
                        # Gọi hàm gửi mail
                        if "EMAIL_USER" in st.secrets:
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
                            st.warning("⚠️ Chưa cấu hình Email Server! (Xem hướng dẫn bên dưới)")

    else:
        st.error("Không đọc được file.")
else:
    st.info("👈 Hãy tải file Excel lên để bắt đầu.")