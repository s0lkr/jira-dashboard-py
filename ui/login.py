from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuração Inicial do Sightline")
        self.setModal(True)
        self.resize(400, 250)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("URL Base do Jira (ex: https://sua-empresa.atlassian.net):"))
        self.input_url = QLineEdit()
        layout.addWidget(self.input_url)

        layout.addWidget(QLabel("E-mail da Conta Atlassian:"))
        self.input_email = QLineEdit()
        layout.addWidget(self.input_email)

        layout.addWidget(QLabel("Token de API:"))
        self.input_token = QLineEdit()
        self.input_token.setEchoMode(QLineEdit.EchoMode.Password) # esconde o token com asteriscos
        layout.addWidget(self.input_token)

        self.btn_salvar = QPushButton("Salvar Credenciais com Segurança")
        self.btn_salvar.setStyleSheet("background-color: #0052CC; color: white; padding: 8px; border-radius: 4px;")
        self.btn_salvar.clicked.connect(self.validar_e_salvar)
        layout.addWidget(self.btn_salvar)

        self.dados = None

    def validar_e_salvar(self):
        url = self.input_url.text().strip()
        email = self.input_email.text().strip()
        token = self.input_token.text().strip()

        if not url or not email or not token:
            QMessageBox.warning(self, "Erro", "Todos os campos são obrigatórios.")
            return

        if url.endswith("/"):
            url = url[:-1]

        self.dados = {"url": url, "email": email, "token": token}
        self.accept()