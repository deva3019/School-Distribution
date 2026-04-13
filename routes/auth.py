from flask import Blueprint, redirect, render_template, request, session, jsonify, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from database import get_db
from bson.objectid import ObjectId

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET'])
def login_page():
    # If already logged in, redirect away from login page
    if 'user_id' in session and not session.get('needs_password_change'):
        return redirect_user(session.get('role'))
    return render_template('login.html')

@auth_bp.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    db = get_db()
    user = db.users.find_one({'username': username})

    if user and check_password_hash(user['password_hash'], password):
        session['user_id'] = str(user['_id'])
        session['role'] = user['role']
        session['username'] = user['username']
        
        # Check if they need to change their password
        if user.get('needs_password_change'):
            session['needs_password_change'] = True
            # Tell the frontend to switch to the password change UI
            return jsonify({"status": "require_password_change", "message": "Security update required."})
        
        session['needs_password_change'] = False
        
        # Tell the frontend to redirect to the dashboard
        return jsonify({
            "status": "success", 
            "redirect_url": get_dashboard_url(user['role'])
        })
        
    return jsonify({"status": "error", "message": "Invalid School ID or Password."}), 401

@auth_bp.route('/api/change-password', methods=['POST'])
def api_change_password():
    if 'user_id' not in session or not session.get('needs_password_change'):
        return jsonify({"status": "error", "message": "Unauthorized action."}), 403

    data = request.get_json()
    new_password = data.get('new_password')
    
    if len(new_password) < 6:
        return jsonify({"status": "error", "message": "Password must be at least 6 characters."}), 400

    db = get_db()
    hashed_password = generate_password_hash(new_password)
    
    db.users.update_one(
        {'_id': ObjectId(session['user_id'])},
        {'$set': {'password_hash': hashed_password, 'needs_password_change': False}}
    )
    
    session['needs_password_change'] = False
    
    return jsonify({
        "status": "success", 
        "message": "Password updated successfully!",
        "redirect_url": get_dashboard_url(session.get('role'))
    })

# --- Helper Functions ---
def get_dashboard_url(role):
    if role == 'distributor':
        return url_for('distributor.dashboard')
    return url_for('principal.dashboard')

def redirect_user(role):
    from flask import redirect
    return redirect(get_dashboard_url(role))

# Add or update this in routes/auth.py
@auth_bp.route('/logout')
def logout():
    session.clear() # Destroys the login token
    return redirect('/') # Redirects to the landing page