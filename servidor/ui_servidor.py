'''
Exibe um terminal de log com todas as etapas do pipeline RX
(demodulação, desenquadramento, detecção e correção de erro)

'''

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Pango, GLib # type: ignore

from servidor.receiver import Receiver


class ServidorUI(Gtk.Window):
    def __init__(self):
        super().__init__(title='Simulador TR1 — Receptor')
        self.set_border_width(10)
        self.set_default_size(820, 620)

        # HeaderBar
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        titulo = Gtk.Label()
        titulo.set_markup(
            '<span font="16" weight="bold" foreground="#2c3e50">'
            'Receptor de Dados</span>'
        )
        titulo.set_xalign(0.0)
        header.pack_start(titulo)
        subtitulo = Gtk.Label()
        subtitulo.set_markup(
            '<span font="10" foreground="#7f8c8d">Terminal de log</span>'
        )
        header.pack_end(subtitulo)
        self.set_titlebar(header)

        # Layout principal
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.add(vbox)

        # Área de texto (terminal de log)
        self.text_view = Gtk.TextView()
        self.text_view.set_editable(False)
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.text_view.set_left_margin(10)
        self.text_view.set_right_margin(10)
        self.text_view.modify_font(Pango.FontDescription('Monospace 11'))

        # Fundo cinza-claro via CSS
        css = b'textview, textview text { background: #f4f4f4; }'
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        self.buffer = self.text_view.get_buffer()

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        scroll.add(self.text_view)

        # Botão iniciar
        self.btn_iniciar = Gtk.Button(label='🚀  Iniciar Servidor')
        self.btn_iniciar.connect('clicked', self._ao_iniciar)
        self.btn_iniciar.set_hexpand(True)
        vbox.pack_start(self.btn_iniciar, False, False, 0)
        vbox.pack_start(scroll, True, True, 0)

        # Receptor (não iniciado ainda)
        self.receiver = Receiver(self._atualizar_ui)

    def _ao_iniciar(self, _btn):
        self.btn_iniciar.set_label('✅  Servidor em execução')
        self.btn_iniciar.set_sensitive(False)
        self.receiver.iniciar()
        self._adicionar_texto('✅ Servidor iniciado com sucesso!\n')

    def _atualizar_ui(self, texto: str):
        GLib.idle_add(self._adicionar_texto, texto)

    def _adicionar_texto(self, texto: str):
        marca = self.buffer.create_mark(None, self.buffer.get_end_iter(), False)
        self.buffer.insert(self.buffer.get_end_iter(), texto)
        self.text_view.scroll_to_mark(marca, 0.0, False, 0.0, 0.0)
