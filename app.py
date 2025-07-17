import streamlit as st
import pandas as pd
import os
from datetime import datetime
import time
import dropbox # Import the dropbox SDK

# --- File Paths and Constants ---
# Ensure 'data' directory exists for storing CSV/TXT files
DATA_DIR = "data" # This local directory will still be used for initial setup, but not for persistent storage
CREDIT_LOG_FILENAME = "credit_log.csv"
DEBIT_LOG_FILENAME = "debit_log.txt"
DUE_LIST_FILENAME = "due_list.csv"

# Dropbox paths (these are relative to your Dropbox app's root or full Dropbox root)
# If you chose "App folder" access, these paths are relative to that app folder.
# If you chose "Full Dropbox" access, these paths are relative to your Dropbox root.
DROPBOX_CREDIT_LOG_PATH = f"/{CREDIT_LOG_FILENAME}"
DROPBOX_DEBIT_LOG_PATH = f"/{DEBIT_LOG_FILENAME}"
DROPBOX_DUE_LIST_PATH = f"/{DUE_LIST_FILENAME}"

ZONES = ["zone1", "zone2", "zone3", "zone4", "zone5", "donation"]
ZONE_BILL_RANGES = {
    "zone1": (1, 100),
    "zone2": (101, 200),
    "zone3": (201, 300),
    "zone4": (301, 400),
    "zone5": (401, 500)
}

ADMIN_PASSWORD = "puja2025" # INSECURE: Hardcoded password. Replace with proper authentication for production.

# --- Data Initialization (Local for startup, Dropbox for persistence) ---
os.makedirs(DATA_DIR, exist_ok=True)

# --- Dropbox Client Initialization ---
# Get Dropbox access token from Streamlit secrets
try:
    DROPBOX_ACCESS_TOKEN = st.secrets["DROPBOX_ACCESS_TOKEN"]
    dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)
    # st.success("Connected to Dropbox!") # Commented out to reduce clutter on every rerun
except KeyError:
    st.error("Dropbox access token not found in Streamlit secrets. Please set `DROPBOX_ACCESS_TOKEN`.")
    st.stop()
except Exception as e:
    st.error(f"Error connecting to Dropbox: {e}")
    st.stop()

# --- Dropbox File Operations ---

def dropbox_file_exists(path):
    """Checks if a file exists on Dropbox."""
    try:
        dbx.files_get_metadata(path)
        return True
    except dropbox.exceptions.ApiError as err:
        if err.error.get_path() and err.error.get_path().is_not_found():
            return False
        raise # Re-raise other API errors
    except Exception as e:
        st.error(f"Error checking Dropbox file existence for {path}: {e}")
        return False # Assume not found on other errors for now

def read_file_from_dropbox(path):
    """Reads content of a file from Dropbox."""
    try:
        metadata, res = dbx.files_download(path)
        return res.content.decode('utf-8')
    except dropbox.exceptions.ApiError as err:
        if err.error.get_path() and err.error.get_path().is_not_found():
            return None # File not found
        raise # Re-raise other API errors
    except Exception as e:
        st.error(f"Error reading {path} from Dropbox: {e}")
        return None

def write_file_to_dropbox(path, content):
    """Writes content to a file on Dropbox."""
    try:
        dbx.files_upload(content.encode('utf-8'), path, mode=dropbox.files.WriteMode('overwrite'))
        return True
    except Exception as e:
        st.error(f"Error writing to {path} on Dropbox: {e}")
        return False

def append_to_dropbox_file(path, content_to_append):
    """Appends content to a text file on Dropbox."""
    try:
        # Download existing content, append, then upload
        existing_content = read_file_from_dropbox(path)
        if existing_content is None: # File didn't exist
            full_content = content_to_append
        else:
            full_content = existing_content + content_to_append
        
        return write_file_to_dropbox(path, full_content)
    except Exception as e:
        st.error(f"Error appending to {path} on Dropbox: {e}")
        return False

# --- Data Initialization (Modified for Dropbox) ---
def initialize_dropbox_files():
    """Initializes CSV/TXT files on Dropbox if they don't exist."""
    # CREDIT_LOG
    if not dropbox_file_exists(DROPBOX_CREDIT_LOG_PATH):
        df = pd.DataFrame(columns=["Zone", "Bill No", "Name", "Address", "Amount on Billbook", "Actual Amount Received", "Date", "Due Payment Date"])
        write_file_to_dropbox(DROPBOX_CREDIT_LOG_PATH, df.to_csv(index=False))
        st.info(f"Initialized {CREDIT_LOG_FILENAME} on Dropbox.")
    
    # DUE_LIST
    if not dropbox_file_exists(DROPBOX_DUE_LIST_PATH):
        df = pd.DataFrame(columns=["Zone", "Bill No", "Name", "Due Amount"])
        write_file_to_dropbox(DROPBOX_DUE_LIST_PATH, df.to_csv(index=False))
        st.info(f"Initialized {DUE_LIST_FILENAME} on Dropbox.")

    # DEBIT_LOG
    if not dropbox_file_exists(DROPBOX_DEBIT_LOG_PATH):
        write_file_to_dropbox(DROPBOX_DEBIT_LOG_PATH, "") # Empty file
        st.info(f"Initialized {DEBIT_LOG_FILENAME} on Dropbox.")

# Call initialization once at the start
initialize_dropbox_files()

# --- Data Loading (Modified for Dropbox) ---
@st.cache_data
def load_credit_data():
    """Loads credit log data from Dropbox, ensuring 'Due Payment Date' column exists."""
    content = read_file_from_dropbox(DROPBOX_CREDIT_LOG_PATH)
    if content:
        df = pd.read_csv(pd.io.common.StringIO(content))
        if 'Due Payment Date' not in df.columns:
            df['Due Payment Date'] = pd.NA # Use pandas NA for missing values
        return df
    return pd.DataFrame(columns=["Zone", "Bill No", "Name", "Address", "Amount on Billbook", "Actual Amount Received", "Date", "Due Payment Date"])

@st.cache_data
def load_due_data():
    """Loads due list data from Dropbox."""
    content = read_file_from_dropbox(DROPBOX_DUE_LIST_PATH)
    if content:
        return pd.read_csv(pd.io.common.StringIO(content))
    return pd.DataFrame(columns=["Zone", "Bill No", "Name", "Due Amount"])

@st.cache_data
def load_debit_data():
    """Loads debit log data from Dropbox."""
    total_debit = 0
    debit_entries = []
    content = read_file_from_dropbox(DROPBOX_DEBIT_LOG_PATH)
    if content:
        for line in content.splitlines():
            parts = line.strip().split('|')
            if len(parts) >= 3:
                try:
                    date_str = parts[0].strip()
                    amount = int(parts[1].strip())
                    purpose = parts[2].strip()
                    debit_entries.append({"Date": date_str, "Amount": amount, "Purpose": purpose})
                    total_debit += amount
                except ValueError:
                    st.warning(f"Skipping malformed debit log entry: {line.strip()}")
    return debit_entries, total_debit

# --- Utility Functions ---

def get_next_bill_no(zone, current_credit_df):
    """Calculates the next available bill number for a given zone."""
    if zone not in ZONE_BILL_RANGES:
        return None # No specific range for 'donation' or unconfigured zones

    start, end = ZONE_BILL_RANGES[zone]
    zone_transactions = current_credit_df[current_credit_df["Zone"] == zone]
    used_bill_nos = set(zone_transactions["Bill No"].tolist())

    for i in range(start, end + 1):
        if i not in used_bill_nos:
            return i
    return None # All bills in range are used

def display_message(type, text, duration=2):
    """Displays a Streamlit message and clears it after a duration."""
    if type == 'success':
        st.success(text)
    elif type == 'error':
        st.error(text)
    elif type == 'warning':
        st.warning(text)
    elif type == 'info':
        st.info(text)
    
    time.sleep(duration)
    st.rerun() # Rerun to clear message and refresh state

# --- Main Application Logic ---

def main():
    st.sidebar.title("🔁 Switch Mode")
    mode = st.sidebar.radio("Select Mode", ["User", "Admin"])

    # Load dataframes at the start of each run (will use cache if available)
    credit_df = load_credit_data()
    due_df = load_due_data() # Load due_df explicitly
    debit_entries, total_debit = load_debit_data()

    # --- USER MODE ---
    if mode == "User":
        st.title("👥 User Section")
        user_zone = st.selectbox("Select Zone to View Transactions", ZONES, key="user_zone_select")

        if st.button("Show Zone Transactions", key="show_user_tx_btn"):
            user_data = credit_df[credit_df["Zone"] == user_zone]
            if not user_data.empty:
                st.dataframe(user_data.sort_values(by="Bill No"), use_container_width=True)
            else:
                st.info("No transactions yet for this zone.")

    # --- ADMIN MODE ---
    elif mode == "Admin":
        st.sidebar.title("🔐 Admin Login")
        password = st.sidebar.text_input("Enter Password", type="password", key="admin_password_input")

        if password != ADMIN_PASSWORD:
            st.warning("Admin access required.")
            st.stop() # Stop execution if password is incorrect

        st.title("🛠 Admin Panel")

        # Admin Navigation Tabs (Top Level)
        admin_tab_main_ops, admin_tab_debit, admin_tab_summary, admin_tab_amount_per_date, admin_tab_bill_info = st.tabs(["Main Operations", "Debit Entry", "Summary", "Amount Per Date", "Bill Book Info"])

        # --- Admin Main Operations Tab (Nested Tabs) ---
        with admin_tab_main_ops:
            st.header("Main Operations")
            selected_zone = st.selectbox("Select Zone", ZONES, key="admin_zone_select_main_ops")

            # Nested tabs for Main Operations functionalities
            main_ops_credit_view, main_ops_update_tx, main_ops_due_management = st.tabs(["Credit & View Transactions", "Update Transaction", "Due Management"])

            # --- Credit Entry & Show Transactions Page ---
            with main_ops_credit_view:
                st.subheader("➕ Credit Entry")
                next_bill = get_next_bill_no(selected_zone, credit_df)

                with st.form("credit_form", clear_on_submit=True):
                    st.write(f"Next Bill No: `{next_bill if next_bill is not None else 'N/A'}`")
                    bill_no = st.number_input("Bill No", value=next_bill if next_bill is not None else 1, min_value=1, max_value=500, key="credit_bill_no")
                    name = st.text_input("Name", key="credit_name")
                    address = st.text_input("Address", key="credit_address")
                    book_amt = st.number_input("Amount on Billbook", min_value=0.0, value=0.0, key="credit_book_amt")
                    received_amt = st.number_input("Actual Amount Received", min_value=0.0, value=0.0, key="credit_received_amt")
                    date = st.date_input("Date", value=datetime.today(), key="credit_date")
                    submit_credit = st.form_submit_button("Submit Credit")

                    if submit_credit:
                        if not name.strip() or not address.strip():
                            display_message('error', "Name and Address cannot be empty.")
                        elif bill_no is None:
                            display_message('error', "Cannot assign bill number. Range might be full or undefined.")
                        elif credit_df[(credit_df["Zone"] == selected_zone) & (credit_df["Bill No"] == bill_no)].any().any():
                            display_message('error', f"Bill No {bill_no} already exists for {selected_zone}.")
                        else:
                            # Calculate due amount for due_list.csv
                            calculated_due_amt = book_amt - received_amt
                            
                            # Determine Due Payment Date for credit_log.csv
                            due_payment_date_in_credit_log = pd.NA # Default to Not Applicable/Null
                            if calculated_due_amt <= 0: # If fully paid or overpaid at time of entry
                                due_payment_date_in_credit_log = date.strftime("%Y-%m-%d") # Mark as paid today

                            new_credit_row = pd.DataFrame([{
                                "Zone": selected_zone,
                                "Bill No": int(bill_no),
                                "Name": name,
                                "Address": address,
                                "Amount on Billbook": book_amt,
                                "Actual Amount Received": received_amt,
                                "Date": date.strftime("%Y-%m-%d"),
                                "Due Payment Date": due_payment_date_in_credit_log
                            }])
                            
                            # Append to CREDIT_LOG on Dropbox
                            current_credit_df_content = load_credit_data().to_csv(index=False)
                            updated_credit_df_content = current_credit_df_content + new_credit_row.to_csv(header=False, index=False)
                            write_file_to_dropbox(DROPBOX_CREDIT_LOG_PATH, updated_credit_df_content)
                            load_credit_data.clear() # Clear cache to reload fresh data

                            msg = "✅ Credit entry recorded."
                            if calculated_due_amt > 0:
                                # Add entry to DUE_LIST on Dropbox
                                new_due_entry = pd.DataFrame([{
                                    "Zone": selected_zone,
                                    "Bill No": int(bill_no),
                                    "Name": name,
                                    "Due Amount": calculated_due_amt
                                }])
                                current_due_df_content = load_due_data().to_csv(index=False)
                                updated_due_df_content = current_due_df_content + new_due_entry.to_csv(header=False, index=False)
                                write_file_to_dropbox(DROPBOX_DUE_LIST_PATH, updated_due_df_content)
                                load_due_data.clear() # Clear cache for due_df
                                msg += f" ⚠️ Amount mismatch! ₹{calculated_due_amt:.2f} due recorded."
                            
                            display_message('success', msg)

                st.subheader("📋 Show Transactions")
                if st.button("Show Transactions for Zone", key="show_admin_tx_btn"):
                    # Reload data just before display to ensure latest state after any credit entry
                    current_credit_df_for_display = load_credit_data()
                    zone_data_display = current_credit_df_for_display[current_credit_df_for_display["Zone"] == selected_zone]
                    if not zone_data_display.empty:
                        st.dataframe(zone_data_display.sort_values(by="Bill No"), use_container_width=True)
                    else:
                        st.info("No transactions to display for this zone.")

            # --- Update Transaction Page ---
            with main_ops_update_tx:
                st.subheader("✏️ Update Transaction")
                zone_transactions_for_update = credit_df[credit_df["Zone"] == selected_zone]
                bill_list_for_update = zone_transactions_for_update["Bill No"].tolist()

                if bill_list_for_update:
                    selected_bill_to_edit = st.selectbox("Select Bill to Edit", bill_list_for_update, key="update_tx_bill_select")
                    record_to_edit = zone_transactions_for_update[zone_transactions_for_update["Bill No"] == selected_bill_to_edit].iloc[0]

                    with st.form("update_transaction_form"):
                        new_name = st.text_input("Name", record_to_edit["Name"], key="update_tx_name")
                        new_addr = st.text_input("Address", record_to_edit["Address"], key="update_tx_address")
                        new_book = st.number_input("Amount on Billbook", value=float(record_to_edit["Amount on Billbook"]), min_value=0.0, key="update_tx_book_amt")
                        new_actual = st.number_input("Actual Amount Received", value=float(record_to_edit["Actual Amount Received"]), min_value=0.0, key="update_tx_actual_amt")
                        
                        # Ensure date is a datetime object for date_input
                        new_date_obj = datetime.strptime(record_to_edit["Date"], "%Y-%m-%d")
                        new_date = st.date_input("Date", value=new_date_obj, key="update_tx_date")
                        
                        update_btn = st.form_submit_button("Update Entry")

                        if update_btn:
                            if not new_name.strip() or not new_addr.strip():
                                display_message('error', "Name and Address cannot be empty.")
                            elif new_book < 0 or new_actual < 0:
                                display_message('error', "Amounts cannot be negative.")
                            else:
                                # Get the latest credit_df for modification
                                current_credit_df_mod = load_credit_data()
                                idx = current_credit_df_mod[(current_credit_df_mod["Zone"] == selected_zone) & (current_credit_df_mod["Bill No"] == selected_bill_to_edit)].index[0]
                                
                                current_credit_df_mod.at[idx, "Name"] = new_name
                                current_credit_df_mod.at[idx, "Address"] = new_addr
                                current_credit_df_mod.at[idx, "Amount on Billbook"] = new_book
                                current_credit_df_mod.at[idx, "Actual Amount Received"] = new_actual
                                current_credit_df_mod.at[idx, "Date"] = new_date.strftime("%Y-%m-%d")

                                # Update Due Payment Date in credit_log.csv based on new amounts
                                recalculated_due = new_book - new_actual
                                if recalculated_due <= 0: # If fully paid or overpaid
                                    current_credit_df_mod.at[idx, "Due Payment Date"] = new_date.strftime("%Y-%m-%d")
                                else:
                                    current_credit_df_mod.at[idx, "Due Payment Date"] = pd.NA # Mark as not paid yet

                                # Save updated credit_df to Dropbox
                                write_file_to_dropbox(DROPBOX_CREDIT_LOG_PATH, current_credit_df_mod.to_csv(index=False))
                                load_credit_data.clear() # Clear cache

                                # --- Update due_list.csv based on new amounts ---
                                current_due_df_mod = load_due_data()
                                due_idx_in_due_list = current_due_df_mod[(current_due_df_mod["Zone"] == selected_zone) & (current_due_df_mod["Bill No"] == selected_bill_to_edit)].index

                                if recalculated_due > 0: # Still has a due
                                    if not due_idx_in_due_list.empty: # Update existing due entry
                                        current_due_df_mod.at[due_idx_in_due_list[0], "Due Amount"] = recalculated_due
                                        current_due_df_mod.at[due_idx_in_due_list[0], "Name"] = new_name # Update name in due list too
                                    else: # Add new due entry
                                        new_due_row = pd.DataFrame([{
                                            "Zone": selected_zone,
                                            "Bill No": int(selected_bill_to_edit),
                                            "Name": new_name,
                                            "Due Amount": recalculated_due
                                        }])
                                        current_due_df_mod = pd.concat([current_due_df_mod, new_due_row], ignore_index=True)
                                else: # No longer due, remove from due_list.csv
                                    if not due_idx_in_due_list.empty:
                                        current_due_df_mod = current_due_df_mod.drop(due_idx_in_due_list).reset_index(drop=True)
                                
                                # Save updated due_df to Dropbox
                                write_file_to_dropbox(DROPBOX_DUE_LIST_PATH, current_due_df_mod.to_csv(index=False))
                                load_due_data.clear() # Clear cache for due_df

                                display_message('success', "✅ Transaction updated.")
                else:
                    st.info("No transactions available to update for this zone.")

            # --- Due Management Page ---
            with main_ops_due_management:
                st.subheader("💸 Update Due List")
                
                # Load the latest due_df for this section
                current_due_df_for_due_ops = load_due_data()
                zone_dues_for_update = current_due_df_for_due_ops[current_due_df_for_due_ops["Zone"] == selected_zone]
                bill_options_for_due = zone_dues_for_update["Bill No"].tolist()
                
                # Determine the index for the selectbox
                default_index = 0
                if 'selected_due_bill_select' in st.session_state and st.session_state['selected_due_bill_select'] in bill_options_for_due:
                    default_index = bill_options_for_due.index(st.session_state['selected_due_bill_select'])
                elif not bill_options_for_due: # No options available
                    default_index = 0 # This will make the selectbox display 'No options' if list is empty
                else: # Options available, but previous selection is gone or no previous selection
                    default_index = 0 # Default to the first item

                if not zone_dues_for_update.empty:
                    selected_due_bill = st.selectbox(
                        "Due Bill No",
                        options=bill_options_for_due,
                        key="selected_due_bill_select",
                        index=default_index
                    )
                    
                    # Ensure a valid record is selected before proceeding
                    if selected_due_bill is not None:
                        # Get the due record from the current due_df
                        due_record = zone_dues_for_update[zone_dues_for_update["Bill No"] == selected_due_bill].iloc[0]
                        
                        st.write(f"Name: {due_record['Name']} | Current Due: ₹{due_record['Due Amount']:.2f}")
                        
                        with st.form("update_due_form"):
                            amt_now = st.number_input("Received Now", min_value=0.0, max_value=float(due_record["Due Amount"]), value=0.0, key="received_now_input")
                            # Added the date input for due payment
                            due_payment_date_input = st.date_input("Due Payment Date (if fully paid)", value=datetime.today(), key="due_payment_date_input")
                            col1, col2 = st.columns(2)
                            update_due_btn = col1.form_submit_button("Update Due")
                            delete_due_btn = col2.form_submit_button("❌ Clear Due") # Changed text to "Clear Due"

                            if update_due_btn:
                                if amt_now <= 0:
                                    display_message('error', "Received amount must be greater than zero.")
                                else:
                                    # --- Update credit_log.csv (Actual Amount Received) ---
                                    current_credit_df_mod = load_credit_data()
                                    credit_tx_idx = current_credit_df_mod[
                                        (current_credit_df_mod["Zone"] == selected_zone) & 
                                        (current_credit_df_mod["Bill No"] == selected_due_bill)
                                    ].index

                                    if not credit_tx_idx.empty:
                                        current_credit_df_mod.at[credit_tx_idx[0], "Actual Amount Received"] += amt_now
                                        
                                        # --- Update due_list.csv (Due Amount) ---
                                        current_due_df_mod = load_due_data()
                                        due_idx_in_due_list = current_due_df_mod[
                                            (current_due_df_mod["Zone"] == selected_zone) & 
                                            (current_due_df_mod["Bill No"] == selected_due_bill)
                                        ].index[0]
                                        
                                        old_due_in_due_list = float(current_due_df_mod.at[due_idx_in_due_list, "Due Amount"])
                                        remaining_due_in_due_list = round(old_due_in_due_list - amt_now, 2)

                                        if remaining_due_in_due_list > 0:
                                            current_due_df_mod.at[due_idx_in_due_list, "Due Amount"] = remaining_due_in_due_list
                                            # Due Payment Date in credit_log remains NA if still due
                                            current_credit_df_mod.at[credit_tx_idx[0], "Due Payment Date"] = pd.NA
                                            msg = f"✅ ₹{amt_now:.2f} received. Remaining due: ₹{remaining_due_in_due_list:.2f}"
                                        else: # Due is fully paid or overpaid
                                            current_due_df_mod = current_due_df_mod.drop(due_idx_in_due_list).reset_index(drop=True)
                                            # Set Due Payment Date in credit_log.csv using the input date
                                            current_credit_df_mod.at[credit_tx_idx[0], "Due Payment Date"] = due_payment_date_input.strftime("%Y-%m-%d")
                                            msg = f"✅ ₹{amt_now:.2f} received. Full due paid! Entry removed from due list."
                                        
                                        # Save updated credit_df to Dropbox
                                        write_file_to_dropbox(DROPBOX_CREDIT_LOG_PATH, current_credit_df_mod.to_csv(index=False))
                                        load_credit_data.clear() # Clear credit cache
                                        
                                        # Save updated due_df to Dropbox
                                        write_file_to_dropbox(DROPBOX_DUE_LIST_PATH, current_due_df_mod.to_csv(index=False))
                                        load_due_data.clear() # Clear due cache
                                        
                                        display_message('success', msg)
                                    else:
                                        display_message('warning', "⚠️ Could not find matching entry in due list.")
                                # else:
                                #     display_message('warning', "⚠️ Original credit transaction not found for due update.")


                            if delete_due_btn: # This button means "clear the due" (write-off)
                                # Use a session state variable for confirmation
                                if st.session_state.get('confirm_clear_due', False):
                                    # --- Update credit_log.csv (ONLY Due Payment Date) ---
                                    current_credit_df_mod = load_credit_data()
                                    credit_tx_idx = current_credit_df_mod[
                                        (current_credit_df_mod["Zone"] == selected_zone) & 
                                        (current_credit_df_mod["Bill No"] == selected_due_bill)
                                    ].index
                                    
                                    if not credit_tx_idx.empty:
                                        # DO NOT change Actual Amount Received. Keep it as is.
                                        # Only set Due Payment Date to mark the due as cleared/written off.
                                        current_credit_df_mod.at[credit_tx_idx[0], "Due Payment Date"] = datetime.today().strftime("%Y-%m-%d") 
                                        
                                        # Save updated credit_df to Dropbox
                                        write_file_to_dropbox(DROPBOX_CREDIT_LOG_PATH, current_credit_df_mod.to_csv(index=False))
                                        load_credit_data.clear() # Clear credit cache
                                    else:
                                        display_message('warning', "⚠️ Original credit transaction not found for due clearing.")
                                        st.session_state['confirm_clear_due'] = False # Reset confirmation
                                        return

                                    # --- Remove from due_list.csv ---
                                    current_due_df_mod = load_due_data()
                                    due_idx_to_delete = current_due_df_mod[(current_due_df_mod["Zone"] == selected_zone) & (current_due_df_mod["Bill No"] == selected_due_bill)].index[0]
                                    current_due_df_mod = current_due_df_mod.drop(due_idx_to_delete).reset_index(drop=True)
                                    # Save updated due_df to Dropbox
                                    write_file_to_dropbox(DROPBOX_DUE_LIST_PATH, current_due_df_mod.to_csv(index=False))
                                    load_due_data.clear() # Clear due cache
                                    
                                    display_message('success', "✅ Due cleared (written off)! Entry removed from due list.")
                                    st.session_state['confirm_clear_due'] = False # Reset confirmation
                                else:
                                    st.warning(f"Click '❌ Clear Due' again to confirm clearing due for Bill No {selected_due_bill}.")
                                    st.session_state['confirm_clear_due'] = True # Set confirmation flag
                                    # No rerun here, let user click again or interact
                else: # No selected_due_bill available
                    st.info("No outstanding due entries for this zone.")

                st.subheader("📄 Show Due List")
                if st.button("Show Due List", key="show_due_list_btn"):
                    # Reload data just before display to ensure latest state
                    current_due_df_for_display = load_due_data()
                    filtered_dues = current_due_df_for_display[current_due_df_for_display["Zone"] == selected_zone]
                    if not filtered_dues.empty:
                        st.dataframe(filtered_dues.sort_values(by="Bill No"), use_container_width=True)
                    else:
                        st.info("No outstanding due entries for this zone.")

        # --- Admin Debit Entry Tab ---
        with admin_tab_debit:
            st.header("Debit Entry")
            st.subheader("➖ Debit Entry")
            with st.form("debit_form", clear_on_submit=True):
                purpose = st.text_input("Purpose", key="debit_purpose")
                debit_amt = st.number_input("Amount Debited", min_value=0.0, value=0.0, key="debit_amount")
                debit_date = st.date_input("Date", value=datetime.today(), key="debit_date")
                submit_debit = st.form_submit_button("Submit Debit")

                if submit_debit:
                    if not purpose.strip():
                        display_message('error', "Purpose cannot be empty.")
                    elif debit_amt < 0:
                        display_message('error', "Amount cannot be negative.")
                    else:
                        # Append to DEBIT_LOG on Dropbox
                        append_to_dropbox_file(DROPBOX_DEBIT_LOG_PATH, f"{debit_date.strftime('%Y-%m-%d')} | {int(debit_amt)} | {purpose}\n")
                        load_debit_data.clear() # Clear cache for debit data
                        display_message('success', "✅ Debit entry saved.")

        # --- Admin Summary Tab ---
        with admin_tab_summary:
            st.header("Summary")
            st.subheader("📊 Summary")

            # Recalculate totals based on latest data
            current_credit_df_summary = load_credit_data()
            current_due_df_summary = load_due_data() # Load due_df for summary
            _, current_total_debit_summary = load_debit_data() # Reload debit data for summary

            grand_total_credited = current_credit_df_summary["Actual Amount Received"].sum()
            total_cash_in_hand = grand_total_credited - current_total_debit_summary
            
            # Total outstanding dues come from due_list.csv
            total_due_all = current_due_df_summary["Due Amount"].sum()

            # Ensure selected_zone is available, default if not (e.g., if summary tab is opened first)
            summary_zone = st.session_state.get('admin_zone_select_main_ops', ZONES[0])

            zone_total_credited = current_credit_df_summary[current_credit_df_summary["Zone"] == summary_zone]["Actual Amount Received"].sum()
            
            # Zone-specific outstanding dues come from due_list.csv
            due_zone_total = current_due_df_summary[current_due_df_summary["Zone"] == summary_zone]["Due Amount"].sum()

            st.info(f"💰 Total Credited for {summary_zone}: ₹{zone_total_credited:.2f}")
            st.success(f"🏦 Grand Total Credited: ₹{grand_total_credited:.2f}")
            st.error(f"💸 Total Debited: ₹{current_total_debit_summary:.2f}")
            st.warning(f"🧮 Cash in Hand: ₹{total_cash_in_hand:.2f}")
            st.info(f"⏳ Total Due for {summary_zone}: ₹{due_zone_total:.2f}")
            st.warning(f"📄 Total Dues All Zones: ₹{total_due_all:.2f}")

            st.subheader("Debit Log Details")
            if debit_entries:
                debit_df_display = pd.DataFrame(debit_entries)
                st.dataframe(debit_df_display.sort_values(by="Date", ascending=False), use_container_width=True)
            else:
                st.info("No debit entries recorded.")

        # --- Admin Amount Per Date Tab ---
        with admin_tab_amount_per_date:
            st.header("Amount Per Date")
            st.subheader("📅 Daily Financial Overview")

            selected_date_for_view = st.date_input("Select Date", value=datetime.today(), key="amount_per_date_select")
            selected_date_str = selected_date_for_view.strftime("%Y-%m-%d")

            st.markdown("---")
            st.subheader(f"Credit Transactions for {selected_date_str}")

            daily_credit_transactions = credit_df[credit_df["Date"] == selected_date_str].copy()

            if not daily_credit_transactions.empty:
                total_received_on_date = 0.0
                total_billed_on_date = 0.0

                for zone in ZONES:
                    zone_daily_transactions = daily_credit_transactions[daily_credit_transactions["Zone"] == zone]
                    if not zone_daily_transactions.empty:
                        st.markdown(f"**Zone: {zone.upper()}**")
                        st.dataframe(zone_daily_transactions[['Bill No', 'Name', 'Address', 'Amount on Billbook', 'Actual Amount Received']], use_container_width=True)
                        
                        zone_received_sum = zone_daily_transactions["Actual Amount Received"].sum()
                        zone_billed_sum = zone_daily_transactions["Amount on Billbook"].sum()
                        
                        st.info(f"Total Received for {zone.upper()} on {selected_date_str}: ₹{zone_received_sum:.2f}")
                        st.markdown("---") # Separator for zones
                        
                        total_received_on_date += zone_received_sum
                        total_billed_on_date += zone_billed_sum
                
                st.success(f"**Total Money Received from All Zones on {selected_date_str}: ₹{total_received_on_date:.2f}**")
                
                total_due_on_date = total_billed_on_date - total_received_on_date
                st.warning(f"**Total Due Pending from Transactions on {selected_date_str}: ₹{total_due_on_date:.2f}**")

            else:
                st.info(f"No credit transactions found for {selected_date_str}.")

            st.markdown("---")
            st.subheader(f"Debit Transactions for {selected_date_str}")

            daily_debit_transactions = pd.DataFrame([entry for entry in debit_entries if entry["Date"] == selected_date_str])
            
            if not daily_debit_transactions.empty:
                st.dataframe(daily_debit_transactions[['Date', 'Purpose', 'Amount']], use_container_width=True)
                daily_debit_sum = daily_debit_transactions["Amount"].sum()
                st.error(f"Total Debited on {selected_date_str}: ₹{daily_debit_sum:.2f}")
            else:
                st.info(f"No debit transactions found for {selected_date_str}.")

        # --- Admin Bill Book Information Tab ---
        with admin_tab_bill_info:
            st.header("Bill Book Information")
            st.subheader("🔍 Search Bill Details")

            search_bill_no = st.number_input("Enter Bill Number", min_value=1, value=1, key="search_bill_no_input")
            
            if st.button("Fetch Bill Information", key="fetch_bill_info_btn"):
                # Load the latest credit data to ensure search is accurate
                current_credit_df_for_search = load_credit_data()
                
                # Search for the bill number across all zones
                found_bills = current_credit_df_for_search[current_credit_df_for_search["Bill No"] == search_bill_no]

                if not found_bills.empty:
                    st.success(f"Details for Bill No: {search_bill_no}")
                    # Display all columns for the found bill(s)
                    st.dataframe(found_bills, use_container_width=True)
                else:
                    st.info(f"Bill No {search_bill_no} Not Issued Yet.")


# Run the main application
if __name__ == "__main__":
    main()
