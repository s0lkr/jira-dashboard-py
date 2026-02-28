import time
from PyQt6.QtCore import QThread, pyqtSignal
from core.jira_api import JiraAPIClient

class JiraPoller(QThread):
    dados_recebidos = pyqtSignal(list)
    # "Título" e "Mensagem"
    notificacao_disparada = pyqtSignal(str, str)
    busca_iniciada = pyqtSignal()

    def __init__(self, jql_inicial):
        super().__init__()
        self.cliente = JiraAPIClient()
        self._forcar_busca = False
        self.tickets_vistos = set() 
        self.primeira_busca = True 
        self.jql_atual = jql_inicial # Guarda a query atual
        
    def atualizar_jql(self, nova_jql):
        self.jql_atual = nova_jql
        self.tickets_vistos.clear() # Limpa a memória para evitar conflitos se não da pau
        self.primeira_busca = True
        self.forcar_busca()

    def forcar_busca(self):
        self._forcar_busca = True

    def run(self):
        while True:
            # só vai para a internet se o JQL estiver preenchido
            if self.jql_atual.strip():
                self.busca_iniciada.emit() 
                
                resultado = self.cliente.obter_novos_tickets(self.jql_atual)
                
                if resultado is not None:
                    novos_nesta_rodada = []
                    for ticket in resultado:
                        id_ticket = ticket["id"]
                        if id_ticket not in self.tickets_vistos:
                            self.tickets_vistos.add(id_ticket)
                            novos_nesta_rodada.append(ticket)

                    if not self.primeira_busca and novos_nesta_rodada:
                        for novo in novos_nesta_rodada:
                            titulo = f"Novo Ticket Jira: {novo['id']}"
                            mensagem = novo['resumo']
                            self.notificacao_disparada.emit(titulo, mensagem)

                    self.primeira_busca = False 
                    self.dados_recebidos.emit(resultado)
                    
            for _ in range(60):
                if self._forcar_busca:
                    self._forcar_busca = False
                    break
                time.sleep(1)