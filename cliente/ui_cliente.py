'''
Permite ao usuário configurar e executar toda a cadeia de transmissão,
visualizando os sinais digitais e de portadora em tempo real.

'''

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Pango # type: ignore

import matplotlib
import numpy as np
from matplotlib.figure import Figure
from cliente.transmitter import Transmitter
from matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg as FigureCanvas

matplotlib.rcParams['text.usetex'] = False
matplotlib.rcParams['font.size'] = 9
matplotlib.rcParams['figure.dpi'] = 80 

class ClienteUI(Gtk.Window):
    def __init__(self):
        super().__init__(title='Simulador TR1 — Transmissor')
        self.set_border_width(12)
        self.set_default_size(980, 900)

        self.transmitter = Transmitter()
        self.nome_usuario = 'Usuário'
        self._pedir_nome()

        # HeaderBar
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)

        titulo = Gtk.Label()
        titulo.set_markup(
            '<span font="16" weight="bold" foreground="#2c3e50">'
            'Transmissor de Dados</span>'
        )

        titulo.set_xalign(0.0)
        header.pack_start(titulo)

        subtitulo = Gtk.Label()
        subtitulo.set_markup(
            '<span font="10" foreground="#7f8c8d">'
            'Teleinformática e Redes 1</span>'
        )

        header.pack_end(subtitulo)
        self.set_titlebar(header)

        # Layout raiz
        raiz = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(raiz)

        # Entrada de texto
        frame_entrada = Gtk.Frame(label=' Mensagem ')
        raiz.pack_start(frame_entrada, False, False, 0)
        self.entrada = Gtk.Entry()
        self.entrada.set_placeholder_text('Digite o texto a transmitir…')
        self.entrada.set_margin_top(6)
        self.entrada.set_margin_bottom(6)
        self.entrada.set_margin_start(6)
        self.entrada.set_margin_end(6)
        frame_entrada.add(self.entrada)

        # Configurações dos protocolos (4 combos)
        frame_cfg = Gtk.Frame(label=' Configuração dos Protocolos ')
        raiz.pack_start(frame_cfg, False, False, 0)
        grade = Gtk.Grid(column_spacing=12, row_spacing=6)
        grade.set_margin_top(8)
        grade.set_margin_bottom(8)
        grade.set_margin_start(8)
        grade.set_margin_end(8)
        frame_cfg.add(grade)

        # Linha 0 — rótulos
        for col, texto in enumerate(
            ['Modulação Digital', 'Modulação por Portadora',
             'Enquadramento', 'Detecção de Erros']
        ):
            lbl = Gtk.Label()
            lbl.set_markup(f'<b>{texto}</b>')
            lbl.set_xalign(0.0)
            grade.attach(lbl, col, 0, 1, 1)

        # Linha 1 — combos
        self.combo_mod_digital = self._combo(
            ['NRZ-Polar', 'Manchester', 'Bipolar'])
        
        self.combo_mod_portadora = self._combo(
            ['ASK', 'FSK', 'QPSK', '16-QAM'])
        
        self.combo_enquadramento = self._combo(
            ['Contagem de Caracteres', 'Inserção de Bytes', 'Inserção de Bits'])
        
        self.combo_deteccao = self._combo(
            ['Paridade Par', 'Checksum', 'CRC'])
        
        self.combo_deteccao.set_active(2)   # CRC como padrão

        for col, combo in enumerate([
            self.combo_mod_digital,
            self.combo_mod_portadora,
            self.combo_enquadramento,
            self.combo_deteccao,
        ]):
            combo.set_hexpand(True)
            grade.attach(combo, col, 1, 1, 1)

        # Botão Transmitir
        self.btn_transmitir = Gtk.Button(label='▶  Transmitir')
        self.btn_transmitir.connect('clicked', self._ao_transmitir)
        raiz.pack_start(self.btn_transmitir, False, False, 0)

        # Saída de texto (etapas do pipeline)
        frame_saida = Gtk.Frame(label=' Pipeline de Codificação ')
        raiz.pack_start(frame_saida, False, False, 0)

        scroll_saida = Gtk.ScrolledWindow()
        scroll_saida.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll_saida.set_min_content_height(140)
        frame_saida.add(scroll_saida)

        self.label_saida = Gtk.Label()
        self.label_saida.set_line_wrap(True)
        self.label_saida.set_xalign(0.0)
        self.label_saida.set_margin_start(6)
        mono = Pango.FontDescription('Monospace 10')
        self.label_saida.modify_font(mono)
        scroll_saida.add(self.label_saida)

        # Área dos gráficos ----------------------------------------------------
        frame_graficos = Gtk.Frame(label=' Sinais ')
        raiz.pack_start(frame_graficos, True, True, 0)

        box_graficos = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box_graficos.set_margin_top(4)
        box_graficos.set_margin_bottom(4)
        box_graficos.set_margin_start(4)
        box_graficos.set_margin_end(4)
        frame_graficos.add(box_graficos)

        # Rótulo do gráfico digital (GTK, fora do Matplotlib)
        self.lbl_titulo_digital = Gtk.Label()
        self.lbl_titulo_digital.set_markup('<b>Digital</b>')
        self.lbl_titulo_digital.set_xalign(0.0)
        box_graficos.pack_start(self.lbl_titulo_digital, False, False, 0)

        self.scroll_graf1 = Gtk.ScrolledWindow()
        self.scroll_graf1.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.scroll_graf1.set_min_content_height(200)
        self.scroll_graf1.set_hexpand(True)
        self.scroll_graf1.set_vexpand(True)
        box_graficos.pack_start(self.scroll_graf1, True, True, 0)

        # Rótulo do gráfico de portadora (GTK, fora do Matplotlib)
        self.lbl_titulo_portadora = Gtk.Label()
        self.lbl_titulo_portadora.set_markup('<b>Portadora</b>')
        self.lbl_titulo_portadora.set_xalign(0.0)
        box_graficos.pack_start(self.lbl_titulo_portadora, False, False, 0)

        self.scroll_graf2 = Gtk.ScrolledWindow()
        self.scroll_graf2.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.scroll_graf2.set_min_content_height(200)
        self.scroll_graf2.set_hexpand(True)
        self.scroll_graf2.set_vexpand(True)
        box_graficos.pack_start(self.scroll_graf2, True, True, 0)

        self.canvas1 = None
        self.canvas2 = None


    def _combo(self, opcoes: list[str]) -> Gtk.ComboBoxText:
        cb = Gtk.ComboBoxText()
        for op in opcoes:
            cb.append(op, op)

        cb.set_active(0)
        return cb

    def _pedir_nome(self):
        dlg = Gtk.Dialog(title='Identificação', transient_for=self, flags=0)
        dlg.add_buttons(Gtk.STOCK_OK, Gtk.ResponseType.OK)
        dlg.set_default_size(300, 100)
        area = dlg.get_content_area()
        area.set_spacing(6)
        area.add(Gtk.Label(label='Digite seu nome:'))
        entrada = Gtk.Entry()
        area.add(entrada)
        dlg.show_all()

        if dlg.run() == Gtk.ResponseType.OK:
            self.nome_usuario = entrada.get_text().strip() or 'Usuário'

        dlg.destroy()

    def _aviso(self, msg: str):
        dlg = Gtk.MessageDialog(
            parent=self,
            type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK,
            message_format=msg,
        )
        dlg.run()
        dlg.destroy()

    def _ao_transmitir(self, _widget):
        texto = self.entrada.get_text().strip()

        if not texto:
            self._aviso('Por favor, insira um texto para transmitir.')
            return

        # Atualiza configurações
        self.transmitter.mod_digital   = self.combo_mod_digital.get_active_text()
        self.transmitter.mod_portadora = self.combo_mod_portadora.get_active_text()
        self.transmitter.enquadramento = self.combo_enquadramento.get_active_text()
        self.transmitter.deteccao      = self.combo_deteccao.get_active_text()

        try:
            resultado = self.transmitter.processar(texto)

        except Exception as exc:
            self._aviso(f'Erro ao processar mensagem:\n{exc}')
            return

        # Exibe etapas do pipeline
        def resumo(s, max_len=80):
            return s[:max_len] + ('…' if len(s) > max_len else '')

        saida = (
            f"Mensagem      : {resultado['texto']}\n"
            f"Bits (ASCII)  : {resumo(resultado['bits_brutos'])}\n"
            f"Após Hamming  : {resumo(resultado['bits_hamming'])}\n"
            f"Após Detecção : {resumo(resultado['bits_deteccao'])}\n"
            f"Enquadrado    : {resumo(resultado['bits_enquadrado'])}\n"
            f"Com Ruído     : {resumo(resultado['bits_ruidosos'])}\n"
        )

        self.label_saida.set_text(saida)

        # Atualiza gráficos
        self._atualizar_graficos(resultado)

        # Tenta enviar ao servidor
        try:
            self.transmitter.enviar(resultado, self.nome_usuario)

        except ConnectionRefusedError as exc:
            self._aviso(str(exc))

    def _atualizar_graficos(self, resultado: dict):
        mod_digital   = self.transmitter.mod_digital
        mod_portadora = self.transmitter.mod_portadora

        # Atualiza rótulos GTK
        self.lbl_titulo_digital.set_markup(f'<b>Digital — {mod_digital}</b>')
        self.lbl_titulo_portadora.set_markup(f'<b>Portadora — {mod_portadora}</b>')

        MAX_PTS = 1000

        # Gráfico 1: sinal digital
        for filho in self.scroll_graf1.get_children():
            self.scroll_graf1.remove(filho)

        sinal_d = resultado['sinal_digital']
        if len(sinal_d) > MAX_PTS:
            idx = np.linspace(0, len(sinal_d) - 1, MAX_PTS, dtype=int)
            sinal_d = sinal_d[idx]

        fig1 = Figure(figsize=(12, 2.5), dpi=80)
        ax1  = fig1.add_subplot(1, 1, 1)
        fig1.subplots_adjust(top=0.95, bottom=0.05, left=0.01, right=0.99)
        ax1.set_xticks([])
        ax1.set_yticks([])
        ax1.tick_params(labelbottom=False, labelleft=False,
                        labeltop=False, labelright=False)
        
        ax1.step(range(len(sinal_d)), sinal_d, where='post',
                color='steelblue', linewidth=1.0)
        
        ax1.grid(True, alpha=0.3)

        self.canvas1 = FigureCanvas(fig1)
        self.canvas1.set_size_request(900, 200)
        self.scroll_graf1.add(self.canvas1)

        # Gráfico 2: sinal de portadora
        for filho in self.scroll_graf2.get_children():
            self.scroll_graf2.remove(filho)

        tempo, sinal_p = resultado['sinal_portadora']

        if len(sinal_p) > MAX_PTS:
            idx = np.linspace(0, len(sinal_p) - 1, MAX_PTS, dtype=int)
            tempo   = tempo[idx]
            sinal_p = sinal_p[idx]

        fig2 = Figure(figsize=(12, 2.5), dpi=80)
        ax2  = fig2.add_subplot(1, 1, 1)
        fig2.subplots_adjust(top=0.95, bottom=0.05, left=0.01, right=0.99)
        ax2.set_xticks([])
        ax2.set_yticks([])
        ax2.tick_params(labelbottom=False, labelleft=False,
                        labeltop=False, labelright=False)
        
        ax2.plot(tempo, sinal_p, color='darkorange', linewidth=0.8)
        ax2.grid(True, alpha=0.3)

        self.canvas2 = FigureCanvas(fig2)
        self.canvas2.set_size_request(900, 200)
        self.scroll_graf2.add(self.canvas2)

        self.scroll_graf1.show_all()
        self.scroll_graf2.show_all()