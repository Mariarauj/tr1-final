"""
Ponto de entrada do Receptor/Servidor.
Execute com:
    python main_servidor.py
"""
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from servidor.ui_servidor import ServidorUI

if __name__ == '__main__':
    janela = ServidorUI()
    janela.connect('destroy', Gtk.main_quit)
    janela.show_all()
    Gtk.main()
