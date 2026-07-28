import mysql.connector

# Database Connection
try:
    conn = mysql.connector.connect(
        host='127.0.0.1',
        user='root',
        password='root@123',
        database='EventDB'
    )
    cursor = conn.cursor(dictionary=True, buffered=True)
    print("Database connected successfully!")
    
    # Check Events table
    cursor.execute("SELECT COUNT(*) as count FROM Events")
    count_result = cursor.fetchone()
    event_count = count_result['count'] if count_result else 0
    print(f"Total events in Events table: {event_count}")
    
    if event_count > 0:
        cursor.execute("SELECT * FROM Events")
        events = cursor.fetchall()
        print("Events found:")
        for event in events:
            print(f"  {event}")
    else:
        print("No events found in Events table")
        
        # Check if Venues table has data
        cursor.execute("SELECT COUNT(*) as count FROM Venues")
        venue_count = cursor.fetchone()['count']
        print(f"Venues in database: {venue_count}")
        
        if venue_count > 0:
            cursor.execute("SELECT * FROM Venues")
            venues = cursor.fetchall()
            print("Venues found:")
            for venue in venues:
                print(f"  {venue}")
    
    # Check table structure
    cursor.execute("DESCRIBE Events")
    structure = cursor.fetchall()
    print("\nEvents table structure:")
    for field in structure:
        print(f"  {field}")
        
except Exception as e:
    print(f"Database connection error: {e}")
finally:
    if 'conn' in locals():
        conn.close()
        print("Database connection closed.") 