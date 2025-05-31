from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import mysql.connector
import os
from datetime import datetime
from dotenv import load_dotenv
import requests
import json
import re

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME')
}

# Groq API configuration
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Solution validation constants
MIN_ANALYZE_LENGTH = 2  # Very minimal for analysis
MIN_SUBMIT_LENGTH = 100  # Higher requirement for submission
MAX_SOLUTION_LENGTH = 10000

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create database if not exists
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
    cursor.execute(f"USE {DB_CONFIG['database']}")
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_score INT DEFAULT 0
        )
    ''')
    
    # Problems table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS problems (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(200) NOT NULL,
            description TEXT NOT NULL,
            question_type ENUM('LLD', 'HLD') NOT NULL,
            difficulty ENUM('easy', 'medium', 'hard') NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            submissions INT DEFAULT 0
        )
    ''')
    
    # Submissions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS submissions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            problem_id INT,
            solution TEXT NOT NULL,
            score INT DEFAULT 0,
            feedback TEXT,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (problem_id) REFERENCES problems(id)
        )
    ''')
    
    # Admin table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert default admin
    cursor.execute('''
        INSERT IGNORE INTO admins (username, password) 
        VALUES (%s, %s)
    ''', ('admin', 'admin123'))
    
    # Insert sample problems with proper formatting
    sample_problems = [
        ('Design a URL Shortener', '''Design a URL shortening service like bit.ly or tinyurl.com.

Functional Requirements:
• Shorten long URLs to a short alias
• Redirect short URLs to original URLs  
• Handle 100M URLs per day
• Support custom aliases
• Analytics for click tracking
• URL expiration feature

Non-Functional Requirements:
• System should handle 100M URLs per day
• 99.9% uptime requirement
• Response time < 100ms for redirects
• Support for 1M concurrent users

Considerations:
• Database design and sharding strategy
• Caching strategy for popular URLs
• Load balancing across multiple servers
• Rate limiting to prevent abuse
• Security measures against malicious URLs''', 'HLD', 'medium'),
        
        ('Implement LRU Cache', '''Design and implement a data structure for Least Recently Used (LRU) cache.

Functional Requirements:
• get(key) - Get the value of the key if it exists, otherwise return -1
• put(key, value) - Set or insert the value if the key is not already present
• When cache reaches capacity, invalidate the least recently used item
• Support for any data type as key and value

Non-Functional Requirements:
• Both operations should run in O(1) average time complexity
• Memory efficient implementation
• Thread-safe operations

Considerations:
• Use appropriate data structures (HashMap + Doubly Linked List)
• Handle edge cases like capacity = 0
• Consider using built-in data structures vs custom implementation
• Memory management and cleanup''', 'LLD', 'medium'),
        
        ('Design Chat System', '''Design a real-time chat system like WhatsApp or Slack.

Functional Requirements:
• One-on-one messaging
• Group chats with multiple participants
• Online presence and last seen status
• Message delivery status (sent, delivered, read)
• Push notifications for offline users
• File and media sharing
• Message history and search
• User authentication and profiles

Non-Functional Requirements:
• Support 1 billion users
• Handle 100 million daily active users
• Process 50 billion messages per day
• 99.99% uptime requirement
• Real-time message delivery < 100ms
• Support for multiple devices per user

Considerations:
• WebSocket connections for real-time communication
• Database design for message storage and retrieval
• Microservices architecture for scalability
• CDN for media file distribution
• End-to-end encryption for security
• Load balancing and auto-scaling strategies''', 'HLD', 'hard'),
        
        ('Design Parking Lot System', '''Design a parking lot system with multiple levels and vehicle types.

Functional Requirements:
• Multiple levels with different vehicle types
• Compact, Large, and Motorcycle parking spots
• Track available spots in real-time
• Calculate parking fees based on time and vehicle type
• Generate and validate parking tickets
• Handle payments (cash, card, mobile)
• Admin panel for monitoring and management

Non-Functional Requirements:
• System should handle 1000+ vehicles simultaneously
• Real-time spot availability updates
• 99.9% system availability
• Fast ticket generation < 2 seconds

Considerations:
• Object-oriented design with proper inheritance
• Design patterns (Strategy for pricing, Observer for notifications)
• Database design for vehicles, spots, and transactions
• Concurrency handling for spot allocation
• Integration with payment gateways
• Scalability for multiple parking locations''', 'LLD', 'easy'),
        
        ('Design Netflix Streaming Service', '''Design a video streaming service like Netflix with global scale.

Functional Requirements:
• User registration and authentication
• Video upload, encoding, and storage
• Video streaming with multiple quality options
• Search and recommendation system
• User profiles and watchlists
• Content rating and reviews
• Subscription management
• Download for offline viewing

Non-Functional Requirements:
• Support 200 million users globally
• Handle 1 billion hours watched per week
• 99.99% uptime requirement
• Video streaming latency < 2 seconds
• Support for multiple devices and platforms
• Global content delivery

Considerations:
• Microservices architecture for different functionalities
• CDN strategy for global content delivery
• Video encoding and adaptive bitrate streaming
• Recommendation algorithms and machine learning
• Data analytics for user behavior
• Content licensing and geo-restrictions
• Auto-scaling based on demand patterns''', 'HLD', 'hard')
    ]
    
    for title, desc, qtype, diff in sample_problems:
        cursor.execute('''
            INSERT IGNORE INTO problems (title, description, question_type, difficulty) 
            VALUES (%s, %s, %s, %s)
        ''', (title, desc, qtype, diff))
    
    conn.commit()
    cursor.close()
    conn.close()

def validate_solution_for_analysis(solution):
    """Validate solution for analysis - very lenient"""
    if not solution or not solution.strip():
        return False, "Solution cannot be empty."
    
    solution = solution.strip()
    
    if len(solution) < MIN_ANALYZE_LENGTH:
        return False, f"Solution too short. Please provide at least {MIN_ANALYZE_LENGTH} characters for analysis."
    
    if len(solution) > MAX_SOLUTION_LENGTH:
        return False, f"Solution too long. Please keep it under {MAX_SOLUTION_LENGTH} characters."
    
    return True, "Valid solution for analysis."

def validate_solution_for_submission(solution):
    """Validate solution for submission - more strict"""
    if not solution or not solution.strip():
        return False, "Solution cannot be empty."
    
    solution = solution.strip()
    
    if len(solution) < MIN_SUBMIT_LENGTH:
        return False, f"Solution too short for submission. Please provide at least {MIN_SUBMIT_LENGTH} characters for a complete solution."
    
    if len(solution) > MAX_SOLUTION_LENGTH:
        return False, f"Solution too long. Please keep it under {MAX_SOLUTION_LENGTH} characters."
    
    # Check for meaningful content (not just repeated characters or spaces)
    unique_chars = len(set(solution.replace(' ', '').replace('\n', '')))
    if unique_chars < 10:
        return False, "Solution appears to lack meaningful content. Please provide a detailed solution."
    
    # Check for minimum word count
    words = solution.split()
    if len(words) < 20:
        return False, "Solution too brief. Please provide a more detailed explanation with at least 20 words."
    
    return True, "Valid solution for submission."

def analyze_solution_with_groq(solution, problem_description, problem_type, problem_title):
    """Analyze solution using Groq API with structured prompt and return score and feedback"""
    try:
        # Create a comprehensive prompt template
        prompt = f"""You are an expert system design interviewer evaluating a {problem_type} solution. 

PROBLEM: {problem_title}
{problem_description}

CANDIDATE'S SOLUTION:
{solution}

EVALUATION CRITERIA:
For {problem_type} problems, evaluate based on:
{"• Class design and relationships" if problem_type == "LLD" else "• System architecture and components"}
{"• Design patterns usage" if problem_type == "LLD" else "• Scalability and performance considerations"}
{"• Code structure and implementation" if problem_type == "LLD" else "• Database design and data flow"}
{"• Object-oriented principles" if problem_type == "LLD" else "• API design and microservices"}
{"• Error handling and edge cases" if problem_type == "LLD" else "• Caching and load balancing strategies"}

SCORING GUIDELINES:
• 9-10: Excellent solution with comprehensive design, best practices, and scalability considerations
• 7-8: Good solution with solid design but missing some advanced concepts or optimizations
• 5-6: Average solution that meets basic requirements but lacks depth or has design flaws
• 3-4: Below average solution with significant gaps or incorrect approaches
• 1-2: Poor solution with major flaws or incomplete understanding

Please provide your evaluation in this EXACT format:

SCORE: [number from 1-10]

FEEDBACK: [Detailed feedback covering strengths, weaknesses, and specific suggestions for improvement. Be constructive and educational.]

SUGGESTIONS:
• [Specific suggestion 1]
• [Specific suggestion 2]
• [Specific suggestion 3]"""

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "llama3-8b-8192",
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert system design interviewer with 10+ years of experience at top tech companies. You provide detailed, constructive feedback on system design solutions."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,
            "max_tokens": 800
        }
        
        response = requests.post(GROQ_API_URL, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # Parse the response to extract score and feedback
            score = 5  # default score
            feedback = "Analysis completed."
            suggestions = ""
            
            # Extract score using regex
            score_match = re.search(r'SCORE:\s*(\d+)', content)
            if score_match:
                score = int(score_match.group(1))
                score = max(1, min(10, score))  # Ensure score is between 1-10
            
            # Extract feedback
            feedback_match = re.search(r'FEEDBACK:\s*(.*?)(?=SUGGESTIONS:|$)', content, re.DOTALL)
            if feedback_match:
                feedback = feedback_match.group(1).strip()
            
            # Extract suggestions
            suggestions_match = re.search(r'SUGGESTIONS:\s*(.*)', content, re.DOTALL)
            if suggestions_match:
                suggestions = suggestions_match.group(1).strip()
                # Combine feedback and suggestions
                if suggestions:
                    feedback += f"\n\nSuggestions for Improvement:\n{suggestions}"
            
            return score, feedback
        else:
            print(f"Groq API Error: {response.status_code} - {response.text}")
            return 5, "AI analysis temporarily unavailable. Please try again later."
            
    except requests.exceptions.Timeout:
        print("Groq API timeout")
        return 5, "Analysis timed out. Please try again with a shorter solution."
    except requests.exceptions.RequestException as e:
        print(f"Groq API request error: {e}")
        return 5, "Network error during analysis. Please check your connection and try again."
    except Exception as e:
        print(f"Error in Groq analysis: {e}")
        return 5, "An error occurred during analysis. Please try again."

# Initialize database when app starts
with app.app_context():
    init_db()

@app.route('/')
def index():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('''
        SELECT p.*, COUNT(s.id) as submission_count 
        FROM problems p 
        LEFT JOIN submissions s ON p.id = s.problem_id 
        GROUP BY p.id 
        ORDER BY p.created_at DESC
    ''')
    problems = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('index.html', problems=problems)

@app.route('/problem/<int:problem_id>')
def problem_detail(problem_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('SELECT * FROM problems WHERE id = %s', (problem_id,))
    problem = cursor.fetchone()
    
    if not problem:
        flash('Problem not found!', 'error')
        return redirect(url_for('index'))
    
    submissions = []
    if 'user_id' in session:
        cursor.execute('''
            SELECT * FROM submissions 
            WHERE user_id = %s AND problem_id = %s 
            ORDER BY submitted_at DESC 
            LIMIT 5
        ''', (session['user_id'], problem_id))
        submissions = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('problem.html', problem=problem, submissions=submissions)

@app.route('/submit_solution', methods=['POST'])
def submit_solution():
    if 'user_id' not in session:
        return jsonify({'error': 'Please login to submit solutions'}), 401
    
    problem_id = request.json.get('problem_id')
    solution = request.json.get('solution')
    
    if not solution or not problem_id:
        return jsonify({'error': 'Missing solution or problem ID'}), 400
    
    # Validate solution for submission (stricter)
    is_valid, validation_message = validate_solution_for_submission(solution)
    if not is_valid:
        return jsonify({'error': validation_message}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('SELECT * FROM problems WHERE id = %s', (problem_id,))
    problem = cursor.fetchone()
    
    if not problem:
        return jsonify({'error': 'Problem not found'}), 404
    
    # Analyze solution with enhanced prompt
    score, feedback = analyze_solution_with_groq(
        solution, 
        problem['description'], 
        problem['question_type'],
        problem['title']
    )
    
    cursor.execute('''
        INSERT INTO submissions (user_id, problem_id, solution, score, feedback) 
        VALUES (%s, %s, %s, %s, %s)
    ''', (session['user_id'], problem_id, solution, score, feedback))
    
    cursor.execute('UPDATE problems SET submissions = submissions + 1 WHERE id = %s', (problem_id,))
    cursor.execute('UPDATE users SET total_score = total_score + %s WHERE id = %s', (score, session['user_id']))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({
        'score': score,
        'feedback': feedback,
        'message': f'Solution submitted successfully! Score: {score}/10'
    })

@app.route('/analyze_solution', methods=['POST'])
def analyze_solution():
    if 'user_id' not in session:
        return jsonify({'error': 'Please login to analyze solutions'}), 401
    
    problem_id = request.json.get('problem_id')
    solution = request.json.get('solution')
    
    if not solution or not problem_id:
        return jsonify({'error': 'Missing solution or problem ID'}), 400
    
    # Validate solution for analysis (very lenient)
    is_valid, validation_message = validate_solution_for_analysis(solution)
    if not is_valid:
        return jsonify({'error': validation_message}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('SELECT * FROM problems WHERE id = %s', (problem_id,))
    problem = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if not problem:
        return jsonify({'error': 'Problem not found'}), 404
    
    # Analyze solution with enhanced prompt
    score, feedback = analyze_solution_with_groq(
        solution, 
        problem['description'], 
        problem['question_type'],
        problem['title']
    )
    
    return jsonify({
        'score': score,
        'feedback': feedback,
        'analysis': f'Analysis complete. Preliminary score: {score}/10'
    })

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        next_url = request.form.get('next', url_for('index'))
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long!', 'error')
            return render_template('register.html', next=next_url)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM users WHERE username = %s OR email = %s', (username, email))
        if cursor.fetchone():
            flash('Username or email already exists!', 'error')
            cursor.close()
            conn.close()
            return render_template('register.html', next=next_url)
        
        cursor.execute('''
            INSERT INTO users (username, email, password) 
            VALUES (%s, %s, %s)
        ''', (username, email, password))
        
        user_id = cursor.lastrowid
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Auto login after registration
        session['user_id'] = user_id
        session['username'] = username
        
        flash('Registration successful! You are now logged in.', 'success')
        return redirect(next_url)
    
    next_url = request.args.get('next', url_for('index'))
    return render_template('register.html', next=next_url)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        next_url = request.form.get('next', url_for('index'))
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('SELECT * FROM users WHERE email = %s AND password = %s', (email, password))
        user = cursor.fetchone()
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Login successful!', 'success')
            cursor.close()
            conn.close()
            return redirect(next_url)
        else:
            flash('Invalid email or password!', 'error')
            cursor.close()
            conn.close()
    
    next_url = request.args.get('next', url_for('index'))
    return render_template('login.html', next=next_url)

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
    user = cursor.fetchone()
    
    cursor.execute('''
        SELECT s.*, p.title, p.question_type, p.difficulty 
        FROM submissions s 
        JOIN problems p ON s.problem_id = p.id 
        WHERE s.user_id = %s 
        ORDER BY s.submitted_at DESC
    ''', (session['user_id'],))
    submissions = cursor.fetchall()
    
    cursor.execute('SELECT COUNT(*) as total_submissions FROM submissions WHERE user_id = %s', (session['user_id'],))
    total_submissions = cursor.fetchone()['total_submissions']
    
    cursor.execute('SELECT AVG(score) as avg_score FROM submissions WHERE user_id = %s', (session['user_id'],))
    avg_score = cursor.fetchone()['avg_score'] or 0
    
    cursor.close()
    conn.close()
    
    return render_template('profile.html', 
                         user=user, 
                         submissions=submissions, 
                         total_submissions=total_submissions,
                         avg_score=round(avg_score, 1))

@app.route('/leaderboard')
def leaderboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('''
        SELECT u.username, u.total_score, COUNT(s.id) as total_submissions,
               AVG(s.score) as avg_score
        FROM users u 
        LEFT JOIN submissions s ON u.id = s.user_id 
        GROUP BY u.id 
        ORDER BY u.total_score DESC, avg_score DESC
        LIMIT 50
    ''')
    leaderboard = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('leaderboard.html', leaderboard=leaderboard)

# Admin routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('SELECT * FROM admins WHERE username = %s AND password = %s', (username, password))
        admin = cursor.fetchone()
        
        if admin:
            session['admin_id'] = admin['id']
            session['admin_username'] = admin['username']
            cursor.close()
            conn.close()
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials!', 'error')
            cursor.close()
            conn.close()
    
    return render_template('admin/login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('SELECT COUNT(*) as count FROM users')
    total_users = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM problems')
    total_problems = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM submissions')
    total_submissions = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM problems WHERE question_type = 'LLD'")
    lld_problems = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM problems WHERE question_type = 'HLD'")
    hld_problems = cursor.fetchone()['count']
    
    cursor.execute('SELECT * FROM problems ORDER BY created_at DESC LIMIT 5')
    recent_problems = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         total_problems=total_problems,
                         total_submissions=total_submissions,
                         lld_problems=lld_problems,
                         hld_problems=hld_problems,
                         recent_problems=recent_problems)

@app.route('/admin/add_problem', methods=['GET', 'POST'])
def admin_add_problem():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        functional_req = request.form['functional_req']
        non_functional_req = request.form.get('non_functional_req', '')
        considerations = request.form.get('considerations', '')
        question_type = request.form['question_type']
        difficulty = request.form['difficulty']
        
        # Combine all sections into a formatted description
        full_description = f"""{description}

Functional Requirements:
{functional_req}

Non-Functional Requirements:
{non_functional_req}

Considerations:
{considerations}"""
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO problems (title, description, question_type, difficulty) 
            VALUES (%s, %s, %s, %s)
        ''', (title, full_description, question_type, difficulty))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Problem added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/add_problem.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    session.pop('admin_username', None)
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    app.run(debug=True)
