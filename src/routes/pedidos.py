from flask import Blueprint, jsonify, request
from src.models.models import get_pedidos_collection
from src.routes.auth import require_auth
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