import psycopg2;

def get_connection():
    connection = psycopg2.connect(
        host="localhost",
        port="5432",
        database="resume_db",
        user="postgres",
        password="postgres"
    )

    return connection
