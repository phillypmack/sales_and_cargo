import os
import requests
import json
from datetime import datetime

class SankhyaService:
    def __init__(self):
        self.login_url = os.getenv("SANKHYA_LOGIN_URL")
        self.gateway_url = os.getenv("SANKHYA_GATEWAY_URL") # URL principal do gateway
        self.app_key = os.getenv("SANKHYA_APP_KEY")
        self.client_token = os.getenv("SANKHYA_CLIENT_TOKEN")
        self.username = os.getenv("SANKHYA_USERNAME")
        self.password = os.getenv("SANKHYA_PASSWORD")
        self.codtipoper = os.getenv("SANKHYA_CODTIPOPER")
        self.codemp = os.getenv("SANKHYA_CODEMP")

    def create_or_update_partner(self, client_data):
        """Cria ou atualiza um Parceiro (Cliente) no Sankhya."""
        bearer_token = self.get_bearer_token()
        if not bearer_token:
            raise Exception("Não foi possível autenticar no Sankhya para criar o parceiro.")

        # Mapeamento dos campos do seu formulário para a API do Sankhya
        partner_payload = {
            "NOMECONTATO": client_data.get("legal_name"),
            "NOMEFANTASIA": client_data.get("trade_name"),
            "TELEFONE": client_data.get("contact", {}).get("phone"),
            "EMAIL": client_data.get("contact", {}).get("email"),
            "CGC_CPF": client_data.get("fiscal_info", {}).get("tax_id"),
            "IDENTINSCESTAD": client_data.get("fiscal_info", {}).get("registration_number"),
            "ENDERECO": client_data.get("address", {}).get("street"),
            "NUMEND": client_data.get("address", {}).get("number"),
            "CIDADE": client_data.get("address", {}).get("city"),
            "UF": client_data.get("address", {}).get("state_province"),
            "PAIS": client_data.get("address", {}).get("country"),
            "CEP": client_data.get("address", {}).get("postal_code"),
            "ATIVO": "S",
            "CLIENTE": "S",
            "FORNECEDOR": "N",
            "TRANSPORTADORA": "N",
            "CLASSIFICMS": "C" # Consumidor Final (ajustar se necessário)
        }
        
        # Se já temos um CODPARC, enviamos para ATUALIZAR o parceiro existente
        if client_data.get("sankhya_codparc"):
            partner_payload["CODPARC"] = client_data["sankhya_codparc"]

        # Monta o corpo da requisição final
        request_body = {
            "entidades": {
                "entidade": [partner_payload]
            }
        }

        # Endpoint específico para criar/atualizar contatos/clientes
        partner_url = f"{self.gateway_url.replace('/mgecom/', '/mge/')}/contatoCliente"

        headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json"
        }
        try:
            response = requests.post(partner_url, headers=headers, data=json.dumps(request_body), timeout=30)
            response.raise_for_status()
            response_data = response.json()

            if response_data.get("status") == "1" and response_data.get("entidades"):
                # Extrai o CODPARC da resposta
                codparc = response_data["entidades"]["entidade"][0]["chave"]["CODPARC"]
                print(f"Parceiro criado/atualizado com sucesso no Sankhya. CODPARC: {codparc}")
                return {"success": True, "codparc": codparc, "response": response_data}
            else:
                error_message = response_data.get("statusMessage", "Erro desconhecido ao criar parceiro.")
                print(f"Falha ao criar parceiro no Sankhya: {error_message}")
                return {"success": False, "error": error_message, "response": response_data}

        except requests.exceptions.RequestException as e:
            print(f"Erro de comunicação ao criar parceiro no Sankhya: {e}")
            raise Exception(f"Erro de comunicação com o ERP: {e}")
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            print(f"Erro ao processar a resposta do Sankhya: {e}. Resposta: {response.text}")
            raise Exception(f"Resposta inválida do ERP ao criar parceiro: {response.text}")    

    def get_bearer_token(self):
        """Realiza o login na API Sankhya e retorna o bearer token."""
        headers = {
            "token": self.client_token,
            "appkey": self.app_key,
            "username": self.username,
            "password": self.password
        }
        try:
            response = requests.post(self.login_url, headers=headers, timeout=15)
            response.raise_for_status()
            token = response.json().get("bearerToken")
            if not token:
                print("Bearer token não encontrado na resposta de login.")
                return None
            print("Login no Sankhya (Bearer Token) bem-sucedido.")
            return token
        except requests.exceptions.RequestException as e:
            print(f"Erro ao realizar login no Sankhya: {e}")
            return None
        except json.JSONDecodeError:
            print(f"Erro ao decodificar a resposta de login do Sankhya. Resposta recebida: {response.text}")
            return None

    def send_order(self, order_data):
        """Obtém o token, monta e envia um pedido para a API do Sankhya."""
        bearer_token = self.get_bearer_token()
        if not bearer_token:
            raise Exception("Não foi possível autenticar no Sankhya para enviar o pedido.")

        # Mapeamento de dados do seu pedido para o formato Sankhya
        codparc = order_data.get("codparc")
        if not codparc:
            raise Exception("CODPARC não encontrado nos dados do pedido.")

        sankhya_items = []
        for item in order_data.get("items", []):
            sankhya_items.append({
                "NUNOTA": {},
                "CODPROD": {"$": str(item["Item ID"])},
                "QTDNEG": {"$": str(item["Amount"])},
                "CODLOCALORIG": {"$": "401"},
                "CODVOL": {"$": "UN"},
                "VLRUNIT": {"$": str(item["Sale Price"])},
                "PERCDESC": {"$": "0.00"}
            })

        # Monta o payload final do pedido
        order_payload = {
            "serviceName": "CACSP.incluirNota",
            "requestBody": {
                "nota": {
                    "cabecalho": {
                        "NUNOTA": {},
                        "CODEMP": {"$": self.codemp},
                        "CODPARC": {"$": codparc},
                        "DTNEG": {"$": order_date},
                        "CODTIPOPER": {"$": self.codtipoper},
                        "CODTIPVENDA": {"$": "300"}, # Valor fixo do exemplo
                        "CODVEND": {"$": "360"},     # Valor fixo do exemplo
                        "TIPMOV": {"$": "P"},
                        "CODCENCUS": {"$": "1070100"}, # Valor fixo do exemplo
                        "CODNAT": {"$": "1010110"},   # Valor fixo do exemplo
                        "NUMPEDIDO2": {"$": str(order_data["Order"])},
                        "CIF_FOB": {"$": "C"},
                        "OBSERVACAO": {"$": f"Pedido #{order_data['Order']} gerado via Portal Vasap Web."}
                    },
                    "itens": {
                        "INFORMARPRECO": "True",
                        "item": sankhya_items
                    }
                }
            }
        }

        # Envio do pedido
        headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json"
        }
        params = {
            "serviceName": "CACSP.incluirNota",
            "outputType": "json"
        }
        try:
            response = requests.post(self.gateway_url, headers=headers, params=params, data=json.dumps(order_payload), timeout=30)
            response.raise_for_status()
            response_data = response.json()

            if response_data.get("status") == "1":
                print(f"Pedido #{order_data['Order']} enviado com sucesso para o Sankhya.")
                
                # Extrai o NUNOTA da resposta
                nunota = None
                try:
                    # Navega pela estrutura complexa da resposta para encontrar o NUNOTA
                    nunota = response_data.get("responseBody", {}).get("pk", {}).get("NUNOTA", {}).get("$")
                except (AttributeError, TypeError):
                    print("Não foi possível extrair o NUNOTA da resposta do Sankhya.")

                return {"success": True, "response": response_data, "nunota": nunota}
            else:
                error_message = response_data.get("statusMessage", "Erro desconhecido ao enviar pedido.")
                print(f"Falha ao enviar pedido para o Sankhya: {error_message}")
                return {"success": False, "error": error_message, "response": response_data}

        except requests.exceptions.RequestException as e:
            print(f"Erro de comunicação ao enviar pedido para o Sankhya: {e}")
            raise Exception(f"Erro de comunicação com o ERP: {e}")
        except json.JSONDecodeError:
            print(f"Erro ao decodificar a resposta do Sankhya. Resposta recebida: {response.text}")
            raise Exception(f"Resposta inválida do ERP: {response.text}")
    pass

# Instância global para ser usada nas rotas
sankhya_service = SankhyaService()