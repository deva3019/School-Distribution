import os
from flask import Flask, render_template
from dotenv import load_dotenv
from database import get_db

# Load environment variables immediately
load_dotenv()

def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "fallback_dev_key")

    # Warm up the database connection pool as soon as the server starts
    with app.app_context():
        get_db()

    # -------------------------------------------------------------
    # Blueprint Registration 
    # -------------------------------------------------------------
    
    from routes.auth import auth_bp
    from routes.distributor import dist_bp
    from routes.principal import principal_bp

    # Registering the routes we just built
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dist_bp, url_prefix='/distributor')
    app.register_blueprint(principal_bp, url_prefix='/principal')

    # -------------------------------------------------------------
    # Main Routes
    # -------------------------------------------------------------

    @app.route('/')
    def landing():
        # Serves the completely unique landing page
        return render_template('landing.html')

    return app
app = create_app()

if __name__ == '__main__':
        # Debug=True is great for local development. 
    # For production speed later, we will use a WSGI server like Waitress.
    app.run(debug=True, port=5000)