from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
CORS(app)

# Database config
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'data', 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# DB setup
db = SQLAlchemy()
db.init_app(app)

# Register route blueprints
from routes.project_routes import project_bp
from routes.coding_routes import coding_bp

app.register_blueprint(project_bp)
app.register_blueprint(coding_bp)

if __name__ == "__main__":
    app.run(debug=True)
