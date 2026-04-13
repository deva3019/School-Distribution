import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# Initialize globally to utilize PyMongo's built-in connection pooling.
# This prevents opening a new connection on every single request.
client = None
db = None

def get_db():
    global client, db
    
    # If the database connection already exists, reuse it (Lightning Fast)
    if db is not None:
        return db

    mongo_uri = os.environ.get("MONGO_URI")
    if not mongo_uri:
        raise ValueError("Critical Error: MONGO_URI environment variable not found.")

    try:
        # maxPoolSize=50 allows up to 50 concurrent operations. 
        # serverSelectionTimeoutMS ensures the app doesn't hang if the DB is down.
        client = MongoClient(mongo_uri, maxPoolSize=50, serverSelectionTimeoutMS=5000)
        
        # Ping the server to verify the connection
        client.admin.command('ping')
        
        # Connect to the specific database (it will create it if it doesn't exist)
        db = client.school_distribution_db 

        # Build indexes automatically to speed up common queries
        setup_indexes(db)
        print("MongoDB connected and indexed successfully.")
        
        return db

    except ConnectionFailure as e:
        print(f"MongoDB Connection Failed: {e}")
        return None

def setup_indexes(db):
    """
    Creating indexes ensures that searching through 200+ schools 
    takes milliseconds instead of seconds.
    """
    # Fast logins
    db.users.create_index("username", unique=True)
    
    # Fast filtering of items available to HMs
    db.inventory.create_index("status")
    
    # Fast request lookups for the Distributor dashboard
    db.requests.create_index([("school_id", 1), ("status", 1)])