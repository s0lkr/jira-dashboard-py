from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PyQt6.QtCore import Qt

class RequestAccessDialog(QDialog):
    def __init__(self, email_atual="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sightline - Solicitar Acesso")
        self.setFixedSize(400, 200)
        
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("<b>Seu acesso não está liberado.</b>"))
        layout.addWidget(QLabel("Confirme seu e-mail para solicitar autorização:"))
        
        self.input_email = QLineEdit(email_atual)
        self.input_email.setPlaceholderText("usuario@empresa.com")
        layout.addWidget(self.input_email)
        
        self.btn_solicitar = QPushButton("🚀 Enviar Solicitação ao Administrador")
        self.btn_solicitar.setStyleSheet("""
            QPushButton { background-color: #28a745; color: white; font-weight: bold; padding: 10px; border-radius: 5px; }
            QPushButton:hover { background-color: #218838; }
        """)
        self.btn_solicitar.clicked.connect(self.aceitar)
        layout.addWidget(self.btn_solicitar)
        
        self.email_confirmado = None

    def aceitar(self):
        email = self.input_email.text().strip()
        if "@" not in email:
            QMessageBox.warning(self, "Erro", "Insira um e-mail válido.")
            return
        self.email_confirmado = email
        self.accept()