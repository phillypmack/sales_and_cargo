import os
import requests
import json
from datetime import datetime

class SankhyaService:
    def __init__(self):
        # Lendo as configurações do ambiente
        self.login_url = os.getenv("SANKHYA_LOGIN_URL")
        self.gateway_url = os.getenv("SANKHYA_GATEWAY_URL")
        self.app_key = os.getenv("SANKHYA_APP_KEY")
        self.client_token = os.getenv("SANKHYA_CLIENT_TOKEN")
        self.username = os.getenv("SANKHYA_USERNAME")
        self.password = os.getenv("SANKHYA_PASSWORD")
        self.codtipoper = os.getenv("SANKHYA_CODTIPOPER")
        self.codemp = os.getenv("SANKHYA_CODEMP")

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
        codparc = "1695" # Valor fixo para testes, conforme definido
        order_date = datetime.fromisoformat(order_data["Data"]).strftime("%d/%m/%Y")

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


# Instância global para ser usada nas rotas
sankhya_service = SankhyaService()