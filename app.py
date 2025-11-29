import streamlit as st
import pandas as pd
import io
from datetime import datetime

# --- CẤU HÌNH TRANG WEB ---
st.set_page_config(page_title="My Schedule Maker", page_icon="🎓", layout="wide")
st.title("🎓 Tạo Lịch Học Cá Nhân ")

# --- 1. CÁC HÀM XỬ LÝ LOGIC ---

def check_week_in_string(week_str, current_week):
    """Kiểm tra xem tuần hiện tại có nằm trong chuỗi tuần học (vd: 2-9, 11-19) không"""
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
    """Đọc file Excel với header ở dòng 3 (index 2)"""
    try:
        df = pd.read_excel(file, header=2)
        # Tạo cột nhãn hiển thị: "Tên Môn (Mã Lớp)" để dễ chọn
        if 'Tên_HP' in df.columns and 'Mã_lớp' in df.columns:
            df['Label_MonHoc'] = df['Tên_HP'] + " (" + df['Mã_lớp'].astype(str) + ")"
        return df
    except Exception as e:
        return None

def to_excel(df_school, list_personal):
    """Hàm xuất dữ liệu ra file Excel"""
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    
    # Sheet 1: Lịch Học (Các môn đã đăng ký)
    if not df_school.empty:
        df_school.to_excel(writer, index=False, sheet_name='Lịch Học Trường')
    
    # Sheet 2: Lịch Cá Nhân (Thêm từ Chatbox)
    if list_personal:
        df_personal = pd.DataFrame(list_personal)
        df_personal.to_excel(writer, index=False, sheet_name='Lịch Cá Nhân')
        
    writer.close()
    processed_data = output.getvalue()
    return processed_data

# --- 2. KHỞI TẠO BỘ NHỚ (SESSION STATE) ---
if 'personal_schedule' not in st.session_state:
    st.session_state['personal_schedule'] = []
if 'selected_classes' not in st.session_state:
    st.session_state['selected_classes'] = []

# --- 3. GIAO DIỆN & XỬ LÝ CHÍNH ---

# --- SIDEBAR: Cấu hình ---
with st.sidebar:
    st.header("1. Nhập liệu")
    uploaded_file = st.file_uploader("Tải lịch toàn trường (xlsx)", type=['xlsx'])
    
    st.divider()
    st.header("2. Chọn thời gian")
    selected_week = st.number_input("Chọn Tuần cần xem", min_value=1, max_value=50, value=1)
    st.info(f"Đang xem: **Tuần {selected_week}**")

# --- MAIN: Xử lý dữ liệu ---
if uploaded_file:
    df = load_data(uploaded_file)

    if df is not None:
        # Kiểm tra cột
        required_cols = ['Tuần', 'Thứ', 'Thời_gian', 'Tên_HP', 'Phòng', 'Mã_lớp', 'Label_MonHoc']
        missing = [c for c in required_cols if c not in df.columns]
        
        if missing:
            st.error("File thiếu cột quan trọng! Hãy kiểm tra lại file gốc.")
        else:
            # === BƯỚC 1: CHỌN MÔN HỌC (TÍNH NĂNG MỚI) ===
            st.subheader("✅ Bước 1: Chọn các môn bạn học")
            
            # Lấy danh sách tất cả các lớp có trong file
            unique_classes = df['Label_MonHoc'].unique()
            
            # Hộp chọn đa năng (Multiselect)
            my_classes = st.multiselect(
                "Tìm và chọn các lớp học phần của bạn:",
                options=unique_classes,
                default=st.session_state['selected_classes'] # Giữ lại lựa chọn cũ nếu có
            )
            
            # Lưu lựa chọn vào bộ nhớ để không bị mất khi thao tác khác
            st.session_state['selected_classes'] = my_classes

            if my_classes:
                # === BƯỚC 2: TẠO LỊCH CÁ NHÂN ===
                # Lọc data gốc: Chỉ lấy những dòng thuộc các lớp bạn đã chọn
                df_my_schedule = df[df['Label_MonHoc'].isin(my_classes)].copy()
                
                # Lọc theo tuần: Xem tuần này có học không
                df_my_schedule['Hoc_Tuan_Nay'] = df_my_schedule['Tuần'].apply(lambda x: check_week_in_string(x, selected_week))
                df_weekly_view = df_my_schedule[df_my_schedule['Hoc_Tuan_Nay'] == True].copy()
                
                # Sắp xếp
                df_weekly_view['Thứ'] = df_weekly_view['Thứ'].astype(str)
                df_weekly_view = df_weekly_view.sort_values(by=['Thứ', 'Thời_gian'])

                # Hiển thị bảng
                st.divider()
                st.subheader(f"📅 Lịch Trình Tuần {selected_week}")
                
                # Tab để chuyển đổi giữa xem Lịch Học và Lịch Đi Chơi
                tab1, tab2 = st.tabs(["🏫 Lịch Học", "🎉 Lịch Đi Chơi (Thêm)"])
                
                with tab1:
                    if not df_weekly_view.empty:
                        st.dataframe(
                            df_weekly_view[['Thứ', 'Thời_gian', 'Tên_HP', 'Phòng', 'Mã_lớp', 'Ghi_chú']],
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.info(f"Tuần {selected_week} các môn bạn chọn không có lịch học.")
                
                with tab2:
                    # Hiển thị lịch đi chơi của tuần này
                    my_plans = [p for p in st.session_state['personal_schedule'] if p['week'] == selected_week]
                    if my_plans:
                        st.table(pd.DataFrame(my_plans)[['day', 'time', 'content']])
                    else:
                        st.write("Chưa có kế hoạch đi chơi tuần này.")

                    # Chatbox thêm lịch
                    user_input = st.chat_input("Thêm lịch: Thứ 7, 19h, Đi xem phim")
                    if user_input:
                        parts = user_input.split(',')
                        if len(parts) >= 3:
                            new_plan = {
                                'week': selected_week,
                                'day': parts[0].strip(),
                                'time': parts[1].strip(),
                                'content': ",".join(parts[2:]).strip()
                            }
                            st.session_state['personal_schedule'].append(new_plan)
                            st.success("Đã thêm lịch!")
                            st.rerun()

                # === BƯỚC 3: XUẤT FILE EXCEL (TÍNH NĂNG MỚI) ===
                st.divider()
                st.subheader("📥 Xuất Lịch Của Tôi")
                st.write("Tải xuống file Excel gồm 2 trang: Lịch Học (các môn đã chọn) và Lịch Đi Chơi.")
                
                # Nút download
                excel_data = to_excel(df_my_schedule, st.session_state['personal_schedule'])
                st.download_button(
                    label="⬇️ Tải file Excel Lịch Cá Nhân",
                    data=excel_data,
                    file_name=f'Lich_Ca_Nhan_Tuan_{selected_week}.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )

            else:
                st.warning("👆 Hãy chọn ít nhất một môn học ở trên để xem lịch.")
    else:
        st.error("Không đọc được file.")
else:
    st.write("👈 Vui lòng tải file Excel lịch toàn trường lên.")