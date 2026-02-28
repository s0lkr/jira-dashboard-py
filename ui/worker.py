import time

from PyQt6.QtCore import QThread, pyqtSignal

from core.jira_api import JiraAPIClient


class JiraPoller(QThread):
    """
    Um worker que roda em background, verifica o Jira periodicamente
    e emite um sinal com os tickets encontrados.
    """
    dados_recebidos = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.cliente = JiraAPIClient()

    def run(self):
        while True:
            resultado = self.cliente.obter_novos_tickets()
            if resultado is not None:
                self.dados_recebidos.emit(resultado)
            time.sleep(60)  # Espera 60 segundos antes da próxima verificação