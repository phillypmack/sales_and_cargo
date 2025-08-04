from flask import Blueprint, jsonify, request, session
from werkzeug.security import generate_password_hash, check_password_hash
from src.models.models import get_users_collection
from datetime import datetime, timedelta
import jwt
import os
from functools import wraps

auth_bp = Blueprint("auth", __name__)

# Configurações JWT
JWT_SECRET = os.environ.get('JWT_SECRET', 'vasap_secret_key_2025')
JWT_EXPIRATION_HOURS = 24

def create_jwt_token(user_data):
    """Cria um token JWT para o usuário"""
    payload = {
        'user_id': str(user_data['_id']),
        'email': user_data['email'],
        'is_admin': user_data.get('is_admin', False),
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def verify_jwt_token(token):
    """Verifica e decodifica um token JWT"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def require_auth(f):
    """Decorator para rotas que requerem autenticação"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token de acesso requerido'}), 401
        
        if token.startswith('Bearer '):
            token = token[7:]
        
        payload = verify_jwt_token(token)
        if not payload:
            return jsonify({'error': 'Token inválido ou expirado'}), 401
        
        request.current_user = payload
        return f(*args, **kwargs)
    
    return decorated_function

def require_admin(f):
    """Decorator para rotas que requerem privilégios de administrador"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(request, 'current_user') or not request.current_user.get('is_admin'):
            return jsonify({'error': 'Privilégios de administrador requeridos'}), 403
        return f(*args, **kwargs)
    
    return decorated_function

@auth_bp.route("/register", methods=["POST"])
def register():
    """Registro de novo usuário"""
    try:
        data = request.json
        email = data.get('email', '').lower().strip()
        password = data.get('password', '')
        name = data.get('name', '').strip()
        
        # Validações
        if not email or not password or not name:
            return jsonify({'error': 'Email, senha e nome são obrigatórios'}), 400
        
        if len(password) < 6:
            return jsonify({'error': 'A senha deve ter pelo menos 6 caracteres'}), 400
        
        # Verifica se o usuário já existe
        users_collection = get_users_collection()
        existing_user = users_collection.find_one({'email': email})
        
        if existing_user:
            return jsonify({'error': 'Email já cadastrado'}), 409
        
        # Cria o novo usuário
        password_hash = generate_password_hash(password)
        
        # Define se é admin baseado no email (para demonstração)
        admin_emails = ['admin@vasap.com', 'feliperohneltrds@gmail.com']
        is_admin = email in admin_emails
        
        new_user = {
            'email': email,
            'password_hash': password_hash,
            'name': name,
            'is_admin': is_admin,
            'created_at': datetime.utcnow(),
            'last_login': None
        }
        
        result = users_collection.insert_one(new_user)
        new_user['_id'] = result.inserted_id
        
        # Cria token JWT
        token = create_jwt_token(new_user)
        
        return jsonify({
            'message': 'Usuário registrado com sucesso',
            'token': token,
            'user': {
                'id': str(new_user['_id']),
                'email': email,
                'name': name,
                'is_admin': is_admin
            }
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route("/login", methods=["POST"])
def login():
    """Login de usuário"""
    try:
        data = request.json
        email = data.get('email', '').lower().strip()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'error': 'Email e senha são obrigatórios'}), 400
        
        # Busca o usuário
        users_collection = get_users_collection()
        user = users_collection.find_one({'email': email})
        
        if not user or not check_password_hash(user['password_hash'], password):
            return jsonify({'error': 'Email ou senha inválidos'}), 401
        
        # Atualiza último login
        users_collection.update_one(
            {'_id': user['_id']},
            {'$set': {'last_login': datetime.utcnow()}}
        )
        
        # Cria token JWT
        token = create_jwt_token(user)
        
        return jsonify({
            'message': 'Login realizado com sucesso',
            'token': token,
            'user': {
                'id': str(user['_id']),
                'email': user['email'],
                'name': user['name'],
                'is_admin': user.get('is_admin', False)
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route("/verify", methods=["GET"])
@require_auth
def verify_token():
    """Verifica se o token é válido"""
    return jsonify({
        'valid': True,
        'user': {
            'id': request.current_user['user_id'],
            'email': request.current_user['email'],
            'is_admin': request.current_user.get('is_admin', False)
        }
    })

@auth_bp.route("/logout", methods=["POST"])
def logout():
    """Logout do usuário (apenas retorna sucesso, pois JWT é stateless)"""
    return jsonify({'message': 'Logout realizado com sucesso'})

@auth_bp.route("/profile", methods=["GET"])
@require_auth
def get_profile():
    """Retorna o perfil do usuário logado"""
    try:
        users_collection = get_users_collection()
        user = users_collection.find_one({'_id': request.current_user['user_id']})
        
        if not user:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        return jsonify({
            'user': {
                'id': str(user['_id']),
                'email': user['email'],
                'name': user['name'],
                'is_admin': user.get('is_admin', False),
                'created_at': user.get('created_at'),
                'last_login': user.get('last_login')
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route("/change-password", methods=["POST"])
@require_auth
def change_password():
    """Altera a senha do usuário"""
    try:
        data = request.json
        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')
        
        if not current_password or not new_password:
            return jsonify({'error': 'Senha atual e nova senha são obrigatórias'}), 400
        
        if len(new_password) < 6:
            return jsonify({'error': 'A nova senha deve ter pelo menos 6 caracteres'}), 400
        
        # Busca o usuário
        users_collection = get_users_collection()
        user = users_collection.find_one({'_id': request.current_user['user_id']})
        
        if not user or not check_password_hash(user['password_hash'], current_password):
            return jsonify({'error': 'Senha atual incorreta'}), 401
        
        # Atualiza a senha
        new_password_hash = generate_password_hash(new_password)
        users_collection.update_one(
            {'_id': user['_id']},
            {'$set': {'password_hash': new_password_hash}}
        )
        
        return jsonify({'message': 'Senha alterada com sucesso'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

