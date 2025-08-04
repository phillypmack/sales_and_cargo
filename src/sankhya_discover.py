import random
import requests
import json

# Configurações da API Sankhya
SANKHYA_BASE_URL = "http://ecoplax.rcs.inf.br:8180/mge"
SANKHYA_LOGIN_URL = "https://api.sankhya.com.br/login" # Revertido para o URL original de login
SANKHYA_GATEWAY_URL = "https://api.sankhya.com.br/gateway/v1/mgecom/service.sbr"
SANKHYA_APP_KEY = "61787b87-e480-4918-8d03-9830cab7c200"
SANKHYA_CLIENT_TOKEN = "b7f11066-c0d5-41dd-862b-724eb03b982c"
SANKHYA_USERNAME = "felipe.santos@vasap.com.br"
SANKHYA_PASSWORD = "Shark@777"

def login(username, password, app_key, client_token):
    """Realiza o login na API Sankhya e retorna o bearer token."""
    headers = {
        "token": client_token,
        "appkey": app_key,
        "username": username,
        "password": password
    }
    try:
        response = requests.post(SANKHYA_LOGIN_URL, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response Text: {response.text}")
        response.raise_for_status()  # Levanta um erro para status de resposta HTTP ruins (4xx ou 5xx)
        return response.json().get("bearerToken")
    except requests.exceptions.RequestException as e:
        print(f"Erro ao realizar login: {e}")
        return None

def insert_order(bearer_token, order_data):
    """Insere um pedido no sistema Sankhya."""
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json"
    }
    params = {
        "serviceName": "CACSP.incluirNota",
        "outputType": "json"
    }
    try:
        response = requests.post(SANKHYA_GATEWAY_URL, headers=headers, params=params, data=json.dumps(order_data))
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao inserir pedido: {e}")
        return None

if __name__ == "__main__":
    # 1. Realizar login
    print("Realizando login...")
    bearer_token = login(SANKHYA_USERNAME, SANKHYA_PASSWORD, SANKHYA_APP_KEY, SANKHYA_CLIENT_TOKEN)

    if bearer_token:
        print("Login bem-sucedido. Bearer Token obtido.")
        # 2. Preparar dados do pedido (exemplo) com base no JSON fornecido
        order_data = {
            "serviceName": "CACSP.incluirNota",
            "requestBody": {
                "nota": {
                    "cabecalho": {
                        "NUNOTA": {},
                        "CODEMP": {
                            "$": "1"
                        },
                        "CODPARC": {
                            "$": "1695" #parceiro exempli fixo até termos uma tela de cadastro de parceiros
                        },
                        "DTNEG": {
                            "$": "30/07/2025"
                        },
                        "CODTIPOPER": {
                            "$": "3050"
                        },
                        "CODTIPVENDA": {
                            "$": "300"
                        },
                        "CODVEND": {
                            "$": "360"
                        },
                        "TIPMOV": {
                            "$": "P"
                        },
                        "CODCENCUS": {
                            "$": "1070100"
                        },
                        "CODNAT": {
                            "$": "1010110"
                        },
                        "NUMPEDIDO2": {
                            "$": "9999999999999" #numero do pedido de DA PLATAFORMA DE EXPORTAÇÃO
                        },
                        "CIF_FOB": {
                            "$": "C"
                        },
                        "OBSERVACAO": {
                            "$": "pedido Proxindo do sitema de exportações" # essa Observação deve ser mehlorada.
                        }
                    },
                    "itens": {
                        "INFORMARPRECO": "True",
                        "item": [
                            {
                                "NUNOTA": {},
                                "CODPROD": {
                                    "$": "7123"
                                },
                                "QTDNEG": {
                                    "$": "1"
                                },
                                "CODLOCALORIG": {
                                    "$": "401"
                                },
                                "CODVOL": {
                                    "$": "UN"
                                },
                                "VLRUNIT": {
                                    "$": "36.41"
                                },
                                "PERCDESC": {
                                    "$": "0.00"
                                }
                            },
                            {
                                "NUNOTA": {},
                                "CODPROD": {
                                    "$": "7114"
                                },
                                "QTDNEG": {
                                    "$": "1"
                                },
                                "CODLOCALORIG": {
                                    "$": "401"
                                },
                                "CODVOL": {
                                    "$": "UN"
                                },
                                "VLRUNIT": {
                                    "$": "60.66"
                                },
                                "PERCDESC": {
                                    "$": "0.00"
                                }
                            },
                            {
                                "NUNOTA": {},
                                "CODPROD": {
                                    "$": "5166"
                                },
                                "QTDNEG": {
                                    "$": "4"
                                },
                                "CODLOCALORIG": {
                                    "$": "401"
                                },
                                "CODVOL": {
                                    "$": "UN"
                                },
                                "VLRUNIT": {
                                    "$": "58.70"
                                },
                                "PERCDESC": {
                                    "$": "0.00"
                                }
                            },
                            {
                                "NUNOTA": {},
                                "CODPROD": {
                                    "$": "7121"
                                },
                                "QTDNEG": {
                                    "$": "1"
                                },
                                "CODLOCALORIG": {
                                    "$": "401"
                                },
                                "CODVOL": {
                                    "$": "UN"
                                },
                                "VLRUNIT": {
                                    "$": "75.22"
                                },
                                "PERCDESC": {
                                    "$": "0.00"
                                }
                            },
                            {
                                "NUNOTA": {},
                                "CODPROD": {
                                    "$": "6932"
                                },
                                "QTDNEG": {
                                    "$": "3"
                                },
                                "CODLOCALORIG": {
                                    "$": "401"
                                },
                                "CODVOL": {
                                    "$": "UN"
                                },
                                "VLRUNIT": {
                                    "$": "108.98"
                                },
                                "PERCDESC": {
                                    "$": "0.00"
                                }
                            },
                            {
                                "NUNOTA": {},
                                "CODPROD": {
                                    "$": "6805"
                                },
                                "QTDNEG": {
                                    "$": "11"
                                },
                                "CODLOCALORIG": {
                                    "$": "401"
                                },
                                "CODVOL": {
                                    "$": "UN"
                                },
                                "VLRUNIT": {
                                    "$": "21.41"
                                },
                                "PERCDESC": {
                                    "$": "0.00"
                                }
                            }
                        ]
                    }
                }
            }
        }

        # 3. Inserir pedido
        print("Inserindo pedido...")
        result = insert_order(bearer_token, order_data)

        if result:
            print("Resultado da inserção do pedido:")
            print(json.dumps(result, indent=4))
        else:
            print("Falha ao inserir pedido.")
    else:
        print("Falha no login. Não foi possível prosseguir com a inserção do pedido.")