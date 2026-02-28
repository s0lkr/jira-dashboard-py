import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon  # carrega icon no qt

from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    
    # carrega qss
    try:
        with open("ui/style.qss", "r", encoding="utf-8") as arquivo_estilo:
            app.setStyleSheet(arquivo_estilo.read())
    except FileNotFoundError:
        print("Aviso: Arquivo style.qss não encontrado. Carregando tema padrão do Windows.")

    # icon
    app.setWindowIcon(QIcon("ui/assets/app_icon.png"))

    # Inicia
    janela = MainWindow()
    janela.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()