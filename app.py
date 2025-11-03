from flask import Flask, render_template, redirect, url_for, session, flash, request
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, ValidationError
import bcrypt
from flask_mysqldb import MySQL
from dotenv import load_dotenv
import os
import google.generativeai as genai  # Gemini library

# Load environment variables
load_dotenv()

app = Flask(__name__)

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'namrata@123'
app.config['MYSQL_DB'] = 'auth_system'
app.config['SECRET_KEY'] = 'your_very_secret_key'

# Initialize MySQL
mysql = MySQL(app)

# Configure Gemini using key from .env
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


# ------------------- FORMS -------------------
class RegisterForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Register")

    def validate_email(self, field):
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email=%s", (field.data,))
        user = cursor.fetchone()
        cursor.close()
        if user:
            raise ValidationError('Email Already Taken')


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")


class BookForm(FlaskForm):
    title = StringField("Book Title", validators=[DataRequired()])
    submit = SubmitField("Add Book")


# ------------------- ROUTES -------------------
@app.route('/')
def home():
    return render_template("index.html")


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        cursor.close()

        if user and bcrypt.checkpw(password.encode('utf-8'), user[3].encode('utf-8')):
            session['user_id'] = user[0]
            return redirect(url_for('dashboard'))
        else:
            flash("Login failed. Please check your email and password")
            return redirect(url_for('login'))

    return render_template('login.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                       (username, email, hashed_password))
        mysql.connection.commit()
        cursor.close()

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for('login'))

    return render_template('register.html', form=form)


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    form = BookForm()
    chatbot_response = None
    chat_query = None

    # Fetch user's books
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT title FROM books WHERE user_id=%s", (user_id,))
    books = [row[0] for row in cursor.fetchall()]
    cursor.close()

    if request.method == "POST":
        # Add a new book
        if 'title' in request.form and request.form['title']:
            book_title = request.form['title']
            cursor = mysql.connection.cursor()
            cursor.execute("INSERT INTO books (user_id, title) VALUES (%s, %s)", (user_id, book_title))
            mysql.connection.commit()
            cursor.close()
            flash("Book added successfully!", "success")
            return redirect(url_for('dashboard'))

        # Handle chat message
        elif 'chat_query' in request.form:
            chat_query = request.form['chat_query'].strip()
            if chat_query:
                context = f"User has these books: {', '.join(books)}."
                prompt = f"You are a friendly library assistant. {context}\nUser: {chat_query}"
                try:
                    model = genai.GenerativeModel("gemini-2.0-flash-exp")
                    result = model.generate_content(prompt)
                    chatbot_response = result.text if result and result.text else "Sorry, I couldn’t generate a response."
                except Exception as e:
                    chatbot_response = f"⚠️ Error: {str(e)}"

    return render_template('dashboard.html', form=form, books=books,
                           chatbot_response=chatbot_response, chat_query=chat_query)



@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("You have been logged out successfully.")
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)
