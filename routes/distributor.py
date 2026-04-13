from flask import Blueprint, render_template, request, session, jsonify, redirect, url_for
from database import get_db
from bson.objectid import ObjectId
from datetime import datetime

dist_bp = Blueprint('distributor', __name__)

# --- Authentication Middleware ---
def check_distributor():
    if 'user_id' not in session or session.get('role') != 'distributor':
        return False
    return True

# --- 1. Main Page Render ---
@dist_bp.route('/dashboard')
def dashboard():
    if not check_distributor():
        return redirect(url_for('auth.login_page'))
    # Renders the empty SPA shell. Data is loaded via JS for speed.
    return render_template('distributor/dashboard.html')

# --- 2. Analytics & Overview API ---
@dist_bp.route('/api/stats', methods=['GET'])
def get_stats():
    if not check_distributor(): return jsonify({"error": "Unauthorized"}), 403
    db = get_db()
    
    # Fast Aggregation for KPIs
    pipeline = [
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1}
        }}
    ]
    req_stats = list(db.requests.aggregate(pipeline))
    
    pending_count = next((item['count'] for item in req_stats if item['_id'] == 'pending'), 0)
    approved_count = next((item['count'] for item in req_stats if item['_id'] == 'approved'), 0)
    
    total_schools = db.users.count_documents({"role": "principal"})
    
    return jsonify({
        "status": "success",
        "data": {
            "pending_requests": pending_count,
            "approved_requests": approved_count,
            "total_schools": total_schools
        }
    })

# --- 3. Inventory Management API ---
@dist_bp.route('/api/inventory', methods=['GET', 'POST'])
def manage_inventory():
    if not check_distributor(): return jsonify({"error": "Unauthorized"}), 403
    db = get_db()

    if request.method == 'GET':
        # Fetch all inventory items
        items = list(db.inventory.find({}))
        # Convert ObjectId to string for JSON serialization
        for item in items:
            item['_id'] = str(item['_id'])
        return jsonify({"status": "success", "data": items})

    if request.method == 'POST':
        # Add new item from Government
        data = request.get_json()
        new_item = {
            "item_name": data.get('item_name'),
            "category": data.get('category'),
            "total_allocated": int(data.get('quantity')),
            "remaining_balance": int(data.get('quantity')),
            "added_date": datetime.now(),
            "status": "active"
        }
        db.inventory.insert_one(new_item)
        return jsonify({"status": "success", "message": "Item added to inventory successfully."})

# --- 4. Request Decision Center API ---
@dist_bp.route('/api/requests', methods=['GET'])
def get_requests():
    if not check_distributor(): return jsonify({"error": "Unauthorized"}), 403
    db = get_db()
    
    # Join requests with inventory and school names
    requests = list(db.requests.aggregate([
        {"$match": {"status": "pending"}},
        {"$lookup": {
            "from": "inventory",
            "localField": "item_id",
            "foreignField": "_id",
            "as": "item_details"
        }},
        {"$lookup": {
            "from": "users",
            "localField": "school_id",
            "foreignField": "_id",
            "as": "school_details"
        }}
    ]))
    
    # Format data for frontend
    clean_requests = []
    for req in requests:
        clean_requests.append({
            "request_id": str(req['_id']),
            "school_name": req['school_details'][0]['school_name'] if req['school_details'] else "Unknown",
            "item_name": req['item_details'][0]['item_name'] if req['item_details'] else "Unknown",
            "requested_qty": req['requested_qty'],
            "date": req['request_date'].strftime("%Y-%m-%d") if 'request_date' in req else "N/A",
            "stock_available": req['item_details'][0]['remaining_balance'] if req['item_details'] else 0
        })
        
    return jsonify({"status": "success", "data": clean_requests})

@dist_bp.route('/api/requests/action', methods=['POST'])
def action_request():
    if not check_distributor(): return jsonify({"error": "Unauthorized"}), 403
    db = get_db()
    data = request.get_json()
    
    req_id = ObjectId(data.get('request_id'))
    action = data.get('action') # 'approve', 'reject', 'partial'
    approved_qty = int(data.get('approved_qty', 0))
    
    request_doc = db.requests.find_one({"_id": req_id})
    if not request_doc: return jsonify({"error": "Request not found"}), 404
    
    if action in ['approve', 'partial']:
        # Check stock again to prevent race conditions
        item = db.inventory.find_one({"_id": request_doc['item_id']})
        if item['remaining_balance'] < approved_qty:
            return jsonify({"status": "error", "message": "Insufficient stock for this approval."})
            
        # Deduct stock and update request
        db.inventory.update_one(
            {"_id": item['_id']},
            {"$inc": {"remaining_balance": -approved_qty}}
        )
        db.requests.update_one(
            {"_id": req_id},
            {"$set": {"status": "approved", "fulfilled_qty": approved_qty, "action_date": datetime.now()}}
        )
        return jsonify({"status": "success", "message": f"Successfully allocated {approved_qty} units."})

    elif action == 'reject':
        db.requests.update_one(
            {"_id": req_id},
            {"$set": {"status": "rejected", "reject_reason": data.get('reason', 'N/A'), "action_date": datetime.now()}}
        )
        return jsonify({"status": "success", "message": "Request rejected."})

# --- 5. School 1-Click Password Reset API ---
@dist_bp.route('/api/schools', methods=['GET'])
def get_schools():
    if not check_distributor(): return jsonify({"error": "Unauthorized"}), 403
    db = get_db()
    schools = list(db.users.find({"role": "principal"}, {"password_hash": 0}))
    for s in schools: s['_id'] = str(s['_id'])
    return jsonify({"status": "success", "data": schools})

@dist_bp.route('/api/schools/reset-password', methods=['POST'])
def reset_school_password():
    if not check_distributor(): return jsonify({"error": "Unauthorized"}), 403
    db = get_db()
    data = request.get_json()
    school_id = data.get('school_id')
    
    from werkzeug.security import generate_password_hash
    user = db.users.find_one({"_id": ObjectId(school_id)})
    if not user: return jsonify({"error": "School not found"}), 404
    
    # Generate default password (e.g., HM@SCH1045)
    default_pass = f"HM@{user['username']}"
    hashed_pass = generate_password_hash(default_pass)
    
    db.users.update_one(
        {"_id": ObjectId(school_id)},
        {"$set": {"password_hash": hashed_pass, "needs_password_change": True}}
    )
    
    return jsonify({
        "status": "success", 
        "message": f"Password reset to {default_pass}. School must change it on next login."
    })
