# Updated book_ticket route with file upload support
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
                
                # Insert attendee if not already present
                if cursor and conn:
                    cursor.execute(
                        "SELECT AttendeeID FROM Attendees WHERE AttendeeName = %s AND Email = %s",
                        (name, email)
                    )
                    attendee = cursor.fetchone()
                    if attendee:
                        attendee_id = attendee['AttendeeID']
                    else:
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