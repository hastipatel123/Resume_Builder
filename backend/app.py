from flask import Flask, jsonify, request, render_template
from flask_cors import CORS

from database import get_connection

app = Flask(__name__, template_folder="../frontend")

CORS(app)

@app.route("/")
def home():
    return render_template("home.html")


@app.route("/login")
def login_page():
    return render_template("login.html")


@app.route("/register")
def register_page():
    return render_template("register.html")


@app.route("/api/users", methods=["GET"])
def get_users():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT user_id, name, email, password FROM users"
    )

    users = cursor.fetchall()

    cursor.close()
    connection.close()

    result = []

    for user in users:
        result.append({
            "user_id": user[0],
            "name": user[1],
            "email": user[2],
            "password": user[3]
        })

    return jsonify(result)

@app.route("/api/register", methods=["POST"])
def register():

    data = request.get_json()

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    if not name or not email or not password:

        return jsonify({
            "message":"All fields are required"
        }),400

    connection = get_connection()
    cursor= connection.cursor()

    cursor.execute(
        "SELECT user_id FROM users WHERE email = %s",
        (email,)
    )

    existing_user = cursor.fetchone()

    if existing_user:

        cursor.close()
        connection.close()

        return jsonify({

            "message":"Email already registered"
        }),409

    cursor.execute(
        """
        INSERT INTO users (name,email,password)
        VALUES(%s,%s,%s)
        RETURNING user_id
        """,
        (name,email,password)
    )

    user_id = cursor.fetchone()[0]

    connection.commit()

    cursor.close()
    connection.close()

    return jsonify({

        "message":"Registration successful",
        "user_id":user_id
    }),201

@app.route("/api/login", methods=["POST"])
def login():

    data = request.get_json()

    email = data.get("email")
    password = data.get("password")


    # Check empty fields
    if not email or not password:

        return jsonify({
            "message": "Email and password are required"
        }), 400


    connection = get_connection()
    cursor = connection.cursor()


    # Find user by email
    cursor.execute(
        """
        SELECT user_id, name, email, password
        FROM users
        WHERE email = %s
        """,
        (email,)
    )


    user = cursor.fetchone()


    cursor.close()
    connection.close()


    # User does not exist
    if not user:

        return jsonify({
            "message": "Invalid email or password"
        }), 401


    user_id = user[0]
    name = user[1]
    stored_password = user[3]


    # Check password
    if password != stored_password:

        return jsonify({
            "message": "Invalid email or password"
        }), 401


    # Login successful
    return jsonify({
        "message": "Login successful",
        "user_id": user_id,
        "name": name
    }), 200

if __name__ == "__main__":
    app.run(debug=True, port=5000)