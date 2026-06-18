import os
import logging
from flask import Flask, render_template, redirect, url_for
from config import Config

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure necessary folders exist
    for folder in [app.config['UPLOAD_FOLDER'], app.config['PROCESSED_FOLDER'], app.config['CHUNKS_FOLDER']]:
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
            logger.info(f"Created directory: {folder}")

    # Register Blueprints
    from blueprints.upload.routes import upload_bp
    from blueprints.validation.routes import validation_bp
    from blueprints.cleaning.routes import cleaning_bp
    from blueprints.chunking.routes import chunking_bp

    app.register_blueprint(upload_bp)
    app.register_blueprint(validation_bp)
    app.register_blueprint(cleaning_bp)
    app.register_blueprint(chunking_bp)

    @app.route('/')
    def index():
        return render_template('home.html')

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('layout.html', error_msg="Page not found"), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('layout.html', error_msg="Internal server error occurred"), 500

    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
