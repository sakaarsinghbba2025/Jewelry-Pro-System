import streamlit as st
import pandas as pd
import os
from datetime import datetime
import matplotlib.pyplot as plt
import requests
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Jewelry Pro System", layout="wide")

FILE = "inventory.csv"
IMG_FOLDER = "images"
os.makedirs(IMG_FOLDER, exist_ok=True)

# ---------------- GOLD PRICE ----------------
def get_gold_price():
    try:
        res = requests.get("https://api.metals.live/v1/spot/gold", timeout=5)
        data = res.json()

        if isinstance(data, list) and len(data) > 0:
            price_per_ounce = data[0]["price"]
            usd_to_inr = 83

            price_per_gram = (price_per_ounce / 31.1035) * usd_to_inr
            price_per_10g = price_per_gram * 10

            return round(price_per_10g, 2)
    except:
        pass

    return None

# ---------------- LOGIN ----------------
def login():
    st.title("🔐 Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username == "admin" and password == "1234":
            st.session_state["logged_in"] = True
        else:
            st.error("Invalid credentials")

# Initialize session
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "gold_price" not in st.session_state:
    st.session_state.gold_price = 0

if "show_success" not in st.session_state:
    st.session_state.show_success = False

# Stop app if not logged in
if not st.session_state.logged_in:
    login()
    st.stop()

# ---------------- LOGOUT BUTTON ----------------
with st.sidebar:
    if st.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.rerun()

# ---------------- DATA ----------------
def create_df():
    return pd.DataFrame(columns=[
        "ID","Name","Category","Weight","Quantity",
        "Price","Total","Date","Image"
    ])

def load_data():
    if not os.path.exists(FILE):
        df = create_df()
        df.to_csv(FILE, index=False)
        return df

    try:
        df = pd.read_csv(FILE)
        return df if not df.empty else create_df()
    except:
        return create_df()

def save_data(df):
    df.to_csv(FILE, index=False)

df = load_data()

# Fix Total column
if "Total" not in df.columns:
    df["Total"] = 0

df["Total"] = pd.to_numeric(df["Total"], errors="coerce").fillna(0)

# ---------------- SUCCESS POPUP ----------------
def show_success_dialog():
    @st.dialog("✅ Success")
    def success():
        st.success("Item added successfully!")
        if st.button("OK"):
            st.rerun()
    success()

if st.session_state.get("show_success"):
    st.session_state.show_success = False
    show_success_dialog()

# ---------------- DELETE POPUP ----------------
def open_delete_dialog(del_id):
    @st.dialog("⚠️ Confirm Deletion")
    def confirm():
        st.warning(f"Delete item ID {del_id}?")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("✅ Yes"):
                global df
                df = df[df["ID"] != del_id]
                save_data(df)
                st.success("Deleted")
                st.rerun()

        with col2:
            if st.button("❌ Cancel"):
                st.rerun()

    confirm()

# ---------------- SIDEBAR MENU ----------------
menu = st.sidebar.radio("Menu", [
    "Dashboard", "Add Item", "Inventory", "Invoice"
])

# ---------------- DASHBOARD ----------------
if menu == "Dashboard":
    st.title("📊 Dashboard")

    total_value = df["Total"].sum()
    total_items = len(df)

    col1, col2 = st.columns(2)
    col1.metric("Total Items", total_items)
    col2.metric("Total Value ₹", f"{total_value:,.2f}")

    st.subheader("🪙 Gold Price (India)")

    auto_price = get_gold_price()

    if auto_price:
        st.success(f"Live Gold Price: ₹ {auto_price} / 10g")

        use_auto = st.checkbox("Use Auto Gold Price", value=True)

        if use_auto:
            gold_price = auto_price
        else:
            gold_price = st.number_input("Enter Gold Price ₹ / 10g", min_value=0.0)

    else:
        st.error("❌ Unable to fetch gold price")
        gold_price = st.number_input("Enter Gold Price ₹ / 10g (Required)", min_value=0.0)

    st.session_state.gold_price = gold_price

    st.info(f"Using Gold Price: ₹ {gold_price} / 10g")

    st.subheader("📈 Inventory Trend")

    if not df.empty:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        trend = df.groupby("Date")["Total"].sum()

        plt.figure()
        plt.plot(trend.index, trend.values)
        st.pyplot(plt)

# ---------------- ADD ITEM ----------------
elif menu == "Add Item":
    st.title("➕ Add Jewelry Item")

    name = st.text_input("Name")
    category = st.selectbox("Category", ["Gold", "Silver", "Diamond"])

    weight = st.number_input("Weight (grams)", min_value=0.0)
    qty = st.number_input("Quantity", min_value=1)

    gold_price = st.session_state.get("gold_price", 0)

    if gold_price == 0:
        st.warning("⚠️ Please set gold price in Dashboard first")
        st.stop()

    st.success(f"Using Gold Price: ₹ {gold_price} / 10g")

    use_auto_price = st.checkbox("Auto calculate item price from gold")

    if use_auto_price:
        price = (weight / 10) * gold_price
        st.info(f"Calculated Price: ₹ {price:.2f}")
    else:
        price = st.number_input("Enter Item Price ₹", min_value=0.0)

    image = st.file_uploader("Upload Image", type=["jpg", "png"])

    if st.button("Add Item"):
        if name == "" or price == 0:
            st.error("Please enter valid details")
        else:
            total = qty * price
            new_id = 1 if df.empty else int(df["ID"].max()) + 1

            img_path = ""
            if image:
                img_path = os.path.join(IMG_FOLDER, image.name)
                with open(img_path, "wb") as f:
                    f.write(image.getbuffer())

            new_row = pd.DataFrame([[
                new_id, name, category, weight,
                qty, price, total,
                datetime.today(), img_path
            ]], columns=df.columns)

            df = pd.concat([df, new_row], ignore_index=True)
            save_data(df)

            st.session_state.show_success = True
            st.rerun()

# ---------------- INVENTORY ----------------
elif menu == "Inventory":
    st.title("📦 Inventory")

    search = st.text_input("Search")
    filtered = df[df["Name"].astype(str).str.contains(search, case=False, na=False)]

    st.dataframe(filtered, use_container_width=True, hide_index=True)

    for _, row in filtered.iterrows():
        if isinstance(row["Image"], str) and row["Image"] != "" and os.path.exists(row["Image"]):
            st.image(row["Image"], width=120)

    st.subheader("🗑 Delete Item")

    del_id = st.number_input("Enter ID", min_value=1)

    if st.button("Delete"):
        if del_id in df["ID"].values:
            open_delete_dialog(del_id)
        else:
            st.error("ID not found")

# ---------------- INVOICE ----------------
elif menu == "Invoice":
    st.title("🧾 Generate Invoice")

    customer = st.text_input("Customer Name")
    item_id = st.number_input("Item ID", min_value=1)

    if st.button("Generate Invoice"):
        item = df[df["ID"] == item_id]

        if item.empty:
            st.error("Item not found")
        else:
            item = item.iloc[0]

            file_name = f"invoice_{item_id}.pdf"

            doc = SimpleDocTemplate(file_name)
            styles = getSampleStyleSheet()

            content = [
                Paragraph(f"Customer: {customer}", styles["Normal"]),
                Paragraph(f"Item: {item['Name']}", styles["Normal"]),
                Paragraph(f"Price: ₹{item['Price']}", styles["Normal"]),
                Paragraph(f"Quantity: {item['Quantity']}", styles["Normal"]),
                Paragraph(f"Total: ₹{item['Total']}", styles["Normal"]),
            ]

            doc.build(content)

            with open(file_name, "rb") as f:
                st.download_button("Download Invoice", f, file_name)