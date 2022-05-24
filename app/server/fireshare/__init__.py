import os
import os.path
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_cors import CORS
from pathlib import Path

# init SQLAlchemy so we can use it later in our models
db = SQLAlchemy()

def create_app():
    app = Flask(__name__, static_url_path='', static_folder='build', template_folder='build')
    CORS(app, supports_credentials=True)

    app.config['SECRET_KEY'] = 'secret-key-goes-here'
    app.config['DATA_DIRECTORY'] = os.getenv('DATA_DIRECTORY')
    app.config['PROCESSED_DIRECTORY'] = os.getenv('PROCESSED_DIRECTORY')
    app.config['ADMIN_PASSWORD'] = os.getenv('ADMIN_PASSWORD')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///{data_directory}/db.sqlite'.format(data_directory=app.config['DATA_DIRECTORY'])

    processed_dir = Path(app.config['PROCESSED_DIRECTORY'])
    data_dir = Path(app.config['DATA_DIRECTORY'])
    if not processed_dir.is_dir():
        processed_dir.mkdir()
        print(f"Creating {str(processed_dir)}")
    video_dir = data_dir / "video_links"
    if not video_dir.is_dir():
        print(f"Creating {str(video_dir)}")
        video_dir.mkdir(parents=True)

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # blueprint for auth routes in our app
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    # blueprint for api routes
    from .api import api as api_blueprint
    app.register_blueprint(api_blueprint)

    # blueprint for non-auth parts of app
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    with app.app_context():
        db.create_all()
        return app