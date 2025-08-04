from flask import Blueprint, jsonify, request
from src.models.models import get_items_collection
from src.models.models import get_fotos_collection
from src.models.models import get_items_collection, get_oracle_engine
from sqlalchemy import text
import math
import re

items_bp = Blueprint("items", __name__)

def clean_nan_values(obj):
    """Remove valores NaN e None de um objeto"""
    if isinstance(obj, dict):
        return {k: clean_nan_values(v) for k, v in obj.items() if v is not None and not (isinstance(v, float) and math.isnan(v))}
    elif isinstance(obj, list):
        return [clean_nan_values(item) for item in obj]
    elif isinstance(obj, float) and math.isnan(obj):
        return 0
    return obj

@items_bp.route("/", methods=["GET"])
def get_all_items():
    # --- INÍCIO DA LÓGICA ORACLE CORRIGIDA ---
    stock_map = {}
    engine = get_oracle_engine()
    if engine:
        # Usar 'with' garante que a conexão seja fechada automaticamente
        try:
            with engine.connect() as connection:
                sql_query = text("""
                    SELECT CODPROD, GREATEST(ESTOQUE - RESERVADO, 0) AS DISPONIVEL
                    FROM TGFEST
                    WHERE CODLOCAL = 401
                """)
                result = connection.execute(sql_query)
                for row in result:
                    # O resultado de 'row' é uma tupla, então acessamos por índice
                    stock_map[row[0]] = row[1]
        except Exception as e:
            print(f"Erro ao executar a query no Oracle com SQLAlchemy: {e}")
    # --- FIM DA LÓGICA ORACLE ---

    # Parâmetros de paginação
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    
    # Parâmetros de filtros
    category_filter = request.args.get('category', '')
    min_price = request.args.get('min_price', '')
    max_price = request.args.get('max_price', '')
    search = request.args.get('search', '')
    query = {}
    if category_filter:
        query['Category'] = {'$regex': re.escape(category_filter), '$options': 'i'}
    price_query = {}
    if min_price:
        try: price_query['$gte'] = float(min_price)
        except ValueError: pass
    if max_price:
        try: price_query['$lte'] = float(max_price)
        except ValueError: pass
    if price_query:
        query['Sale Price'] = price_query
    if search:
        or_conditions = []
        try:
            or_conditions.append({'Item ID': int(search)})
        except ValueError:
            pass
        search_words = search.split()
        and_conditions = []
        for word in search_words:
            and_conditions.append({'Name': {'$regex': re.escape(word), '$options': 'i'}})
        or_conditions.append({'$and': and_conditions})
        or_conditions.append({'Category': {'$regex': re.escape(search), '$options': 'i'}})
        query['$or'] = or_conditions

    items_collection = get_items_collection()
    total_items = items_collection.count_documents(query)
    skip = (page - 1) * per_page
    total_pages = math.ceil(total_items / per_page) if per_page > 0 else 0
    
    user_id = None
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        from src.routes.auth import verify_jwt_token
        token = auth_header[7:]
        payload = verify_jwt_token(token)
        if payload:
            user_id = payload.get('user_id')

    pipeline = [
        {'$match': query}, {'$skip': skip}, {'$limit': per_page},
        {'$addFields': {'original_price': '$Sale Price'}},
    ]
    if user_id:
        pipeline.extend([
            {'$lookup': {'from': 'client_prices', 'let': {'itemId': '$Item ID'}, 'pipeline': [{'$match': {'$expr': {'$and': [{'$eq': ['$item_id', '$$itemId']}, {'$eq': ['$client_id', user_id]}]}}}], 'as': 'special_price_info'}},
            {'$addFields': {'special_price_obj': {'$arrayElemAt': ['$special_price_info', 0]}}},
            {'$addFields': {'Sale Price': {'$ifNull': ['$special_price_obj.special_price', '$Sale Price']}, 'has_special_price': {'$cond': {'if': {'$gt': [{'$size': '$special_price_info'}, 0]}, 'then': True, 'else': False}}}}
        ])
    pipeline.extend([
        {'$lookup': {'from': 'fotos', 'localField': 'Item ID', 'foreignField': 'Item ID', 'as': 'photos'}},
        {'$addFields': {'main_photo_url': {'$let': {'vars': {'primaryPhoto': {'$arrayElemAt': [{'$filter': {'input': '$photos', 'as': 'p', 'cond': {'$eq': ['$$p.Is Primary', True]}}}, 0]}, 'firstPhoto': {'$arrayElemAt': ['$photos', 0]}}, 'in': {'$ifNull': ['$$primaryPhoto.Photo URL', '$$firstPhoto.Photo URL']}}}}},
        {'$project': {'photos': 0, 'special_price_info': 0, 'special_price_obj': 0}}
    ])
    
    items = list(items_collection.aggregate(pipeline))
    
    for item in items:
        item["_id"] = str(item["_id"])
        item['available_stock'] = stock_map.get(item.get('Item ID'), 0)

    items = clean_nan_values(items)
    
    return jsonify({
        'items': items,
        'pagination': {
            'page': page, 'per_page': per_page, 'total_items': total_items,
            'total_pages': total_pages, 'has_prev': page > 1, 'has_next': page < total_pages
        }
    })

@items_bp.route("/categories", methods=["GET"])
def get_categories():
    """Retorna todas as categorias únicas"""
    categories = get_items_collection().distinct('Category')
    categories = [cat for cat in categories if cat is not None and cat != '']
    return jsonify(sorted(categories))


@items_bp.route("/<item_id>", methods=["GET"])
def get_item_by_id(item_id):
    item = get_items_collection().find_one({"Item ID": int(item_id)})
    if item:
        item["_id"] = str(item["_id"])
        item = clean_nan_values(item)
        return jsonify(item)
    return jsonify({"message": "Item not found"}), 404

@items_bp.route("/<int:item_id>/photos", methods=["GET"])
def get_item_photos(item_id):
    """ Retorna todas as fotos de um produto específico, garantindo que a URL exista. """
    try:
        fotos_collection = get_fotos_collection()
        
        # NOVA QUERY: Garante que o campo 'Photo URL' existe e não está vazio.
        query = {
            "Item ID": item_id,
            "Photo URL": {
                "$exists": True,  # O campo deve existir
                "$ne": ""         # O campo não pode ser uma string vazia
            }
        }
        
        # Executa a busca com a query aprimorada
        photos = list(fotos_collection.find(query).sort("Is Primary", -1))
        
        # Converte ObjectId para string para ser compatível com JSON
        for photo in photos:
            photo['_id'] = str(photo['_id'])
        
        return jsonify(photos)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
