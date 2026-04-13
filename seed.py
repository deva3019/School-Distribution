import os
from datetime import datetime
from pymongo import MongoClient
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

# Load environment variables (Make sure your .env file has MONGO_URI)
load_dotenv()

def seed_database():
    mongo_uri = os.environ.get("MONGO_URI")
    if not mongo_uri:
        print("❌ Error: MONGO_URI not found in .env file.")
        return

    print("🔄 Connecting to MongoDB...")
    client = MongoClient(mongo_uri)
    db = client.school_distribution_db

    # 1. Clear existing data for a clean slate
    print("🧹 Clearing old database collections...")
    db.users.drop()
    db.inventory.drop()
    db.requests.drop()

    # 2. Create the Master Distributor Account
    print("👤 Creating Distributor Account...")
    distributor = {
        "username": "admin",
        "role": "distributor",
        "password_hash": generate_password_hash("admin123"), # Easy password for testing
        "needs_password_change": False
    }
    db.users.insert_one(distributor)

    # 3. Create Dummy School Accounts
    print("🏫 Creating 5 Dummy School Accounts...")
    schools_to_insert = []
    for i in range(1, 6):
        school_id = f"SCH100{i}"
        default_password = f"HM@{school_id}"
        
        schools_to_insert.append({
            "username": school_id,
            "school_name": f"Govt Higher Secondary School, Zone {i}",
            "role": "principal",
            "password_hash": generate_password_hash(default_password),
            "needs_password_change": True # Forces them to change it on first login
        })
    
    db.users.insert_many(schools_to_insert)

    # 4. Create Dummy Inventory
    print("📦 Stocking Government Inventory...")
    inventory_items = [
        {
            "item_name": "Class 10 Science Textbooks",
            "category": "Textbooks",
            "total_allocated": 5000,
            "remaining_balance": 5000,
            "added_date": datetime.now(),
            "status": "active"
        },
        {
            "item_name": "Lenovo Student Laptops",
            "category": "Electronics",
            "total_allocated": 250,
            "remaining_balance": 250,
            "added_date": datetime.now(),
            "status": "active"
        },
        {
            "item_name": "Winter Uniform Sets (All Sizes)",
            "category": "Uniforms",
            "total_allocated": 1500,
            "remaining_balance": 1500,
            "added_date": datetime.now(),
            "status": "active"
        }
    ]
    
    # Insert inventory and keep track of their generated IDs
    inserted_inventory = db.inventory.insert_many(inventory_items)
    inventory_ids = inserted_inventory.inserted_ids

    # 5. Create Dummy Requests (To populate the Distributor Dashboard)
    print("📥 Generating Dummy Requests from Schools...")
    
    # Fetch the first two schools we just created
    school_1 = db.users.find_one({"username": "SCH1001"})
    school_2 = db.users.find_one({"username": "SCH1002"})

    dummy_requests = [
        {
            "school_id": school_1["_id"],
            "item_id": inventory_ids[1], # Requesting Laptops
            "requested_qty": 45,
            "status": "pending",
            "request_date": datetime.now()
        },
        {
            "school_id": school_2["_id"],
            "item_id": inventory_ids[0], # Requesting Textbooks
            "requested_qty": 120,
            "status": "pending",
            "request_date": datetime.now()
        }
    ]
    db.requests.insert_many(dummy_requests)

    print("\n✅ Database Seeded Successfully!")
    print("=========================================")
    print("🧪 TEST CREDENTIALS:")
    print("-----------------------------------------")
    print("Distributor Login:")
    print("Username : admin")
    print("Password : admin123")
    print("-----------------------------------------")
    print("School / Principal Login (Test forcing password change):")
    print("Username : SCH1001")
    print("Password : HM@SCH1001")
    print("=========================================")

if __name__ == "__main__":
    seed_database()