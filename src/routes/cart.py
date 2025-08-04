from flask import Blueprint, jsonify, request
from src.models.models import get_cart_collection, get_items_collection
from datetime import datetime
import uuid
import math
from src.routes.auth import require_auth

cart_bp = Blueprint("cart", __name__)

def clean_nan_values(obj):
    """Remove valores NaN e None de um objeto"""
    if isinstance(obj, dict):
        return {k: clean_nan_values(v) for k, v in obj.items() if v is not None and not (isinstance(v, float) and math.isnan(v))}
    elif isinstance(obj, list):
        return [clean_nan_values(item) for item in obj]
    elif isinstance(obj, float) and math.isnan(obj):
        return 0
    return obj

def calculate_volume(item):
    """Calcula o volume em m³ baseado nas dimensões do produto"""
    try:
        height = float(item.get('Height', 0)) / 100  # cm para m
        width = float(item.get('Width', 0)) / 100    # cm para m
        length = float(item.get('Length', 0)) / 100  # cm para m
        return height * width * length
    except (ValueError, TypeError):
        return 0

@cart_bp.route("/", methods=["GET"])
@require_auth
def get_cart():
    user_id = request.current_user["user_id"]
    cart_items = list(get_cart_collection().find({"user_id": user_id}))
    for item in cart_items:
        item["_id"] = str(item["_id"])
    cart_items = clean_nan_values(cart_items)
    return jsonify(cart_items)

@cart_bp.route("/totals", methods=["GET"])
@require_auth
def get_cart_totals():
    """Retorna os totais do carrinho: valor, peso e cubagem"""
    user_id = request.current_user["user_id"]
    cart_items = list(get_cart_collection().find({"user_id": user_id}))
    
    total_value = 0
    total_weight = 0
    total_volume = 0
    total_items = len(cart_items)
    
    for cart_item in cart_items:
        # Busca informações completas do item
        item = get_items_collection().find_one({"Item ID": cart_item["Item ID"]})
        if item:
            amount = cart_item.get("Amount", 1)
            
            # Valor total
            price = float(item.get("Sale Price", 0))
            total_value += price * amount
            
            # Peso total
            weight = float(item.get("Weight", 0))
            total_weight += weight * amount
            
            # Volume total (cubagem)
            volume = calculate_volume(item)
            total_volume += volume * amount
    
    return jsonify({
        "total_items": total_items,
        "total_value": round(total_value, 2),
        "total_weight": round(total_weight, 2),
        "total_volume": round(total_volume, 6),  # m³ com 6 casas decimais
        "currency": "USD"
    })

@cart_bp.route("/clear", methods=["DELETE"])
@require_auth
def clear_cart():
    """Limpa todo o carrinho de um cliente"""
    user_id = request.current_user["user_id"]
    result = get_cart_collection().delete_many({"user_id": user_id})
    
    return jsonify({
        "message": f"Carrinho limpo com sucesso",
        "items_removed": result.deleted_count
    })

@cart_bp.route("/", methods=["POST"])
@require_auth
def add_to_cart():
    data = request.json
    user_id = request.current_user["user_id"]
    
    # Busca informações do item
    item = get_items_collection().find_one({"Item ID": data["item_id"]})
    if not item:
        return jsonify({"message": "Item not found"}), 404
    
    # Verifica se o item já existe no carrinho
    existing_item = get_cart_collection().find_one({
        "Item ID": data["item_id"],
        "user_id": user_id
    })
    
    if existing_item:
        # Atualiza a quantidade
        new_amount = existing_item["Amount"] + data.get("amount", 1)
        new_total_price = item["Sale Price"] * new_amount
        new_total_weight = (item.get("Weight", 0) * new_amount)
        
        get_cart_collection().update_one(
            {"_id": existing_item["_id"]},
            {"$set": {
                "Amount": new_amount,
                "Total price": new_total_price,
                "Total wheight Kg": new_total_weight,
                "DateTime": datetime.now().isoformat()
            }}
        )
        
        updated_item = get_cart_collection().find_one({"_id": existing_item["_id"]})
        updated_item["_id"] = str(updated_item["_id"])
        return jsonify(updated_item)
    else:
        # Cria novo item no carrinho
        amount = data.get("amount", 1)
        cart_item = {
            "Inventory ID": str(uuid.uuid4())[:8],
            "Item ID": data["item_id"],
            "Description": item.get("Description", ""),
            "Category": item.get("Category", ""),
            "Name": item.get("Name", ""),
            "Shape": item.get("Shape", "box"),
            
            # --- CAMPOS ADICIONADOS/CORRIGIDOS ---
            "Length": item.get("Length", 0),
            "Width": item.get("Width", 0),
            "Height": item.get("Height", 0),
            "Weight": item.get("Weight", 0), # Peso unitário
            # --- FIM DOS CAMPOS ADICIONADOS ---

            "DateTime": datetime.now().isoformat(),
            "Amount": amount,
            "Sale Price": item["Sale Price"],
            "Total price": item["Sale Price"] * amount,
            "Total weight Kg": item.get("Weight", 0) * amount, # Corrigido de "wheight"
            "Client": user_id,
            "user_id": user_id
        }
        
        get_cart_collection().insert_one(cart_item)
        cart_item["_id"] = str(cart_item["_id"])
        
        return jsonify(cart_item), 201

@cart_bp.route("/<inventory_id>", methods=["DELETE"])
@require_auth
def remove_from_cart(inventory_id):
    user_id = request.current_user["user_id"]
    result = get_cart_collection().delete_one({"Inventory ID": inventory_id, "user_id": user_id})
    if result.deleted_count:
        return jsonify({"message": "Item removed from cart"})
    return jsonify({"message": "Item not found in cart"}), 404

@cart_bp.route("/<inventory_id>", methods=["PUT"])
@require_auth
def update_cart_item(inventory_id):
    """Atualiza a quantidade de um item no carrinho"""
    data = request.json
    new_amount = data.get("amount", 1)
    user_id = request.current_user["user_id"]
    
    cart_item = get_cart_collection().find_one({"Inventory ID": inventory_id, "user_id": user_id})
    if not cart_item:
        return jsonify({"message": "Item not found in cart"}), 404
    
    # Busca informações do produto
    item = get_items_collection().find_one({"Item ID": cart_item["Item ID"]})
    if not item:
        return jsonify({"message": "Product not found"}), 404
    
    # Calcula novos totais
    new_total_price = item["Sale Price"] * new_amount
    new_total_weight = item.get("Weight", 0) * new_amount
    
    # Atualiza o item
    get_cart_collection().update_one(
        {"Inventory ID": inventory_id},
        {"$set": {
            "Amount": new_amount,
            "Total price": new_total_price,
            "Total wheight Kg": new_total_weight,
            "DateTime": datetime.now().isoformat()
        }}
    )
    
    updated_item = get_cart_collection().find_one({"Inventory ID": inventory_id})
    updated_item["_id"] = str(updated_item["_id"])
    return jsonify(updated_item)

@cart_bp.route("/place-order", methods=["POST"])
@require_auth
def place_order():
    user_id = request.current_user["user_id"]
    
    # Busca itens do carrinho para o cliente
    cart_items = list(get_cart_collection().find({"user_id": user_id}))
    
    if not cart_items:
        return jsonify({"message": "Cart is empty"}), 400
    
    # Limpa os _id do MongoDB dos itens do carrinho antes de salvá-los no pedido
    for item in cart_items:
        item.pop('_id', None)

    # Calcula totais usando a função de totais
    totals_response = get_cart_totals()
    totals = totals_response.get_json()
    
    # Cria o pedido
    from src.models.models import get_pedidos_collection
    order = {
        "Order": len(list(get_pedidos_collection().find({}))) + 1,
        "Data": datetime.now().isoformat(),
        "Total Itens": totals["total_items"],
        "Total price": totals["total_value"],
        "Total weight Kg": totals["total_weight"],
        "Total volume m3": totals["total_volume"],
        "Client": user_id,
        "user_id": user_id,
        "items": cart_items,  # <-- Copia os itens para dentro do pedido
        "deleted_by_users": [] # <-- Campo para soft delete
    }
    
    get_pedidos_collection().insert_one(order)
    
    # Limpa o carrinho
    get_cart_collection().delete_many({"user_id": user_id})
    
    order["_id"] = str(order["_id"])
    return jsonify(order), 201

