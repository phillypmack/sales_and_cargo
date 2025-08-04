from flask import Blueprint, jsonify, request, current_app, send_from_directory
import math

cargo_optimizer_bp = Blueprint("cargo_optimizer", __name__)

# Rota principal para servir a página HTML
@cargo_optimizer_bp.route("/")
def cargo_optimizer_page():
    """Serve a página estática do otimizador de cargas."""
    return send_from_directory(current_app.static_folder, 'cargo_optimizer.html')

# Nova rota de API para fornecer os tipos de container
@cargo_optimizer_bp.route("/api/containers", methods=["GET"])
def get_container_types():
    """Retorna a lista de tipos de container padronizados."""
    container_types = [
        { "name": "Custom", "length": 12.0, "width": 2.3, "height": 2.3, "maxPayloadKg": 999999 },
        { "name": "20' Dry Standard", "length": 5.90, "width": 2.35, "height": 2.39, "maxPayloadKg": 28280 },
        { "name": "40' Dry Standard", "length": 12.03, "width": 2.35, "height": 2.39, "maxPayloadKg": 26680 },
        { "name": "40' High Cube (HC)", "length": 12.03, "width": 2.35, "height": 2.69, "maxPayloadKg": 28500 },
        { "name": "45' High Cube (HC)", "length": 13.56, "width": 2.35, "height": 2.69, "maxPayloadKg": 27700 },
        { "name": "20' Reefer (Refrigerado)", "length": 5.44, "width": 2.29, "height": 2.27, "maxPayloadKg": 27480 },
        { "name": "40' Reefer (Refrigerado)", "length": 11.56, "width": 2.29, "height": 2.25, "maxPayloadKg": 25980 },
        { "name": "20' Open Top", "length": 5.89, "width": 2.35, "height": 2.35, "maxPayloadKg": 28080 },
    ]
    return jsonify(container_types)

# A rota de otimização existente permanece a mesma
@cargo_optimizer_bp.route("/api/optimize", methods=["POST"])
def optimize_cargo_api():
    """API endpoint para otimização de cargas"""
    try:
        data = request.json
        order_id = data.get('order_id')
        container_dimensions = data.get('container_dimensions', {})
        
        # Busca o pedido
        pedidos_collection = get_pedidos_collection()
        order = pedidos_collection.find_one({"Order": int(order_id)})
        
        if not order:
            return jsonify({"error": "Pedido não encontrado"}), 404
        
        # Algoritmo simples de otimização
        container_width = container_dimensions.get('width', 120)
        container_height = container_dimensions.get('height', 100)
        container_depth = container_dimensions.get('depth', 200)
        
        container_volume = (container_width * container_height * container_depth) / 1000000  # m³
        
        total_items = order.get('Total Itens', 0)
        total_weight = order.get('Total wheight Kg', 0)
        
        # Estimativa de volume baseada no peso
        estimated_item_volume = total_weight * 0.001  # 1kg ≈ 0.001m³
        
        space_efficiency = min((estimated_item_volume / container_volume) * 100, 100)
        items_fitted = int(total_items * (space_efficiency / 100))
        
        optimization_result = {
            "order_id": order_id,
            "container_dimensions": {
                "width": container_width,
                "height": container_height,
                "depth": container_depth,
                "volume": container_volume
            },
            "optimization": {
                "space_efficiency": round(space_efficiency, 2),
                "items_fitted": items_fitted,
                "total_items": total_items,
                "volume_used": round(estimated_item_volume, 3),
                "weight_total": total_weight
            },
            "recommendations": [
                f"Eficiência de espaço: {space_efficiency:.1f}%",
                f"{items_fitted} de {total_items} itens acomodados",
                "Container otimizado para transporte seguro"
            ]
        }
        
        return jsonify(optimization_result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@cargo_optimizer_bp.route("/api/containers", methods=["GET"])
def get_container_templates():
    """Retorna templates de containers disponíveis"""
    templates = [
        {
            "name": "Container Pequeno",
            "dimensions": {"width": 120, "height": 100, "depth": 200},
            "volume": 2.4,
            "description": "Ideal para pedidos pequenos e médios"
        },
        {
            "name": "Container Médio",
            "dimensions": {"width": 150, "height": 120, "depth": 250},
            "volume": 4.5,
            "description": "Recomendado para pedidos de volume médio"
        },
        {
            "name": "Container Grande",
            "dimensions": {"width": 200, "height": 150, "depth": 300},
            "volume": 9.0,
            "description": "Para pedidos de grande volume"
        }
    ]
    
    return jsonify(templates)

