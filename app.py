from flask import Flask, render_template, request, redirect, session, flash
import mysql.connector
import os
from dotenv import load_dotenv
from datetime import datetime


load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# --- MySQL Connection Setup ---
def get_db_connection():
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )
    return conn 

# --- Routes ---
@app.route('/')
def home():
    return render_template('home.html')

import re

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']
        age = request.form['age']
        gender = request.form['gender']
        occupation = request.form['occupation']
        ini_deposit = request.form['ini_deposit']
        city = request.form['city']
        state = request.form['state']
        account_type = request.form['account_type']

        # Validate email
        if not re.match(r'^[a-zA-Z0-9._%+-]+@gmail\.com$', email):
            flash('Please enter a valid Gmail address.', 'danger')
            return render_template('register.html')

        # Validate password
        if not re.match(r'^(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*]).{8,}$', password):
            flash('Password must be at least 8 characters long, contain one uppercase letter, one number, and one special character.', 'danger')
            return render_template('register.html')
        
        try:
            age_int = int(age)
            if age_int < 16:
                flash('Account holders must be at least 16 years old.', 'danger')
                return render_template('register.html')
        except ValueError:
            flash('Invalid age provided.', 'danger')
            return render_template('register.html')

        # Check if the email already exists in the database
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        existing_user = cur.fetchone()

        if existing_user:
            flash('Email already exists. Please use a different email address.', 'danger')
            return render_template('register.html')  # Redirect back to the registration page

        try:
            # Insert new user data into users table
            cur.execute(""" 
                INSERT INTO users (name, email, password, age, gender, occupation, ini_deposit, city, state)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (name, email, password, age, gender, occupation, ini_deposit, city, state))
            conn.commit()
            user_id = cur.lastrowid

            # Insert new account data into accounts table
            cur.execute(""" 
                INSERT INTO accounts (user_id, balance, account_type)
                VALUES (%s, %s, %s)
            """, (user_id, ini_deposit, account_type))
            conn.commit()

            flash('Registration successful! Please log in.', 'success')
            return redirect('/login')

        except mysql.connector.Error as e:
            flash(f'Error during registration: {e}', 'danger')
            conn.rollback()  # Rollback the transaction if any error occurs
            return redirect('/register')

        finally:
            conn.close()

    return render_template('register.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form['user_id']
        password = request.form['password']
        
        print(f"Attempting to login with user_id: {user_id} and password: {password}")

        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute('SELECT * FROM users WHERE email = %s AND password = %s', (user_id, password))
        user = cur.fetchone()
        conn.close()

        print(f"Query result: {user}")  # Debug print: Check the result of the query

        if user:
            print(f"User found: {user}")  # Debug print
            session['user_id'] = user['user_id']
            flash('Login successful!', 'success')
            return redirect('/dashboard')
        else:
            flash('Incorrect user ID or password.', 'danger')
            return redirect('/login')

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute('SELECT * FROM users WHERE user_id = %s', (user_id,))
    user = cur.fetchone()

    cur.execute('SELECT * FROM accounts WHERE user_id = %s', (user_id,))
    accounts = cur.fetchall()

    # Fetch only 10 most recent transactions
    cur.execute('''
        SELECT * FROM transactions 
        WHERE from_account IN (SELECT account_id FROM accounts WHERE user_id = %s)
           OR to_account IN (SELECT account_id FROM accounts WHERE user_id = %s)
        ORDER BY timestamp DESC
        LIMIT 10
    ''', (user_id, user_id))
    transactions = cur.fetchall()

    conn.close()

    return render_template('dashboard.html', user=user, accounts=accounts, transactions=transactions)

@app.route('/all_users')
def all_users():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    query = "SELECT user_id, name, email, city, state FROM users ORDER BY name ASC"
    cur.execute(query)
    users = cur.fetchall()
    cur.close()
    return render_template("all_users.html", users=users)


@app.route('/transaction', methods=['POST'])
def transaction():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    action = request.form['action']
    account_id = int(request.form['account_id'])
    amount = float(request.form['amount'])
    today = datetime.today().strftime('%Y-%m-%d')

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute('SELECT * FROM accounts WHERE account_id = %s AND user_id = %s', (account_id, user_id))
    account = cur.fetchone()

    if not account:
        flash('Invalid account.', 'danger')
        conn.close()
        return redirect('/dashboard')

    if action == 'deposit':
        cur.execute('UPDATE accounts SET balance = balance + %s WHERE account_id = %s', (amount, account_id))
        cur.execute('''
            INSERT INTO transactions (from_account, to_account, amount, transaction_type, date)
            VALUES (%s, %s, %s, %s, %s)
        ''', (account_id, account_id, amount, 'deposit', today))

    elif action == 'withdrawal':
        if account['balance'] < amount:
            flash('Insufficient balance.', 'danger')
            conn.close()
            return redirect('/dashboard')
        cur.execute('UPDATE accounts SET balance = balance - %s WHERE account_id = %s', (amount, account_id))
        cur.execute('''
            INSERT INTO transactions (from_account, to_account, amount, transaction_type, date)
            VALUES (%s, %s, %s, %s, %s)
        ''', (account_id, account_id, amount, 'withdrawal', today))

    elif action == 'transfer':
        to_account_number = request.form['to_account_number'].strip()

        # Check if recipient account exists based on account_number
        cur.execute('SELECT * FROM accounts WHERE account_number = %s', (to_account_number,))
        to_account = cur.fetchone()

        if not to_account:
            flash('Recipient account not found.', 'danger')
            conn.close()
            return redirect('/dashboard')

        to_account_id = to_account['account_id']

        if account['balance'] < amount:
            flash('Insufficient balance.', 'danger')
            conn.close()
            return redirect('/dashboard')

        # Proceed with transfer
        cur.execute('UPDATE accounts SET balance = balance - %s WHERE account_id = %s', (amount, account_id))
        cur.execute('UPDATE accounts SET balance = balance + %s WHERE account_id = %s', (amount, to_account_id))
        cur.execute('''
            INSERT INTO transactions (from_account, to_account, amount, transaction_type, date)
            VALUES (%s, %s, %s, %s, %s)
        ''', (account_id, to_account_id, amount, 'transfer', today))


    conn.commit()
    conn.close()
    flash('Transaction successful.', 'success')
    return redirect('/dashboard')

@app.route('/all-transactions')
def all_transactions():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute('''
        SELECT * FROM transactions 
        WHERE from_account IN (SELECT account_id FROM accounts WHERE user_id = %s)
           OR to_account IN (SELECT account_id FROM accounts WHERE user_id = %s)
        ORDER BY timestamp DESC
    ''', (user_id, user_id))
    transactions = cur.fetchall()
    conn.close()

    return render_template('all_transactions.html', transactions=transactions)



@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)