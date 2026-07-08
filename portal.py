import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import base64
import time
from io import BytesIO
from datetime import date
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

    .stApp {
        background-color: #FFFFFF !important;
    }

    h1, h2, h3 {
        color: #1B2A4A !important;
        font-weight: 700 !important;
    }

    .stButton > button {
        background-color: #1B2A4A !important;
        color: white !important;
        border: none !important;
        border-radius: 6px !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
        width: 100% !important;
    }
    .stButton > button:hover {
        background-color: #2E86C1 !important;
    }

    [data-testid="stMetricValue"] {
        color: #1B2A4A !important;
        font-weight: 700 !important;
    }
    [data-testid="stMetricLabel"] {
        color: #2E86C1 !important;
    }

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

    hr {
        border-color: #2E86C1;
    }

    .stTextInput input:focus, .stDateInput input:focus {
        border-color: #2E86C1 !important;
        box-shadow: 0 0 0 2px rgba(46,134,193,0.2) !important;
    }

    div[data-testid="stRadio"] input[type="radio"] {
        accent-color: #2E86C1 !important;
    }

    .stTabs [aria-selected="true"] {
        background-color: #1B2A4A !important;
        color: white !important;
    }

    [data-testid="stExpander"] summary {
        border-left: 3px solid #2E86C1 !important;
    }

    .stSuccess {
        border-left: 4px solid #4CAF50 !important;
    }
    .stError {
        border-left: 4px solid #f44336 !important;
    }

    /* Footer */
    .footer {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background-color: #1B2A4A;
        color: white;
        text-align: center;
        padding: 12px;
        font-size: 14px;
        z-index: 100;
    }

    /* Section cards */
    .section-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 16px;
        border-left: 4px solid #2E86C1;
    }
    .section-card h4 {
        color: #1B2A4A !important;
        margin-top: 0;
    }

    /* Detail rows */
    .detail-row {
        display: flex;
        justify-content: space-between;
        padding: 8px 0;
        border-bottom: 1px solid #f0f0f0;
    }
    .detail-label {
        color: #666;
        font-weight: 600;
    }
    .detail-value {
        color: #1B2A4A;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)

SPREADSHEET_NAME = "Focus Oasis Foundation"

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


@st.cache_resource
def get_spreadsheet():
    # Cached alongside connect_to_sheets so the same open spreadsheet handle
    # is reused instead of re-opening it on every single read/write.
    return connect_to_sheets().open(SPREADSHEET_NAME)


@st.cache_data(ttl=60)
def get_worksheet_titles():
    # Cached for a minute so pages that check "does this optional sheet
    # exist" (Performance, Fee Structure, etc.) don't make a fresh API
    # call to list worksheets every time they render.
    return [ws.title for ws in get_spreadsheet().worksheets()]


def load_data(sheet_name, optional=False):
    """Load a worksheet as a DataFrame.

    If optional=True and the sheet doesn't exist, returns an empty
    DataFrame instead of raising, so pages relying on not-yet-created
    sheets (e.g. Performance) degrade gracefully.
    """
    if optional and sheet_name not in get_worksheet_titles():
        return pd.DataFrame()

    last_error = None
    for attempt in range(3):
        try:
            sheet = get_spreadsheet().worksheet(sheet_name)
            return pd.DataFrame(sheet.get_all_records())
        except Exception as e:
            last_error = e
            if attempt < 2:
                time.sleep(2)
    raise last_error


def update_cell(sheet_name, row, col, value):
    sheet = get_spreadsheet().worksheet(sheet_name)
    sheet.update_cell(row, col, value)

# ============================================
# PROFILE HELPERS
# ============================================
def get_student_profile(username):
    try:
        df = load_data("Student Profiles", optional=True)
        if len(df) == 0:
            return {"Username": username, "Display Name": "", "Profile Photo": ""}
        user = df[df["Username"] == username]
        if len(user) > 0:
            return user.iloc[0].to_dict()
    except Exception:
        pass
    return {"Username": username, "Display Name": "", "Profile Photo": ""}

def save_student_profile(username, display_name, photo_b64=""):
    sheet = get_spreadsheet().worksheet("Student Profiles")
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
            get_worksheet_titles.clear()
            return
    sheet.append_row(row_data)
    get_worksheet_titles.clear()

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
    if not full_name:
        return "?"
    parts = [p for p in full_name.strip().split() if p]
    if not parts:
        return "?"
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

def detail_row(label, value):
    st.markdown(
        f'<div class="detail-row"><span class="detail-label">{label}</span>'
        f'<span class="detail-value">{value}</span></div>',
        unsafe_allow_html=True
    )

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
DEFAULT_SESSION_STATE = {
    "logged_in": False,
    "user_type": None,
    "student_name": None,
    "username": None,
    "student_class": None,
    "current_page": "My Dashboard",
}
for key, default in DEFAULT_SESSION_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = default

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
                    st.session_state.current_page = "My Dashboard"
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

    # Load core data
    students_df = load_data("Students")
    fee_payments_df = load_data("Fee Payments")

    # Get student info
    student_info = students_df[students_df['Student Name'] == st.session_state.student_name]
    has_student_row = len(student_info) > 0
    student_row = student_info.iloc[0] if has_student_row else pd.Series(dtype=object)

    def field(name, default="N/A"):
        return student_row.get(name, default) if has_student_row else default

    if has_student_row:
        student_class = student_row.get('Class', st.session_state.student_class)

        # Fee calculations
        all_payments = fee_payments_df[fee_payments_df['Student Name'] == st.session_state.student_name]
        total_paid = all_payments['Amount Paid'].sum()

        # Current term fees (latest month)
        current_month = date.today().strftime('%B %Y')
        current_term_paid = all_payments[all_payments['Month Covered'] == current_month]['Amount Paid'].sum()

        # Previous terms balance (all months except current)
        prev_payments = all_payments[all_payments['Month Covered'] != current_month]

        # Monthly fee from Fee Structure, if that sheet exists
        fee_structure_df = load_data("Fee Structure", optional=True)
        if len(fee_structure_df) > 0:
            monthly_fee = fee_structure_df[fee_structure_df['Class'] == student_class]['Monthly Fee'].sum()
        else:
            monthly_fee = 50  # default

        # Calculate previous terms balance
        months_enrolled = len(all_payments['Month Covered'].unique()) if len(all_payments) > 0 else 1
        prev_terms_fees = (months_enrolled - 1) * monthly_fee if months_enrolled > 1 else 0
        prev_terms_paid = prev_payments['Amount Paid'].sum() if len(prev_payments) > 0 else 0
        prev_balance = max(0, prev_terms_fees - prev_terms_paid)

        # Overall balance
        total_fees_due = months_enrolled * monthly_fee
        overall_balance = max(0, total_fees_due - total_paid)

        current_term_fee = monthly_fee
        current_balance = max(0, current_term_fee - current_term_paid)

    else:
        student_class = st.session_state.student_class
        total_paid = 0
        current_term_paid = 0
        prev_balance = 0
        overall_balance = 0
        current_term_fee = 0
        current_balance = 0
        monthly_fee = 0

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

    # ============================================
    # PAGE: MY DASHBOARD
    # ============================================
    if st.session_state.current_page == "My Dashboard":
        # Personal Details Section
        st.markdown('<div class="section-card"><h4>Personal Details</h4>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            detail_row("Full Name", st.session_state.student_name)
            detail_row("Date of Birth", field("Date of Birth"))
            detail_row("Gender", field("Gender"))
        with col2:
            detail_row("Address", field("Address"))
            detail_row("Guardian Name", field("Guardian Name"))
            detail_row("Guardian Phone", field("Guardian Phone"))
        st.markdown("</div>", unsafe_allow_html=True)

        # Academic Details Section
        st.markdown('<div class="section-card"><h4>Academic Details</h4>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            detail_row("Student Number", field("Student Number"))
            detail_row("Class", student_class)
        with col2:
            detail_row("Registration Status", "Active")
            detail_row("Academic Year", "2026")
        st.markdown("</div>", unsafe_allow_html=True)

        # Financial Details Section
        st.markdown('<div class="section-card"><h4>Financial Details</h4>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Current Term Fees", f"${current_term_fee:,.0f}")
            st.metric("Current Fees Paid", f"${current_term_paid:,.0f}")
        with col2:
            st.metric("Previous Terms Balance", f"${prev_balance:,.0f}")
            st.metric("Overall Fees Balance", f"${overall_balance:,.0f}",
                     delta="Paid Full" if overall_balance <= 0 else "Outstanding")
        st.markdown("</div>", unsafe_allow_html=True)

    # ============================================
    # PAGE: FEE SUMMARY
    # ============================================
    elif st.session_state.current_page == "Fee Summary":
        st.subheader("Fee Summary")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Fees Payable", f"${current_term_fee:,.0f}")
        with col2:
            st.metric("Fees Paid", f"${total_paid:,.0f}")
        with col3:
            st.metric("Balance Owing", f"${overall_balance:,.0f}",
                     delta="Paid Full" if overall_balance <= 0 else "Outstanding")

    # ============================================
    # PAGE: PAYMENT HISTORY
    # ============================================
    elif st.session_state.current_page == "Payment History":
        st.subheader("Payment History")

        my_payments = fee_payments_df[fee_payments_df['Student Name'] == st.session_state.student_name]

        if len(my_payments) > 0:
            payment_display = my_payments[['Date', 'Month Covered', 'Amount Paid', 'Payment Method']].copy()
            payment_display.columns = ['Date', 'Description', 'Amount', 'Method']
            payment_display = payment_display.sort_values('Date', ascending=False)
            st.dataframe(payment_display, use_container_width=True, hide_index=True)

            st.divider()
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Payments", len(payment_display))
            with col2:
                st.metric("Total Paid", f"${total_paid:,.0f}")
            with col3:
                st.metric("Latest Payment", f"${payment_display.iloc[0]['Amount']:,.0f}" if len(payment_display) > 0 else "$0")
        else:
            st.info("No payment records found.")

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align:center;color:#1B2A4A;padding:20px 0;">
        <p style="margin:0;font-size:14px;">© 2026 Focus Oasis Foundation</p>
        <p style="margin:5px 0 0 0;font-size:12px;color:#2E86C1;">All Rights Reserved</p>
    </div>
    """, unsafe_allow_html=True)

    # ============================================
    # SIDEBAR
    # ============================================
    with st.sidebar:
        st.markdown("## Focus Oasis")
        st.markdown("---")

        display_student_photo(profile.get("Profile Photo", ""), size=80, name=st.session_state.student_name)
        st.markdown(f"<p style='text-align:center;color:white;font-weight:700;'>{display_name}</p>",
                   unsafe_allow_html=True)
        st.markdown(f"<p style='text-align:center;color:#2E86C1;font-size:12px;'>{student_class}</p>",
                   unsafe_allow_html=True)
        st.markdown("---")

        if st.button("My Dashboard", use_container_width=True,
                    type="primary" if st.session_state.current_page == "My Dashboard" else "secondary"):
            st.session_state.current_page = "My Dashboard"
            st.rerun()

        if st.button("Fee Summary", use_container_width=True,
                    type="primary" if st.session_state.current_page == "Fee Summary" else "secondary"):
            st.session_state.current_page = "Fee Summary"
            st.rerun()

        if st.button("Payment History", use_container_width=True,
                    type="primary" if st.session_state.current_page == "Payment History" else "secondary"):
            st.session_state.current_page = "Payment History"
            st.rerun()

        st.markdown("---")

        if st.button("Profile Settings", use_container_width=True):
            profile_settings_dialog(st.session_state.username, profile)

        st.markdown("---")

        if st.button("Logout", use_container_width=True):
            for key, default in DEFAULT_SESSION_STATE.items():
                st.session_state[key] = default
            st.rerun()

# ============================================
# ADMIN DASHBOARD
# ============================================
def admin_dashboard():
    st.title("Admin Dashboard - Focus Oasis Foundation")

    students_df = load_data("Students")
    fee_payments_df = load_data("Fee Payments")
    expenses_df = load_data("Expenses", optional=True)
    other_income_df = load_data("Other Income", optional=True)

    tab1, tab2, tab3 = st.tabs(["Overview", "Finances", "All Students"])

    with tab1:
        st.subheader("School Overview")
        classes = students_df['Class'].value_counts()

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Students", len(students_df))
        with col2:
            st.metric("Classes", len(classes))
        with col3:
            st.metric("Fees Collected", f"${fee_payments_df['Amount Paid'].sum():,.0f}")
        with col4:
            st.metric("Expenses", f"${expenses_df['Amount'].sum() if len(expenses_df) > 0 else 0:,.0f}")

        st.subheader("Students by Class")
        st.bar_chart(classes)

    with tab2:
        st.subheader("Financial Summary")
        fees = fee_payments_df['Amount Paid'].sum()
        expenses = expenses_df['Amount'].sum() if len(expenses_df) > 0 else 0
        other = other_income_df['Amount'].sum() if len(other_income_df) > 0 else 0

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Fees", f"${fees:,.0f}")
        with col2:
            st.metric("Other Income", f"${other:,.0f}")
        with col3:
            st.metric("Expenses", f"${expenses:,.0f}")
        st.metric("Net Position", f"${fees + other - expenses:,.0f}")

    with tab3:
        st.subheader("All Students")
        st.dataframe(students_df, use_container_width=True, hide_index=True)

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align:center;color:#1B2A4A;padding:20px 0;">
        <p style="margin:0;font-size:14px;">© 2026 Focus Oasis Foundation</p>
        <p style="margin:5px 0 0 0;font-size:12px;color:#2E86C1;">All Rights Reserved</p>
    </div>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("## Focus Oasis")
        st.markdown("---")
        if st.button("Logout", use_container_width=True):
            for key, default in DEFAULT_SESSION_STATE.items():
                st.session_state[key] = default
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
