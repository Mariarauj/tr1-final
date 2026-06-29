#python main_servidor.py

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk # type: ignore

from servidor.ui_servidor import ServidorUI

if __name__ == '__main__':
    janela = ServidorUI()
    janela.connect('destroy', Gtk.main_quit)
    janela.show_all()
    Gtk.main()
