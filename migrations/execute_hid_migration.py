import os
import pymysql
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection parameters - based on App/__init__.py configuration
DB_HOST = 'localhost'
DB_PORT = 3306
DB_USER = 'root'
DB_PASSWORD = '651748264Zz*'
DB_NAME = 'travelindustry'

# Connect to the database
conn = pymysql.connect(
    host=DB_HOST,
    port=DB_PORT,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_NAME,
    charset='utf8mb4'
)

try:
    # Create a cursor
    cur = conn.cursor()
    
    # Read the SQL file
    with open('migrations/add_hid_field.sql', 'r') as f:
        sql = f.read()
    
    # Execute the SQL commands
    for command in sql.split(';'):
        command = command.strip()
        if command:
            print(f"Executing: {command}")
            cur.execute(command)
    
    # Commit the changes
    conn.commit()
    
    print("Migration executed successfully!")

except Exception as e:
    # If an error occurs, rollback changes
    conn.rollback()
    print(f"Error occurred: {e}")

finally:
    # Close the cursor and connection
    if 'cur' in locals():
        cur.close()
    conn.close() 