#python main_cliente.py

# Ponto de entrada do transmissor: abre a janela do simulador (GTK).
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk # type: ignore

from cliente.ui_cliente import ClienteUI

# Cria a janela, encerra o programa ao fechá-la e inicia o laço de eventos da interface.
if __name__ == '__main__':
    janela = ClienteUI()
    janela.connect('destroy', Gtk.main_quit)
    janela.show_all()
    Gtk.main()