import requests
import json
from requests.auth import HTTPBasicAuth

class JiraAPIClient:
    def __init__(self, base_url, email, api_token):
        self.base_url = base_url
        self.auth = HTTPBasicAuth(email, api_token)
        self.icon_cache = {}  # Cache para ícones de prioridade
    
    def obter_novos_tickets(self, jql_query):
        """
        Busca por issues, filtra os dados relevantes e os retorna em uma lista usando JQL personalizado direto na tela
        """
        url = f"{self.base_url}/rest/api/3/search/jql"
        
        params = {
            'jql': jql_query,
            'fields': 'key,summary,status,priority'
        }
        headers = {
            "Accept": "application/json"
        }
        
        try:
            resposta = requests.get(
                url, headers=headers, params=params, auth=self.auth
            )
            resposta.raise_for_status()

            dados = resposta.json()
            tickets_processados = []

            for ticket in dados.get("issues", []):
                campos = ticket.get("fields") or {}
                status_obj = campos.get("status") or {}
                prioridade_obj = campos.get("priority") or {}
                
                prioridade_nome = prioridade_obj.get("name", "Normal")
                icone_url = prioridade_obj.get("iconUrl", "")
                icone_bytes = None
                
                if icone_url:
                    if icone_url not in self.icon_cache:
                        resp_icone = requests.get(icone_url, auth=self.auth)
                        if resp_icone.status_code == 200:
                            self.icon_cache[icone_url] = resp_icone.content
                        else:
                            self.icon_cache[icone_url] = None
                    icone_bytes = self.icon_cache[icone_url]
                
                ticket_filtrado = {
                    "id": ticket.get("key", ticket.get("id", "S/N")),
                    "resumo": campos.get("summary", "Sem Resumo"),
                    "status": status_obj.get("name", "Desconhecido"),
                    "prioridade": prioridade_nome
                }
                
                tickets_processados.append(ticket_filtrado)

            return tickets_processados

        except requests.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
            return None
        except requests.RequestException as e:
            print(f"Erro ao buscar issues no Jira: {e}")
            return None
    
    def alterar_status_ticket(self, ticket_id, id_transicao):
        """
        alterar status do ticket
        """
        url = f"{self.base_url}/rest/api/3/issue/{ticket_id}/transitions"
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        # formato aceito pelo jira, peguei no raiox do json completo
        payload = {
            "transition": {
                "id": str(id_transicao)
            }
        }
        
        try:
            resposta = requests.post(
                url, 
                json=payload, 
                headers=headers, 
                auth=self.auth
            )
            # Lança exceção se der erro
            resposta.raise_for_status()
            
            return True
            
        except requests.RequestException as e:
            print(f"Erro crítico ao tentar mover o ticket {ticket_id}: {e}")
            return False
    
    def descobrir_transicoes(self, ticket_id):
        """
        Faz um GET para descobrir as transições disponíveis e retorna uma lista de dicionários.
        """
        url = f"{self.base_url}/rest/api/3/issue/{ticket_id}/transitions"
        headers = {"Accept": "application/json"}
        
        try:
            resposta = requests.get(url, headers=headers, auth=self.auth)
            resposta.raise_for_status()
            
            transicoes = resposta.json().get("transitions", [])
            # Extrai apenas o ID e o Nome de cada transição e devolve como lista
            return [{"id": t["id"], "name": t["name"]} for t in transicoes]
            
        except requests.RequestException as e:
            print(f"Erro ao buscar transições do ticket {ticket_id}:\n{e}")
            return None
            