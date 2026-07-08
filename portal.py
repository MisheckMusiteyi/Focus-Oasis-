import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import base64
import time
from io import BytesIO
from datetime import datetime, date
from PIL import Image

# ============================================
# PAGE CONFIGURATION
# ============================================
st.set_page_config(
    page_title="Focus Oasis Portal",
    layout="wide"
)

# ============================================
# CUSTOM CSS - Focus Oasis Branding
# ============================================
st.markdown("""
<style>
    * { font-family: 'Georgia', 'Times New Roman', serif !important; }
    
    /* Background */
    .stApp { 
        background-color: #FFFFFF !important; 
    }
    
    /* Headers - Dark navy blue */
    h1, h2, h3 { 
        color: #1B2A4A !important; 
        font-weight: 700 !important; 
    }
    
    /* Buttons - Dark navy blue with sky blue hover */
    .stButton > button {
        background-color: #1B2A4A !important;
        color: white !important;
        border: none !important;
        border-radius: 6px !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
    }
    .stButton > button:hover {
        background-color: #2E86C1 !important;
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        color: #1B2A4A !important;
        font-weight: 700 !important;
    }
    [data-testid="stMetricLabel"] {
        color: #2E86C1 !important;
    }
    
    /* Sidebar - Dark navy blue */
    [data-testid="stSidebar"] {
        background-color: #1B2A4A !important;
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label {
        color: white !important;
    }
    [data-testid="stSidebar"] .stButton > button {
        background-color: #2E86C1 !important;
        color: white !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background-color: #1B2A4A !important;
        border: 1px solid #2E86C1 !important;
    }
    
    /* Dividers */
    hr { 
        border-color: #2E86C1; 
    }
    
    /* Input focus */
    .stTextInput input:focus, .stDateInput input:focus {
        border-color: #2E86C1 !important;
        box-shadow: 0 0 0 2px rgba(46,134,193,0.2) !important;
    }
    
    /* Radio buttons */
    div[data-testid="stRadio"] input[type="radio"] {
        accent-color: #2E86C1 !important;
    }
    
    /* Tabs */
    .stTabs [aria-selected="true"] {
        background-color: #1B2A4A !important;
        color: white !important;
    }
    
    /* Expanders */
    [data-testid="stExpander"] summary {
        border-left: 3px solid #2E86C1 !important;
    }
    
    /* Success/Error messages */
    .stSuccess {
        border-left: 4px solid #4CAF50 !important;
    }
    .stError {
        border-left: 4px solid #f44336 !important;
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# GOOGLE SHEETS SETUP
# ============================================
@st.cache_resource
def connect_to_sheets():
    scope = ["https://spreadsheets.google.com/feeds",
             "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = {
            "type": st.secrets["type"],
            "project_id": st.secrets["project_id"],
            "private_key_id": st.secrets["private_key_id"],
            "private_key": st.secrets["private_key"],
            "client_email": st.secrets["client_email"],
            "client_id": st.secrets["client_id"],
            "auth_uri": st.secrets["auth_uri"],
            "token_uri": st.secrets["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["client_x509_cert_url"],
            "universe_domain": st.secrets.get("universe_domain", "googleapis.com")
        }
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    except Exception:
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    return gspread.authorize(creds)

def load_data(sheet_name):
    for attempt in range(3):
        try:
            connect_to_sheets.clear()
            client = connect_to_sheets()
            sheet = client.open("Focus Oasis Dashboard").worksheet(sheet_name)
            return pd.DataFrame(sheet.get_all_records())
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
            else:
                raise e

def update_cell(sheet_name, row, col, value):
    connect_to_sheets.clear()
    client = connect_to_sheets()
    sheet = client.open("Focus Oasis Dashboard").worksheet(sheet_name)
    sheet.update_cell(row, col, value)

# ============================================
# PROFILE HELPERS
# ============================================
def get_student_profile(username):
    try:
        df = load_data("Student Profiles")
        user = df[df["Username"] == username]
        if len(user) > 0:
            return user.iloc[0].to_dict()
    except:
        pass
    return {"Username": username, "Display Name": "", "Profile Photo": ""}

def save_student_profile(username, display_name, photo_b64=""):
    connect_to_sheets.clear()
    client = connect_to_sheets()
    sheet = client.open("Focus Oasis Dashboard").worksheet("Student Profiles")
    records = sheet.get_all_records()
    
    if not display_name:
        display_name = username
    if len(photo_b64) > 45000:
        st.warning("Image too large. Please use a smaller image.")
        photo_b64 = ""
    
    row_data = [username, display_name, photo_b64]
    for idx, row in enumerate(records, start=2):
        if row["Username"] == username:
            sheet.update(f"A{idx}:C{idx}", [row_data])
            return
    sheet.append_row(row_data)

def resize_image_for_storage(image_bytes):
    img = Image.open(BytesIO(image_bytes))
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    w, h = img.size
    side = min(w, h)
    img = img.crop(((w-side)//2, (h-side)//2, (w+side)//2, (h+side)//2))
    img = img.resize((200, 200), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format='JPEG', quality=60, optimize=True)
    return buf.getvalue()

def get_initials(full_name):
    if not full_name: return "?"
    parts = [p for p in full_name.strip().split() if p]
    if not parts: return "?"
    return parts[0][0].upper() if len(parts) == 1 else (parts[0][0] + parts[-1][0]).upper()

def display_student_photo(photo_b64=None, size=120, name=""):
    if photo_b64:
        st.markdown(f"""
            <img src="data:image/jpeg;base64,{photo_b64}"
            style="width:{size}px;height:{size}px;border-radius:50%;
                   object-fit:cover;border:4px solid #2E86C1;
                   display:block;margin:0 auto;">
        """, unsafe_allow_html=True)
    else:
        initials = get_initials(name)
        st.markdown(f"""
            <div style="width:{size}px;height:{size}px;border-radius:50%;
                        background:#1B2A4A;color:white;display:flex;
                        align-items:center;justify-content:center;
                        font-size:{int(size*0.4)}px;font-weight:bold;
                        margin:0 auto;border:4px solid #2E86C1;">
            {initials}
            </div>
        """, unsafe_allow_html=True)

# ============================================
# DIALOG: Profile Settings
# ============================================
@st.dialog("Profile Settings")
def profile_settings_dialog(username, profile):
    new_name = st.text_input("Display Name", value=profile.get("Display Name", username))
    new_photo = st.file_uploader("Profile Photo", type=["png", "jpg", "jpeg"])
    if new_photo:
        st.image(new_photo, width=150, caption="Preview")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Save", use_container_width=True):
            photo_b64 = profile.get("Profile Photo", "")
            if new_photo:
                compressed = resize_image_for_storage(new_photo.getvalue())
                photo_b64 = base64.b64encode(compressed).decode()
            save_student_profile(username, new_name, photo_b64)
            st.success("Profile updated!")
            st.rerun()
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()

# ============================================
# SESSION STATE
# ============================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_type' not in st.session_state:
    st.session_state.user_type = None
if 'student_name' not in st.session_state:
    st.session_state.student_name = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'student_class' not in st.session_state:
    st.session_state.student_class = None

# ============================================
# LOGIN PAGE
# ============================================
def login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align:center;'>Focus Oasis Foundation</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center;color:#2E86C1;'>Student & Admin Portal</p>", unsafe_allow_html=True)
        st.divider()
        
        login_type = st.radio("Login as:", ["Student", "Admin"], horizontal=True)
        
        if login_type == "Student":
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.button("Login", use_container_width=True):
                logins_df = load_data("Student Logins")
                match = logins_df[
                    (logins_df['Username'] == username) &
                    (logins_df['Password'] == password) &
                    (logins_df['Status'] == 'Active')
                ]
                if len(match) > 0:
                    st.session_state.logged_in = True
                    st.session_state.user_type = "Student"
                    st.session_state.username = username
                    st.session_state.student_name = match.iloc[0]['Student Name']
                    st.session_state.student_class = match.iloc[0].get('Class', '')
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid credentials or account inactive.")
        else:
            admin_username = st.text_input("Admin Username")
            admin_password = st.text_input("Admin Password", type="password")
            if st.button("Login", use_container_width=True):
                admin_logins_df = load_data("Admin Logins")
                match = admin_logins_df[
                    (admin_logins_df['Username'] == admin_username) &
                    (admin_logins_df['Password'] == admin_password)
                ]
                if len(match) > 0:
                    st.session_state.logged_in = True
                    st.session_state.user_type = "Admin"
                    st.success("Admin login successful!")
                    st.rerun()
                else:
                    st.error("Invalid admin username or password.")

# ============================================
# STUDENT DASHBOARD
# ============================================
def student_dashboard():
    profile = get_student_profile(st.session_state.username)
    display_name = profile.get("Display Name", "") or st.session_state.student_name
    
    students_df = load_data("Students")
    fee_structure_df = load_data("Fee Structure")
    fee_payments_df = load_data("Fee Payments")
    performance_df = load_data("Performance")
    
    student_info = students_df[students_df['Student Name'] == st.session_state.student_name]
    
    if len(student_info) > 0:
        student_row = student_info.iloc[0]
        student_class = student_row.get('Class', st.session_state.student_class)
        class_fee = fee_structure_df[fee_structure_df['Class'] == student_class]['Monthly Fee'].sum()
        total_paid = fee_payments_df[fee_payments_df['Name of Student'] == st.session_state.student_name]['Amount Paid'].sum()
        balance = class_fee - total_paid
    else:
        student_class = st.session_state.student_class
        class_fee = 0
        total_paid = 0
        balance = 0
    
    my_performance = performance_df[performance_df['Student Name'] == st.session_state.student_name]
    
    # Header
    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        display_student_photo(profile.get("Profile Photo", ""), size=100, name=st.session_state.student_name)
    with col2:
        st.title(f"Welcome, {display_name}")
    with col3:
        st.markdown(f"""
        <div style="text-align:center;margin-top:10px;">
            <p style="color:#1B2A4A;font-weight:700;font-size:14px;">{display_name}</p>
            <p style="color:#2E86C1;font-size:12px;">{student_class}</p>
        </div>
        """, unsafe_allow_html=True)
    st.divider()
    
    tab1, tab2 = st.tabs(["My Details", "My Performance"])
    
    with tab1:
        st.subheader("Student Information")
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("Name", st.session_state.student_name)
        with col2: st.metric("Class", student_class)
        with col3: st.metric("Status", "Active")
        
        st.divider()
        st.subheader("Fee Summary")
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("Fees Charged", f"${class_fee:,.0f}")
        with col2: st.metric("Total Paid", f"${total_paid:,.0f}")
        with col3: st.metric("Balance Owing", f"${balance:,.0f}",
                            delta="Paid Full" if balance <= 0 else "Outstanding")
        
        my_payments = fee_payments_df[fee_payments_df['Name of Student'] == st.session_state.student_name]
        if len(my_payments) > 0:
            st.divider()
            st.subheader("Payment History")
            st.dataframe(my_payments[['Date', 'Amount Paid', 'Month Covered', 'Payment Method']],
                       use_container_width=True, hide_index=True)
    
    with tab2:
        st.subheader("My Performance")
        if len(my_performance) > 0:
            marks = my_performance['Mark'].apply(lambda x: float(str(x).replace('%','')))
            avg_mark = marks.mean()
            
            col1, col2 = st.columns(2)
            with col1: st.metric("Activities", len(my_performance))
            with col2: st.metric("Average Mark", f"{avg_mark:.1f}%")
            
            st.divider()
            for idx, row in my_performance.iterrows():
                with st.expander(f"{row['Activity']} — {row['Date']}"):
                    st.write(f"**Mark:** {row['Mark']}")
                    st.write(f"**Comment:** {row['Comment']}")
        else:
            st.info("No performance records yet.")
    
    # Sidebar
    with st.sidebar:
        st.markdown("## Focus Oasis")
        st.markdown("---")
        display_student_photo(profile.get("Profile Photo", ""), size=80, name=st.session_state.student_name)
        st.markdown(f"<p style='text-align:center;color:white;font-weight:700;'>{display_name}</p>",
                   unsafe_allow_html=True)
        st.markdown(f"<p style='text-align:center;color:#2E86C1;font-size:12px;'>{student_class}</p>",
                   unsafe_allow_html=True)
        st.markdown("---")
        if st.button("Profile Settings", use_container_width=True):
            profile_settings_dialog(st.session_state.username, profile)
        st.markdown("---")
        if st.button("Logout", use_container_width=True):
            for key in ['logged_in', 'user_type', 'student_name', 'username', 'student_class']:
                st.session_state[key] = None
            st.session_state.logged_in = False
            st.rerun()

# ============================================
# ADMIN DASHBOARD
# ============================================
def admin_dashboard():
    st.title("Admin Dashboard - Focus Oasis Foundation")
    
    students_df = load_data("Students")
    fee_payments_df = load_data("Fee Payments")
    expenses_df = load_data("Expenses")
    other_income_df = load_data("Other Income")
    
    tab1, tab2, tab3 = st.tabs(["Overview", "Finances", "All Students"])
    
    with tab1:
        st.subheader("School Overview")
        classes = students_df['Class'].value_counts()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1: st.metric("Total Students", len(students_df))
        with col2: st.metric("Classes", len(classes))
        with col3: st.metric("Fees Collected", f"${fee_payments_df['Amount Paid'].sum():,.0f}")
        with col4: st.metric("Expenses", f"${expenses_df['Amount'].sum() if len(expenses_df)>0 else 0:,.0f}")
        
        st.subheader("Students by Class")
        st.bar_chart(classes)
    
    with tab2:
        st.subheader("Financial Summary")
        fees = fee_payments_df['Amount Paid'].sum()
        expenses = expenses_df['Amount'].sum() if len(expenses_df)>0 else 0
        other = other_income_df['Amount'].sum() if len(other_income_df)>0 else 0
        
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("Fees", f"${fees:,.0f}")
        with col2: st.metric("Other Income", f"${other:,.0f}")
        with col3: st.metric("Expenses", f"${expenses:,.0f}")
        st.metric("Net Position", f"${fees + other - expenses:,.0f}")
    
    with tab3:
        st.subheader("All Students")
        st.dataframe(students_df, use_container_width=True, hide_index=True)
    
    with st.sidebar:
        st.markdown("## Focus Oasis")
        st.markdown("---")
        if st.button("Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user_type = None
            st.rerun()

# ============================================
# MAIN
# ============================================
if not st.session_state.logged_in:
    login_page()
else:
    if st.session_state.user_type == "Student":
        student_dashboard()
    else:
        admin_dashboard()
