import streamlit as st
import pandas as pd
from datetime import datetime
import time
import dropbox  # Import the dropbox SDK

# --- App Configuration ---
st.set_page_config(layout="wide")

# --- File Paths and Constants ---
CREDIT_LOG_FILENAME = "credit_log.csv"
DEBIT_LOG_FILENAME = "debit_log.txt"
DUE_LIST_FILENAME = "due_list.csv"
DUE_COLLECTION_FILENAME = "due_collection.csv" # New file for due transactions

# Dropbox paths
DROPBOX_CREDIT_LOG_PATH = f"/{CREDIT_LOG_FILENAME}"
DROPBOX_DEBIT_LOG_PATH = f"/{DEBIT_LOG_FILENAME}"
DROPBOX_DUE_LIST_PATH = f"/{DUE_LIST_FILENAME}"
DROPBOX_DUE_COLLECTION_PATH = f"/{DUE_COLLECTION_FILENAME}" # New Dropbox path

ZONES = [
    "BILL no. 1- (1-100)",
    "BILL no. 2- (101-200)",
    "BILL no. 3- (201-300)",
    "BILL no. 4- (301-400)",
    "BILL no. 5- (401-500)",
    "BILL no. 6- (501-550)",
    "BILL no. 7- (551-600)",
    "BILL no. 8- (601-650)",
    "BILL no. 9- (651-700)",
    "BILL no. 10- (701-750)",
    "BILL no. 11- (751-800)",
    "BILL no. 12- (801-850)",
    "BILL no. 13- (851-875)",
    "BILL no. 14- (876-900)",
    "BILL no. 15- (901-925)",
    "BILL no. 16- (926-950)",
    "BILL no. 17- (951-975)",
    "BILL no. 18- (976-1000)",
    "donation"
]
ZONE_BILL_RANGES = {
    "BILL no. 1- (1-100)": (1, 100),
    "BILL no. 2- (101-200)": (101, 200),
    "BILL no. 3- (201-300)": (201, 300),
    "BILL no. 4- (301-400)": (301, 400),
    "BILL no. 5- (401-500)": (401, 500),
    "BILL no. 6- (501-550)": (501, 550),
    "BILL no. 7- (551-600)": (551, 600),
    "BILL no. 8- (601-650)": (601, 650),
    "BILL no. 9- (651-700)": (651, 700),
    "BILL no. 10- (701-750)": (701, 750),
    "BILL no. 11- (751-800)": (751, 800),
    "BILL no. 12- (801-850)": (801, 850),
    "BILL no. 13- (851-875)": (851, 875),
    "BILL no. 14- (876-900)": (876, 900),
    "BILL no. 15- (901-925)": (901, 925),
    "BILL no. 16- (926-950)": (926, 950),
    "BILL no. 17- (951-975)": (951, 975),
    "BILL no. 18- (976-1000)": (976, 1000)
}

# --- Passwords ---
STARTUP_PASSWORD = "start" 
ADMIN_PASSWORD = "puja2025"

# --- Dropbox File Operations ---

def dropbox_file_exists(dbx, path):
    """Checks if a file exists on Dropbox."""
    try:
        dbx.files_get_metadata(path)
        return True
    except dropbox.exceptions.ApiError as err:
        if err.error.get_path() and err.error.get_path().is_not_found():
            return False
        raise
    except Exception as e:
        st.error(f"Error checking Dropbox file existence for {path}: {e}")
        return False

def read_file_from_dropbox(dbx, path):
    """Reads content of a file from Dropbox."""
    try:
        _, res = dbx.files_download(path)
        return res.content.decode('utf-8')
    except dropbox.exceptions.ApiError as err:
        if err.error.get_path() and err.error.get_path().is_not_found():
            return None
        raise
    except Exception as e:
        st.error(f"Error reading {path} from Dropbox: {e}")
        return None

def write_file_to_dropbox(dbx, path, content):
    """Writes content to a file on Dropbox."""
    try:
        dbx.files_upload(content.encode('utf-8'), path, mode=dropbox.files.WriteMode('overwrite'))
        return True
    except Exception as e:
        st.error(f"Error writing to {path} on Dropbox: {e}")
        return False

def append_to_dropbox_file(dbx, path, content_to_append):
    """Appends content to a text file on Dropbox."""
    try:
        existing_content = read_file_from_dropbox(dbx, path)
        full_content = (existing_content or "") + content_to_append
        return write_file_to_dropbox(dbx, path, full_content)
    except Exception as e:
        st.error(f"Error appending to {path} on Dropbox: {e}")
        return False

# --- Data Initialization ---
def initialize_dropbox_files(dbx):
    """Initializes all required CSV/TXT files on Dropbox if they don't exist."""
    # CREDIT_LOG
    if not dropbox_file_exists(dbx, DROPBOX_CREDIT_LOG_PATH):
        df = pd.DataFrame(columns=["Zone", "Bill No", "Name", "Address", "Amount on Billbook", "Actual Amount Received", "Date", "Due Payment Date", "Partial Due Payment Date"])
        write_file_to_dropbox(dbx, DROPBOX_CREDIT_LOG_PATH, df.to_csv(index=False))
        st.info(f"Initialized {CREDIT_LOG_FILENAME} on Dropbox.")
    
    # DUE_LIST
    if not dropbox_file_exists(dbx, DROPBOX_DUE_LIST_PATH):
        df = pd.DataFrame(columns=["Zone", "Bill No", "Name", "Address", "Due Amount"])
        write_file_to_dropbox(dbx, DROPBOX_DUE_LIST_PATH, df.to_csv(index=False))
        st.info(f"Initialized {DUE_LIST_FILENAME} on Dropbox.")

    # DEBIT_LOG
    if not dropbox_file_exists(dbx, DROPBOX_DEBIT_LOG_PATH):
        write_file_to_dropbox(dbx, DROPBOX_DEBIT_LOG_PATH, "")
        st.info(f"Initialized {DEBIT_LOG_FILENAME} on Dropbox.")

    # DUE_COLLECTION_LOG (New)
    if not dropbox_file_exists(dbx, DROPBOX_DUE_COLLECTION_PATH):
        df = pd.DataFrame(columns=["Zone", "Bill No", "Name", "Address", "Amount on Billbook", "Total Amount Received", "Amount Paid Now", "Remaining Due", "Payment Date", "Status"])
        write_file_to_dropbox(dbx, DROPBOX_DUE_COLLECTION_PATH, df.to_csv(index=False))
        st.info(f"Initialized {DUE_COLLECTION_FILENAME} on Dropbox.")


# --- Data Loading ---
@st.cache_data(ttl=300) # Cache data for 5 minutes
def load_credit_data(_dbx):
    """Loads credit log data from Dropbox."""
    content = read_file_from_dropbox(_dbx, DROPBOX_CREDIT_LOG_PATH)
    if content:
        df = pd.read_csv(pd.io.common.StringIO(content))
        if 'Due Payment Date' not in df.columns:
            df['Due Payment Date'] = pd.NA
        if 'Partial Due Payment Date' not in df.columns:
            df['Partial Due Payment Date'] = pd.NA
        return df
    return pd.DataFrame(columns=["Zone", "Bill No", "Name", "Address", "Amount on Billbook", "Actual Amount Received", "Date", "Due Payment Date", "Partial Due Payment Date"])

@st.cache_data(ttl=300)
def load_due_data(_dbx):
    """Loads due list data from Dropbox."""
    content = read_file_from_dropbox(_dbx, DROPBOX_DUE_LIST_PATH)
    if content:
        df = pd.read_csv(pd.io.common.StringIO(content))
        if 'Address' not in df.columns: # For backward compatibility
            df['Address'] = "N/A"
        return df
    return pd.DataFrame(columns=["Zone", "Bill No", "Name", "Address", "Due Amount"])

@st.cache_data(ttl=300)
def load_debit_data(_dbx):
    """Loads debit log data from Dropbox."""
    total_debit = 0
    debit_entries = []
    content = read_file_from_dropbox(_dbx, DROPBOX_DEBIT_LOG_PATH)
    if content:
        for line in content.splitlines():
            parts = line.strip().split('|')
            if len(parts) >= 3:
                try:
                    date_str, amount_str, purpose = parts[0].strip(), parts[1].strip(), parts[2].strip()
                    amount = int(amount_str)
                    debit_entries.append({"Date": date_str, "Amount": amount, "Purpose": purpose})
                    total_debit += amount
                except (ValueError, IndexError):
                    st.warning(f"Skipping malformed debit log entry: {line.strip()}")
    return debit_entries, total_debit

@st.cache_data(ttl=300)
def load_due_collection_data(_dbx):
    """Loads due collection log data from Dropbox."""
    content = read_file_from_dropbox(_dbx, DROPBOX_DUE_COLLECTION_PATH)
    if content:
        return pd.read_csv(pd.io.common.StringIO(content))
    return pd.DataFrame(columns=["Zone", "Bill No", "Name", "Address", "Amount on Billbook", "Total Amount Received", "Amount Paid Now", "Remaining Due", "Payment Date", "Status"])

# --- Utility Functions ---

def get_next_bill_no(zone, current_credit_df):
    """Calculates the next available bill number for a given zone."""
    if zone not in ZONE_BILL_RANGES:
        return None
    start, end = ZONE_BILL_RANGES[zone]
    zone_transactions = current_credit_df[current_credit_df["Zone"] == zone]
    used_bill_nos = set(zone_transactions["Bill No"].tolist())
    for i in range(start, end + 1):
        if i not in used_bill_nos:
            return i
    return None

def display_message(type, text, duration=2):
    """Displays a Streamlit message and clears it after a duration."""
    placeholder = st.empty()
    if type == 'success':
        placeholder.success(text)
    elif type == 'error':
        placeholder.error(text)
    elif type == 'warning':
        placeholder.warning(text)
    elif type == 'info':
        placeholder.info(text)
    
    time.sleep(duration)
    placeholder.empty()
    st.rerun()

# --- Main Application Logic ---

def main():
    """Main function to run the Streamlit application."""
    
    if not st.session_state.get("startup_auth_success", False):
        st.title("🔐 Application Startup")
        st.info("Please enter the password to connect to the database and start the application.")
        with st.form("startup_form"):
            password = st.text_input("Startup Password", type="password")
            if st.form_submit_button("Login"):
                if password == STARTUP_PASSWORD:
                    st.session_state["startup_auth_success"] = True
                    st.rerun()
                else:
                    st.error("The startup password was incorrect.")
        return

    @st.cache_resource
    def get_dbx_client():
        token = st.secrets["DROPBOX_ACCESS_TOKEN"]
        return dropbox.Dropbox(token)
    
    try:
        dbx = get_dbx_client()
    except Exception as e:
        st.error(f"Error connecting to Dropbox: {e}")
        st.stop()

    initialize_dropbox_files(dbx)
    
    st.sidebar.title("🔁 Switch Mode")
    mode = st.sidebar.radio("Select Mode", ["User", "Admin"], key="main_mode_select")

    if mode == "User":
        st.title("👥 User Section")
        credit_df = load_credit_data(dbx)
        user_zone = st.selectbox("Select Zone to View Transactions", ZONES, key="user_zone_select")
        if st.button("Show Zone Transactions", key="show_user_tx_btn"):
            user_data = credit_df[credit_df["Zone"] == user_zone]
            if not user_data.empty:
                st.dataframe(user_data.sort_values(by="Bill No"), use_container_width=True)
            else:
                st.info("No transactions yet for this zone.")


    elif mode == "Admin":
        if not st.session_state.get("admin_auth_success", False):
            st.sidebar.title("🔐 Admin Login")
            password = st.sidebar.text_input("Enter Admin Password", type="password", key="admin_password_input")
            if st.sidebar.button("Login", key="admin_login_btn"):
                if password == ADMIN_PASSWORD:
                    st.session_state["admin_auth_success"] = True
                    st.rerun()
                else:
                    st.sidebar.error("Incorrect password.")
            st.warning("Admin access required to view panel.")
            st.stop()
        
        st.sidebar.title("🛠️ Admin Controls")
        selected_zone = st.sidebar.selectbox("Select Zone for Operations", ZONES, key="admin_global_zone_select")
        
        st.title("🛠 Admin Panel")
        st.header(f"Operating in: {selected_zone.upper()}")

        credit_tab, update_tab, due_tab, debit_tab, summary_tab, date_tab, bill_info_tab = st.tabs([
            "Credit & View Transactions", "Update Transaction", "Due Management", 
            "Debit Entry", "Summary", "Amount Per Date", "Bill Book Info"
        ])

        with credit_tab:
            st.header("Credit Entry & Transactions")
            credit_df = load_credit_data(dbx)
            st.subheader("➕ Credit Entry")
            next_bill = get_next_bill_no(selected_zone, credit_df)
            with st.form("credit_form", clear_on_submit=True):
                st.write(f"Next Bill No for {selected_zone}: `{next_bill or 'N/A'}`")
                bill_no = st.number_input("Bill No", value=next_bill or 1, min_value=1, max_value=500)
                name = st.text_input("Name")
                address = st.text_input("Address")
                book_amt = st.number_input("Amount on Billbook", min_value=0.0, value=0.0)
                received_amt = st.number_input("Actual Amount Received", min_value=0.0, value=0.0)
                date = st.date_input("Date", value=datetime.today())
                if st.form_submit_button("Submit Credit"):
                    if not all([name.strip(), address.strip()]):
                        display_message('error', "Name and Address cannot be empty.")
                    elif credit_df[(credit_df["Zone"] == selected_zone) & (credit_df["Bill No"] == bill_no)].any().any():
                        display_message('error', f"Bill No {bill_no} already exists for {selected_zone}.")
                    else:
                        calculated_due = book_amt - received_amt
                        new_row_data = {
                            "Zone": selected_zone, "Bill No": int(bill_no), "Name": name, "Address": address,
                            "Amount on Billbook": book_amt, "Actual Amount Received": received_amt,
                            "Date": date.strftime("%Y-%m-%d"),
                            "Due Payment Date": date.strftime("%Y-%m-%d") if calculated_due <= 0 else pd.NA,
                            "Partial Due Payment Date": pd.NA
                        }
                        new_credit_row = pd.DataFrame([new_row_data])
                        updated_credit_df = pd.concat([credit_df, new_credit_row], ignore_index=True)
                        write_file_to_dropbox(dbx, DROPBOX_CREDIT_LOG_PATH, updated_credit_df.to_csv(index=False))
                        load_credit_data.clear()

                        msg = "✅ Credit entry recorded."
                        if calculated_due > 0:
                            due_df = load_due_data(dbx)
                            new_due_row = pd.DataFrame([{"Zone": selected_zone, "Bill No": int(bill_no), "Name": name, "Address": address, "Due Amount": calculated_due}])
                            updated_due_df = pd.concat([due_df, new_due_row], ignore_index=True)
                            write_file_to_dropbox(dbx, DROPBOX_DUE_LIST_PATH, updated_due_df.to_csv(index=False))
                            load_due_data.clear()
                            msg += f" ⚠️ ₹{calculated_due:.2f} due recorded."
                        display_message('success', msg)

            st.subheader("📋 Show Transactions")
            if st.button("Show Transactions for Zone", key="show_admin_tx_btn"):
                zone_data = credit_df[credit_df["Zone"] == selected_zone]
                if not zone_data.empty:
                    st.dataframe(zone_data.sort_values(by="Bill No"), use_container_width=True)
                else:
                    st.info("No transactions yet for this zone.")

        with due_tab:
            st.header("Due Management")
            st.subheader("💸 Update Due List")
            current_due_df = load_due_data(dbx)
            zone_dues = current_due_df[current_due_df["Zone"] == selected_zone]
            bill_options = zone_dues["Bill No"].tolist()

            if bill_options:
                selected_bill = st.selectbox("Due Bill No", options=bill_options, key="due_bill_select")
                due_record_series = zone_dues[zone_dues["Bill No"] == selected_bill]
                
                if not due_record_series.empty:
                    due_record = due_record_series.iloc[0]
                    st.write(f"Name: {due_record['Name']} | Address: {due_record.get('Address', 'N/A')} | Current Due: ₹{due_record['Due Amount']:.2f}")

                    with st.form("update_due_form"):
                        amt_now = st.number_input("Received Now", min_value=0.0, max_value=float(due_record['Due Amount']), value=0.0)
                        payment_date = st.date_input("Payment Date", value=datetime.today())
                        update_btn, cancel_btn = st.columns(2)
                        
                        if update_btn.form_submit_button("Update Due"):
                            if amt_now > 0:
                                full_credit_df = load_credit_data(dbx)
                                credit_idx = full_credit_df[(full_credit_df["Zone"] == selected_zone) & (full_credit_df["Bill No"] == selected_bill)].index
                                
                                if not credit_idx.empty:
                                    credit_idx = credit_idx[0]
                                    original_credit_record = full_credit_df.loc[credit_idx]
                                    
                                    full_credit_df.loc[credit_idx, "Actual Amount Received"] += amt_now
                                    remaining_due = round(float(due_record["Due Amount"]) - amt_now, 2)
                                    
                                    due_collection_log = {
                                        "Zone": selected_zone, "Bill No": selected_bill, "Name": original_credit_record["Name"],
                                        "Address": original_credit_record["Address"], "Amount on Billbook": original_credit_record["Amount on Billbook"],
                                        "Total Amount Received": full_credit_df.loc[credit_idx, "Actual Amount Received"],
                                        "Amount Paid Now": amt_now, "Remaining Due": remaining_due,
                                        "Payment Date": payment_date.strftime("%Y-%m-%d")
                                    }

                                    if remaining_due > 0:
                                        full_credit_df.loc[credit_idx, "Partial Due Payment Date"] = payment_date.strftime("%Y-%m-%d")
                                        full_credit_df.loc[credit_idx, "Due Payment Date"] = pd.NA
                                        
                                        due_list_idx = current_due_df[current_due_df['Bill No'] == selected_bill].index[0]
                                        current_due_df.loc[due_list_idx, "Due Amount"] = remaining_due
                                        write_file_to_dropbox(dbx, DROPBOX_DUE_LIST_PATH, current_due_df.to_csv(index=False))
                                        due_collection_log["Status"] = "Partially Paid"
                                        msg = f"✅ ₹{amt_now:.2f} received. Remaining: ₹{remaining_due:.2f}"
                                    else:
                                        full_credit_df.loc[credit_idx, "Due Payment Date"] = payment_date.strftime("%Y-%m-%d")
                                        full_credit_df.loc[credit_idx, "Partial Due Payment Date"] = pd.NA
                                        
                                        due_list_idx = current_due_df[current_due_df['Bill No'] == selected_bill].index[0]
                                        current_due_df = current_due_df.drop(due_list_idx)
                                        write_file_to_dropbox(dbx, DROPBOX_DUE_LIST_PATH, current_due_df.to_csv(index=False))
                                        due_collection_log["Status"] = "Fully Paid"
                                        msg = f"✅ ₹{amt_now:.2f} received. Full due paid!"

                                    write_file_to_dropbox(dbx, DROPBOX_CREDIT_LOG_PATH, full_credit_df.to_csv(index=False))
                                    
                                    due_collection_df = load_due_collection_data(dbx)
                                    new_due_collection_entry = pd.DataFrame([due_collection_log])
                                    updated_due_collection_df = pd.concat([due_collection_df, new_due_collection_entry], ignore_index=True)
                                    write_file_to_dropbox(dbx, DROPBOX_DUE_COLLECTION_PATH, updated_due_collection_df.to_csv(index=False))

                                    load_credit_data.clear()
                                    load_due_data.clear()
                                    load_due_collection_data.clear()
                                    display_message('success', msg)

                        if cancel_btn.form_submit_button("❌ Cancel Due"):
                            confirm_key = f"confirm_cancel_{selected_bill}"
                            if st.session_state.get(confirm_key, False):
                                due_list_idx = current_due_df[current_due_df['Bill No'] == selected_bill].index[0]
                                current_due_df = current_due_df.drop(due_list_idx)
                                write_file_to_dropbox(dbx, DROPBOX_DUE_LIST_PATH, current_due_df.to_csv(index=False))
                                load_due_data.clear()
                                st.session_state[confirm_key] = False
                                display_message('success', f"Due for Bill No {selected_bill} has been cancelled.")
                            else:
                                st.session_state[confirm_key] = True
                                st.warning(f"Confirm cancellation for Bill No {selected_bill} by clicking '❌ Cancel Due' again.")
            else:
                st.info(f"No outstanding due entries for {selected_zone}.")

            st.subheader("📄 Due Lists")
            show_dues, show_due_collections = st.columns(2)
            if show_dues.button("Show Current Due List", key="show_due_list_btn"):
                due_df_display = load_due_data(dbx)
                filtered_dues = due_df_display[due_df_display["Zone"] == selected_zone]
                if not filtered_dues.empty:
                    st.dataframe(filtered_dues.sort_values(by="Bill No"), use_container_width=True)
                else:
                    st.info("No current dues for this zone.")

            if show_due_collections.button("Show Due Collection History", key="show_due_collection_btn"):
                due_collection_df = load_due_collection_data(dbx)
                filtered_collections = due_collection_df[due_collection_df["Zone"] == selected_zone]
                if not filtered_collections.empty:
                    st.dataframe(filtered_collections.sort_values(by="Payment Date", ascending=False), use_container_width=True)
                else:
                    st.info("No collection history yet for this zone.")
        
        with update_tab:
            st.header("Update Transaction")
            credit_df = load_credit_data(dbx)
            zone_transactions_for_update = credit_df[credit_df["Zone"] == selected_zone]
            bill_list_for_update = zone_transactions_for_update["Bill No"].tolist()

            if bill_list_for_update:
                selected_bill_to_edit = st.selectbox("Select Bill to Edit", bill_list_for_update, key="update_tx_bill_select")
                
                record_to_edit_series = zone_transactions_for_update[zone_transactions_for_update["Bill No"] == selected_bill_to_edit]
                
                if not record_to_edit_series.empty:
                    record_to_edit = record_to_edit_series.iloc[0]

                    with st.form("update_transaction_form"):
                        st.write(f"Editing Bill No: **{selected_bill_to_edit}**")
                        new_name = st.text_input("Name", record_to_edit["Name"])
                        new_addr = st.text_input("Address", record_to_edit["Address"])
                        new_book = st.number_input("Amount on Billbook", value=float(record_to_edit["Amount on Billbook"]), min_value=0.0)
                        new_actual = st.number_input("Actual Amount Received", value=float(record_to_edit["Actual Amount Received"]), min_value=0.0)
                        
                        try:
                            new_date_obj = pd.to_datetime(record_to_edit["Date"]).date()
                        except (ValueError, TypeError):
                            new_date_obj = datetime.today()
                            
                        new_date = st.date_input("Date", value=new_date_obj)
                        
                        if st.form_submit_button("Update Entry"):
                            full_credit_df = load_credit_data(dbx)
                            full_due_df = load_due_data(dbx)
                            full_due_collection_df = load_due_collection_data(dbx)

                            credit_idx = full_credit_df[
                                (full_credit_df["Zone"] == selected_zone) & 
                                (full_credit_df["Bill No"] == selected_bill_to_edit)
                            ].index

                            if not credit_idx.empty:
                                credit_idx = credit_idx[0]
                                original_record = full_credit_df.loc[credit_idx].copy()
                                update_message = f"✅ Bill No {selected_bill_to_edit} has been updated."

                                amounts_changed = (float(original_record["Amount on Billbook"]) != new_book) or \
                                                  (float(original_record["Actual Amount Received"]) != new_actual)
                                
                                details_changed = (original_record["Name"] != new_name) or \
                                                  (original_record["Address"] != new_addr)

                                due_collection_indices = full_due_collection_df[
                                    (full_due_collection_df["Bill No"] == selected_bill_to_edit) &
                                    (full_due_collection_df["Zone"] == selected_zone)
                                ].index

                                if not due_collection_indices.empty:
                                    if amounts_changed:
                                        full_due_collection_df = full_due_collection_df.drop(due_collection_indices)
                                        write_file_to_dropbox(dbx, DROPBOX_DUE_COLLECTION_PATH, full_due_collection_df.to_csv(index=False))
                                        load_due_collection_data.clear()
                                        update_message += " ⚠️ Due collection history was cleared due to amount changes."
                                    elif details_changed:
                                        full_due_collection_df.loc[due_collection_indices, "Name"] = new_name
                                        full_due_collection_df.loc[due_collection_indices, "Address"] = new_addr
                                        write_file_to_dropbox(dbx, DROPBOX_DUE_COLLECTION_PATH, full_due_collection_df.to_csv(index=False))
                                        load_due_collection_data.clear()
                                        update_message += " Name/Address updated in due collection history."

                                full_credit_df.loc[credit_idx, "Name"] = new_name
                                full_credit_df.loc[credit_idx, "Address"] = new_addr
                                full_credit_df.loc[credit_idx, "Amount on Billbook"] = new_book
                                full_credit_df.loc[credit_idx, "Actual Amount Received"] = new_actual
                                full_credit_df.loc[credit_idx, "Date"] = new_date.strftime("%Y-%m-%d")

                                recalculated_due = new_book - new_actual
                                due_idx = full_due_df[
                                    (full_due_df["Zone"] == selected_zone) & 
                                    (full_due_df["Bill No"] == selected_bill_to_edit)
                                ].index

                                if recalculated_due > 0:
                                    if not due_idx.empty:
                                        full_due_df.loc[due_idx[0], "Due Amount"] = recalculated_due
                                        full_due_df.loc[due_idx[0], "Name"] = new_name
                                        full_due_df.loc[due_idx[0], "Address"] = new_addr
                                    else:
                                        new_due_row = pd.DataFrame([{"Zone": selected_zone, "Bill No": selected_bill_to_edit, "Name": new_name, "Address": new_addr, "Due Amount": recalculated_due}])
                                        full_due_df = pd.concat([full_due_df, new_due_row], ignore_index=True)
                                    
                                    full_credit_df.loc[credit_idx, "Due Payment Date"] = pd.NA
                                    full_credit_df.loc[credit_idx, "Partial Due Payment Date"] = pd.NA
                                else:
                                    if not due_idx.empty:
                                        full_due_df = full_due_df.drop(due_idx)
                                    
                                    full_credit_df.loc[credit_idx, "Due Payment Date"] = new_date.strftime("%Y-%m-%d")
                                    full_credit_df.loc[credit_idx, "Partial Due Payment Date"] = pd.NA

                                write_file_to_dropbox(dbx, DROPBOX_CREDIT_LOG_PATH, full_credit_df.to_csv(index=False))
                                write_file_to_dropbox(dbx, DROPBOX_DUE_LIST_PATH, full_due_df.to_csv(index=False))
                                
                                load_credit_data.clear()
                                load_due_data.clear()

                                display_message('success', update_message)
                            else:
                                display_message('error', "Could not find the record to update.")
            else:
                st.info(f"No transactions available to update for {selected_zone}.")

        with debit_tab:
            st.header("Debit Entry")
            with st.form("debit_form", clear_on_submit=True):
                purpose = st.text_input("Purpose")
                debit_amt = st.number_input("Amount Debited", min_value=0.0, value=0.0)
                debit_date = st.date_input("Date", value=datetime.today())
                if st.form_submit_button("Submit Debit"):
                    if purpose.strip() and debit_amt >= 0:
                        append_to_dropbox_file(dbx, DROPBOX_DEBIT_LOG_PATH, f"{debit_date.strftime('%Y-%m-%d')} | {int(debit_amt)} | {purpose}\n")
                        load_debit_data.clear()
                        display_message('success', "✅ Debit entry saved.")
                    else:
                        display_message('error', "Purpose cannot be empty and amount cannot be negative.")
            
            st.markdown("---")
            st.subheader("Show All Debits")
            if st.button("Show All Debit Transactions"):
                all_debits, _ = load_debit_data(dbx)
                if all_debits:
                    debit_df = pd.DataFrame(all_debits)
                    st.dataframe(debit_df.sort_values(by="Date", ascending=False), use_container_width=True)
                else:
                    st.info("No debit transactions have been recorded yet.")


        with summary_tab:
            st.header("Financial Summary")
            summary_zone_choice = st.selectbox("View Summary for Zone", ZONES, key="summary_zone_select")
            
            credit_df_summary = load_credit_data(dbx)
            due_df_summary = load_due_data(dbx)
            _, total_debit_summary = load_debit_data(dbx)

            zone_total_credited = credit_df_summary[credit_df_summary["Zone"] == summary_zone_choice]["Actual Amount Received"].sum()
            due_zone_total = due_df_summary[due_df_summary["Zone"] == summary_zone_choice]["Due Amount"].sum()
            grand_total_credited = credit_df_summary["Actual Amount Received"].sum()
            total_cash_in_hand = grand_total_credited - total_debit_summary
            total_due_all = due_df_summary["Due Amount"].sum()

            st.subheader(f"Totals for {summary_zone_choice.upper()}")
            col1, col2 = st.columns(2)
            col1.info(f"💰 Total Credited: ₹{zone_total_credited:,.2f}")
            col2.warning(f"⏳ Total Due: ₹{due_zone_total:,.2f}")
            
            st.markdown("---")
            st.subheader("🏦 Overall Totals (All Zones)")
            col1, col2, col3, col4 = st.columns(4)
            col1.success(f"Grand Total Credited\n\n₹{grand_total_credited:,.2f}")
            col2.error(f"Total Debited\n\n₹{total_debit_summary:,.2f}")
            col3.info(f"Cash in Hand\n\n₹{total_cash_in_hand:,.2f}")
            col4.warning(f"Total Dues All Zones\n\n₹{total_due_all:,.2f}")

        with date_tab:
            st.header("Daily Financial Overview")
            credit_df_date = load_credit_data(dbx)
            debit_entries_date, _ = load_debit_data(dbx)
            selected_date_for_view = st.date_input("Select Date", value=datetime.today(), key="amount_per_date_select")
            selected_date_str = selected_date_for_view.strftime("%Y-%m-%d")

            st.subheader(f"Credit Transactions for {selected_date_str}")
            daily_credit_transactions = credit_df_date[credit_df_date["Date"] == selected_date_str]

            if not daily_credit_transactions.empty:
                grand_total_for_date = 0.0
                for zone in ZONES:
                    zone_daily_tx = daily_credit_transactions[daily_credit_transactions["Zone"] == zone]
                    if not zone_daily_tx.empty:
                        st.markdown(f"#### Zone: {zone.upper()}")
                        st.dataframe(zone_daily_tx, use_container_width=True)
                        zone_total = zone_daily_tx["Actual Amount Received"].sum()
                        st.info(f"Total Received for {zone.upper()}: ₹{zone_total:,.2f}")
                        grand_total_for_date += zone_total
                        st.markdown("---") 
                st.success(f"**Grand Total Received on {selected_date_str}: ₹{grand_total_for_date:,.2f}**")
            else:
                st.info(f"No credit transactions found for {selected_date_str}.")

            st.subheader(f"Debit Transactions for {selected_date_str}")
            daily_debit_transactions = [e for e in debit_entries_date if e["Date"] == selected_date_str]
            if daily_debit_transactions:
                st.dataframe(pd.DataFrame(daily_debit_transactions), use_container_width=True)
                daily_debit_sum = sum(e["Amount"] for e in daily_debit_transactions)
                st.error(f"Total Debited on {selected_date_str}: ₹{daily_debit_sum:,.2f}")
            else:
                st.info(f"No debit transactions found for {selected_date_str}.")

        with bill_info_tab:
            st.header("Bill Book Information")
            credit_df_bill = load_credit_data(dbx)
            search_bill_no = st.number_input("Enter Bill Number to Search", min_value=1, value=1, key="search_bill_no_input")
            if st.button("Fetch Bill Information", key="fetch_bill_info_btn"):
                found_bills = credit_df_bill[credit_df_bill["Bill No"] == search_bill_no]
                if not found_bills.empty:
                    st.success(f"Details for Bill No: {search_bill_no}")
                    st.dataframe(found_bills, use_container_width=True)
                else:
                    st.info(f"Bill No {search_bill_no} has not been issued yet.")

if __name__ == "__main__":
    main()
