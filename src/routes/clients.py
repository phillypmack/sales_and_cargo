import os
from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename
from src.models.models import get_clients_collection
from datetime import datetime
from src.routes.auth import require_auth
from bson import ObjectId 

clients_bp = Blueprint("clients", __name__)

# Configure um local seguro para uploads
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'static', 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@clients_bp.route("/profile", methods=["GET"])
@require_auth
def get_client_profile():
    """Retorna os dados da empresa associados ao usuário logado."""
    user_id = request.current_user["user_id"]
    clients_collection = get_clients_collection()
    
    client_profile = clients_collection.find_one({"user_id": ObjectId(user_id)})
    
    if not client_profile:
        return jsonify({"error": "Perfil não encontrado."}), 404
        
    client_profile["_id"] = str(client_profile["_id"])
    return jsonify({"client": client_profile})

@clients_bp.route("/profile", methods=["POST"])
@require_auth
def update_client_profile():
    """Cria ou atualiza o perfil da empresa e sincroniza com o Sankhya."""
    user_id = request.current_user["user_id"]
    clients_collection = get_clients_collection()
    
    try:
        form_data = request.form
        client_data = {
            "user_id": ObjectId(user_id),
            "legal_name": form_data.get("legal_name"),
            "trade_name": form_data.get("trade_name"),
            "address": {
                "street": form_data.get("street"),
                "number": form_data.get("number"),
                "city": form_data.get("city"),
                "state_province": form_data.get("state_province"),
                "postal_code": form_data.get("postal_code"),
                "country": form_data.get("country"),
            },
            "contact": {
                "phone": form_data.get("phone"),
                "email": form_data.get("email"),
                "website": form_data.get("website"),
            },
            "fiscal_info": {
                "tax_id": form_data.get("tax_id"),
                "registration_number": form_data.get("registration_number"),
                "legal_representative": form_data.get("legal_representative"),
            },
            "last_updated": datetime.now().isoformat()
        }

        existing_profile = clients_collection.find_one({"user_id": ObjectId(user_id)})
        documents = existing_profile.get("documents", {}) if existing_profile else {}
        if existing_profile and existing_profile.get("sankhya_codparc"):
            client_data["sankhya_codparc"] = existing_profile.get("sankhya_codparc")

        files = request.files
        for key, file in files.items():
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                file.save(file_path)
                documents[key] = f"/static/uploads/{unique_filename}"
        
        client_data["documents"] = documents

        # Salva/Atualiza no MongoDB primeiro
        clients_collection.update_one(
            {"user_id": ObjectId(user_id)},
            {"$set": client_data},
            upsert=True
        )
        
        # Agora, tenta sincronizar com o Sankhya
        try:
            sankhya_result = sankhya_service.create_or_update_partner(client_data)
            if sankhya_result.get("success") and sankhya_result.get("codparc"):
                # Se bem-sucedido, salva o CODPARC de volta no MongoDB
                clients_collection.update_one(
                    {"user_id": ObjectId(user_id)},
                    {"$set": {"sankhya_codparc": sankhya_result["codparc"]}}
                )
                return jsonify({"message": "Perfil salvo e sincronizado com o ERP com sucesso!"})
            else:
                # O perfil foi salvo localmente, mas a sincronização falhou
                return jsonify({"message": f"Perfil salvo, mas falha ao sincronizar com o ERP: {sankhya_result.get('error')}"}), 202 # 202 Accepted
        except Exception as e:
            # O perfil foi salvo, mas a comunicação com o ERP falhou
            return jsonify({"message": f"Perfil salvo, mas erro de comunicação com o ERP: {str(e)}"}), 202

    except Exception as e:
        print(f"Erro ao atualizar perfil: {e}")
        return jsonify({"error": "Erro interno ao salvar o perfil."}), 500

@clients_bp.route("/register", methods=["POST"])
def register_client():
    try:
        # request.form é usado para dados de texto quando se usa FormData
        form_data = request.form
        
        client_data = {
            "legal_name": form_data.get("legal_name"),
            "trade_name": form_data.get("trade_name"),
            "address": {
                "street": form_data.get("address"),
                "city": form_data.get("city"),
                "state_province": form_data.get("state_province"),
                "postal_code": form_data.get("postal_code"),
                "country": form_data.get("country"),
            },
            "contact": {
                "phone": form_data.get("phone"),
                "email": form_data.get("email"),
                "website": form_data.get("website"),
            },
            "fiscal_info": {
                "tax_id": form_data.get("tax_id"),
                "registration_number": form_data.get("registration_number"),
                "legal_representative": form_data.get("legal_representative"),
            },
            "primary_contact": {
                "name": form_data.get("primary_contact_name"),
                "email": form_data.get("primary_contact_email"),
                "phone": form_data.get("primary_contact_phone"),
            },
            "documents": {},
            "status": "pending_review", # Status inicial
            "created_at": datetime.now().isoformat()
        }

        # Processamento dos arquivos
        files = request.files
        for key, file in files.items():
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Adiciona um timestamp para evitar nomes de arquivo duplicados
                unique_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                file.save(file_path)
                # Salva o caminho relativo para ser usado no frontend
                client_data["documents"][key] = f"/static/uploads/{unique_filename}"

        # Salva no MongoDB
        clients_collection = get_clients_collection()
        clients_collection.insert_one(client_data)

        return jsonify({"message": "Cadastro recebido com sucesso!"}), 201

    except Exception as e:
        print(f"Erro no registro do cliente: {e}")
        return jsonify({"error": "Ocorreu um erro interno ao processar o cadastro."}), 500