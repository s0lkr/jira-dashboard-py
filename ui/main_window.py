from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)

from ui.worker import JiraPoller


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Jira - Tickets 'A fazer'")
        self.resize(800, 600)

        # Configuração do widget central e layout
        widget_central = QWidget()
        self.setCentralWidget(widget_central)
        layout = QVBoxLayout(widget_central)

        # Configuração da Tabela
        self.tabela = QTableWidget()
        self.tabela.setColumnCount(3)
        self.tabela.setHorizontalHeaderLabels(["ID", "Resumo", "Status"])
        layout.addWidget(self.tabela)

        # Ajusta a coluna de resumo para preencher o espaço
        header = self.tabela.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        # Inicia o worker para buscar dados do Jira
        self.worker = JiraPoller()
        self.worker.dados_recebidos.connect(self.atualizar_tabela)
        self.worker.start()

    def atualizar_tabela(self, tickets):
        """Este método (slot) é chamado quando o worker emite o sinal."""
        self.tabela.setRowCount(0)  # Limpa a tabela antes de preencher
        for linha, ticket in enumerate(tickets):
            self.tabela.insertRow(linha)
            self.tabela.setItem(linha, 0, QTableWidgetItem(str(ticket["id"])))
            self.tabela.setItem(linha, 1, QTableWidgetItem(str(ticket["resumo"])))
            self.tabela.setItem(linha, 2, QTableWidgetItem(str(ticket["status"])))