import streamlit as st
import pandas as pd
from datetime import datetime
import time
import dropbox
from io import StringIO

# --- App Configuration ---
st.set_page_config(layout="wide", page_title="RKSC 2025 DURGA PUJA")

# --- File Paths and Constants ---
CREDIT_LOG_FILENAME = "credit_log.csv"
DEBIT_LOG_FILENAME = "debit_log.txt"
DUE_LIST_FILENAME = "due_list.csv"
DUE_COLLECTION_FILENAME = "due_collection.csv"

# Dropbox paths
DROPBOX_CREDIT_LOG_PATH = f"/{CREDIT_LOG_FILENAME}"
DROPBOX_DEBIT_LOG_PATH = f"/{DEBIT_LOG_FILENAME}"
DROPBOX_DUE_LIST_PATH = f"/{DUE_LIST_FILENAME}"
DROPBOX_DUE_COLLECTION_PATH = f"/{DUE_COLLECTION_FILENAME}"

ZONES = [
    "BILL no. 1- (1-100)", "BILL no. 2- (101-200)", "BILL no. 3- (201-300)",
    "BILL no. 4- (301-400)", "BILL no. 5- (401-500)", "BILL no. 6- (501-550)",
    "BILL no. 7- (551-600)", "BILL no. 8- (601-650)", "BILL no. 9- (651-700)",
    "BILL no. 10- (701-750)", "BILL no. 11- (751-800)", "BILL no. 12- (801-850)",
    "BILL no. 13- (851-875)", "BILL no. 14- (876-900)", "BILL no. 15- (901-925)",
    "BILL no. 16- (926-950)", "BILL no. 17- (951-975)", "BILL no. 18- (976-1000)",
    "donation"
]
ZONE_BILL_RANGES = {
    "BILL no. 1- (1-100)": (1, 100), "BILL no. 2- (101-200)": (101, 200),
    "BILL no. 3- (201-300)": (201, 300), "BILL no. 4- (301-400)": (301, 400),
    "BILL no. 5- (401-500)": (401, 500), "BILL no. 6- (501-550)": (501, 550),
    "BILL no. 7- (551-600)": (551, 600), "BILL no. 8- (601-650)": (601, 650),
    "BILL no. 9- (651-700)": (651, 700), "BILL no. 10- (701-750)": (701, 750),
    "BILL no. 11- (751-800)": (751, 800), "BILL no. 12- (801-850)": (801, 850),
    "BILL no. 13- (851-875)": (851, 875), "BILL no. 14- (876-900)": (876, 900),
    "BILL no. 15- (901-925)": (901, 925), "BILL no. 16- (926-950)": (926, 950),
    "BILL no. 17- (951-975)": (951, 975), "BILL no. 18- (976-1000)": (976, 1000)
}

# --- Passwords ---
STARTUP_PASSWORD = "start"
ADMIN_PASSWORD = "puja2025"

# --- Dropbox File Operations ---
def dropbox_file_exists(dbx, path):
    try:
        dbx.files_get_metadata(path)
        return True
    except dropbox.exceptions.ApiError as err:
        if err.error.get_path() and err.error.get_path().is_not_found():
            return False
        raise

def read_file_from_dropbox(dbx, path):
    try:
        _, res = dbx.files_download(path)
        return res.content.decode('utf-8')
    except dropbox.exceptions.ApiError as err:
        if err.error.get_path() and err.error.get_path().is_not_found():
            return None
        st.error(f"Dropbox API error reading {path}: {err}")
        return None

def write_file_to_dropbox(dbx, path, content):
    try:
        dbx.files_upload(content.encode('utf-8'), path, mode=dropbox.files.WriteMode('overwrite'))
        return True
    except Exception as e:
        st.error(f"Error writing to {path} on Dropbox: {e}")
        return False

def append_to_dropbox_file(dbx, path, content_to_append):
    try:
        existing_content = read_file_from_dropbox(dbx, path)
        full_content = (existing_content or "") + content_to_append
        return write_file_to_dropbox(dbx, path, full_content)
    except Exception as e:
        st.error(f"Error appending to {path} on Dropbox: {e}")
        return False

# --- Data Initialization ---
def initialize_dropbox_files(dbx):
    # CREDIT_LOG
    if not dropbox_file_exists(dbx, DROPBOX_CREDIT_LOG_PATH):
        df = pd.DataFrame(columns=["Zone", "Bill No", "Name", "Address", "Amount on Billbook", "Actual Amount Received", "Date", "Due Payment Date", "Partial Due Payment Date"])
        write_file_to_dropbox(dbx, DROPBOX_CREDIT_LOG_PATH, df.to_csv(index=False))

    # DUE_LIST
    if not dropbox_file_exists(dbx, DROPBOX_DUE_LIST_PATH):
        df = pd.DataFrame(columns=["Zone", "Bill No", "Name", "Address", "Due Amount"])
        write_file_to_dropbox(dbx, DROPBOX_DUE_LIST_PATH, df.to_csv(index=False))

    # DEBIT_LOG
    if not dropbox_file_exists(dbx, DROPBOX_DEBIT_LOG_PATH):
        write_file_to_dropbox(dbx, DROPBOX_DEBIT_LOG_PATH, "")

    # DUE_COLLECTION_LOG
    if not dropbox_file_exists(dbx, DROPBOX_DUE_COLLECTION_PATH):
        df = pd.DataFrame(columns=["Zone", "Bill No", "Name", "Address", "Amount on Billbook", "Total Amount Received", "Amount Paid Now", "Remaining Due", "Payment Date", "Status"])
        write_file_to_dropbox(dbx, DROPBOX_DUE_COLLECTION_PATH, df.to_csv(index=False))

# --- Data Loading ---
@st.cache_data(ttl=60)
def load_credit_data(_dbx):
    content = read_file_from_dropbox(_dbx, DROPBOX_CREDIT_LOG_PATH)
    if content:
        df = pd.read_csv(StringIO(content))
        if 'Due Payment Date' not in df.columns: df['Due Payment Date'] = pd.NA
        if 'Partial Due Payment Date' not in df.columns: df['Partial Due Payment Date'] = pd.NA
        return df
    return pd.DataFrame(columns=["Zone", "Bill No", "Name", "Address", "Amount on Billbook", "Actual Amount Received", "Date", "Due Payment Date", "Partial Due Payment Date"])

@st.cache_data(ttl=60)
def load_due_data(_dbx):
    content = read_file_from_dropbox(_dbx, DROPBOX_DUE_LIST_PATH)
    if content:
        df = pd.read_csv(StringIO(content))
        if 'Address' not in df.columns: df['Address'] = "N/A"
        return df
    return pd.DataFrame(columns=["Zone", "Bill No", "Name", "Address", "Due Amount"])

@st.cache_data(ttl=60)
def load_debit_data(_dbx):
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

@st.cache_data(ttl=60)
def load_due_collection_data(_dbx):
    content = read_file_from_dropbox(_dbx, DROPBOX_DUE_COLLECTION_PATH)
    if content:
        return pd.read_csv(StringIO(content))
    return pd.DataFrame(columns=["Zone", "Bill No", "Name", "Address", "Amount on Billbook", "Total Amount Received", "Amount Paid Now", "Remaining Due", "Payment Date", "Status"])

# --- Utility Functions ---
def get_next_bill_no(zone, current_credit_df):
    if zone not in ZONE_BILL_RANGES: return None
    start, end = ZONE_BILL_RANGES[zone]
    zone_transactions = current_credit_df[current_credit_df["Zone"] == zone]
    if zone_transactions.empty:
        return start
    used_bill_nos = set(zone_transactions["Bill No"].dropna().astype(int).tolist())
    for i in range(start, end + 1):
        if i not in used_bill_nos:
            return i
    return None

def display_message(type, text, duration=2):
    placeholder = st.empty()
    if type == 'success': placeholder.success(text)
    elif type == 'error': placeholder.error(text)
    elif type == 'warning': placeholder.warning(text)
    
    load_credit_data.clear()
    load_debit_data.clear()
    load_due_data.clear()
    load_due_collection_data.clear()
    
    time.sleep(duration)
    placeholder.empty()
    st.rerun()

# --- Main Application Logic ---
def main():
    if not st.session_state.get("startup_auth_success", False):
        st.title("🔐 Application Startup")
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
        try:
            token = st.secrets["DROPBOX_ACCESS_TOKEN"]
            return dropbox.Dropbox(token)
        except Exception as e:
            st.error(f"Could not connect to Dropbox. Check secrets.toml. Error: {e}")
            return None

    dbx = get_dbx_client()
    if not dbx: st.stop()

    initialize_dropbox_files(dbx)

    st.sidebar.title("🔁 Switch Mode")
    mode = st.sidebar.radio("Select Mode", ["User", "Admin"], key="main_mode_select")

    if mode == "User":
        st.title("👥 User Section")
        credit_df_user = load_credit_data(dbx)
        user_zone = st.selectbox("Select Zone to View Transactions", ZONES)
        if st.button("Show Zone Transactions"):
            user_data = credit_df_user[credit_df_user["Zone"] == user_zone]
            if not user_data.empty:
                st.dataframe(user_data.sort_values(by="Bill No"), use_container_width=True)
            else:
                st.info("No transactions yet for this zone.")

    elif mode == "Admin":
        if not st.session_state.get("admin_auth_success", False):
            st.sidebar.title("🔐 Admin Login")
            password = st.sidebar.text_input("Enter Admin Password", type="password")
            if st.sidebar.button("Login"):
                if password == ADMIN_PASSWORD:
                    st.session_state["admin_auth_success"] = True
                    st.rerun()
                else:
                    st.sidebar.error("Incorrect password.")
            st.warning("Admin access required to view panel.")
            st.stop()

        st.sidebar.title("🛠️ Admin Controls")
        selected_zone = st.sidebar.selectbox("Select Zone for Operations", ZONES)

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
                bill_no = st.number_input("Bill No", value=next_bill or 1, min_value=1, step=1)
                name = st.text_input("Name")
                address = st.text_input("Address")
                book_amt = st.number_input("Amount on Billbook", min_value=0.0, value=0.0)
                received_amt = st.number_input("Actual Amount Received", min_value=0.0, value=0.0)
                date = st.date_input("Date", value=datetime.today())
                
                if st.form_submit_button("Submit Credit"):
                    if not all([name.strip(), address.strip()]):
                        display_message('error', "Name and Address cannot be empty.")
                    elif not credit_df[(credit_df["Zone"] == selected_zone) & (credit_df["Bill No"] == bill_no)].empty:
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
                        updated_credit_df = pd.concat([credit_df, pd.DataFrame([new_row_data])], ignore_index=True)
                        write_file_to_dropbox(dbx, DROPBOX_CREDIT_LOG_PATH, updated_credit_df.sort_values(by=["Zone", "Bill No"]).to_csv(index=False))
                        
                        msg = "✅ Credit entry recorded."
                        if calculated_due > 0:
                            due_df = load_due_data(dbx)
                            new_due_row = {"Zone": selected_zone, "Bill No": int(bill_no), "Name": name, "Address": address, "Due Amount": calculated_due}
                            updated_due_df = pd.concat([due_df, pd.DataFrame([new_due_row])], ignore_index=True)
                            # MODIFIED: Sort due list before saving
                            write_file_to_dropbox(dbx, DROPBOX_DUE_LIST_PATH, updated_due_df.sort_values(by=["Zone", "Bill No"]).to_csv(index=False))
                            msg += f" ⚠️ ₹{calculated_due:.2f} due recorded."

                        display_message('success', msg)

            st.subheader("📋 Show Transactions")
            if st.button("Show Transactions for Zone"):
                zone_data = credit_df[credit_df["Zone"] == selected_zone]
                if not zone_data.empty:
                    st.dataframe(zone_data.sort_values(by="Bill No"), use_container_width=True)
                else:
                    st.info("No transactions yet for this zone.")
            
            if st.button("Show All Credit Bills"):
                all_credit_df = load_credit_data(dbx)
                if not all_credit_df.empty:
                    st.dataframe(all_credit_df.sort_values(by=["Zone", "Bill No"]), use_container_width=True)
                else:
                    st.info("No credit bills have been recorded yet.")

        with due_tab:
            st.header("Due Management")
            st.subheader("💸 Update Due List")
            current_due_df = load_due_data(dbx)
            zone_dues = current_due_df[current_due_df["Zone"] == selected_zone]
            bill_options = zone_dues["Bill No"].dropna().astype(int).tolist()

            if bill_options:
                selected_bill = st.selectbox("Due Bill No", options=bill_options)
                due_record = zone_dues[zone_dues["Bill No"] == selected_bill].iloc[0]
                
                st.write(f"Name: {due_record['Name']} | Address: {due_record.get('Address', 'N/A')} | Current Due: ₹{due_record['Due Amount']:.2f}")

                with st.form("update_due_form"):
                    amt_now = st.number_input("Received Now", min_value=0.0, max_value=float(due_record['Due Amount']), value=0.0)
                    payment_date = st.date_input("Payment Date", value=datetime.today())
                    update_btn, cancel_btn = st.columns(2)
                    
                    if update_btn.form_submit_button("Update Due"):
                        if amt_now > 0:
                            full_credit_df = load_credit_data(dbx)
                            credit_idx = full_credit_df[(full_credit_df["Zone"] == selected_zone) & (full_credit_df["Bill No"] == selected_bill)].index[0]
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
                                due_list_idx = current_due_df[(current_due_df["Zone"] == selected_zone) & (current_due_df['Bill No'] == selected_bill)].index[0]
                                current_due_df.loc[due_list_idx, "Due Amount"] = remaining_due
                                # MODIFIED: Sort due list before saving
                                write_file_to_dropbox(dbx, DROPBOX_DUE_LIST_PATH, current_due_df.sort_values(by=["Zone", "Bill No"]).to_csv(index=False))
                                due_collection_log["Status"] = "Partially Paid"
                                msg = f"✅ ₹{amt_now:.2f} received. Remaining: ₹{remaining_due:.2f}"
                            else:
                                full_credit_df.loc[credit_idx, "Due Payment Date"] = payment_date.strftime("%Y-%m-%d")
                                full_credit_df.loc[credit_idx, "Partial Due Payment Date"] = pd.NA
                                due_list_idx = current_due_df[(current_due_df["Zone"] == selected_zone) & (current_due_df['Bill No'] == selected_bill)].index[0]
                                current_due_df = current_due_df.drop(due_list_idx)
                                # MODIFIED: Sort due list before saving
                                write_file_to_dropbox(dbx, DROPBOX_DUE_LIST_PATH, current_due_df.sort_values(by=["Zone", "Bill No"]).to_csv(index=False))
                                due_collection_log["Status"] = "Fully Paid"
                                msg = f"✅ ₹{amt_now:.2f} received. Full due paid!"

                            write_file_to_dropbox(dbx, DROPBOX_CREDIT_LOG_PATH, full_credit_df.sort_values(by=["Zone", "Bill No"]).to_csv(index=False))
                            
                            due_collection_df = load_due_collection_data(dbx)
                            updated_due_collection_df = pd.concat([due_collection_df, pd.DataFrame([due_collection_log])], ignore_index=True)
                            write_file_to_dropbox(dbx, DROPBOX_DUE_COLLECTION_PATH, updated_due_collection_df.to_csv(index=False))
                            
                            display_message('success', msg)

                    if cancel_btn.form_submit_button("❌ Cancel Due"):
                        confirm_key = f"confirm_cancel_{selected_bill}"
                        if st.session_state.get(confirm_key, False):
                            due_list_idx = current_due_df[(current_due_df["Zone"] == selected_zone) & (current_due_df['Bill No'] == selected_bill)].index[0]
                            current_due_df = current_due_df.drop(due_list_idx)
                            # MODIFIED: Sort due list before saving
                            write_file_to_dropbox(dbx, DROPBOX_DUE_LIST_PATH, current_due_df.sort_values(by=["Zone", "Bill No"]).to_csv(index=False))
                            st.session_state[confirm_key] = False
                            display_message('success', f"Due for Bill No {selected_bill} has been cancelled.")
                        else:
                            st.session_state[confirm_key] = True
                            st.warning(f"Confirm cancellation for Bill No {selected_bill} by clicking '❌ Cancel Due' again.")
                            st.rerun()
            else:
                st.info(f"No outstanding due entries for {selected_zone}.")
            
            st.subheader("📄 Due Lists")
            show_dues, show_due_collections = st.columns(2)
            if show_dues.button("Show Current Due List"):
                due_df_display = load_due_data(dbx)
                filtered_dues = due_df_display[due_df_display["Zone"] == selected_zone]
                if not filtered_dues.empty:
                    st.dataframe(filtered_dues.sort_values(by="Bill No"), use_container_width=True)
                else: st.info("No current dues for this zone.")

            if show_due_collections.button("Show Due Collection History"):
                due_collection_df_display = load_due_collection_data(dbx)
                filtered_collections = due_collection_df_display[due_collection_df_display["Zone"] == selected_zone]
                if not filtered_collections.empty:
                    st.dataframe(filtered_collections.sort_values(by="Payment Date", ascending=False), use_container_width=True)
                else: st.info("No collection history yet for this zone.")
            
            if st.button("Show All Due Bills"):
                all_due_df = load_due_data(dbx)
                if not all_due_df.empty:
                    st.dataframe(all_due_df.sort_values(by=["Zone", "Bill No"]), use_container_width=True)
                else:
                    st.info("There are no outstanding due bills.")

        with update_tab:
            st.header("Update Transaction")
            credit_df_update = load_credit_data(dbx)
            zone_tx_update = credit_df_update[credit_df_update["Zone"] == selected_zone]
            bill_list_update = zone_tx_update["Bill No"].dropna().astype(int).tolist()

            if bill_list_update:
                selected_bill_edit = st.selectbox("Select Bill to Edit", bill_list_update)
                record_to_edit = zone_tx_update[zone_tx_update["Bill No"] == selected_bill_edit].iloc[0]

                with st.form("update_transaction_form"):
                    st.write(f"Editing Bill No: **{selected_bill_edit}**")
                    new_name = st.text_input("Name", record_to_edit["Name"])
                    new_addr = st.text_input("Address", record_to_edit["Address"])
                    new_book = st.number_input("Amount on Billbook", value=float(record_to_edit["Amount on Billbook"]), min_value=0.0)
                    new_actual = st.number_input("Actual Amount Received", value=float(record_to_edit["Actual Amount Received"]), min_value=0.0)
                    new_date = st.date_input("Date", value=pd.to_datetime(record_to_edit["Date"]).date())
                    
                    if st.form_submit_button("Update Entry"):
                        full_credit_df = load_credit_data(dbx)
                        full_due_df = load_due_data(dbx)
                        full_due_collection_df = load_due_collection_data(dbx)
                        
                        credit_idx = full_credit_df[(full_credit_df["Zone"] == selected_zone) & (full_credit_df["Bill No"] == selected_bill_edit)].index[0]
                        original_record = full_credit_df.loc[credit_idx].copy()
                        update_message = f"✅ Bill No {selected_bill_edit} has been updated."

                        amounts_changed = (float(original_record["Amount on Billbook"]) != new_book) or (float(original_record["Actual Amount Received"]) != new_actual)
                        details_changed = (original_record["Name"] != new_name) or (original_record["Address"] != new_addr)

                        due_collection_indices = full_due_collection_df[(full_due_collection_df["Bill No"] == selected_bill_edit) & (full_due_collection_df["Zone"] == selected_zone)].index
                        if not due_collection_indices.empty:
                            if amounts_changed:
                                full_due_collection_df = full_due_collection_df.drop(due_collection_indices)
                                write_file_to_dropbox(dbx, DROPBOX_DUE_COLLECTION_PATH, full_due_collection_df.to_csv(index=False))
                                update_message += " ⚠️ Due collection history was cleared due to amount changes."
                            elif details_changed:
                                full_due_collection_df.loc[due_collection_indices, ["Name", "Address"]] = [new_name, new_addr]
                                write_file_to_dropbox(dbx, DROPBOX_DUE_COLLECTION_PATH, full_due_collection_df.to_csv(index=False))
                                update_message += " Name/Address updated in due collection history."

                        full_credit_df.loc[credit_idx, ["Name", "Address", "Amount on Billbook", "Actual Amount Received", "Date"]] = [new_name, new_addr, new_book, new_actual, new_date.strftime("%Y-%m-%d")]
                        
                        recalculated_due = new_book - new_actual
                        due_idx = full_due_df[(full_due_df["Zone"] == selected_zone) & (full_due_df["Bill No"] == selected_bill_edit)].index
                        
                        if recalculated_due > 0:
                            if not due_idx.empty:
                                full_due_df.loc[due_idx[0], ["Due Amount", "Name", "Address"]] = [recalculated_due, new_name, new_addr]
                            else:
                                new_due_row = {"Zone": selected_zone, "Bill No": selected_bill_edit, "Name": new_name, "Address": new_addr, "Due Amount": recalculated_due}
                                full_due_df = pd.concat([full_due_df, pd.DataFrame([new_due_row])], ignore_index=True)
                            full_credit_df.loc[credit_idx, ["Due Payment Date", "Partial Due Payment Date"]] = [pd.NA, pd.NA]
                        else:
                            if not due_idx.empty:
                                full_due_df = full_due_df.drop(due_idx)
                            full_credit_df.loc[credit_idx, "Due Payment Date"] = new_date.strftime("%Y-%m-%d")
                            full_credit_df.loc[credit_idx, "Partial Due Payment Date"] = pd.NA
                        
                        write_file_to_dropbox(dbx, DROPBOX_CREDIT_LOG_PATH, full_credit_df.sort_values(by=["Zone", "Bill No"]).to_csv(index=False))
                        # MODIFIED: Sort due list before saving
                        write_file_to_dropbox(dbx, DROPBOX_DUE_LIST_PATH, full_due_df.sort_values(by=["Zone", "Bill No"]).to_csv(index=False))
                        
                        display_message('success', update_message)
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
                        display_message('success', "✅ Debit entry saved.")
                    else:
                        display_message('error', "Purpose cannot be empty and amount cannot be negative.")
            
            st.markdown("---")
            st.subheader("Show All Debits")
            if st.button("Show All Debit Transactions"):
                all_debits, _ = load_debit_data(dbx)
                if all_debits:
                    st.dataframe(pd.DataFrame(all_debits).sort_values(by="Date", ascending=False), use_container_width=True)
                else:
                    st.info("No debit transactions recorded yet.")

        with summary_tab:
            st.header("Financial Summary")
            credit_df_summary = load_credit_data(dbx)
            due_df_summary = load_due_data(dbx)
            _, total_debit_summary = load_debit_data(dbx)
            
            summary_zone_choice = st.selectbox("View Summary for Zone", ZONES)
            
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
            selected_date = st.date_input("Select Date", value=datetime.today())
            selected_date_str = selected_date.strftime("%Y-%m-%d")

            st.subheader(f"Credit Transactions for {selected_date_str}")
            daily_credit = credit_df_date[credit_df_date["Date"] == selected_date_str]
            if not daily_credit.empty:
                st.dataframe(daily_credit, use_container_width=True)
                st.success(f"Total Credit on this day: ₹{daily_credit['Actual Amount Received'].sum():,.2f}")
            else:
                st.info("No credit transactions on this day.")

            st.subheader(f"Debit Transactions for {selected_date_str}")
            daily_debits = [e for e in debit_entries_date if e["Date"] == selected_date_str]
            if daily_debits:
                st.dataframe(pd.DataFrame(daily_debits), use_container_width=True)
                st.error(f"Total Debit on this day: ₹{sum(e['Amount'] for e in daily_debits):,.2f}")
            else:
                st.info("No debit transactions on this day.")

        with bill_info_tab:
            st.header("Bill Book Information")
            credit_df_bill = load_credit_data(dbx)
            search_bill_no = st.number_input("Enter Bill Number to Search", min_value=1, step=1)
            if st.button("Fetch Bill Information"):
                found_bills = credit_df_bill[credit_df_bill["Bill No"] == search_bill_no]
                if not found_bills.empty:
                    st.success(f"Details for Bill No: {search_bill_no}")
                    st.dataframe(found_bills, use_container_width=True)
                else:
                    st.info(f"Bill No: {search_bill_no} hasn't been issued yet")

if __name__ == "__main__":
    main()
