import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}

def setup_database():
    """Create database and tables"""
    try:
        # Connect to MySQL server
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Create database
        database_name = os.getenv('DB_NAME')
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database_name}")
        cursor.execute(f"USE {database_name}")
        
        print(f"✅ Database '{database_name}' created successfully!")
        
        cursor.close()
        conn.close()
        
        print("✅ Database setup completed!")
        print("You can now run: python app.py")
        
    except mysql.connector.Error as err:
        print(f"❌ Error: {err}")
        print("Please check your MySQL connection and credentials in .env file")

if __name__ == "__main__":
    setup_database()
