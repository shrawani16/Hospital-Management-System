# Hospital Management System

A comprehensive web-based hospital management system built with Flask and MySQL. This system provides features for managing patients, doctors, appointments, medical records, and hospital staff.

## Features

- **User Authentication**
  - Secure login system for patients, doctors, and administrators
  - Role-based access control
  - Password hashing and security

- **Patient Management**
  - Patient registration and profile management
  - Medical records management
  - Appointment booking and history

- **Doctor Management**
  - Doctor profiles and availability management
  - Appointment scheduling
  - Medical records access

- **Appointment System**
  - Real-time availability checking
  - Appointment booking and cancellation
  - Automated scheduling

- **Administrative Features**
  - User management
  - System configuration
  - Reports and analytics

## Prerequisites

- Python 3.8 or higher
- MySQL Server 8.0 or higher
- pip (Python package manager)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/hospital-management-system.git
cd hospital-management-system
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up the database:
   - Create a MySQL database
   - Update the `.env` file with your database credentials
   - Run the database setup script:
```bash
python setup_database.py
```

5. Run the application:
```bash
python app.py
```

The application will be available at `http://127.0.0.1:5000`

## Configuration

Create a `.env` file in the project root with the following variables:
```
DB_HOST=localhost
DB_USER=your_username
DB_PASSWORD=your_password
DB_NAME=hospital_db
SECRET_KEY=your_secret_key
```

## Project Structure

```
hospital-management-system/
├── app.py                 # Main application file
├── setup_database.py      # Database initialization script
├── requirements.txt       # Project dependencies
├── .env                   # Environment variables
├── database_schema.sql    # Database schema
├── templates/            # HTML templates
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── book_appointment.html
│   ├── medical_records.html
│   └── manage_availability.html
└── static/               # Static files
    ├── css/
    ├── js/
    └── images/
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contact

Your Name - shrawani.rayalkar16@gmail.com
Project Link: https://github.com/yourusername/hospital-management-system 
