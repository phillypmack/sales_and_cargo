from pymongo import MongoClient
import pandas as pd
import json
from datetime import datetime
import os

# Conexão com o MongoDB
client = MongoClient("mongodb+srv://feliperrds:<db_password>@cluster0.3f5rbmw.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client.vasap_db

def import_excel_to_mongodb(excel_path):
    """
    Importa dados do Excel para o MongoDB
    """
    # Lê todas as abas do Excel
    excel_data = pd.read_excel(excel_path, sheet_name=None)
    
    for sheet_name, df in excel_data.items():
        print(f"Importando aba: {sheet_name}")
        
        # Converte NaN para None para compatibilidade com MongoDB
        df = df.where(pd.notnull(df), None)
        
        # Trata colunas de data/hora
        for col in df.columns:
            if df[col].dtype == 'datetime64[ns]':
                df[col] = df[col].apply(lambda x: x.isoformat() if pd.notnull(x) else None)
        
        # Converte DataFrame para lista de dicionários
        records = df.to_dict('records')
        
        # Mapeia nomes de coleções
        collection_mapping = {
            'Items': 'items',
            'Column': 'columns',
            'Pedidos': 'pedidos',
            'Cart': 'cart',
            'Order': 'orders',
            'Container': 'container',
            'Fotos': 'fotos',
            'Vendors': 'vendors',
            'Categories': 'categories',
            'Inventory': 'inventory'
        }
        
        collection_name = collection_mapping.get(sheet_name, sheet_name.lower())
        collection = db[collection_name]
        
        # Limpa a coleção antes de inserir novos dados
        collection.delete_many({})
        
        # Insere os dados
        if records:
            collection.insert_many(records)
            print(f"Inseridos {len(records)} registros na coleção {collection_name}")
        else:
            print(f"Nenhum registro encontrado na aba {sheet_name}")
    
    print("Importação concluída!")

def create_indexes():
    """
    Cria índices para melhorar a performance
    """
    # Índices para Items
    db.items.create_index("Item ID")
    db.items.create_index("Category")
    
    # Índices para Cart
    db.cart.create_index("Item ID")
    db.cart.create_index("Client")
    db.cart.create_index("Order")
    
    # Índices para Pedidos
    db.pedidos.create_index("Order")
    db.pedidos.create_index("Client")
    
    # Índices para Container
    db.container.create_index("Client")
    
    # Índices para Fotos
    db.fotos.create_index("Item ID")
    
    print("Índices criados com sucesso!")

if __name__ == "__main__":
    excel_path = "/home/ubuntu/upload/Vasap_export.xlsx"
    
    try:
        import_excel_to_mongodb(excel_path)
        create_indexes()
    except Exception as e:
        print(f"Erro durante a importação: {e}")


