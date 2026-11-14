#python main_servidor.py

# Ponto de entrada do receptor: abre a janela do simulador (GTK).
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk # type: ignore

from servidor.ui_servidor import ServidorUI

# Cria a janela, encerra o programa ao fechá-la e inicia o laço de eventos da interface.
if __name__ == '__main__':
    janela = ServidorUI()
    janela.connect('destroy', Gtk.main_quit)
    janela.show_all()
    Gtk.main()