import os
import sys
from dotenv import load_dotenv
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

load_dotenv()

from flask import Flask, send_from_directory
from flask_cors import CORS
from src.routes.items import items_bp
from src.routes.cart import cart_bp
from src.routes.pedidos import pedidos_bp
from src.routes.cargo import cargo_bp
from src.routes.clients import clients_bp
from src.routes.admin import admin_bp
from src.routes.cargo_optimizer import cargo_optimizer_bp
from src.routes.auth import auth_bp
from src.routes.auth import require_auth, require_admin



app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'
CORS(app)
app.register_blueprint(clients_bp, url_prefix='/api/clients')
app.register_blueprint(items_bp, url_prefix='/api/items')
app.register_blueprint(cart_bp, url_prefix='/api/cart')
app.register_blueprint(pedidos_bp, url_prefix='/api/pedidos')
app.register_blueprint(cargo_bp, url_prefix='/api/cargo')
app.register_blueprint(admin_bp, url_prefix='/api/admin')
app.register_blueprint(cargo_optimizer_bp, url_prefix='/cargo-optimizer')
app.register_blueprint(auth_bp, url_prefix='/api/auth')

@app.route('/profile')
def profile_page():
    """ Serve a página de perfil estática. """
    return send_from_directory(app.static_folder, 'profile.html')

@app.route('/register')
def register_page():
    """ Serve a página de cadastro estática. """
    return send_from_directory(app.static_folder, 'register.html')

@app.route('/admin')
def admin_page():
    """ Serve a página de administração estática. """
    return send_from_directory(app.static_folder, 'admin.html')

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)


