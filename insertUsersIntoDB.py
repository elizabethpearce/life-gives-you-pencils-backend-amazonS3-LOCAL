from app import app, db
from app import Users
from flask_bcrypt import Bcrypt
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize the Flask app context
app.app_context().push()

# Function to create a new user
def create_new_user(username, password):
    bcrypt = Bcrypt(app)
    password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    user = Users(username=username, password_hash=password_hash)
    db.session.add(user)
    db.session.commit()

if __name__ == "__main__":
    # Specify the username and password for the new user
    username = os.getenv("NEW_USERNAME")
    password = os.getenv("NEW_PASSWORD")

    # Call the create_new_user function to insert the user into the database
    create_new_user(username, password)

    print("New user inserted successfully.")
