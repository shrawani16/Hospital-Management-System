from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_login import LoginManager, login_required, current_user, UserMixin, login_user, logout_user
import mysql.connector
from mysql.connector import pooling
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from mysql.connector import Error

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, user_data):
        self.id = user_data['id']
        self.username = user_data['username']
        self.role = user_data['role']

@login_manager.user_loader
def load_user(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
        user_data = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user_data:
            return User(user_data)
        return None
    except Exception as e:
        print(f"Error loading user: {e}")
        return None

# MySQL Configuration
db_config = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', 'Dhruv@69'),
    'database': os.getenv('MYSQL_DB', 'hospital_db'),
    'raise_on_warnings': True
}

def get_db_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        if conn.is_connected():
            return conn
        return None
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

# Test database connection
def test_db_connection():
    try:
        conn = get_db_connection()
        if conn and conn.is_connected():
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchall()  # Consume the result
            cursor.close()
            conn.close()
            return True
        return False
    except Exception as e:
        print(f"Database connection error: {str(e)}")
        return False

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
            user_data = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if user_data and check_password_hash(user_data['password'], password):
                user = User(user_data)
                login_user(user)
                flash('Logged in successfully!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password', 'error')
        except Exception as e:
            flash(f'Login error: {str(e)}', 'error')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        role = request.form.get('role', '').strip()
        
        # Validate required fields
        if not all([username, password, full_name, email, role]):
            flash('All fields are required', 'error')
            return redirect(url_for('register'))
            
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            if not conn:
                flash('Database connection failed. Please try again later.', 'error')
                return redirect(url_for('register'))
                
            cursor = conn.cursor()
            
            # Check if username or email already exists
            cursor.execute('SELECT * FROM users WHERE username = %s OR email = %s', (username, email))
            if cursor.fetchone():
                flash('Username or email already exists', 'error')
                return redirect(url_for('register'))
            
            # Create new user
            hashed_password = generate_password_hash(password)
            cursor.execute('''
                INSERT INTO users (username, password, full_name, email, role)
                VALUES (%s, %s, %s, %s, %s)
            ''', (username, hashed_password, full_name, email, role))
            
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Registration failed: {str(e)}', 'error')
            return redirect(url_for('register'))
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        if current_user.role == 'doctor':
            # Get doctor's availability
            cursor.execute('''
                SELECT da.*,
                       DATE_FORMAT(da.availability_date, '%Y-%m-%d') as formatted_date,
                       TIME_FORMAT(da.start_time, '%H:%i') as formatted_start_time,
                       TIME_FORMAT(da.end_time, '%H:%i') as formatted_end_time
                FROM doctor_availability da
                WHERE doctor_id = %s
                AND availability_date >= CURDATE()
                ORDER BY availability_date, start_time
            ''', (current_user.id,))
            availability = cursor.fetchall()
            
            # Get upcoming appointments
            cursor.execute('''
                SELECT a.*, u.full_name as patient_name,
                       DATE_FORMAT(a.appointment_date, '%Y-%m-%d') as formatted_date,
                       TIME_FORMAT(a.start_time, '%H:%i') as formatted_start_time,
                       TIME_FORMAT(a.end_time, '%H:%i') as formatted_end_time
                FROM appointments a
                JOIN users u ON a.patient_id = u.id
                WHERE a.doctor_id = %s AND a.status = 'scheduled'
                AND a.appointment_date >= CURDATE()
                ORDER BY a.appointment_date, a.start_time
            ''', (current_user.id,))
            appointments = cursor.fetchall()
            
            cursor.close()
            conn.close()
            return render_template('dashboard.html', 
                                 availability=availability,
                                 appointments=appointments)
            
        elif current_user.role == 'patient':
            # Get available doctors
            cursor.execute('''
                SELECT DISTINCT u.id, u.full_name, u.email
                FROM users u
                JOIN doctor_availability da ON u.id = da.doctor_id
                WHERE u.role = 'doctor'
                AND da.availability_date >= CURDATE()
            ''')
            doctors = cursor.fetchall()
            
            # Get patient's appointments
            cursor.execute('''
                SELECT a.*, u.full_name as doctor_name,
                       DATE_FORMAT(a.appointment_date, '%Y-%m-%d') as formatted_date,
                       TIME_FORMAT(a.start_time, '%H:%i') as formatted_start_time,
                       TIME_FORMAT(a.end_time, '%H:%i') as formatted_end_time
                FROM appointments a
                JOIN users u ON a.doctor_id = u.id
                WHERE a.patient_id = %s
                ORDER BY a.appointment_date, a.start_time
            ''', (current_user.id,))
            appointments = cursor.fetchall()
            
            cursor.close()
            conn.close()
            return render_template('dashboard.html',
                                 doctors=doctors,
                                 appointments=appointments)
            
        elif current_user.role == 'admin':
            # Get system statistics
            cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'doctor'")
            total_doctors = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'patient'")
            total_patients = cursor.fetchone()['count']
            
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM appointments 
                WHERE appointment_date = CURDATE()
            """)
            todays_appointments = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM appointments")
            total_appointments = cursor.fetchone()['count']
            
            # Get all users for management
            cursor.execute("SELECT * FROM users ORDER BY role, username")
            users = cursor.fetchall()
            
            stats = {
                'total_doctors': total_doctors,
                'total_patients': total_patients,
                'todays_appointments': todays_appointments,
                'total_appointments': total_appointments
            }
            
            cursor.close()
            conn.close()
            return render_template('dashboard.html',
                                 stats=stats,
                                 users=users)
        
        return render_template('dashboard.html')
        
    except Exception as e:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('dashboard.html')

@app.route('/availability', methods=['GET', 'POST'])
@login_required
def manage_availability():
    if current_user.role != 'doctor':
        flash('Only doctors can manage availability', 'error')
        return redirect(url_for('dashboard'))
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get current availability slots
        cursor.execute('''
            SELECT da.*,
                   DATE_FORMAT(da.availability_date, '%Y-%m-%d') as formatted_date,
                   TIME_FORMAT(da.start_time, '%H:%i') as formatted_start_time,
                   TIME_FORMAT(da.end_time, '%H:%i') as formatted_end_time
            FROM doctor_availability da
            WHERE doctor_id = %s
            AND availability_date >= CURDATE()
            ORDER BY availability_date, start_time
        ''', (current_user.id,))
        availability = cursor.fetchall()
        
        if request.method == 'POST':
            date = request.form.get('date', '').strip()
            start_time = request.form.get('start_time', '').strip()
            end_time = request.form.get('end_time', '').strip()
            
            if not all([date, start_time, end_time]):
                flash('All fields are required', 'error')
                return redirect(url_for('manage_availability'))
            
            # Validate time format and logic
            try:
                availability_date = datetime.strptime(date, '%Y-%m-%d').date()
                start_time_obj = datetime.strptime(start_time, '%H:%M').time()
                end_time_obj = datetime.strptime(end_time, '%H:%M').time()
                
                # Check if date is in the past
                if availability_date < datetime.now().date():
                    flash('Cannot set availability for past dates', 'error')
                    return redirect(url_for('manage_availability'))
                
                if start_time_obj >= end_time_obj:
                    flash('End time must be after start time', 'error')
                    return redirect(url_for('manage_availability'))
            except ValueError:
                flash('Invalid date or time format', 'error')
                return redirect(url_for('manage_availability'))
            
            # Check for overlapping slots
            cursor.execute('''
                SELECT * FROM doctor_availability
                WHERE doctor_id = %s 
                AND availability_date = %s
                AND (
                    (start_time <= %s AND end_time > %s) OR
                    (start_time < %s AND end_time >= %s) OR
                    (start_time >= %s AND end_time <= %s)
                )
            ''', (current_user.id, availability_date, 
                  start_time, start_time,
                  end_time, end_time,
                  start_time, end_time))
            
            if cursor.fetchone():
                flash('Time slot overlaps with existing availability', 'error')
                return redirect(url_for('manage_availability'))
            
            # Add new availability
            cursor.execute('''
                INSERT INTO doctor_availability 
                (doctor_id, availability_date, start_time, end_time)
                VALUES (%s, %s, %s, %s)
            ''', (current_user.id, availability_date, start_time, end_time))
            
            conn.commit()
            flash('Availability added successfully!', 'success')
            return redirect(url_for('manage_availability'))
            
        cursor.close()
        conn.close()
        
        # Pass today's date to template for min date validation
        today = datetime.now().date().strftime('%Y-%m-%d')
        return render_template('manage_availability.html', 
                             availability=availability,
                             today=today)
        
    except Exception as e:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
        flash(f'Error managing availability: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/availability/delete/<int:availability_id>', methods=['POST'])
@login_required
def delete_availability(availability_id):
    if current_user.role != 'doctor':
        flash('Only doctors can manage availability', 'error')
        return redirect(url_for('dashboard'))
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if the availability belongs to the current doctor and is not in the past
        cursor.execute('''
            SELECT * FROM doctor_availability 
            WHERE id = %s AND doctor_id = %s AND availability_date >= CURDATE()
        ''', (availability_id, current_user.id))
        
        if not cursor.fetchone():
            flash('Invalid availability slot or slot is in the past', 'error')
            return redirect(url_for('manage_availability'))
        
        # Delete the availability
        cursor.execute('DELETE FROM doctor_availability WHERE id = %s', (availability_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Availability slot deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting availability: {str(e)}', 'error')
        
    return redirect(url_for('manage_availability'))

@app.route('/book-appointment', methods=['GET', 'POST'])
@login_required
def book_appointment():
    if current_user.role != 'patient':
        flash('Only patients can book appointments', 'error')
        return redirect(url_for('dashboard'))
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get all doctors
        cursor.execute('''
            SELECT DISTINCT u.id, u.full_name, u.email
            FROM users u
            JOIN doctor_availability da ON u.id = da.doctor_id
            WHERE u.role = 'doctor'
            AND da.availability_date >= CURDATE()
        ''')
        doctors = cursor.fetchall()
        
        # Get selected doctor's availability if doctor_id is provided
        selected_doctor_id = request.args.get('doctor_id', type=int)
        available_slots = []
        
        if selected_doctor_id:
            # Get doctor's availability for future dates
            cursor.execute('''
                SELECT da.*, u.full_name as doctor_name,
                       DATE_FORMAT(da.availability_date, '%Y-%m-%d') as formatted_date,
                       TIME_FORMAT(da.start_time, '%H:%i') as formatted_start_time,
                       TIME_FORMAT(da.end_time, '%H:%i') as formatted_end_time,
                       TIMESTAMPDIFF(MINUTE, da.start_time, da.end_time) as duration_minutes
                FROM doctor_availability da
                JOIN users u ON da.doctor_id = u.id
                WHERE da.doctor_id = %s
                AND da.availability_date >= CURDATE()
                ORDER BY da.availability_date, da.start_time
            ''', (selected_doctor_id,))
            availability = cursor.fetchall()
            
            # Convert availability to 30-minute time slots
            if availability:
                for slot in availability:
                    slot_date = slot['availability_date']
                    start_time = datetime.strptime(slot['formatted_start_time'], '%H:%M')
                    end_time = datetime.strptime(slot['formatted_end_time'], '%H:%M')
                    
                    # Calculate time slots
                    current_slot = start_time
                    while current_slot + timedelta(minutes=30) <= end_time:
                        slot_end = current_slot + timedelta(minutes=30)
                        
                        # Format times for display and database
                        formatted_slot_start = current_slot.strftime('%H:%M')
                        formatted_slot_end = slot_end.strftime('%H:%M')
                        
                        # Check if slot is already booked
                        cursor.execute('''
                            SELECT id FROM appointments
                            WHERE doctor_id = %s 
                            AND appointment_date = %s
                            AND ((start_time <= %s AND end_time > %s) OR
                                 (start_time < %s AND end_time >= %s))
                        ''', (selected_doctor_id, slot_date,
                              formatted_slot_start, formatted_slot_start,
                              formatted_slot_end, formatted_slot_end))
                        
                        if not cursor.fetchone():
                            available_slots.append({
                                'date': slot['formatted_date'],
                                'start_time': formatted_slot_start,
                                'end_time': formatted_slot_end,
                                'doctor_name': slot['doctor_name']
                            })
            
        if request.method == 'POST':
            appointment_slot = request.form.get('appointment_slot')
            doctor_id = request.form.get('doctor')
            reason = request.form.get('reason')
            
            if not all([appointment_slot, doctor_id, reason]):
                flash('All fields are required', 'error')
                return redirect(url_for('book_appointment', doctor_id=doctor_id))
            
            # Parse the appointment slot value (format: "YYYY-MM-DD,HH:MM")
            try:
                date_str, time_str = appointment_slot.split(',')
                appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                start_time = datetime.strptime(time_str, '%H:%M').time()
                end_time = (datetime.combine(datetime.min, start_time) + timedelta(minutes=30)).time()
                
                # Check if date is in the past
                if appointment_date < datetime.now().date():
                    flash('Cannot book appointments for past dates', 'error')
                    return redirect(url_for('book_appointment', doctor_id=doctor_id))
            except ValueError:
                flash('Invalid appointment slot format', 'error')
                return redirect(url_for('book_appointment', doctor_id=doctor_id))
            
            # Check if slot is still available
            cursor.execute('''
                SELECT id FROM appointments
                WHERE doctor_id = %s 
                AND appointment_date = %s
                AND ((start_time <= %s AND end_time > %s) OR
                     (start_time < %s AND end_time >= %s))
            ''', (doctor_id, appointment_date,
                  start_time, start_time,
                  end_time, end_time))
            
            if cursor.fetchone():
                flash('This time slot is no longer available. Please choose another.', 'error')
                return redirect(url_for('book_appointment', doctor_id=doctor_id))
            
            # Create appointment
            cursor.execute('''
                INSERT INTO appointments 
                (doctor_id, patient_id, appointment_date, start_time, end_time, status, reason)
                VALUES (%s, %s, %s, %s, %s, 'scheduled', %s)
            ''', (doctor_id, current_user.id, appointment_date, start_time, end_time, reason))
            
            conn.commit()
            flash('Appointment booked successfully!', 'success')
            return redirect(url_for('dashboard'))
            
        cursor.close()
        conn.close()
        
        # Get user's existing appointments
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('''
            SELECT a.*, u.full_name as doctor_name,
                   DATE_FORMAT(a.appointment_date, '%Y-%m-%d') as formatted_date,
                   TIME_FORMAT(a.start_time, '%H:%i') as formatted_start_time,
                   TIME_FORMAT(a.end_time, '%H:%i') as formatted_end_time
            FROM appointments a
            JOIN users u ON a.doctor_id = u.id
            WHERE a.patient_id = %s
            ORDER BY a.appointment_date, a.start_time
        ''', (current_user.id,))
        appointments = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return render_template('book_appointment.html',
                             doctors=doctors,
                             selected_doctor_id=selected_doctor_id,
                             available_slots=available_slots,
                             appointments=appointments)
                             
    except Exception as e:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
        flash(f'Error booking appointment: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/appointment/cancel/<int:appointment_id>', methods=['POST'])
@login_required
def cancel_appointment(appointment_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if the appointment belongs to the current user
        cursor.execute('''
            SELECT * FROM appointments
            WHERE id = %s AND (patient_id = %s OR doctor_id = %s)
        ''', (appointment_id, current_user.id, current_user.id))
        
        if not cursor.fetchone():
            flash('Invalid appointment', 'error')
            return redirect(url_for('dashboard'))
        
        # Cancel the appointment
        cursor.execute('''
            UPDATE appointments
            SET status = 'cancelled'
            WHERE id = %s
        ''', (appointment_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Appointment cancelled successfully!', 'success')
    except Exception as e:
        flash(f'Error cancelling appointment: {str(e)}', 'error')
        
    return redirect(url_for('dashboard'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('home'))

# Medical Records Routes
@app.route('/medical-records/<int:patient_id>')
@login_required
def view_medical_records(patient_id):
    try:
        cursor = mysql.connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT mr.*, p.name as patient_name 
            FROM medical_records mr 
            JOIN patients p ON mr.patient_id = p.id 
            WHERE mr.patient_id = %s
        """, (patient_id,))
        records = cursor.fetchall()
        return render_template('medical_records.html', records=records)
    except Exception as e:
        flash(f'Error fetching medical records: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/medical-records/add/<int:patient_id>', methods=['GET', 'POST'])
@login_required
def add_medical_record(patient_id):
    if request.method == 'POST':
        try:
            diagnosis = request.form['diagnosis']
            symptoms = request.form['symptoms']
            notes = request.form['notes']
            
            cursor = mysql.connection.cursor()
            cursor.execute("""
                INSERT INTO medical_records (patient_id, diagnosis, symptoms, notes)
                VALUES (%s, %s, %s, %s)
            """, (patient_id, diagnosis, symptoms, notes))
            mysql.connection.commit()
            
            flash('Medical record added successfully!', 'success')
            return redirect(url_for('view_medical_records', patient_id=patient_id))
        except Exception as e:
            flash(f'Error adding medical record: {str(e)}', 'error')
            return redirect(url_for('dashboard'))
    return render_template('add_medical_record.html', patient_id=patient_id)

# Doctor Schedule Routes
@app.route('/doctor/schedule/<int:doctor_id>')
@login_required
def view_schedule(doctor_id):
    try:
        cursor = mysql.connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM doctor_schedules 
            WHERE doctor_id = %s
        """, (doctor_id,))
        schedules = cursor.fetchall()
        return render_template('doctor_schedule.html', schedules=schedules)
    except Exception as e:
        flash(f'Error fetching schedule: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

# Billing Routes
@app.route('/billing/<int:appointment_id>')
@login_required
def generate_bill(appointment_id):
    try:
        cursor = mysql.connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT a.*, p.name as patient_name, d.name as doctor_name, d.consultation_fee
            FROM appointments a
            JOIN patients p ON a.patient_id = p.id
            JOIN doctors d ON a.doctor_id = d.id
            WHERE a.id = %s
        """, (appointment_id,))
        appointment = cursor.fetchone()
        
        if not appointment:
            flash('Appointment not found!', 'error')
            return redirect(url_for('dashboard'))
            
        return render_template('generate_bill.html', appointment=appointment)
    except Exception as e:
        flash(f'Error generating bill: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

# Pharmacy Routes
@app.route('/pharmacy/inventory')
@login_required
def view_inventory():
    try:
        cursor = mysql.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM medicines")
        medicines = cursor.fetchall()
        return render_template('pharmacy_inventory.html', medicines=medicines)
    except Exception as e:
        flash(f'Error fetching inventory: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

# Lab Tests Routes
@app.route('/lab-tests/<int:patient_id>')
@login_required
def view_lab_tests(patient_id):
    try:
        cursor = mysql.connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM lab_tests 
            WHERE patient_id = %s
        """, (patient_id,))
        tests = cursor.fetchall()
        return render_template('lab_tests.html', tests=tests)
    except Exception as e:
        flash(f'Error fetching lab tests: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

# Messaging Routes
@app.route('/messages')
@login_required
def view_messages():
    try:
        cursor = mysql.connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT m.*, 
                   CASE 
                       WHEN m.sender_id = %s THEN receiver.name
                       ELSE sender.name
                   END as other_party_name
            FROM messages m
            JOIN users sender ON m.sender_id = sender.id
            JOIN users receiver ON m.receiver_id = receiver.id
            WHERE m.sender_id = %s OR m.receiver_id = %s
            ORDER BY m.created_at DESC
        """, (current_user.id, current_user.id, current_user.id))
        messages = cursor.fetchall()
        return render_template('messages.html', messages=messages)
    except Exception as e:
        flash(f'Error fetching messages: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

# Reviews Routes
@app.route('/reviews/<int:doctor_id>')
def view_reviews(doctor_id):
    try:
        cursor = mysql.connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT r.*, p.name as patient_name
            FROM reviews r
            JOIN patients p ON r.patient_id = p.id
            WHERE r.doctor_id = %s
            ORDER BY r.created_at DESC
        """, (doctor_id,))
        reviews = cursor.fetchall()
        return render_template('reviews.html', reviews=reviews)
    except Exception as e:
        flash(f'Error fetching reviews: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

# Notifications Routes
@app.route('/notifications')
@login_required
def view_notifications():
    try:
        cursor = mysql.connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM notifications
            WHERE user_id = %s
            ORDER BY created_at DESC
        """, (current_user.id,))
        notifications = cursor.fetchall()
        return render_template('notifications.html', notifications=notifications)
    except Exception as e:
        flash(f'Error fetching notifications: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

# User Management Routes
@app.route('/user/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        if request.method == 'POST':
            full_name = request.form.get('full_name', '').strip()
            email = request.form.get('email', '').strip()
            role = request.form.get('role', '').strip()
            
            if not all([full_name, email, role]):
                flash('All fields are required', 'error')
                return redirect(url_for('edit_user', user_id=user_id))
                
            # Check if email exists for other users
            cursor.execute('SELECT id FROM users WHERE email = %s AND id != %s', (email, user_id))
            if cursor.fetchone():
                flash('Email already exists', 'error')
                return redirect(url_for('edit_user', user_id=user_id))
            
            # Update user
            cursor.execute('''
                UPDATE users 
                SET full_name = %s, email = %s, role = %s
                WHERE id = %s
            ''', (full_name, email, role, user_id))
            
            conn.commit()
            flash('User updated successfully', 'success')
            return redirect(url_for('dashboard'))
            
        # Get user details
        cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()
        
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('dashboard'))
            
        cursor.close()
        conn.close()
        
        return render_template('edit_user.html', user=user)
        
    except Exception as e:
        flash(f'Error editing user: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/user/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if user exists and is not admin
        cursor.execute('SELECT username FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()
        
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('dashboard'))
            
        if user['username'] == 'admin':
            flash('Cannot delete admin user', 'error')
            return redirect(url_for('dashboard'))
            
        # Delete user's appointments
        cursor.execute('DELETE FROM appointments WHERE doctor_id = %s OR patient_id = %s', (user_id, user_id))
        
        # Delete user's availability if they are a doctor
        cursor.execute('DELETE FROM doctor_availability WHERE doctor_id = %s', (user_id,))
        
        # Delete user
        cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('User deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting user: {str(e)}', 'error')
        
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    if test_db_connection():
        print("Database connection successful!")
        app.run(host='127.0.0.1', port=5000)
    else:
        print("Failed to connect to database. Please check your MySQL server and credentials.") 