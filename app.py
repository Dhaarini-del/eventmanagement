import streamlit as st
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

# Page Configuration
st.set_page_config(page_title="Event Management System", page_icon="📅", layout="wide")

# Initialize Session State Variables
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "role" not in st.session_state:
    st.session_state.role = ""
if "user_id" not in st.session_state:
    st.session_state.user_id = None

# Database Connection
@st.cache_resource
def init_connection():
    try:
        conn = mysql.connector.connect(
            host='127.0.0.1',
            port=3306,
            user='root',
            password='root@123',
            database='EventDB'
        )
        return conn
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return None

conn = init_connection()

def run_query(query, params=(), fetch=True, commit=False):
    if not conn:
        return None
    try:
        cursor = conn.cursor(dictionary=True, buffered=True)
        cursor.execute(query, params)
        if commit:
            conn.commit()
        result = cursor.fetchall() if fetch else None
        cursor.close()
        return result
    except Exception as e:
        st.error(f"Database error: {e}")
        return None

ADMIN_SECRET = "4576"

# Authentication Views
def login_page():
    st.subheader("🔑 Login to Event Management System")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Type Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            users = run_query("SELECT * FROM Users WHERE Username = %s", (username,))
            if users:
                user = users[0]
                if check_password_hash(str(user['Password']), password):
                    st.session_state.logged_in = True
                    st.session_state.user_id = user['UserID']
                    st.session_state.username = user['Username']
                    st.session_state.role = user['Role']
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
            else:
                st.error("Invalid credentials.")

def register_page():
    st.subheader("📝 Register New Account")
    with st.form("register_form"):
        username = st.text_input("Choose Username")
        password = st.text_input("Choose Password", type="password")
        role = st.selectbox("Role", ["user", "admin"])
        admin_code = st.text_input("Admin Code (if registering as admin)", type="password")
        submit = st.form_submit_button("Register")
        
        if submit:
            if role == 'admin' and admin_code != ADMIN_SECRET:
                st.error("Invalid admin registration code.")
            else:
                hash_pw = generate_password_hash(password)
                try:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO Users (Username, Password, Role) VALUES (%s, %s, %s)", (username, hash_pw, role))
                    conn.commit()
                    cursor.close()
                    st.success("Registration successful! Please go to Login.")
                except Exception as e:
                    st.error(f"Username already exists or error: {e}")

# Main Application Router
def main():
    if not st.session_state.logged_in:
        choice = st.sidebar.selectbox("Navigation", ["Login", "Register"])
        if choice == "Login":
            login_page()
        else:
            register_page()
        return

    # Sidebar Navigation for Logged-In Users
    st.sidebar.write(f"Welcome, **{st.session_state.username}** ({st.session_state.role.upper()})")
    
    menu_options = ["Home (Events)", "Event Details", "All Attendees", "VIP Tickets", "Venues", "Upcoming Events", "Feedback"]
    
    if st.session_state.role == 'admin':
        menu_options.extend(["Add Event", "Admin Controls", "Insert Sample Data"])

    choice = st.sidebar.selectbox("Menu", menu_options)
    
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.role = ""
        st.session_state.user_id = None
        st.rerun()

    # Route Views
    if choice == "Home (Events)":
        st.header("📅 Available Events")
        events = run_query("""
            SELECT e.EventID, e.EventName, e.EventDate, e.EventTime, e.VenueID, v.VenueName 
            FROM Events e LEFT JOIN Venues v ON e.VenueID = v.VenueID
        """)
        if events:
            for event in events:
                st.subheader(event['EventName'])
                st.write(f"**Date:** {event['EventDate']} | **Time:** {event['EventTime']} | **Venue:** {event['VenueName']}")
                st.divider()
        else:
            st.info("No events found.")

    elif choice == "Event Details":
        st.header("🔍 Event Details & Specs")
        events = run_query("SELECT EventID, EventName FROM Events")
        if events:
            event_dict = {e['EventName']: e['EventID'] for e in events}
            selected_event_name = st.selectbox("Select Event", list(event_dict.keys()))
            event_id = event_dict[selected_event_name]
            
            event_info = run_query("SELECT * FROM Events WHERE EventID = %s", (event_id,))
            speakers = run_query("SELECT s.SpeakerName, s.Bio FROM Speakers s JOIN Event_Speakers es ON s.SpeakerID = es.SpeakerID WHERE es.EventID = %s", (event_id,))
            sponsors = run_query("SELECT sp.SponsorName FROM Sponsors sp JOIN Event_Sponsors es ON sp.SponsorID = es.SponsorID WHERE es.EventID = %s", (event_id,))
            
            if event_info:
                st.write(f"### {event_info[0]['EventName']}"); st.write(f"Date: {event_info[0]['EventDate']}")
            st.write("#### Speakers")
            for sp in speakers:
                st.write(f"- **{sp['SpeakerName']}**: {sp['Bio']}")
            st.write("#### Sponsors")
            for sn in sponsors:
                st.write(f"- {sn['SponsorName']}")

    elif choice == "All Attendees":
        st.header("👥 Attendee List")
        attendees = run_query("""
            SELECT a.AttendeeName, a.Email, e.EventName, t.TicketType, t.Price 
            FROM Attendees a LEFT JOIN Tickets t ON a.AttendeeID = t.AttendeeID LEFT JOIN Events e ON t.EventID = e.EventID
        """)
        if attendees:
            st.dataframe(attendees)
        else:
            st.info("No attendees found.")

    elif choice == "VIP Tickets":
        st.header("🌟 VIP Tickets Summary")
        tickets = run_query("""
            SELECT t.TicketID, a.AttendeeName, e.EventName, t.Price 
            FROM Tickets t JOIN Attendees a ON t.AttendeeID = a.AttendeeID JOIN Events e ON t.EventID = e.EventID WHERE t.TicketType = 'VIP'
        """)
        if tickets:
            st.dataframe(tickets)
        else:
            st.info("No VIP tickets found.")

    elif choice == "Venues":
        st.header("🏟️ Venues List")
        venues = run_query("SELECT * FROM Venues WHERE VenueName IS NOT NULL")
        if venues:
            st.dataframe(venues)
        else:
            st.info("No venues found.")

    elif choice == "Upcoming Events":
        st.header("🚀 Upcoming Events")
        upcoming = run_query("""
            SELECT e.EventName, e.EventDate, v.VenueName, v.Address, v.Capacity 
            FROM Events e LEFT JOIN Venues v ON e.VenueID = v.VenueID WHERE e.EventDate >= CURDATE() ORDER BY e.EventDate
        """)
        if upcoming:
            st.dataframe(upcoming)
        else:
            st.info("No upcoming events found.")

    elif choice == "Feedback":
        st.header("💬 Leave Feedback")
        with st.form("feedback_form"):
            name = st.text_input("Your Name")
            email = st.text_input("Your Email")
            message = st.text_area("Message")
            submitted = st.form_submit_button("Submit Feedback")
            if submitted:
                run_query("INSERT INTO Feedback (Name, Email, Message) VALUES (%s, %s, %s)", (name, email, message), fetch=False, commit=True)
                st.success("Thanks for your feedback!")

    elif choice == "Add Event" and st.session_state.role == 'admin':
        st.header("➕ Add New Event")
        venues = run_query("SELECT * FROM Venues")
        venue_dict = {v['VenueName']: v['VenueID'] for v in venues} if venues else {}
        
        with st.form("add_event_form"):
            event_name = st.text_input("Event Name")
            event_date = st.date_input("Event Date")
            event_time = st.time_input("Event Time")
            selected_venue = st.selectbox("Venue", list(venue_dict.keys()) if venue_dict else ["No Venues"])
            submitted = st.form_submit_button("Add Event")
            
            if submitted and venue_dict:
                venue_id = venue_dict[selected_venue]
                event_datetime = f"{event_date} {event_time}"
                run_query("INSERT INTO Events (EventName, EventDate, VenueID) VALUES (%s, %s, %s)", (event_name, event_datetime, venue_id), fetch=False, commit=True)
                st.success("Event added successfully!")

    elif choice == "Admin Controls" and st.session_state.role == 'admin':
        st.header("⚙️ Admin Control Center")
        events = run_query("SELECT * FROM Events")
        st.dataframe(events)

    elif choice == "Insert Sample Data" and st.session_state.role == 'admin':
        st.header("📥 Insert Sample Data")
        if st.button("Run Sample Data Script"):
            try:
                run_query("INSERT IGNORE INTO Venues (VenueID, VenueName, Address, Capacity) VALUES (1, 'Convention Center', '123 Main St', 1000), (2, 'Stadium Arena', '456 Sports Ave', 5000)", fetch=False, commit=True)
                st.success("Sample data inserted successfully!")
            except Exception as e:
                st.error(f"Error: {e}")

if __name__ == '__main__':
    main()
