from pymongo import MongoClient
import os
from sqlalchemy import create_engine

# Lembre-se: a função load_dotenv() deve estar no seu main.py para carregar
# as variáveis de ambiente no início da execução da aplicação.

# --- INÍCIO DA CORREÇÃO ---
# Configuração do MongoDB lendo do arquivo .env
MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME", "vasap_db") # Usa 'vasap_db' como padrão se não for encontrado

# Validação para garantir que a URI do MongoDB foi carregada
if not MONGO_URI:
    raise ValueError("A variável de ambiente MONGO_URI não foi definida. Verifique seu arquivo .env")

client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]
# --- FIM DA CORREÇÃO ---


# --- O RESTO DO ARQUIVO PERMANECE O MESMO ---

def get_items_collection():
    return db.items

def get_cart_collection():
    return db.cart

def get_pedidos_collection():
    return db.pedidos

def get_container_collection():
    return db.container

def get_users_collection():
    return db.users

# Coleção Fotos
def get_fotos_collection():
    return db.fotos

# Coleção Vendors
def get_vendors_collection():
    return db.vendors

# Coleção Categories
def get_categories_collection():
    return db.categories

# Coleção Inventory
def get_inventory_collection():
    return db.inventory

# Coleção Clients (nova tabela proposta)
def get_clients_collection():
    return db.clients

# Função de conexão com Oracle (já corrigida anteriormente)
def get_oracle_engine():
    """
    Cria e retorna um 'engine' do SQLAlchemy para o banco de dados Oracle.
    O engine gerencia um pool de conexões.
    """
    try:
        user = os.getenv("ORACLE_USER")
        password = os.getenv("ORACLE_PASSWORD")
        host = os.getenv("ORACLE_HOST")
        port = os.getenv("ORACLE_PORT")
        service = os.getenv("ORACLE_SERVICE")

        if not all([user, password, host, port, service]):
            print("Erro: Uma ou mais variáveis de ambiente do Oracle não foram definidas.")
            return None

        oracle_uri = (
            f"oracle+oracledb://{user}:{password}"
            f"@{host}:{port}/?service_name={service}"
        )
        engine = create_engine(oracle_uri)
        return engine
    except Exception as e:
        print(f"Erro ao criar o engine do Oracle com SQLAlchemy: {e}")
        return None