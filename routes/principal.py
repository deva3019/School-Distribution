from flask import Blueprint, render_template, request, session, jsonify, redirect, url_for
from database import get_db
from bson.objectid import ObjectId
from datetime import datetime

principal_bp = Blueprint('principal', __name__)

def check_principal():
    if 'user_id' not in session or session.get('role') != 'principal':
        return False
    return True

@principal_bp.route('/dashboard')
def dashboard():
    if not check_principal():
        return redirect(url_for('auth.login_page'))
    return render_template('principal/dashboard.html', school_name=session.get('username'))

@principal_bp.route('/api/inventory', methods=['GET'])
def get_available_inventory():
    if not check_principal(): return jsonify({"error": "Unauthorized"}), 403
    db = get_db()
    
    items = list(db.inventory.find({"remaining_balance": {"$gt": 0}}))
    clean_items = []
    for item in items:
        clean_items.append({
            "item_id": str(item['_id']),
            "item_name": item['item_name'],
            "category": item['category'],
            "available": item['remaining_balance']
        })
    return jsonify({"status": "success", "data": clean_items})

# --- UPGRADED: Batch Submit Request API ---
@principal_bp.route('/api/request', methods=['POST'])
def submit_request():
    if not check_principal(): return jsonify({"error": "Unauthorized"}), 403
    db = get_db()
    data = request.get_json()
    
    # Expecting an array of items: {"items": [{"item_id": "...", "quantity": 50}, ...]}
    items_to_request = data.get('items', [])
    
    if not items_to_request:
        return jsonify({"status": "error", "message": "No items selected for request."})

    new_requests = []
    school_id_obj = ObjectId(session['user_id'])
    
    # Process each item in the batch
    for req_item in items_to_request:
        item_id = req_item.get('item_id')
        requested_qty = int(req_item.get('quantity', 0))
        
        if requested_qty > 0:
            new_requests.append({
                "school_id": school_id_obj,
                "item_id": ObjectId(item_id),
                "requested_qty": requested_qty,
                "status": "pending",
                "request_date": datetime.now()
            })
            
    # Insert all requests at once (Lightning Fast)
    if new_requests:
        db.requests.insert_many(new_requests)
        return jsonify({
            "status": "success", 
            "message": f"Successfully submitted {len(new_requests)} item requests!"
        })
        
    return jsonify({"status": "error", "message": "Invalid quantities provided."})

@principal_bp.route('/api/my-requests', methods=['GET'])
def get_my_requests():
    if not check_principal(): return jsonify({"error": "Unauthorized"}), 403
    db = get_db()
    
    pipeline = [
        {"$match": {"school_id": ObjectId(session['user_id'])}},
        {"$lookup": {
            "from": "inventory",
            "localField": "item_id",
            "foreignField": "_id",
            "as": "item_details"
        }},
        {"$sort": {"request_date": -1}}
    ]
    
    requests = list(db.requests.aggregate(pipeline))
    clean_requests = []
    for req in requests:
        clean_requests.append({
            "request_id": str(req['_id']),
            "item_name": req['item_details'][0]['item_name'] if req['item_details'] else "Unknown Item",
            "requested_qty": req['requested_qty'],
            "fulfilled_qty": req.get('fulfilled_qty', 0),
            "status": req['status'],
            "date": req['request_date'].strftime("%B %d, %Y")
        })
        
    return jsonify({"status": "success", "data": clean_requests})