from flask import Blueprint, jsonify, request
from src.models.models import db, get_users_collection, get_items_collection, get_fotos_collection, get_pedidos_collection
import math
import pandas as pd
from io import StringIO
from bson import ObjectId
import requests
from src.routes.auth import require_auth, require_admin
from pymongo import UpdateOne
from datetime import datetime
from flask import send_file
from io import BytesIO # <-- LINHA ADICIONADA

admin_bp = Blueprint("admin", __name__)

def clean_nan_values(obj):
    """Remove valores NaN e None de um objeto"""
    if isinstance(obj, dict):
        return {k: clean_nan_values(v) for k, v in obj.items() if v is not None and not (isinstance(v, float) and math.isnan(v))}
    elif isinstance(obj, list):
        return [clean_nan_values(item) for item in obj]
    elif isinstance(obj, float) and math.isnan(obj):
        return 0
    return obj

@admin_bp.route("/items", methods=["GET"])
def get_admin_items():
    """Retorna todos os itens para administração"""
    items = list(get_items_collection().find({}))
    for item in items:
        item["_id"] = str(item["_id"])
    items = clean_nan_values(items)
    return jsonify(items)

@admin_bp.route('/photos/cleanup', methods=['POST'])
@require_auth
@require_admin
def cleanup_photos():
    """
    Verifica todas as fotos no banco de dados e remove aquelas com URLs inválidas ou inacessíveis.
    """
    try:
        fotos_collection = get_fotos_collection()
        all_photos = list(fotos_collection.find({}, {"_id": 1, "Photo URL": 1}))
        
        ids_to_delete = []
        
        for photo in all_photos:
            photo_url = photo.get("Photo URL")
            
            # Se a URL for nula, vazia ou não for uma string, marque para exclusão
            if not isinstance(photo_url, str) or not photo_url:
                ids_to_delete.append(photo["_id"])
                continue
            
            try:
                # Usa um método HEAD para ser mais rápido (não baixa o corpo da imagem)
                # Timeout de 5 segundos para evitar que a requisição trave
                response = requests.head(photo_url, timeout=5, allow_redirects=True)
                
                # Se o status não for de sucesso (ex: 404 Not Found, 500 Server Error), marque para exclusão
                if not response.ok:
                    ids_to_delete.append(photo["_id"])
                    
            except requests.RequestException:
                # Qualquer erro de rede (DNS, timeout, conexão recusada) significa que o link está quebrado
                ids_to_delete.append(photo["_id"])

        # Se houver IDs para deletar, execute uma única operação de exclusão em massa
        if ids_to_delete:
            result = fotos_collection.delete_many({"_id": {"$in": ids_to_delete}})
            return jsonify({
                "message": f"Limpeza concluída. {result.deleted_count} fotos inválidas foram removidas.",
                "deleted_count": result.deleted_count
            })
        
        return jsonify({
            "message": "Nenhuma foto inválida encontrada.",
            "deleted_count": 0
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route("/items/<item_id>", methods=["PUT"])
def update_item(item_id):
    """Atualiza um item específico"""
    data = request.json
    
    # Campos que podem ser atualizados
    update_fields = {}
    if 'Sale Price' in data:
        update_fields['Sale Price'] = float(data['Sale Price'])
    if 'Group Pile' in data:
        update_fields['Group Pile'] = int(data['Group Pile'])
    if 'Name' in data:
        update_fields['Name'] = data['Name']
    if 'Description' in data:
        update_fields['Description'] = data['Description']
    if 'Category' in data:
        update_fields['Category'] = data['Category']
    
    result = get_items_collection().update_one(
        {"Item ID": int(item_id)},
        {"$set": update_fields}
    )
    
    if result.modified_count:
        return jsonify({"message": "Item updated successfully"})
    return jsonify({"message": "Item not found or no changes made"}), 404

@admin_bp.route("/items/bulk-update", methods=["POST"])
def bulk_update_items():
    """Atualiza múltiplos itens em massa"""
    data = request.json
    update_type = data.get('type')  # 'price', 'stock', 'category'
    items = data.get('items', [])  # Lista de item_ids
    value = data.get('value')
    
    if not update_type or not items or value is None:
        return jsonify({"message": "Missing required fields"}), 400
    
    # Define o campo a ser atualizado
    field_mapping = {
        'price': 'Sale Price',
        'stock': 'Group Pile',
        'category': 'Category'
    }
    
    field = field_mapping.get(update_type)
    if not field:
        return jsonify({"message": "Invalid update type"}), 400
    
    # Converte o valor para o tipo correto
    if update_type in ['price', 'stock']:
        value = float(value) if update_type == 'price' else int(value)
    
    # Atualiza os itens
    result = get_items_collection().update_many(
        {"Item ID": {"$in": [int(item_id) for item_id in items]}},
        {"$set": {field: value}}
    )
    
    return jsonify({
        "message": f"Updated {result.modified_count} items",
        "modified_count": result.modified_count
    })

@admin_bp.route("/items/bulk-price-adjustment", methods=["POST"])
def bulk_price_adjustment():
    """Ajusta preços em massa por porcentagem ou valor fixo"""
    data = request.json
    adjustment_type = data.get('adjustment_type')  # 'percentage' ou 'fixed'
    adjustment_value = data.get('adjustment_value')
    apply_to_all = data.get('apply_to_all', True)
    
    if not adjustment_type or adjustment_value is None:
        return jsonify({"message": "Missing required fields"}), 400
    
    # Define o filtro
    filter_query = {}
    if not apply_to_all:
        items = data.get('items', [])
        if items:
            filter_query = {"Item ID": {"$in": [int(item_id) for item_id in items]}}
    
    # Busca os itens a serem atualizados
    items_to_update = list(get_items_collection().find(filter_query))
    
    updated_count = 0
    for item in items_to_update:
        current_price = item.get('Sale Price', 0)
        if isinstance(current_price, (int, float)) and current_price > 0:
            if adjustment_type == 'percentage':
                new_price = current_price * (1 + float(adjustment_value) / 100)
            else:  # fixed
                new_price = current_price + float(adjustment_value)
            
            # Garante que o preço não seja negativo
            new_price = max(0, new_price)
            
            get_items_collection().update_one(
                {"_id": item["_id"]},
                {"$set": {"Sale Price": round(new_price, 2)}}
            )
            updated_count += 1
    
    return jsonify({
        "message": f"Updated prices for {updated_count} items",
        "updated_count": updated_count
    })

@admin_bp.route("/stats", methods=["GET"])
def get_admin_stats():
    """Retorna estatísticas para o dashboard admin"""
    items_collection = get_items_collection()
    
    total_items = items_collection.count_documents({})
    
    # Itens com estoque baixo (menos de 5)
    low_stock = items_collection.count_documents({"Group Pile": {"$lt": 5}})
    
    # Itens sem estoque
    no_stock = items_collection.count_documents({"Group Pile": 0})
    
    # Valor total do inventário
    pipeline = [
        {"$match": {"Sale Price": {"$exists": True, "$ne": None}}},
        {"$group": {
            "_id": None,
            "total_value": {"$sum": {"$multiply": ["$Sale Price", "$Group Pile"]}}
        }}
    ]
    
    total_value_result = list(items_collection.aggregate(pipeline))
    total_inventory_value = total_value_result[0]["total_value"] if total_value_result else 0
    
    # Categorias mais populares
    categories_pipeline = [
        {"$group": {"_id": "$Category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]
    
    top_categories = list(items_collection.aggregate(categories_pipeline))
    
    return jsonify({
        "total_products": total_items,
        "low_stock_items": low_stock,
        "no_stock_items": no_stock,
        "total_inventory_value": round(total_inventory_value, 2),
        "top_categories": top_categories
    })

# Novas rotas para cadastro de produtos
@admin_bp.route('/products', methods=['POST'])
def create_product():
    """
    Cadastra um novo produto
    """
    try:
        data = request.get_json()
        items_collection = get_items_collection()
        
        # Gera um novo Item ID
        last_item = items_collection.find().sort("Item ID", -1).limit(1)
        last_item_list = list(last_item)
        new_item_id = (last_item_list[0]["Item ID"] + 1) if last_item_list else 1
        
        # Dados do novo produto
        new_product = {
            "Item ID": new_item_id,
            "Name": data.get('name', ''),
            "Category": data.get('category', ''),
            "Description": data.get('description', ''),
            "Sale Price": float(data.get('sale_price', 0)),
            "Group Pile": int(data.get('stock', 0)),
            "Weight": float(data.get('weight', 0)),
            "Height": float(data.get('height', 0)),
            "Width": float(data.get('width', 0)),
            "Length": float(data.get('length', 0)),
            "Shape": data.get('shape', 'box') # <-- LINHA ADICIONADA
        }
        
        result = items_collection.insert_one(new_product)
        
        return jsonify({
            'message': 'Produto cadastrado com sucesso',
            'item_id': new_item_id
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/products/bulk', methods=['POST'])
def bulk_create_products():
    """
    Cadastra produtos em massa via planilha CSV
    """
    try:
        data = request.get_json()
        csv_data = data.get('csv_data', '')
        
        if not csv_data:
            return jsonify({'error': 'Dados CSV não fornecidos'}), 400
        
        # Lê os dados CSV
        df = pd.read_csv(StringIO(csv_data))
        
        items_collection = get_items_collection()
        
        # Gera novos IDs para os produtos
        last_item = items_collection.find().sort("Item ID", -1).limit(1)
        last_item_list = list(last_item)
        start_id = (last_item_list[0]["Item ID"] + 1) if last_item_list else 1
        
        products_to_insert = []
        
        for index, row in df.iterrows():
            product = {
                "Item ID": start_id + index,
                "Name": str(row.get('Name', '')),
                "Category": str(row.get('Category', '')),
                "Description": str(row.get('Description', '')),
                "Sale Price": float(row.get('Sale Price', 0)),
                "Group Pile": int(row.get('Stock', 0)),
                "Weight": float(row.get('Weight', 0)),
                "Height": float(row.get('Height', 0)),
                "Width": float(row.get('Width', 0)),
                "Length": float(row.get('Length', 0))
            }
            products_to_insert.append(product)
        
        if products_to_insert:
            result = items_collection.insert_many(products_to_insert)
            return jsonify({
                'message': f'{len(products_to_insert)} produtos cadastrados com sucesso',
                'inserted_count': len(result.inserted_ids)
            })
        else:
            return jsonify({'error': 'Nenhum produto válido encontrado'}), 400
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Rotas para cadastro de fotos
@admin_bp.route('/photos', methods=['POST'])
def create_photo():
    """
    Cadastra uma nova foto para um produto
    """
    try:
        data = request.get_json()
        fotos_collection = get_fotos_collection()
        
        # Gera um novo Photo ID
        last_photo = fotos_collection.find({"Photo ID": {"$exists": True}}).sort("Photo ID", -1).limit(1)
        last_photo_list = list(last_photo)
        new_photo_id = (last_photo_list[0]["Photo ID"] + 1) if last_photo_list else 1
        
        # Dados da nova foto
        new_photo = {
            "Photo ID": new_photo_id,
            "Item ID": int(data.get('item_id')),
            "Photo URL": data.get('photo_url', ''),
            "Description": data.get('description', ''),
            "Is Primary": data.get('is_primary', False)
        }
        
        # Se esta foto é marcada como principal, remove a marcação das outras fotos do mesmo produto
        if new_photo["Is Primary"]:
            fotos_collection.update_many(
                {"Item ID": new_photo["Item ID"]},
                {"$set": {"Is Primary": False}}
            )
        
        result = fotos_collection.insert_one(new_photo)
        
        return jsonify({
            'message': 'Foto cadastrada com sucesso',
            'photo_id': new_photo_id
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/photos/bulk', methods=['POST'])
def bulk_create_photos():
    """
    Cadastra fotos em massa via planilha CSV
    """
    try:
        data = request.get_json()
        csv_data = data.get('csv_data', '')
        
        if not csv_data:
            return jsonify({'error': 'Dados CSV não fornecidos'}), 400
        
        # Lê os dados CSV
        column_names = ['Item ID', 'Photo URL', 'Description', 'Is Primary']
        df = pd.read_csv(StringIO(csv_data), names=column_names, header=None)
        
        fotos_collection = get_fotos_collection()
        
        # Gera novos IDs para as fotos
        last_photo = fotos_collection.find().sort("Photo ID", -1).limit(1)
        last_photo_list = list(last_photo)
        start_id = (last_photo_list[0]["Photo ID"] + 1) if last_photo_list else 1
        
        photos_to_insert = []

        for index, row in df.iterrows():
            # Converte o valor de 'Is Primary' de forma segura
            is_primary_str = str(row.get('Is Primary', 'false')).strip().lower()
            is_primary = is_primary_str == 'true'

            photo = {
                "Photo ID": start_id + index,
                "Item ID": int(row.get('Item ID', 0)),
                "Photo URL": str(row.get('Photo URL', '')),
                "Description": str(row.get('Description', '')),
                "Is Primary": is_primary
            }
            photos_to_insert.append(photo)
        
        if photos_to_insert:
            result = fotos_collection.insert_many(photos_to_insert)
            return jsonify({
                'message': f'{len(photos_to_insert)} fotos cadastradas com sucesso',
                'inserted_count': len(result.inserted_ids)
            })
        else:
            return jsonify({'error': 'Nenhuma foto válida encontrada'}), 400
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/photos/<int:item_id>', methods=['GET'])
def get_item_photos(item_id):
    """
    Retorna todas as fotos de um produto
    """
    try:
        fotos_collection = get_fotos_collection()
        photos = list(fotos_collection.find({"Item ID": item_id}))
        
        # Converte ObjectId para string
        for photo in photos:
            photo['_id'] = str(photo['_id'])
        
        return jsonify(photos)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/photos/<string:photo_id>', methods=['DELETE'])
def delete_photo(photo_id):
    """
    Remove uma foto pelo seu _id
    """
    try:
        fotos_collection = get_fotos_collection()
        # Usa ObjectId para encontrar o documento pelo seu _id
        result = fotos_collection.delete_one({"_id": ObjectId(photo_id)})
        
        if result.deleted_count > 0:
            return jsonify({'message': 'Foto removida com sucesso'})
        else:
            return jsonify({'error': 'Foto não encontrada'}), 404
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/photos/<string:photo_id>', methods=['PUT'])
def update_photo(photo_id):
    """
    Atualiza uma foto usando seu _id.
    Se 'is_primary' for True, garante que nenhuma outra foto do mesmo produto seja primária.
    """
    try:
        data = request.get_json()
        fotos_collection = get_fotos_collection()
        
        update_data = {}
        if 'photo_url' in data:
            update_data['Photo URL'] = data['photo_url']
        if 'description' in data:
            update_data['Description'] = data['description']
        if 'is_primary' in data:
            update_data['Is Primary'] = data['is_primary']
            
            # Se esta foto está sendo marcada como principal...
            if data['is_primary']:
                # Primeiro, busca a foto para descobrir o Item ID dela
                photo = fotos_collection.find_one({"_id": ObjectId(photo_id)})
                if photo:
                    # Remove a marcação "Is Primary" de todas as outras fotos do mesmo produto
                    fotos_collection.update_many(
                        {"Item ID": photo["Item ID"], "_id": {"$ne": ObjectId(photo_id)}},
                        {"$set": {"Is Primary": False}}
                    )
        
        result = fotos_collection.update_one(
            {"_id": ObjectId(photo_id)},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            return jsonify({'message': 'Foto atualizada com sucesso'})
        else:
            # Pode acontecer se o usuário clicar em "Tornar Principal" em uma foto que já é a principal
            # ou se a foto não for encontrada. Retornar sucesso é aceitável aqui.
            return jsonify({'message': 'Nenhuma alteração necessária ou foto não encontrada'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/orders', methods=['GET'])
# @require_auth  # Descomente se o admin também precisar de token
# @require_admin # Descomente para proteger a rota para admins
def get_all_admin_orders():
    """ Retorna TODOS os pedidos do sistema para o admin. """
    try:
        # Retorna todos os pedidos, ordenados pelo mais recente
        pedidos = list(get_pedidos_collection().find({}).sort("Data", -1))
        
        for pedido in pedidos:
            pedido['_id'] = str(pedido['_id'])
        
        return jsonify(pedidos)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@admin_bp.route('/all-items', methods=['GET'])
@require_auth
@require_admin
def get_all_database_items():
    """
    Retorna uma lista completa de todos os itens no banco de dados para o admin.
    Filtra registros inválidos/vazios.
    """
    try:
        search = request.args.get('search', '')
        
        # Condições base para garantir que o item é válido
        query_conditions = [
            {'Item ID': {'$exists': True}},
            {'Name': {'$exists': True, '$ne': ''}}
        ]
        
        if search:
            search_or_conditions = []
            # Busca por ID, Nome ou Categoria
            try:
                item_id = int(search)
                search_or_conditions.append({'Item ID': item_id})
            except ValueError:
                pass # Ignora se não for um número

            search_or_conditions.append({'Name': {'$regex': re.escape(search), '$options': 'i'}})
            search_or_conditions.append({'Category': {'$regex': re.escape(search), '$options': 'i'}})
            
            query_conditions.append({'$or': search_or_conditions})

        # A query final combina as condições de validade com a busca opcional
        final_query = {'$and': query_conditions}

        items_collection = get_items_collection()
        items = list(items_collection.find(final_query).sort("Item ID", 1))
        
        for item in items:
            item["_id"] = str(item["_id"])
        
        items = clean_nan_values(items)
        
        return jsonify(items)

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@admin_bp.route('/clients', methods=['GET'])
@require_auth
@require_admin
def get_all_clients():
    """ Retorna uma lista de todos os usuários para o seletor. """
    users_collection = get_users_collection()
    clients = list(users_collection.find({}, {"_id": 1, "email": 1, "name": 1}))
    for client in clients:
        client["_id"] = str(client["_id"])
    return jsonify(clients)

@admin_bp.route('/adjust-client-prices', methods=['POST'])
@require_auth
@require_admin
def adjust_client_prices():
    """ Aplica um ajuste de preço para todos os produtos para um cliente específico. """
    data = request.json
    client_id = data.get('client_id')
    adjustment_type = data.get('type')
    adjustment_value = float(data.get('value', 0))

    if not all([client_id, adjustment_type]):
        return jsonify({"error": "Dados insuficientes"}), 400

    items_collection = get_items_collection()
    client_prices_collection = db.client_prices # Acessa a nova coleção

    all_items = list(items_collection.find({}, {"Item ID": 1, "Sale Price": 1}))
    
    operations = []
    for item in all_items:
        current_price = item.get('Sale Price', 0)
        if not isinstance(current_price, (int, float)) or current_price <= 0:
            continue

        if adjustment_type == 'percentage':
            new_price = current_price * (1 + adjustment_value / 100)
        else: # fixed
            new_price = current_price + adjustment_value
        
        new_price = round(max(0, new_price), 2)

        # Prepara uma operação de "update com upsert"
        operations.append(
            UpdateOne(
                {"client_id": client_id, "item_id": item["Item ID"]},
                {"$set": {
                    "special_price": new_price,
                    "last_updated": datetime.now().isoformat()
                }},
                upsert=True
            )
        )
    
    if operations:
        result = client_prices_collection.bulk_write(operations)
        return jsonify({
            "message": f"Preços especiais aplicados a {len(all_items)} produtos para o cliente selecionado.",
            "matched_count": result.matched_count,
            "upserted_count": result.upserted_count
        })
    
    return jsonify({"message": "Nenhum produto encontrado para aplicar preços."})

@admin_bp.route('/export-items', methods=['GET'])
@require_auth
@require_admin
def export_items_to_xlsx():
    """ Exporta todos os itens da base de dados para um arquivo XLSX. """
    try:
        items_collection = get_items_collection()
        all_items = list(items_collection.find({}))
        
        if not all_items:
            return jsonify({"message": "Nenhum item para exportar."}), 404

        # Converte para DataFrame do Pandas
        df = pd.DataFrame(all_items)
        
        # Limpa e reordena as colunas para um formato amigável
        df = df.drop(columns=['_id'], errors='ignore')
        friendly_order = [
            'Item ID', 'Name', 'Shape', 'Category', 'Sale Price', 'Group Pile', # <-- 'Shape' ADICIONADO
            'Weight', 'Height', 'Width', 'Length', 'Description'
        ]
        # Pega apenas as colunas que existem no DataFrame para evitar erros
        existing_columns = [col for col in friendly_order if col in df.columns]
        df = df[existing_columns]

        # Cria um arquivo Excel em memória
        output = BytesIO()
        writer = pd.ExcelWriter(output, engine='openpyxl')
        df.to_excel(writer, index=False, sheet_name='Produtos')
        writer.close()
        output.seek(0)

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='vasap_produtos.xlsx'
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/import-items', methods=['POST'])
@require_auth
@require_admin
def import_items_from_xlsx():
    """ Importa e atualiza itens a partir de um arquivo XLSX. """
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Nenhum arquivo selecionado'}), 400

    if file and file.filename.endswith('.xlsx'):
        try:
            df = pd.read_excel(file)
            items_collection = get_items_collection()
            
            operations = []
            for index, row in df.iterrows():
                # Validação básica: O Item ID é essencial
                if 'Item ID' not in row or pd.isna(row['Item ID']):
                    continue

                item_id = int(row['Item ID'])
                
                update_data = {}
                # Itera sobre as colunas do arquivo e adiciona ao update se não for nulo
                for col_name, value in row.items():
                    if col_name != 'Item ID' and pd.notna(value):
                        update_data[col_name] = value
                    if col_name == 'Shape' and pd.notna(value):
                        shape_value = str(value).lower().strip()
                        update_data['Shape'] = 'cylinder' if shape_value == 'cylinder' else 'box'
                    elif col_name != 'Item ID' and pd.notna(value):
                        update_data[col_name] = value
                
                if update_data:
                    operations.append(
                        UpdateOne(
                            {"Item ID": item_id},
                            {"$set": update_data},
                            upsert=True # Atualiza se existir, insere se não existir
                        )
                    )

            if not operations:
                return jsonify({'message': 'Nenhum dado válido encontrado no arquivo para importar.'}), 400

            result = items_collection.bulk_write(operations)
            return jsonify({
                'message': 'Importação concluída com sucesso!',
                'updated_count': result.modified_count,
                'created_count': result.upserted_count
            })

        except Exception as e:
            return jsonify({'error': f'Erro ao processar o arquivo: {str(e)}'}), 500
    
    return jsonify({'error': 'Formato de arquivo inválido. Por favor, envie um arquivo .xlsx'}), 400