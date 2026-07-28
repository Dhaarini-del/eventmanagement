# Instructions to Fix QR Code Upload Issue

## Problem
Your QR code image is not displaying because:
1. The image path in the template is incorrect
2. The book_ticket route doesn't handle POST requests for file uploads

## Fix 1: QR Code Image Path (Already Fixed)
The QR code image path in `templates/book_ticket.html` has been updated from:
```html
<img src="{{ url_for('static', filename='my_qr.png') }}" alt="QR Code" class="img-thumbnail" style="max-width: 200px;">
```
to:
```html
<img src="{{ url_for('static', filename='qr/my_qr.png') }}" alt="QR Code" class="img-thumbnail" style="max-width: 200px;">
```

## Fix 2: Update Book Ticket Route
You need to manually update the book_ticket route in `app.py`. 

**Find this code around line 502-509:**
```python
@app.route('/book-ticket')
def book_ticket():
    if cursor:
        cursor.execute("SELECT * FROM Events")
        events = cursor.fetchall()
        return render_template('book_ticket.html', events=events)
    return render_template('book_ticket.html', events=[])
```

**Replace it with this code:**
```python
@app.route('/book-ticket', methods=['GET', 'POST'])
def book_ticket():
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form['name']
            email = request.form['email']
            event_id = request.form['event_id']
            ticket_type = request.form['ticket_type']
            payment_method = request.form['payment_method']
            
            # Handle file upload
            payment_proof = request.files['payment_proof']
            
            if payment_proof and payment_proof.filename != '':
                # Create payment_proofs directory if it doesn't exist
                upload_folder = os.path.join(app.static_folder, 'payment_proofs')
                if not os.path.exists(upload_folder):
                    os.makedirs(upload_folder)
                
                # Save the uploaded file
                filename = f"{name}_{event_id}_{payment_proof.filename}"
                filepath = os.path.join(upload_folder, filename)
                payment_proof.save(filepath)
                
                # Insert attendee
                if cursor and conn:
                    cursor.execute(
                        "INSERT INTO Attendees (AttendeeName, Email) VALUES (%s, %s)",
                        (name, email)
                    )
                    attendee_id = cursor.lastrowid
                    
                    # Determine price based on ticket type
                    price = 1000.00 if ticket_type == 'VIP' else 500.00
                    
                    # Insert ticket
                    cursor.execute(
                        "INSERT INTO Tickets (EventID, AttendeeID, TicketType, Price) VALUES (%s, %s, %s, %s)",
                        (event_id, attendee_id, ticket_type, price)
                    )
                    
                    conn.commit()
                    flash(f"Ticket booked successfully! Payment proof uploaded: {filename}", "success")
                    return redirect('/confirm-payment')
                else:
                    flash("Database connection error", "danger")
            else:
                flash("Please upload payment proof", "danger")
                
        except Exception as e:
            print(f"Error booking ticket: {e}")
            flash(f"Error booking ticket: {e}", "danger")
    
    # GET request - show the form
    if cursor:
        cursor.execute("SELECT * FROM Events")
        events = cursor.fetchall()
        return render_template('book_ticket.html', events=events)
    return render_template('book_ticket.html', events=[])
```

## What This Fix Does:
1. **QR Code Display**: The QR code image will now display correctly on the booking page
2. **File Upload**: Users can upload payment proof files (jpg/png/pdf)
3. **Database Integration**: Ticket bookings will be saved to the database
4. **File Storage**: Payment proof files will be saved in the `static/payment_proofs/` directory
5. **User Feedback**: Success/error messages will be shown to users

## Testing:
1. Start your Flask app: `python app.py`
2. Go to `/book-ticket`
3. The QR code should now display correctly
4. Fill out the form and upload a payment proof file
5. Submit the form - it should save the ticket and redirect to confirmation page 