from flask import Blueprint, jsonify
from src.models.models import get_pedidos_collection
from src.routes.auth import require_auth # Protegendo a rota

cargo_bp = Blueprint("cargo", __name__)

@cargo_bp.route("/", methods=["GET"])
@require_auth # Garante que apenas usuários logados possam ver os pedidos
def get_pedidos_para_cargo():
    """
    Retorna todos os pedidos ativos (não excluídos) para a tela de otimização de carga.
    """
    # Retorna pedidos que não foram marcados como excluídos por nenhum usuário
    query = {"deleted_by_users": {"$size": 0}}
    
    pedidos = list(get_pedidos_collection().find(query).sort("Data", -1))
    
    for pedido in pedidos:
        pedido["_id"] = str(pedido["_id"])
        
    return jsonify(pedidos)