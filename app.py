# Flask App for EventDB
from flask import Flask, render_template, request, redirect, flash, session, url_for
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import os
from typing import Dict, Any, Optional
from functools import wraps

# Role-based access decorators

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            flash("Admin access required.", "danger")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def user_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'user':
            flash("User access required.", "danger")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Database Connection
try:
    conn = mysql.connector.connect(
        host='127.0.0.1',
        port=3306,  # Explicitly set to 5000 as per user
        user='root',
        password='root@123',
        database='EventDB'
    )
    cursor = conn.cursor(dictionary=True, buffered=True)
    print("Database connected successfully!")
except Exception as e:
    print(f"Database connection error: {e}")
    conn = None
    cursor = None

@app.before_request
def require_login():
    allowed_routes = ['login', 'register', 'static', 'reset_password']
    if request.endpoint not in allowed_routes and 'user_id' not in session:
        return redirect(url_for('login'))

# Login & Register
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if cursor:
            cursor.execute("SELECT * FROM Users WHERE Username = %s", (username,))
            user = cursor.fetchone()  # type: ignore
            if user and check_password_hash(str(user['Password']), password):  # type: ignore
                session['user_id'] = user['UserID']  # type: ignore
                session['username'] = user['Username']  # type: ignore
                session['role'] = user['Role']  # type: ignore
                return redirect('/home')
        flash("Invalid credentials.", "danger")
    return render_template('login.html')

ADMIN_SECRET = "4576"  # Set your secret code here

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form.get('role', 'user')
        admin_code = request.form.get('admin_code', '')
        hash_pw = generate_password_hash(password)
        try:
            if role == 'admin':
                if admin_code != ADMIN_SECRET:
                    flash("Invalid admin registration code.", "danger")
                    return render_template('register.html')
            if cursor and conn:
                cursor.execute("INSERT INTO Users (Username, Password, Role) VALUES (%s, %s, %s)", (username, hash_pw, role))
                conn.commit()
                flash("Registration successful.", "success")
                return redirect('/login')
        except:
            flash("Username already exists.", "danger")
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/')
def index():
    # Redirect to login page instead of showing events
    return redirect('/login')

@app.route('/home')
def home():
    """New route for the home page with events (previously index)"""
    try:
        if cursor:
            cursor.execute("""
                SELECT e.EventID, e.EventName, e.EventDate, e.EventTime, e.VenueID, v.VenueName
                FROM Events e
                LEFT JOIN Venues v ON e.VenueID = v.VenueID
            """)
            events = cursor.fetchall()
            # Convert EventDate and EventTime to strings for template rendering
            for event in events:
                if event['EventDate']:  # type: ignore
                    event['EventDate'] = str(event['EventDate'])  # type: ignore
                if event['EventTime']:  # type: ignore
                    event['EventTime'] = str(event['EventTime'])  # type: ignore
            print(f"Events fetched for home: {events}")
            return render_template('index.html', events=events)
        else:
            print("Database cursor is None")
            return render_template('index.html', events=[])
    except Exception as e:
        print(f"Error in home route: {e}")
        return render_template('index.html', events=[])

@app.route('/event/<int:event_id>')
def event_detail(event_id):
    try:
        if cursor:
            cursor.execute("SELECT * FROM Events WHERE EventID = %s", (event_id,))
            event = cursor.fetchone()
            cursor.execute("""
                SELECT s.SpeakerName, s.Bio FROM Speakers s
                JOIN Event_Speakers es ON s.SpeakerID = es.SpeakerID
                WHERE es.EventID = %s
            """, (event_id,))
            speakers = cursor.fetchall()
            cursor.execute("""
                SELECT sp.SponsorName FROM Sponsors sp
                JOIN Event_Sponsors es ON sp.SponsorID = es.SponsorID
                WHERE es.EventID = %s
            """, (event_id,))
            sponsors = cursor.fetchall()
            return render_template('event_detail.html', event=event, speakers=speakers, sponsors=sponsors)
        else:
            return render_template('event_detail.html', event=None, speakers=[], sponsors=[])
    except Exception as e:
        print(f"Error in event_detail route: {e}")
        return render_template('event_detail.html', event=None, speakers=[], sponsors=[])

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# Additional Routes for Complete Templates
@app.route('/add_event', methods=['GET', 'POST'])
@admin_required
def add_event():
    if not cursor:
        return render_template('add_event.html', venues=[])
    if request.method == 'POST':
        event_name = request.form['event_name']
        event_date = request.form['event_date']
        event_time = request.form['event_time']
        venue_id = request.form['venue_id']
        # Combine date and time for the EventDate field
        event_datetime = f"{event_date} {event_time}"
        try:
            cursor.execute(
                "INSERT INTO Events (EventName, EventDate, VenueID) VALUES (%s, %s, %s)",
                (event_name, event_datetime, venue_id)
            )
            if conn:
                conn.commit()
            flash("Event added successfully!", "success")
            return redirect('/upcoming-events')
        except Exception as e:
            flash(f"Error adding event: {e}", "danger")
    cursor.execute("SELECT * FROM Venues")
    venues = cursor.fetchall()
    return render_template('add_event.html', venues=venues)

@app.route('/add_venue')
@admin_required
def add_venue():
    return render_template('add_venue.html')

@app.route('/add_speaker')
@admin_required
def add_speaker():
    return render_template('add_speaker.html')

@app.route('/add_sponsor')
@admin_required
def add_sponsor():
    return render_template('add_sponsor.html')

@app.route('/add_attendee')
@admin_required
def add_attendee():
    return render_template('add_attendee.html')

@app.route('/admin-dashboard')
@admin_required
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/admin-event-control')
@admin_required
def admin_event_control():
    if cursor:
        cursor.execute("SELECT * FROM Events")
        events = cursor.fetchall()
        return render_template('admin_event_control.html', events=events)
    return render_template('admin_event_control.html', events=[])

@app.route('/book-ticket')
@user_required
def book_ticket():
    if cursor:
        cursor.execute("SELECT * FROM Events")
        events = cursor.fetchall()
        return render_template('book_ticket.html', events=events)
    return render_template('book_ticket.html', events=[])

@app.route('/feedback', methods=['GET', 'POST'])
@user_required
def feedback():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']
        if cursor and conn:
            cursor.execute("INSERT INTO Feedback (Name, Email, Message) VALUES (%s, %s, %s)", (name, email, message))
            conn.commit()
            flash("Thanks for your feedback.", "success")
    return render_template('feedback.html')

@app.route('/all_attendees')
def all_attendees():
    if cursor:
        try:
            cursor.execute("""
                SELECT a.AttendeeID, a.AttendeeName, a.Email, e.EventName, t.TicketType, t.Price 
                FROM Attendees a 
                LEFT JOIN Tickets t ON a.AttendeeID = t.AttendeeID
                LEFT JOIN Events e ON t.EventID = e.EventID
            """)
            attendees = cursor.fetchall()
            print(f"Found {len(attendees)} attendees")
            return render_template('all_attendees.html', attendees=attendees)
        except Exception as e:
            print(f"Error in all_attendees: {e}")
            return render_template('all_attendees.html', attendees=[])
    return render_template('all_attendees.html', attendees=[])

@app.route('/all-attendees')
def all_attendees_alt():
    if cursor:
        try:
            cursor.execute("""
                SELECT a.AttendeeID, a.AttendeeName, a.Email, e.EventName, t.TicketType, t.Price 
                FROM Attendees a 
                LEFT JOIN Tickets t ON a.AttendeeID = t.AttendeeID
                LEFT JOIN Events e ON t.EventID = e.EventID
            """)
            attendees = cursor.fetchall()
            print(f"Found {len(attendees)} attendees")
            return render_template('all_attendees.html', attendees=attendees)
        except Exception as e:
            print(f"Error in all_attendees_alt: {e}")
            return render_template('all_attendees.html', attendees=[])
    return render_template('all_attendees.html', attendees=[])

@app.route('/vip_tickets')
def vip_tickets():
    if cursor:
        try:
            cursor.execute("""
                SELECT t.TicketID, a.AttendeeName, e.EventName, t.Price 
                FROM Tickets t 
                JOIN Attendees a ON t.AttendeeID = a.AttendeeID 
                JOIN Events e ON t.EventID = e.EventID 
                WHERE t.TicketType = 'VIP'
            """)
            tickets = cursor.fetchall()
            print(f"Found {len(tickets)} VIP tickets")
            return render_template('vip_tickets.html', tickets=tickets)
        except Exception as e:
            print(f"Error in vip_tickets: {e}")
            return render_template('vip_tickets.html', tickets=[])
    return render_template('vip_tickets.html', tickets=[])

@app.route('/vip-tickets')
def vip_tickets_alt():
    if cursor:
        try:
            cursor.execute("""
                SELECT t.TicketID, a.AttendeeName, e.EventName, t.Price 
                FROM Tickets t 
                JOIN Attendees a ON t.AttendeeID = a.AttendeeID 
                JOIN Events e ON t.EventID = e.EventID 
                WHERE t.TicketType = 'VIP'
            """)
            tickets = cursor.fetchall()
            print(f"Found {len(tickets)} VIP tickets")
            return render_template('vip_tickets.html', tickets=tickets)
        except Exception as e:
            print(f"Error in vip_tickets_alt: {e}")
            return render_template('vip_tickets.html', tickets=[])
    return render_template('vip_tickets.html', tickets=[])

# Missing routes that were causing 404 errors
@app.route('/event-speakers')
def event_speakers():
    if cursor:
        try:
            cursor.execute("""
                SELECT e.EventName, s.SpeakerName, s.Bio 
                FROM Events e 
                LEFT JOIN Event_Speakers es ON e.EventID = es.EventID 
                LEFT JOIN Speakers s ON es.SpeakerID = s.SpeakerID
                WHERE s.SpeakerName IS NOT NULL
            """)
            speakers = cursor.fetchall()
            print(f"Found {len(speakers)} event speakers")
            return render_template('event_speakers.html', speakers=speakers)
        except Exception as e:
            print(f"Error in event_speakers: {e}")
            return render_template('event_speakers.html', speakers=[])
    return render_template('event_speakers.html', speakers=[])

@app.route('/ticket-details')
def ticket_details():
    if cursor:
        try:
            cursor.execute("""
                SELECT t.TicketID, a.AttendeeName, e.EventName, t.TicketType, t.Price
                FROM Tickets t 
                LEFT JOIN Attendees a ON t.AttendeeID = a.AttendeeID 
                LEFT JOIN Events e ON t.EventID = e.EventID
            """)
            tickets = cursor.fetchall()
            print(f"Found {len(tickets)} tickets")
            return render_template('ticket_details.html', tickets=tickets)
        except Exception as e:
            print(f"Error in ticket_details: {e}")
            return render_template('ticket_details.html', tickets=[])
    return render_template('ticket_details.html', tickets=[])

@app.route('/event-revenue')
def event_revenue():
    if cursor:
        try:
            cursor.execute("""
                SELECT e.EventName, COALESCE(SUM(t.Price), 0) as TotalRevenue, COUNT(t.TicketID) as TicketsSold
                FROM Events e 
                LEFT JOIN Tickets t ON e.EventID = t.EventID 
                GROUP BY e.EventID, e.EventName
            """)
            revenues = cursor.fetchall()
            print(f"Found {len(revenues)} revenue records")
            return render_template('event_revenue.html', revenues=revenues)
        except Exception as e:
            print(f"Error in event_revenue: {e}")
            return render_template('event_revenue.html', revenues=[])
    return render_template('event_revenue.html', revenues=[])

# Additional routes for other templates
@app.route('/event-venue')
def event_venue():
    if cursor:
        try:
            cursor.execute("""
                SELECT e.EventName, v.VenueName, v.Address, v.Capacity
                FROM Events e
                LEFT JOIN Venues v ON e.VenueID = v.VenueID
            """)
            event_venues = cursor.fetchall()
            print(f"Event-Venue: {event_venues}")
            return render_template('event_venue.html', event_venues=event_venues)
        except Exception as e:
            print(f"Error in event_venue: {e}")
            return render_template('event_venue.html', event_venues=[])
    return render_template('event_venue.html', event_venues=[])

@app.route('/vip-attendees')
def vip_attendees():
    if cursor:
        try:
            cursor.execute("""
                SELECT a.AttendeeName, a.Email, t.Price
                FROM Attendees a
                LEFT JOIN Tickets t ON a.AttendeeID = t.AttendeeID
                WHERE t.TicketType = 'VIP'
            """)
            vip_attendees = cursor.fetchall()
            print(f"VIP Attendees: {vip_attendees}")
            return render_template('vip_attendees.html', vip_attendees=vip_attendees)
        except Exception as e:
            print(f"Error in vip_attendees: {e}")
            return render_template('vip_attendees.html', vip_attendees=[])
    return render_template('vip_attendees.html', vip_attendees=[])

@app.route('/speakers-bio')
def speakers_bio():
    if cursor:
        try:
            cursor.execute("SELECT SpeakerName, Bio FROM Speakers WHERE SpeakerName IS NOT NULL")
            speakers = cursor.fetchall()
            print(f"Found {len(speakers)} speakers")
            return render_template('speakers_bio.html', speakers=speakers)
        except Exception as e:
            print(f"Error in speakers_bio: {e}")
            return render_template('speakers_bio.html', speakers=[])
    return render_template('speakers_bio.html', speakers=[])

@app.route('/multi-sponsor-events')
def multi_sponsor_events():
    if cursor:
        try:
            cursor.execute("""
                SELECT e.EventName, COUNT(es.SponsorID) as SponsorCount
                FROM Events e
                LEFT JOIN Event_Sponsors es ON e.EventID = es.EventID
                GROUP BY e.EventID, e.EventName
                HAVING COUNT(es.SponsorID) > 1
            """)
            events = cursor.fetchall()
            print(f"Multi-Sponsor Events: {events}")
            return render_template('multi_sponsor_events.html', events=events)
        except Exception as e:
            print(f"Error in multi_sponsor_events: {e}")
            return render_template('multi_sponsor_events.html', events=[])
    return render_template('multi_sponsor_events.html', events=[])

@app.route('/attendees-by-event')
def attendees_by_event():
    if cursor:
        try:
            cursor.execute("""
                SELECT e.EventName, COUNT(t.AttendeeID) as AttendeeCount
                FROM Events e
                LEFT JOIN Tickets t ON e.EventID = t.EventID
                GROUP BY e.EventID, e.EventName
            """)
            events = cursor.fetchall()
            print(f"Attendees/Event: {events}")
            return render_template('attendees_by_event.html', events=events)
        except Exception as e:
            print(f"Error in attendees_by_event: {e}")
            return render_template('attendees_by_event.html', events=[])
    return render_template('attendees_by_event.html', events=[])

@app.route('/event-venue-list')
def event_venue_list():
    if cursor:
        try:
            cursor.execute("""
                SELECT e.EventName, v.VenueName, v.Address
                FROM Events e 
                LEFT JOIN Venues v ON e.VenueID = v.VenueID
                WHERE v.VenueName IS NOT NULL
            """)
            events = cursor.fetchall()
            print(f"Found {len(events)} event venue mappings")
            return render_template('event_venue_list.html', events=events)
        except Exception as e:
            print(f"Error in event_venue_list: {e}")
            return render_template('event_venue_list.html', events=[])
    return render_template('event_venue_list.html', events=[])

@app.route('/upcoming-events')
def upcoming_events():
    if cursor:
        try:
            cursor.execute("""
                SELECT e.EventName, e.EventDate, v.VenueName, v.Address, v.Capacity
                FROM Events e
                LEFT JOIN Venues v ON e.VenueID = v.VenueID
                WHERE e.EventDate >= CURDATE()
                ORDER BY e.EventDate
            """)
            events = cursor.fetchall()
            print(f"Found {len(events)} upcoming events")
            return render_template('upcoming_events.html', events=events)
        except Exception as e:
            print(f"Error in upcoming_events: {e}")
            return render_template('upcoming_events.html', events=[])
    return render_template('upcoming_events.html', events=[])

@app.route('/venues')
def venues():
    if cursor:
        try:
            cursor.execute("SELECT * FROM Venues WHERE VenueName IS NOT NULL")
            venues = cursor.fetchall()
            print(f"Found {len(venues)} venues")
            return render_template('venues.html', venues=venues)
        except Exception as e:
            print(f"Error in venues: {e}")
            return render_template('venues.html', venues=[])
    return render_template('venues.html', venues=[])

@app.route('/sponsors-per-event')
def sponsors_per_event():
    if cursor:
        try:
            cursor.execute("""
                SELECT e.EventName, sp.SponsorName
                FROM Events e 
                LEFT JOIN Event_Sponsors es ON e.EventID = es.EventID 
                LEFT JOIN Sponsors sp ON es.SponsorID = sp.SponsorID
                WHERE sp.SponsorName IS NOT NULL
            """)
            sponsors = cursor.fetchall()
            print(f"Found {len(sponsors)} sponsor-event mappings")
            return render_template('sponsors_per_event.html', sponsors=sponsors)
        except Exception as e:
            print(f"Error in sponsors_per_event: {e}")
            return render_template('sponsors_per_event.html', sponsors=[])
    return render_template('sponsors_per_event.html', sponsors=[])

@app.route('/event-sponsors')
def event_sponsors():
    if cursor:
        try:
            cursor.execute("""
                SELECT e.EventName, sp.SponsorName
                FROM Events e 
                LEFT JOIN Event_Sponsors es ON e.EventID = es.EventID 
                LEFT JOIN Sponsors sp ON es.SponsorID = sp.SponsorID
                WHERE sp.SponsorName IS NOT NULL
            """)
            sponsors = cursor.fetchall()
            print(f"Found {len(sponsors)} event sponsors")
            return render_template('sponsors_per_event.html', sponsors=sponsors)
        except Exception as e:
            print(f"Error in event_sponsors: {e}")
            return render_template('sponsors_per_event.html', sponsors=[])
    return render_template('sponsors_per_event.html', sponsors=[])

@app.route('/high-capacity-attendees')
def high_capacity_attendees():
    if cursor:
        try:
            cursor.execute("""
                SELECT a.AttendeeName, COUNT(t.TicketID) as TicketCount
                FROM Attendees a 
                LEFT JOIN Tickets t ON a.AttendeeID = t.AttendeeID 
                GROUP BY a.AttendeeID, a.AttendeeName 
                HAVING COUNT(t.TicketID) > 2
            """)
            attendees = cursor.fetchall()
            print(f"Found {len(attendees)} high capacity attendees")
            return render_template('high_capacity_attendees.html', attendees=attendees)
        except Exception as e:
            print(f"Error in high_capacity_attendees: {e}")
            return render_template('high_capacity_attendees.html', attendees=[])
    return render_template('high_capacity_attendees.html', attendees=[])

@app.route('/book_ticket')
def book_ticket_alt():
    if cursor:
        cursor.execute("SELECT * FROM Events")
        events = cursor.fetchall()
        return render_template('book_ticket.html', events=events)
    return render_template('book_ticket.html', events=[])

@app.route('/confirm-payment')
def confirm_payment():
    return render_template('confirm_payment.html')

@app.route('/reset-password')
def reset_password():
    return render_template('reset_password.html')

@app.route('/table')
def table():
    if cursor:
        cursor.execute("SELECT * FROM Events")
        events = cursor.fetchall()
        return render_template('table.html', events=events)
    return render_template('table.html', events=[])

@app.route('/simple-list')
def simple_list():
    if cursor:
        cursor.execute("SELECT * FROM Events")
        events = cursor.fetchall()
        return render_template('simple_list.html', events=events)
    return render_template('simple_list.html', events=[])

@app.route('/other-pages')
def other_pages():
    return render_template('other_pages.html')

# Routes with event IDs
@app.route('/add_speaker/<int:event_id>', methods=['GET', 'POST'])
@admin_required
def add_speaker_with_event(event_id):
    if cursor:
        cursor.execute("SELECT * FROM Events WHERE EventID = %s", (event_id,))
        event = cursor.fetchone()
        if request.method == 'POST':
            speaker_name = request.form['speaker_name']
            bio = request.form['bio']
            try:
                cursor.execute("INSERT INTO Speakers (SpeakerName, Bio) VALUES (%s, %s)", (speaker_name, bio))
                cursor.execute("INSERT INTO Event_Speakers (EventID, SpeakerID) VALUES (%s, %s)", (event_id, cursor.lastrowid))
                if conn:
                    conn.commit()
                flash("Speaker added successfully!", "success")
                return redirect('/event-speakers')
            except Exception as e:
                flash(f"Error adding speaker: {e}", "danger")
        return render_template('add_speaker.html', event=event)
    return render_template('add_speaker.html', event=None)

@app.route('/add_sponsor/<int:event_id>', methods=['GET', 'POST'])
@admin_required
def add_sponsor_with_event(event_id):
    if cursor:
        cursor.execute("SELECT * FROM Events WHERE EventID = %s", (event_id,))
        event = cursor.fetchone()
        if request.method == 'POST':
            sponsor_name = request.form['sponsor_name']
            try:
                cursor.execute("INSERT INTO Sponsors (SponsorName) VALUES (%s)", (sponsor_name,))
                cursor.execute("INSERT INTO Event_Sponsors (EventID, SponsorID) VALUES (%s, %s)", (event_id, cursor.lastrowid))
                if conn:
                    conn.commit()
                flash("Sponsor added successfully!", "success")
                return redirect('/event-sponsors')
            except Exception as e:
                flash(f"Error adding sponsor: {e}", "danger")
        return render_template('add_sponsor.html', event=event)
    return render_template('add_sponsor.html', event=None)

@app.route('/add_attendee/<int:event_id>', methods=['GET', 'POST'])
@admin_required
def add_attendee_with_event(event_id):
    if cursor:
        cursor.execute("SELECT * FROM Events WHERE EventID = %s", (event_id,))
        event = cursor.fetchone()
        if request.method == 'POST':
            attendee_name = request.form['attendee_name']
            email = request.form['email']
            try:
                cursor.execute("INSERT INTO Attendees (AttendeeName, Email) VALUES (%s, %s)", (attendee_name, email))
                cursor.execute("INSERT INTO Tickets (EventID, AttendeeID, TicketType) VALUES (%s, %s, %s)", (event_id, cursor.lastrowid, 'Regular'))
                if conn:
                    conn.commit()
                flash("Attendee added successfully!", "success")
                return redirect('/all_attendees')
            except Exception as e:
                flash(f"Error adding attendee: {e}", "danger")
        return render_template('add_attendee.html', event=event)
    return render_template('add_attendee.html', event=None)

# Additional missing routes
@app.route('/event-speaker-bio')
def event_speaker_bio():
    if cursor:
        cursor.execute("SELECT SpeakerName, Bio FROM Speakers")
        speakers = cursor.fetchall()
        return render_template('speakers_bio.html', speakers=speakers)
    return render_template('speakers_bio.html', speakers=[])

@app.route('/attendees-per-event')
def attendees_per_event():
    if cursor:
        cursor.execute("""
            SELECT e.EventName, COUNT(t.AttendeeID) as AttendeeCount
            FROM Events e 
            LEFT JOIN Tickets t ON e.EventID = t.EventID 
            GROUP BY e.EventID, e.EventName
        """)
        events = cursor.fetchall()
        return render_template('attendees_by_event.html', events=events)
    return render_template('attendees_by_event.html', events=[])

@app.route('/insert-sample-data')
def insert_sample_data():
    """Insert sample data into the database for testing"""
    if not cursor or not conn:
        return "Database not connected"
    
    try:
        # Insert sample venues
        cursor.execute("""
            INSERT IGNORE INTO Venues (VenueID, VenueName, Address, Capacity) VALUES 
            (1, 'Convention Center', '123 Main St, City', 1000),
            (2, 'Stadium Arena', '456 Sports Ave, Town', 5000),
            (3, 'Conference Hall', '789 Business Blvd, Metro', 500)
        """)
        
        # Insert sample events
        cursor.execute("""
            INSERT IGNORE INTO Events (EventID, EventName, EventDate, VenueID) VALUES 
            (1, 'Tech Conference 2024', '2024-12-15', 1),
            (2, 'Music Festival', '2024-12-20', 2),
            (3, 'Business Summit', '2024-12-25', 3)
        """)
        
        # Insert sample speakers
        cursor.execute("""
            INSERT IGNORE INTO Speakers (SpeakerID, SpeakerName, Bio) VALUES 
            (1, 'John Smith', 'Tech expert with 10 years experience'),
            (2, 'Jane Doe', 'Marketing specialist and consultant'),
            (3, 'Mike Johnson', 'Business development expert')
        """)
        
        # Insert sample sponsors
        cursor.execute("""
            INSERT IGNORE INTO Sponsors (SponsorID, SponsorName) VALUES 
            (1, 'TechCorp'),
            (2, 'MusicMasters'),
            (3, 'BusinessPro')
        """)
        
        # Insert sample attendees
        cursor.execute("""
            INSERT IGNORE INTO Attendees (AttendeeID, AttendeeName, Email) VALUES 
            (1, 'Alice Brown', 'alice@email.com'),
            (2, 'Bob Wilson', 'bob@email.com'),
            (3, 'Carol Davis', 'carol@email.com'),
            (4, 'David Miller', 'david@email.com'),
            (5, 'Eva Garcia', 'eva@email.com')
        """)
        
        # Insert sample event-speaker relationships
        cursor.execute("""
            INSERT IGNORE INTO Event_Speakers (EventID, SpeakerID) VALUES 
            (1, 1), (1, 2), (2, 3), (3, 1)
        """)
        
        # Insert sample event-sponsor relationships
        cursor.execute("""
            INSERT IGNORE INTO Event_Sponsors (EventID, SponsorID) VALUES 
            (1, 1), (1, 2), (2, 2), (3, 3)
        """)
        
        # Insert sample tickets
        cursor.execute("""
            INSERT IGNORE INTO Tickets (TicketID, EventID, AttendeeID, TicketType, Price) VALUES 
            (1, 1, 1, 'VIP', 150.00),
            (2, 1, 2, 'Regular', 75.00),
            (3, 2, 3, 'VIP', 200.00),
            (4, 2, 4, 'Regular', 100.00),
            (5, 3, 5, 'VIP', 120.00)
        """)
        
        conn.commit()
        flash("Sample data inserted successfully!", "success")
        return redirect('/')
        
    except Exception as e:
        print(f"Error inserting sample data: {e}")
        flash(f"Error inserting sample data: {e}", "danger")
        return redirect('/')

@app.route('/debug')
def debug():
    """Debug route to check database connection and data"""
    debug_info = {
        'database_connected': conn is not None,
        'cursor_available': cursor is not None,
        'tables': [],
        'sample_data': {}
    }
    
    if cursor:
        try:
            # Check what tables exist
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            debug_info['tables'] = [list(table.values())[0] for table in tables]  # type: ignore
            
            # Get sample data from each table
            for table in debug_info['tables']:
                try:
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                    count = cursor.fetchone()
                    debug_info['sample_data'][table] = count['count'] if count else 0  # type: ignore
                except Exception as e:
                    debug_info['sample_data'][table] = f"Error: {str(e)}"
                    
        except Exception as e:
            debug_info['error'] = str(e)
    
    return render_template('debug.html', debug_info=debug_info)

if __name__ == '__main__':
    app.run(debug=True)
