import requests
from requests.auth import HTTPBasicAuth

from core.config import api_key, jira_base_url, jira_email


class JiraAPIClient:
    def __init__(self):
        self.base_url = jira_base_url
        self.auth = HTTPBasicAuth(jira_email, api_key)
    
    def obter_novos_tickets(self):
        """
        Busca por issues, filtra os dados relevantes e os retorna em uma lista.
        """
        url = f"{self.base_url}/rest/api/3/search"
        jql_query = 'textfields ~ "tarefa*" AND type IN standardIssueTypes() AND status = "A fazer"'        
        params = {
            'jql': jql_query
        }
        headers = {
            "Accept": "application/json"
        }
        
        try:
            # Faz a requisição para a API
            resposta = requests.get(
                url, headers=headers, params=params, auth=self.auth
            )
            # Lança uma exceção se a resposta for um erro
            resposta.raise_for_status()

            # Converte a resposta para JSON e inicia o processamento
            dados = resposta.json()
            tickets_processados = []

            for ticket in dados.get("issues", []):
                ticket_filtrado = {
                    "id": ticket["key"],
                    "resumo": ticket["fields"]["summary"],
                    "status": ticket["fields"]["status"]["name"],
                }
                tickets_processados.append(ticket_filtrado)

            return tickets_processados

        except requests.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
            return None
        except requests.RequestException as e:
            print(f"Erro ao buscar issues no Jira: {e}")
            return None