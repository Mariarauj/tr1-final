'''
Encapsula toda a cadeia de processamento: texto - bits - quadros com EDC por quadro (enquadramento +
detecção de erros) - Hamming - modulação digital - modulação por portadora - envio TCP
(a detecção de erros e o Hamming podem ser desativados, mas nunca os dois ao mesmo tempo)
(μ e σ do ruído gaussiano são configurados aqui e aplicados pelo meio de comunicação, no servidor)

'''
import json
import socket
import struct

import numpy as np

from auxiliar import texto_para_bits, receber_exato
from camada_enlace.hamming import transmissor_hamming_blocos
from camada_enlace.deteccao_erros import EDC_PADRAO, TAMANHOS_EDC, edc_valido
from camada_enlace.enquadramento import TAMANHO_QUADRO_PADRAO, TAMANHO_QUADRO_MAX, tamanho_quadro_valido
from camada_enlace.quadros import montar_quadros
from camada_fisica.modulacao import (
    nrz_polar, manchester, bipolar,
    ask, fsk, psk8, qam32,
)

# Endereço e porta do servidor (meio de comunicação) para onde os sinais são enviados.
HOST = '127.0.0.1'
PORT = 5000


class Transmitter:
    #Gerencia o pipeline de transmissão.
    def __init__(
        self,
        mod_digital: str = 'NRZ-Polar',
        mod_portadora: str = 'ASK',
        enquadramento: str = 'Contagem de Caracteres',
        deteccao: str = 'CRC',
        tamanho_quadro: int = TAMANHO_QUADRO_PADRAO,
        tamanho_edc: int | None = None,
        usar_hamming: bool = True,
        usar_deteccao: bool = True,
        media_ruido: float = 0.0,
        sigma_ruido: float = 0.05,
    ):
        # Guarda os protocolos e o nível de ruído escolhidos (a interface altera esses valores antes de transmitir).
        self.mod_digital   = mod_digital
        self.mod_portadora = mod_portadora
        self.enquadramento = enquadramento
        self.deteccao      = deteccao
        self.tamanho_quadro = tamanho_quadro   # tamanho máximo do quadro, em bytes de dados
        self.tamanho_edc    = tamanho_edc      # tamanho do EDC, em bits (None = padrão da detecção escolhida)
        self.usar_hamming   = usar_hamming     # False = transmite sem a correção de Hamming
        self.usar_deteccao  = usar_deteccao    # False = transmite os quadros sem EDC
        self.media_ruido   = media_ruido
        self.sigma_ruido   = sigma_ruido

    # Pipeline de codificação (TX)
    def codificar_texto(self, texto: str) -> str:
        # Converte mesnagem para bits
        return texto_para_bits(texto)

    def aplicar_hamming(self, bits: str) -> str:
        # codifica para Hamming.
        return transmissor_hamming_blocos(bits)

    def edc_efetivo(self) -> int:
        # Tamanho do EDC (bits) que será usado: o escolhido pelo usuário ou, se nenhum foi escolhido, o padrão da detecção.
        edc = EDC_PADRAO.get(self.deteccao, 32) if self.tamanho_edc is None else self.tamanho_edc
        if not edc_valido(self.deteccao, edc):   # só valem os tamanhos previstos para cada detecção.
            raise ValueError(f'Tamanho de EDC inválido para {self.deteccao}: {edc} bits '
                             f'(opções: {TAMANHOS_EDC.get(self.deteccao)})')
        return edc

    def validar_controle_de_erros(self):
        # Pelo menos um dos dois protocolos de controle de erros precisa estar ativo.
        if not (self.usar_hamming or self.usar_deteccao):
            raise ValueError('Ative o Hamming ou a detecção de erros: os dois não podem ficar desativados.')

    def validar_quadro(self):
        # O tamanho máximo do quadro vale para os três protocolos de enquadramento.
        if not tamanho_quadro_valido(self.tamanho_quadro):
            raise ValueError(f'Tamanho de quadro inválido: {self.tamanho_quadro} '
                             f'(use um inteiro de 1 a {TAMANHO_QUADRO_MAX} bytes)')

    def aplicar_enquadramento(self, bits: str) -> str:
        # Divide em quadros de até 'tamanho_quadro' bytes e enquadra cada um (ainda sem EDC).
        # O texto é codificado em bytes (8 bits por caractere): não há padding a registrar.
        self.validar_quadro()
        return montar_quadros(bits, self.enquadramento, self.tamanho_quadro)

    def aplicar_deteccao(self, bits: str) -> str:
        # Enquadra cada quadro e anexa a ele o seu próprio EDC (tamanho configurado), pela detecção escolhida.
        self.validar_quadro()
        return montar_quadros(bits, self.enquadramento, self.tamanho_quadro, self.deteccao, self.edc_efetivo())

    def modular_digital(self, bits: list[int]) -> np.ndarray:
        # Seleciona a modulação digital (banda-base).
        if self.mod_digital == 'Manchester':
            return manchester(bits)
        
        elif self.mod_digital == 'Bipolar':
            return bipolar(bits)
        
        else:                                   
            return nrz_polar(bits)

    def modular_portadora(self, bits: list[int]) -> tuple:
        # Seleciona modulação por portadora.
        if self.mod_portadora == 'FSK':
            return fsk(bits)
        
        elif self.mod_portadora == '8PSK':
            return psk8(bits)
        
        elif self.mod_portadora == '32-QAM':
            return qam32(bits)
        
        else:                                   
            return ask(bits)


    # Pipeline completo
    def processar(self, texto: str) -> dict: 
        # Pipeline de codificação: texto -> bits -> quadros -> EDC de cada quadro -> Hamming.
        self.validar_controle_de_erros()
        bits_brutos     = self.codificar_texto(texto)
        bits_enquadrado = self.aplicar_enquadramento(bits_brutos)   # 1º: quadros (flags, contagem...), sem EDC
        bits_deteccao   = (self.aplicar_deteccao(bits_brutos)       # 2º: cada quadro com o seu EDC
                           if self.usar_deteccao else bits_enquadrado)
        bits_hamming    = (self.aplicar_hamming(bits_deteccao)      # 3º: Hamming por bloco de 8 bits (flags inclusive)
                           if self.usar_hamming else bits_deteccao)

        # Converte a string de bits em lista de inteiros, formato esperado pelos moduladores.
        lista_bits = [int(b) for b in bits_hamming]

        # Modulação dos sinais (limpos: o ruído é somado depois, pelo meio de comunicação)
        sinal_digital          = self.modular_digital(lista_bits)
        tempo, sinal_portadora = self.modular_portadora(lista_bits)

        # Devolve todas as etapas e os sinais modulados (limpos) para exibição e envio.
        return {
            'texto'          : texto,
            'bits_brutos'    : bits_brutos,
            'bits_hamming'   : bits_hamming,
            'bits_deteccao'  : bits_deteccao,
            'bits_enquadrado': bits_enquadrado,
            'sinal_digital'  : sinal_digital,
            'sinal_portadora': (tempo, sinal_portadora),
        }

    
    # Envio via TCP
    def enviar(self, resultado: dict) -> dict:
        # Envia os sinais limpos (banda-base e portadora) ao meio de comunicação (servidor) e
        # devolve a resposta dele. Para cada caminho ('banda_base' e 'portadora'): sinal ruidoso,
        # bits ruidosos (antes de qualquer tratamento) e texto recebido.
        # Separa o tempo e o sinal da portadora.
        t, sinal = resultado['sinal_portadora']

        # Monta o pacote: protocolos escolhidos, nível de ruído, tamanhos úteis e os sinais limpos.
        payload = {
            'modulacao_digital': self.mod_digital,
            'modulacao'    : self.mod_portadora,
            'enquadramento': self.enquadramento,
            'deteccao'     : self.deteccao,
            'tamanho_quadro': self.tamanho_quadro,   # só informativo para o receptor (os quadros se delimitam sozinhos)
            'tamanho_edc'  : self.edc_efetivo() if self.usar_deteccao else None,   # o receptor precisa dele para separar o EDC dos dados
            'usar_deteccao': self.usar_deteccao,     # o receptor só confere o EDC se ele foi enviado
            'usar_hamming' : self.usar_hamming,      # o receptor só corrige com Hamming se ele foi aplicado
            'media_ruido'  : self.media_ruido,
            'sigma_ruido'  : self.sigma_ruido,
            'mensagem'     : resultado['texto'],   # exibida no servidor como "mensagem esperada"
            'n_dados'      : len(resultado['bits_deteccao']),  # tamanho antes do Hamming (descarta padding do último bloco)
            'n_bits'       : len(resultado['bits_hamming']),   # descarta o padding do último símbolo
            'sinal_digital': np.asarray(resultado['sinal_digital']).tolist(),
            'tempo'        : t.tolist() if hasattr(t, 'tolist') else list(t),
            'sinal'        : sinal.tolist() if hasattr(sinal, 'tolist') else list(sinal),
        }

        # Serializa o pacote em JSON; o tamanho (4 bytes) vai na frente para o receptor saber quanto ler.
        dados = json.dumps(payload).encode('utf-8')
        tamanho = struct.pack('!I', len(dados))

        # Conecta ao servidor, envia o pacote e aguarda a resposta (sinais ruidosos, bits e texto recebido).
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(10)
                sock.connect((HOST, PORT))
                sock.sendall(tamanho)
                sock.sendall(dados)

                tamanho_resp = struct.unpack('!I', receber_exato(sock, 4))[0]
                return json.loads(receber_exato(sock, tamanho_resp).decode('utf-8'))

        except ConnectionRefusedError:
            raise ConnectionRefusedError(
                f'Não foi possível conectar ao servidor em {HOST}:{PORT}. '
                'Certifique-se de que o servidor está em execução.'
            )