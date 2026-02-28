import os
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QMenu,
    QMessageBox,
    QPushButton,
    QDialog,
    QListWidget,
    QSystemTrayIcon,
    QStyle
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap
from datetime import datetime

from ui.worker import JiraPoller


class MainWindow(QMainWindow):
    """inicializa o GUI"""
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Jira - Tickets Abertos")
        self.resize(800, 600)

        # Configuração do widget central e layout
        widget_central = QWidget()
        self.setCentralWidget(widget_central)
        layout = QVBoxLayout(widget_central)

        # Configuração da Tabela
        self.tabela = QTableWidget()
        self.tabela.setColumnCount(5)
        self.tabela.setHorizontalHeaderLabels(["ID", "Resumo", "Status", "Prioridade", "Ações"])
        
        # block edit
        self.tabela.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabela.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabela.customContextMenuRequested.connect(self.abrir_menu)
        
        layout.addWidget(self.tabela)

        # ajusta a coluna de resumo para preencher o espaço
        header = self.tabela.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
        self.pasta_logs = "logs"
        if not os.path.exists(self.pasta_logs):
            os.makedirs(self.pasta_logs) #criar pasta logs se não existir

        self.historico_logs = []
        self.carregar_logs_do_dia()

        # Inicia o worker para buscar dados do Jira
        self.worker = JiraPoller()
        self.worker.dados_recebidos.connect(self.atualizar_tabela)
        
        # menu top
        menu_bar = self.menuBar()
        
        acao_logs = menu_bar.addAction("Logs do Sistema")
        acao_logs.triggered.connect(self.abrir_janela_logs)
        
        acao_atualizar = menu_bar.addAction("Buscar novos tickets")
        acao_atualizar.triggered.connect(self.solicitar_atualizacao)

        # configura rodape 
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Inicializando motor de busca...")
        
        # configuração das Notificações usando system tray
        self.tray_icon = QSystemTrayIcon(self)
        # Pega o ícone padrão de "Computador" do Windows para não ficar invisível
        icone_padrao = self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        self.tray_icon.setIcon(icone_padrao)
        self.tray_icon.show() # Fica escondidinho perto do relógio

        # conecta notificação do worker com a função que mostra notificação
        self.worker.notificacao_disparada.connect(self.mostrar_notificacao)

        # inicia o worker para buscar dados do Jira
        self.worker.start()

    def atualizar_tabela(self, tickets):
        """Este método (slot) é chamado quando o worker emite o sinal"""
        self.tabela.setRowCount(0)  # Limpa a tabela antes de preencher
        for linha, ticket in enumerate(tickets):
            self.tabela.insertRow(linha)
            self.tabela.setItem(linha, 0, QTableWidgetItem(str(ticket["id"])))
            self.tabela.setItem(linha, 1, QTableWidgetItem(str(ticket["resumo"])))
            self.tabela.setItem(linha, 2, QTableWidgetItem(str(ticket["status"])))
            
            texto_prioridade = str(ticket.get("prioridade", ""))
            item_prioridade = QTableWidgetItem(texto_prioridade)
            
            mapa_icones = {
                "Highest": "ui/assets/prioridade_highest.svg",
                "High": "ui/assets/prioridade_high.svg",
                "Medium": "ui/assets/prioridade_medium.svg",
                "Low": "ui/assets/prioridade_low.svg",
                "Lowest": "ui/assets/prioridade_lowest.svg"
            }
            
            caminho_icone = mapa_icones.get(texto_prioridade)
            if caminho_icone:
                item_prioridade.setIcon(QIcon(caminho_icone))
                
            self.tabela.setItem(linha, 3, item_prioridade)
            
            btn_acoes = QPushButton("Alterar Status ▾")
            # Um pequeno estilo pro botão chamar a atenção sem quebrar o layout
            btn_acoes.setStyleSheet("""
                QPushButton {
                    background-color: #0052CC; 
                    color: white; 
                    border-radius: 4px; 
                    padding: 4px;
                }
                QPushButton:hover { background-color: #0047b3; }
            """)
            
            # conecta o clique do botão a uma função, passando o ID do ticket de forma segura
            btn_acoes.clicked.connect(
                lambda checked, t_id=ticket.get("id"), btn=btn_acoes: self.abrir_menu_transicoes(t_id, btn)
            )
            
            self.tabela.setCellWidget(linha, 4, btn_acoes)

            # Atualiza o rodapé com a hora exata da última sincronização
        from datetime import datetime
        hora_atual = datetime.now().strftime("%H:%M:%S")
        self.status_bar.showMessage(f"Última atualização: {hora_atual} ({len(tickets)} tickets abertos)")
         
    def abrir_menu(self, posicao):
        """Abrir menu para alterar status do ticket"""
        linha = self.tabela.rowAt(posicao.y())
        if linha == -1:
            return
        
        item_id = self.tabela.item(linha, 0)
        ticket_id = item_id.text()
        
        menu = QMenu(self)
        
        # opcoes de status
        acao_analise = menu.addAction("Mover para 'Em análise'")
        
        acao_escolhida = menu.exec(self.tabela.viewport().mapToGlobal(posicao))
        
        if acao_escolhida == acao_analise:
            self.enviar_comando(ticket_id, 21, linha)
    
    def enviar_comando_via_botao(self, ticket_id, id_transicao):
        """Descobre em qual linha o ticket está no momento do clique e envia o comando."""
        linha_alvo = -1
        # Procura a linha que contém esse ticket_id
        for row in range(self.tabela.rowCount()):
            if self.tabela.item(row, 0).text() == str(ticket_id):
                linha_alvo = row
                break
                
        if linha_alvo != -1:
            # Chama a sua função original aproveitando a mesma lógica
            self.enviar_comando(ticket_id, id_transicao, linha_alvo)
            
    def abrir_menu_transicoes(self, ticket_id, botao_widget):
        """Busca as transições ao vivo no Jira e desenha um menu abaixo do botão."""
        # 1. Feedback visual imediato
        texto_original = botao_widget.text()
        botao_widget.setText("Buscando...")
        botao_widget.repaint() # Força a tela a atualizar o texto na hora

        # 2. Consulta o Jira
        transicoes = self.worker.cliente.descobrir_transicoes(ticket_id)
        
        # 3. Restaura o botão
        botao_widget.setText(texto_original)

        if not transicoes:
            QMessageBox.warning(self, "Aviso", f"Nenhuma transição encontrada para o ticket {ticket_id}.")
            return

        # 4. Constrói o menu flutuante
        menu = QMenu(self)
        mapa_acoes = {} # Dicionário para lembrar qual botão pertence a qual ID
        
        for t in transicoes:
            acao = menu.addAction(t["name"])
            mapa_acoes[acao] = t["id"]

        # 5. Exibe o menu ancorado exatamente no canto inferior esquerdo do botão
        acao_escolhida = menu.exec(botao_widget.mapToGlobal(botao_widget.rect().bottomLeft()))

        # 6. Se o usuário clicou em uma opção, dispara a mudança de status
        if acao_escolhida:
            id_transicao = mapa_acoes[acao_escolhida]
            self.enviar_comando_via_botao(ticket_id, id_transicao)
          
    def enviar_comando(self, ticket_id, id_transicao, linha):
        # Usa o cliente worker pra enviar o POST
        sucesso = self.worker.cliente.alterar_status_ticket(ticket_id, id_transicao)
        
        if sucesso:
            # apaga o ticket da tela instantaneamente
            self.tabela.removeRow(linha)
            
            # registra no histórico de log
            self.registrar_log(f"SUCESSO: Ticket {ticket_id} movido (Transição: {id_transicao})")
            
            QMessageBox.information(self, "Sucesso", f"O ticket {ticket_id} teve o status alterado com sucesso!")
        else:
            self.registrar_log(f"ERRO: Falha ao tentar mover o ticket {ticket_id}")
            QMessageBox.warning(self, "Erro", f"Falha! O ticket {ticket_id} não teve o status alterado.")
    
    def obter_arquivo_log_hoje(self):
        """Gera o nome do arquivo com a data de hoje (ex: logs/2023-10-25.txt)"""
        data_hoje = datetime.now().strftime("%Y-%m-%d")
        return os.path.join(self.pasta_logs, f"{data_hoje}.txt")

    def carregar_logs_do_dia(self):
        """Lê o arquivo de texto de hoje para recuperar a memória de ações anteriores."""
        arquivo = self.obter_arquivo_log_hoje()
        if os.path.exists(arquivo):
            with open(arquivo, "r", encoding="utf-8") as f:
                self.historico_logs = [linha.strip() for linha in f.readlines()]
    
    def registrar_log(self, mensagem):
        """Salva a ação na memória e também no arquivo .txt permanentemente."""
        hora_atual = datetime.now().strftime("%H:%M:%S")
        log_formatado = f"[{hora_atual}] {mensagem}"
        
        self.historico_logs.append(log_formatado)
        
        # abre o arquivo no modo "a" de append, que adiciona sem apagar o que já tem
        arquivo = self.obter_arquivo_log_hoje()
        with open(arquivo, "a", encoding="utf-8") as f:
            f.write(log_formatado + "\n")
        
    def abrir_janela_logs(self):
        """Cria e exibe uma janela flutuante com o histórico"""
        janela = QDialog(self)
        janela.setWindowTitle("Logs de Ações (Sessão Atual)")
        janela.resize(500, 300)
        
        layout_janela = QVBoxLayout(janela)
        lista_visual = QListWidget()
        
        # Preenche a tela de logs com a nossa memória
        for log in self.historico_logs:
            lista_visual.addItem(log)
            
        layout_janela.addWidget(lista_visual)
        janela.exec()
    
    def solicitar_atualizacao(self):
        """Muda o texto do rodapé e avisa a thread para buscar na mesma hora"""
        self.status_bar.showMessage("Buscando dados no Jira...")
        self.worker.forcar_busca()
        
    def mostrar_notificacao(self, titulo, mensagem):
        """Dispara o Toast nativo do SO e anota no log a chegada do ticket."""
        self.tray_icon.showMessage(titulo, mensagem, QSystemTrayIcon.MessageIcon.Information, 5000)
        
        # --- NOVO: Anota a entrada de um ticket no histórico! ---
        self.registrar_log(f"ENTRADA: Identificado {titulo} ({mensagem})")