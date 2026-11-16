'''
Permite ao usuário configurar e executar toda a cadeia de transmissão,
visualizando os sinais digitais e de portadora em tempo real.

'''

import gi #cria inteface gráfica
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Pango # type: ignore

import matplotlib #equações matematicas
import numpy as np #analise de dados
from matplotlib.figure import Figure
from cliente.transmitter import Transmitter
from camada_fisica.ruido import NIVEIS_RUIDO
from camada_enlace.deteccao_erros import TAMANHOS_EDC, EDC_PADRAO
from camada_enlace.enquadramento import TAMANHO_QUADRO_PADRAO, TAMANHO_QUADRO_MAX

RUIDO_PERSONALIZADO = 'Personalizado'   # identificador da 4ª opção do combo de ruído (μ e σ livres)
try:
    # Canvas Cairo: desenha os textos dos eixos com o próprio Cairo/GTK
    from matplotlib.backends.backend_gtk3cairo import FigureCanvasGTK3Cairo as FigureCanvas
except ImportError:
    from matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg as FigureCanvas

# Configurações globais dos gráficos (sem LaTeX, tamanho da fonte e resolução).
matplotlib.rcParams['text.usetex'] = False
matplotlib.rcParams['font.size'] = 9
matplotlib.rcParams['figure.dpi'] = 80 

AMOSTRAS_POR_BIT = 100   # amostras por bit nos sinais banda-base (1 bit = 1 s no eixo do tempo)

# Janela do transmissor: entrada da mensagem, escolha dos protocolos e do ruído, pipeline e gráficos.
class ClienteUI(Gtk.Window):
    def __init__(self):
        super().__init__(title='Simulador TR1 — Transmissor')
        self.set_border_width(12)
        self.set_default_size(980, 900)

        # Cria o transmissor, que guarda os protocolos escolhidos e executa a cadeia de codificação.
        self.transmitter = Transmitter()

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
        # Caixa onde o usuário digita a mensagem.
        frame_entrada = Gtk.Frame(label=' Mensagem ')
        raiz.pack_start(frame_entrada, False, False, 0)
        self.entrada = Gtk.Entry()
        self.entrada.set_placeholder_text('Digite o texto a transmitir…')
        self.entrada.set_margin_top(6)
        self.entrada.set_margin_bottom(6)
        self.entrada.set_margin_start(6)
        self.entrada.set_margin_end(6)
        frame_entrada.add(self.entrada)

        # Configurações dos protocolos (4 combos, o tamanho do quadro e do EDC, e o ruído)
        # Quadro com as listas de escolha dos protocolos e do nível de ruído.
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
        # Define as opções de cada lista de escolha (a primeira opção é a padrão).
        self.combo_mod_digital = self._combo(
            ['NRZ-Polar', 'Manchester', 'Bipolar'])
        
        self.combo_mod_portadora = self._combo(
            ['ASK', 'FSK', '8PSK', '32-QAM'])
        
        self.combo_enquadramento = self._combo(
            ['Contagem de Caracteres', 'Inserção de Bytes', 'Inserção de Bits'])
        
        self.combo_deteccao = self._combo(
            ['Paridade Par', 'Checksum', 'CRC', 'Entrelaçamento de Bits'])
        
        # Seleciona o CRC como detecção padrão.
        self.combo_deteccao.set_active(2)   # CRC como padrão

        # Coloca as quatro listas na linha 1 da grade, uma por coluna.
        for col, combo in enumerate([
            self.combo_mod_digital,
            self.combo_mod_portadora,
            self.combo_enquadramento,
            self.combo_deteccao,
        ]):
            combo.set_hexpand(True)
            grade.attach(combo, col, 1, 1, 1)

        # Linha 2 — rótulos; linha 3 — campos: nível de ruído (AWGN), tamanho máximo do quadro
        # (sob o enquadramento) e tamanho do EDC (sob a detecção)
        lbl_quadro = Gtk.Label()
        lbl_quadro.set_markup('<b>Tamanho máx. do quadro (bytes)</b>')
        lbl_quadro.set_xalign(0.0)
        grade.attach(lbl_quadro, 2, 2, 1, 1)

        self.spin_quadro = Gtk.SpinButton.new_with_range(1, TAMANHO_QUADRO_MAX, 1)   # 1 a 255 (cabeçalho de 1 byte)
        self.spin_quadro.set_value(TAMANHO_QUADRO_PADRAO)
        self.spin_quadro.set_numeric(True)
        self.spin_quadro.set_hexpand(True)
        grade.attach(self.spin_quadro, 2, 3, 1, 1)

        # Controle de erros: cada protocolo pode ser desativado, mas nunca os dois ao mesmo tempo.
        lbl_ctrl = Gtk.Label()
        lbl_ctrl.set_markup('<b>Controle de Erros</b>')
        lbl_ctrl.set_xalign(0.0)
        grade.attach(lbl_ctrl, 1, 2, 1, 1)

        caixa_ctrl = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.chk_deteccao = Gtk.CheckButton(label='Detecção de erros')
        self.chk_hamming  = Gtk.CheckButton(label='Hamming')
        self.chk_deteccao.set_active(True)
        self.chk_hamming.set_active(True)
        caixa_ctrl.pack_start(self.chk_deteccao, False, False, 0)
        caixa_ctrl.pack_start(self.chk_hamming, False, False, 0)
        grade.attach(caixa_ctrl, 1, 3, 1, 1)
        self.chk_deteccao.connect('toggled', self._atualizar_controle_de_erros)
        self.chk_hamming.connect('toggled', self._atualizar_controle_de_erros)

        lbl_edc = Gtk.Label()
        lbl_edc.set_markup('<b>Tamanho do EDC (bits)</b>')
        lbl_edc.set_xalign(0.0)
        grade.attach(lbl_edc, 3, 2, 1, 1)

        self.combo_edc = Gtk.ComboBoxText()   # as opções dependem da detecção escolhida
        self.combo_edc.set_hexpand(True)
        grade.attach(self.combo_edc, 3, 3, 1, 1)
        self.combo_deteccao.connect('changed', self._ao_mudar_deteccao)
        self._ao_mudar_deteccao(self.combo_deteccao)   # preenche as opções para a detecção inicial

        lbl_ruido = Gtk.Label()
        lbl_ruido.set_markup('<b>Nível de Ruído (AWGN)</b>')
        lbl_ruido.set_xalign(0.0)
        grade.attach(lbl_ruido, 0, 2, 1, 1)

        # Lista de níveis de ruído (Baixo, Médio, Alto), montada a partir de NIVEIS_RUIDO, mais a opção personalizada.
        self.combo_ruido = Gtk.ComboBoxText()
        for nivel, (_, sigma) in NIVEIS_RUIDO.items():
            self.combo_ruido.append(nivel, f'{nivel} (σ = {sigma:g} V)')
        self.combo_ruido.append(RUIDO_PERSONALIZADO, 'Ruído Personalizado (μ e σ livres)')
        self.combo_ruido.set_hexpand(True)
        grade.attach(self.combo_ruido, 0, 3, 1, 1)

        # Linha 4 — rótulos; linha 5 — campos de média (μ) e desvio padrão (σ) do ruído gaussiano.
        # Os campos só podem ser editados na opção personalizada; nas demais mostram o nível escolhido.
        lbl_media = Gtk.Label()
        lbl_media.set_markup('<b>Média μ do ruído (V)</b>')
        lbl_media.set_xalign(0.0)
        grade.attach(lbl_media, 0, 4, 1, 1)
        self.spin_media = Gtk.SpinButton.new_with_range(-10.0, 10.0, 0.1)
        self.spin_media.set_digits(2)
        self.spin_media.set_numeric(True)
        grade.attach(self.spin_media, 0, 5, 1, 1)

        lbl_sigma = Gtk.Label()
        lbl_sigma.set_markup('<b>Desvio padrão σ do ruído (V)</b>')
        lbl_sigma.set_xalign(0.0)
        grade.attach(lbl_sigma, 1, 4, 1, 1)
        self.spin_sigma = Gtk.SpinButton.new_with_range(0.0, 20.0, 0.1)
        self.spin_sigma.set_digits(2)
        self.spin_sigma.set_numeric(True)
        grade.attach(self.spin_sigma, 1, 5, 1, 1)

        self.combo_ruido.connect('changed', self._ao_mudar_ruido)
        self.combo_ruido.set_active(0)   # Baixo como padrão (também preenche os campos μ e σ)

        # Botão Transmitir
        self.btn_transmitir = Gtk.Button(label='▶  Transmitir')
        self.btn_transmitir.connect('clicked', self._ao_transmitir)
        raiz.pack_start(self.btn_transmitir, False, False, 0)

        # Saída de texto (etapas do pipeline)
        frame_saida = Gtk.Frame(label=' Pipeline de Codificação ')
        raiz.pack_start(frame_saida, False, False, 0)

        # Área com rolagem que mostra as etapas do pipeline de codificação.
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

        # Os canvas dos gráficos são criados a cada transmissão.
        self.canvas1 = None
        self.canvas2 = None


    # Cria uma lista de escolha com as opções informadas.
    def _combo(self, opcoes: list[str]) -> Gtk.ComboBoxText:
        cb = Gtk.ComboBoxText()
        for op in opcoes:
            cb.append(op, op)

        cb.set_active(0)
        return cb

    # Atualiza as opções de tamanho do EDC conforme a detecção escolhida (paridade e CRC têm tamanho fixo).
    def _ao_mudar_deteccao(self, combo):
        deteccao = combo.get_active_text()
        opcoes = TAMANHOS_EDC.get(deteccao, [])
        self.combo_edc.remove_all()
        for op in opcoes:
            self.combo_edc.append(str(op), str(op))
        self.combo_edc.set_active(opcoes.index(EDC_PADRAO[deteccao]) if opcoes else -1)   # seleciona o padrão
        self._atualizar_controle_de_erros()

    # Garante que Hamming e detecção nunca fiquem desativados juntos: o que sobrou ativo é travado.
    # Também libera as escolhas da detecção (tipo e tamanho do EDC) só quando ela está ativa.
    def _atualizar_controle_de_erros(self, *_):
        usa_det = self.chk_deteccao.get_active()
        usa_ham = self.chk_hamming.get_active()
        self.chk_hamming.set_sensitive(usa_det)    # com a detecção desativada, o Hamming não pode ser desmarcado.
        self.chk_deteccao.set_sensitive(usa_ham)   # com o Hamming desativado, a detecção não pode ser desmarcada.
        self.combo_deteccao.set_sensitive(usa_det)
        n_opcoes = len(TAMANHOS_EDC.get(self.combo_deteccao.get_active_text(), []))
        self.combo_edc.set_sensitive(usa_det and n_opcoes > 1)   # com uma única opção não há o que escolher

    # Mostra os valores do nível de ruído escolhido; só a opção personalizada deixa μ e σ editáveis.
    def _ao_mudar_ruido(self, combo):
        nivel = combo.get_active_id()
        personalizado = (nivel == RUIDO_PERSONALIZADO)
        if not personalizado and nivel in NIVEIS_RUIDO:
            media, sigma = NIVEIS_RUIDO[nivel]
            self.spin_media.set_value(media)
            self.spin_sigma.set_value(sigma)
        self.spin_media.set_sensitive(personalizado)
        self.spin_sigma.set_sensitive(personalizado)

    # Mostra uma janela de aviso com a mensagem informada.
    def _aviso(self, msg: str):
        dlg = Gtk.MessageDialog(
            parent=self,
            type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK,
            message_format=msg,
        )
        dlg.run()
        dlg.destroy()

    # Executado ao clicar em 'Transmitir': lê as escolhas, codifica, envia ao servidor e atualiza a tela.
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
        self.spin_quadro.update()   # confirma o valor digitado (sem precisar de Enter) antes de lê-lo
        self.transmitter.tamanho_quadro = self.spin_quadro.get_value_as_int()
        self.transmitter.tamanho_edc    = int(self.combo_edc.get_active_text())
        self.transmitter.usar_deteccao  = self.chk_deteccao.get_active()
        self.transmitter.usar_hamming   = self.chk_hamming.get_active()
        self.spin_media.update()   # confirma os valores digitados antes de lê-los
        self.spin_sigma.update()
        self.transmitter.media_ruido = self.spin_media.get_value()   # nos níveis predefinidos, os campos já mostram o μ e o σ do nível
        self.transmitter.sigma_ruido = self.spin_sigma.get_value()

        try:
            resultado = self.transmitter.processar(texto)

        except Exception as exc:
            self._aviso(f'Erro ao processar mensagem:\n{exc}')
            return

        # Envia o sinal limpo ao meio de comunicação (servidor), que soma o AWGN e responde
        # Envia os sinais ao servidor; se ele estiver fora do ar, o aviso é exibido.
        resposta = None
        try:
            resposta = self.transmitter.enviar(resultado)

        except OSError as exc:
            self._aviso(str(exc))

        # Exibe etapas do pipeline
        # Corta as sequências de bits longas para caber na tela.
        def resumo(s, max_len=80):
            return s[:max_len] + ('…' if len(s) > max_len else '')

        saida = (
            f"  - Mensagem transmitida: {resultado['texto']}\n"
            f"  - Mensagem convertida para bits: {resumo(resultado['bits_brutos'])}\n"
            f"  - Bits com enquadramento: {resumo(resultado['bits_enquadrado'])}\n"
            f"  - Bits com a detecção de erro aplicada: "
            f"{resumo(resultado['bits_deteccao']) if self.transmitter.usar_deteccao else '(desativada)'}\n"
            f"  - Bits com o hamming aplicado: "
            f"{resumo(resultado['bits_hamming']) if self.transmitter.usar_hamming else '(desativado)'}\n"
        )

        exibir = resultado
        if resposta is not None:
            # Os gráficos mostram os sinais que chegaram ao receptor, já com ruído
            exibir = dict(
                resultado,
                sinal_digital=np.array(resposta['banda_base']['sinal_ruidoso']),
                sinal_portadora=(np.array(resposta['portadora']['tempo']),
                                 np.array(resposta['portadora']['sinal_ruidoso'])),
            )

        self.label_saida.set_text(saida)

        # Atualiza gráficos
        self._atualizar_graficos(exibir, resultado)

    # Desenha o sinal digital e o de portadora (ruidoso sobre o original em cinza).
    def _atualizar_graficos(self, resultado: dict, limpo: dict):
        # resultado: sinais exibidos (com ruído, se houver); limpo: sinais originais, desenhados em cinza ao fundo
        mod_digital   = self.transmitter.mod_digital
        mod_portadora = self.transmitter.mod_portadora

        # Atualiza rótulos GTK
        self.lbl_titulo_digital.set_markup(f'<b>Digital — {mod_digital}</b>')
        self.lbl_titulo_portadora.set_markup(f'<b>Portadora — {mod_portadora}</b>')

        # Limite de pontos desenhados por gráfico (reduz as amostras para a tela não travar).
        MAX_PTS = 1000

        # Gráfico 1: sinal digital
        for filho in self.scroll_graf1.get_children():
            self.scroll_graf1.remove(filho)

        sinal_d = np.asarray(resultado['sinal_digital'])
        limpo_d = np.asarray(limpo['sinal_digital'])
        tempo_d = np.arange(len(sinal_d)) / AMOSTRAS_POR_BIT
        if len(sinal_d) > MAX_PTS:
            idx = np.linspace(0, len(sinal_d) - 1, MAX_PTS, dtype=int)
            sinal_d = sinal_d[idx]
            limpo_d = limpo_d[idx]
            tempo_d = tempo_d[idx]

        # Cria a figura, os eixos e as legendas do gráfico digital.
        fig1 = Figure(figsize=(12, 2.5), dpi=80)
        ax1  = fig1.add_subplot(1, 1, 1)
        fig1.subplots_adjust(top=0.95, bottom=0.22, left=0.07, right=0.99)
        ax1.set_xlabel('Tempo (s)')
        ax1.set_ylabel('Tensão (V)')
        
        ax1.step(tempo_d, limpo_d, where='post',
                color='lightgray', linewidth=2.0)       # sinal original, ao fundo

        ax1.step(tempo_d, sinal_d, where='post',
                color='steelblue', linewidth=1.0)
        
        ax1.grid(True, alpha=0.3)

        # Insere o gráfico digital na janela.
        self.canvas1 = FigureCanvas(fig1)
        self.canvas1.set_size_request(900, 200)
        self.scroll_graf1.add(self.canvas1)

        # Gráfico 2: sinal de portadora
        for filho in self.scroll_graf2.get_children():
            self.scroll_graf2.remove(filho)

        tempo, sinal_p = resultado['sinal_portadora']
        limpo_p = np.asarray(limpo['sinal_portadora'][1])

        if len(sinal_p) > MAX_PTS:
            idx = np.linspace(0, len(sinal_p) - 1, MAX_PTS, dtype=int)
            tempo   = tempo[idx]
            sinal_p = sinal_p[idx]
            limpo_p = limpo_p[idx]

        # Cria a figura, os eixos e as legendas do gráfico de portadora.
        fig2 = Figure(figsize=(12, 2.5), dpi=80)
        ax2  = fig2.add_subplot(1, 1, 1)
        fig2.subplots_adjust(top=0.95, bottom=0.22, left=0.07, right=0.99)
        ax2.set_xlabel('Tempo (s)')
        ax2.set_ylabel('Tensão (V)')
        
        ax2.plot(tempo, limpo_p, color='lightgray', linewidth=2.0)   # sinal original, ao fundo
        ax2.plot(tempo, sinal_p, color='darkorange', linewidth=0.8)
        ax2.grid(True, alpha=0.3)

        # Insere o gráfico de portadora na janela.
        self.canvas2 = FigureCanvas(fig2)
        self.canvas2.set_size_request(900, 200)
        self.scroll_graf2.add(self.canvas2)

        self.scroll_graf1.show_all()
        self.scroll_graf2.show_all()