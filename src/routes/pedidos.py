from flask import Blueprint, jsonify, request
from src.models.models import get_pedidos_collection
from src.routes.auth import require_auth
from src.services.sankhya_service import sankhya_service
from src.models.models import get_clients_collection, get_users_collection
from datetime import datetime
from bson import ObjectId

pedidos_bp = Blueprint("pedidos", __name__)

@pedidos_bp.route("/", methods=["GET"])
@require_auth
def get_all_pedidos():
    """ Retorna os pedidos do usuário que não foram 'excluídos' por ele. """
    user_id = request.current_user["user_id"]
    
    # Filtra pedidos que pertencem ao usuário E onde o user_id NÃO está no array 'deleted_by_users'
    query = {
        "user_id": user_id,
        "deleted_by_users": {"$ne": user_id}
    }
    pedidos = list(get_pedidos_collection().find(query).sort("Data", -1)) # Ordena por mais recente
    
    for pedido in pedidos:
        pedido["_id"] = str(pedido["_id"])
    return jsonify(pedidos)

@pedidos_bp.route("/<string:order_id>", methods=["GET"])
@require_auth
def get_pedido_by_id(order_id):
    """ Retorna os detalhes de um pedido específico. """
    user_id = request.current_user["user_id"]
    
    # Garante que o usuário só possa ver seus próprios pedidos
    pedido = get_pedidos_collection().find_one({
        "_id": ObjectId(order_id),
        "user_id": user_id
    })
    
    if pedido:
        pedido["_id"] = str(pedido["_id"])
        return jsonify(pedido)
    return jsonify({"message": "Pedido não encontrado"}), 404

@pedidos_bp.route("/<string:order_id>/delete", methods=["POST"])
@require_auth
def soft_delete_pedido(order_id):
    """ Adiciona o user_id ao array de exclusão do pedido (soft delete). """
    user_id = request.current_user["user_id"]
    
    result = get_pedidos_collection().update_one(
        {"_id": ObjectId(order_id), "user_id": user_id},
        {"$addToSet": {"deleted_by_users": user_id}}
    )
    
    if result.modified_count > 0:
        return jsonify({"message": "Pedido excluído com sucesso"})
    return jsonify({"message": "Pedido não encontrado ou já excluído"}), 404

@pedidos_bp.route("/<string:order_id>/formalize", methods=["POST"])
@require_auth
def formalize_order(order_id):
    """
    Verifica o perfil do cliente, busca um pedido, envia para o Sankhya e atualiza o status.
    """
    user_id = request.current_user["user_id"]
    
    # 1. Verifica se o cliente tem um perfil completo com CODPARC
    clients_collection = get_clients_collection()
    client_profile = clients_collection.find_one({"user_id": ObjectId(user_id)})
    
    if not client_profile or not client_profile.get("sankhya_codparc"):
        return jsonify({"error": "Cadastro da empresa incompleto. Por favor, preencha seu perfil antes de formalizar um pedido.", "action": "redirect_to_profile"}), 400

    # 2. Busca o pedido no banco de dados
    pedidos_collection = get_pedidos_collection()
    order = pedidos_collection.find_one({"_id": ObjectId(order_id), "user_id": user_id})
    
    if not order:
        return jsonify({"error": "Pedido não encontrado ou não pertence ao usuário."}), 404

    # 3. Adiciona o CODPARC aos dados do pedido para enviar ao serviço
    order["codparc"] = client_profile["sankhya_codparc"]

    try:
        # 4. Chama o serviço para enviar o pedido
        result = sankhya_service.send_order(order)

        # 5. Prepara o registro de auditoria
        audit_log = {
            "status": "success" if result.get("success") else "error",
            "timestamp": datetime.now().isoformat(),
            "response": result.get("response"),
            "error_message": result.get("error"),
            "nunota": result.get("nunota")
        }

        # 6. Atualiza o pedido no MongoDB com o resultado da integração
        pedidos_collection.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {"sankhya_integration": audit_log}}
        )

        if result.get("success"):
            return jsonify({"message": "Pedido formalizado e enviado para o ERP com sucesso!"})
        else:
            return jsonify({"error": f"Falha ao enviar para o ERP: {result.get('error')}"}), 500

    except Exception as e:
        error_log = {
            "status": "critical_error",
            "timestamp": datetime.now().isoformat(),
            "error_message": str(e)
        }
        pedidos_collection.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {"sankhya_integration": error_log}}
        )
        return jsonify({"error": f"Erro crítico na integração: {str(e)}"}), 500