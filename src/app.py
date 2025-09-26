"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""


from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path
import mysql.connector
from mysql.connector import Error


app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# MySQL connection config (update as needed)
MYSQL_CONFIG = {
    "host": os.environ.get("MYSQL_HOST", "localhost"),
    "user": os.environ.get("MYSQL_USER", "root"),
    "password": os.environ.get("MYSQL_PASSWORD", "password"),
    "database": os.environ.get("MYSQL_DATABASE", "mergington_school")
}

def get_db_connection():
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        return conn
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        raise HTTPException(status_code=500, detail="Database connection error")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")


# --- MySQL schema expected ---
# Table: activities
#   name VARCHAR PRIMARY KEY
#   description TEXT
#   schedule TEXT
#   max_participants INT
#
# Table: participants
#   id INT AUTO_INCREMENT PRIMARY KEY
#   activity_name VARCHAR (FK to activities.name)
#   email VARCHAR

def fetch_activities_from_db():
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM activities")
        activities = {}
        for row in cur.fetchall():
            name = row["name"]
            activities[name] = {
                "description": row["description"],
                "schedule": row["schedule"],
                "max_participants": row["max_participants"],
                "participants": []
            }
        # Fetch participants
        cur.execute("SELECT activity_name, email FROM participants")
        for row in cur.fetchall():
            act = row["activity_name"]
            if act in activities:
                activities[act]["participants"].append(row["email"])
        return activities
    finally:
        conn.close()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")



@app.get("/activities")
def get_activities():
    return fetch_activities_from_db()



@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity (MySQL)"""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Validate activity exists
        cur.execute("SELECT max_participants FROM activities WHERE name=%s", (activity_name,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Activity not found")
        max_participants = row[0]
        # Check if already signed up
        cur.execute("SELECT 1 FROM participants WHERE activity_name=%s AND email=%s", (activity_name, email))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Student is already signed up")
        # Check if activity is full
        cur.execute("SELECT COUNT(*) FROM participants WHERE activity_name=%s", (activity_name,))
        count = cur.fetchone()[0]
        if count >= max_participants:
            raise HTTPException(status_code=400, detail="Activity is full")
        # Add student
        cur.execute("INSERT INTO participants (activity_name, email) VALUES (%s, %s)", (activity_name, email))
        conn.commit()
        return {"message": f"Signed up {email} for {activity_name}"}
    finally:
        conn.close()



@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity (MySQL)"""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Validate activity exists
        cur.execute("SELECT 1 FROM activities WHERE name=%s", (activity_name,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Activity not found")
        # Validate student is signed up
        cur.execute("SELECT 1 FROM participants WHERE activity_name=%s AND email=%s", (activity_name, email))
        if not cur.fetchone():
            raise HTTPException(status_code=400, detail="Student is not signed up for this activity")
        # Remove student
        cur.execute("DELETE FROM participants WHERE activity_name=%s AND email=%s", (activity_name, email))
        conn.commit()
        return {"message": f"Unregistered {email} from {activity_name}"}
    finally:
        conn.close()
