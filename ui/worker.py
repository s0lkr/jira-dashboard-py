import time
from PyQt6.QtCore import QThread, pyqtSignal
from core.jira_api import JiraAPIClient

class JiraPoller(QThread):
    dados_recebidos = pyqtSignal(list)
    # "Título" e "Mensagem"
    notificacao_disparada = pyqtSignal(str, str) 

    def __init__(self):
        super().__init__()
        self.cliente = JiraAPIClient()
        self._forcar_busca = False
        
        # memoria pra nao ficar loop a notificação
        self.tickets_vistos = set() 
        self.primeira_busca = True  # desliga a notificação depois da primeira vez

    def forcar_busca(self):
        self._forcar_busca = True

    def run(self):
        while True:
            resultado = self.cliente.obter_novos_tickets()
            if resultado is not None:
                
                # Cruza os dados da API com a nossa memória
                novos_nesta_rodada = []
                for ticket in resultado:
                    id_ticket = ticket["id"]
                    if id_ticket not in self.tickets_vistos:
                        self.tickets_vistos.add(id_ticket) # Salva na memória
                        novos_nesta_rodada.append(ticket)

                # Se NÃO for a primeira vez que roda, e achou coisa nova, manda notificação
                if not self.primeira_busca and novos_nesta_rodada:
                    for novo in novos_nesta_rodada:
                        titulo = f"Novo Ticket Jira: {novo['id']}"
                        mensagem = novo['resumo']
                        self.notificacao_disparada.emit(titulo, mensagem)

                self.primeira_busca = False
                
                # Manda a lista inteira pra tela desenhar a tabela normalmente
                self.dados_recebidos.emit(resultado)
                

            # att automatica
            for _ in range(60):
                if self._forcar_busca:
                    self._forcar_busca = False
                    break
                time.sleep(1)