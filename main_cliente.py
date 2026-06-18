"""
Ponto de entrada do Transmissor.
Execute com:
    python main_cliente.py
"""
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from cliente.ui_cliente import ClienteUI

if __name__ == '__main__':
    janela = ClienteUI()
    janela.connect('destroy', Gtk.main_quit)
    janela.show_all()
    Gtk.main()
