# Codign - System Design Platform

A LeetCode-like platform for System Design problems with AI-powered feedback using GPT-2.

## Features

- 🎯 **LLD & HLD Problems**: Low-Level and High-Level Design challenges
- 🤖 **AI Analysis**: GPT-2 powered solution analysis and scoring
- 📊 **Real-time Feedback**: Get instant feedback on your solutions
- 🏆 **Leaderboard**: Track your progress and compete with others
- 📧 **Email Verification**: Secure user registration with OTP
- 👨‍💼 **Admin Panel**: Manage problems and view analytics
- 📱 **Responsive Design**: Works on all devices

## Tech Stack

- **Backend**: Flask, MySQL
- **AI**: Hugging Face Transformers (GPT-2)
- **Frontend**: HTML, CSS, JavaScript
- **Email**: SMTP (Gmail)
- **Authentication**: bcrypt, sessions

## Installation

1. **Clone the repository**
\`\`\`bash
git clone <repository-url>
cd codign-platform
\`\`\`

2. **Install dependencies**
\`\`\`bash
pip install -r requirements.txt
\`\`\`

3. **Setup MySQL Database**
- Install MySQL and create a database
- Update `.env` file with your database credentials

4. **Configure Environment Variables**
Create a `.env` file with:
\`\`\`
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=codign_db

EMAIL_ADDRESS=your_email@gmail.com
EMAIL_PASSWORD=your_app_password

SECRET_KEY=your_secret_key
FLASK_ENV=development
\`\`\`

5. **Initialize Database**
\`\`\`bash
python setup_db.py
\`\`\`

6. **Run the Application**
\`\`\`bash
python app.py
\`\`\`

## Usage

### For Users
1. Register with email verification
2. Browse LLD/HLD problems
3. Write solutions and get AI feedback
4. Track your progress on leaderboard

### For Admins
1. Login at `/admin/login` (default: admin/admin123)
2. Add new problems
3. View analytics and user statistics

## AI Scoring System

The platform uses GPT-2 to analyze solutions and provides:
- **Score**: 0-10 based on solution quality
- **Feedback**: Constructive suggestions for improvement
- **Analysis**: Technical evaluation of the approach

## API Endpoints

- `POST /submit_solution` - Submit solution for scoring
- `POST /analyze_solution` - Analyze without saving
- `GET /leaderboard` - View rankings
- `GET /profile` - User dashboard

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file for details
