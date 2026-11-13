'''
Encapsula toda a cadeia de processamento: texto - bits - detecção de erros - Hamming
- enquadramento - modulação digital - modulação por portadora - envio TCP
(μ e σ do ruído gaussiano são configurados aqui e aplicados pelo meio de comunicação, no servidor)

'''
import json
import socket
import struct

import numpy as np

from auxiliar import texto_para_bits, receber_exato
from camada_enlace.hamming import transmissor_hamming
from camada_enlace.deteccao_erros import (
    transmissor_paridade,
    transmissor_checksum,
    transmissor_crc,
)
from camada_enlace.enquadramento import (
    transmissor_contagem,
    transmissor_entrelacamento,
    transmissor_insercao_bytes,
    transmissor_insercao_bits,
)
from camada_fisica.modulacao import (
    nrz_polar, manchester, bipolar,
    ask, fsk, psk8, qam32,
)

HOST = '127.0.0.1'
PORT = 5000

TAMANHO_QUADRO = 8  # tamanho do quadro, em bytes, usado nos enquadramentos


class Transmitter:
    #Gerencia o pipeline de transmissão.
    def __init__(
        self,
        mod_digital: str = 'NRZ-Polar',
        mod_portadora: str = 'ASK',
        enquadramento: str = 'Contagem de Caracteres',
        deteccao: str = 'CRC',
        media_ruido: float = 0.0,
        sigma_ruido: float = 0.05,
    ):
        self.mod_digital   = mod_digital
        self.mod_portadora = mod_portadora
        self.enquadramento = enquadramento
        self.deteccao      = deteccao
        self.media_ruido   = media_ruido
        self.sigma_ruido   = sigma_ruido

    # Pipeline de codificação (TX)
    def codificar_texto(self, texto: str) -> str:
        # Converte mesnagem para bits
        return texto_para_bits(texto)

    def aplicar_hamming(self, bits: str) -> str:
        # codifica para Hamming.
        return transmissor_hamming(bits)

    def aplicar_deteccao(self, bits: str) -> str:
        # seleciona a detecção de erros
        if self.deteccao == 'Paridade Par':
            return transmissor_paridade(bits)
        
        elif self.deteccao == 'Checksum':
            return transmissor_checksum(bits)
        
        else:                                
            return transmissor_crc(bits)

    def aplicar_enquadramento(self, bits: str) -> str: # Seleciona o enquadramento.
        resto = len(bits) % 8
        pad_len = (8 - resto) % 8
        cabecalho_pad = format(pad_len, '08b')
        bits = cabecalho_pad + bits + '0' * pad_len

        if self.enquadramento == 'Contagem de Caracteres':
            return transmissor_contagem(bits, TAMANHO_QUADRO)

        elif self.enquadramento == 'Inserção de Bytes':
            return transmissor_insercao_bytes(bits, TAMANHO_QUADRO)

        elif self.enquadramento == 'Entrelaçamento de Bits':
            return transmissor_entrelacamento(bits, TAMANHO_QUADRO)

        else:                                   # Inserção de Bits
            return transmissor_insercao_bits(bits)

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
        bits_brutos     = self.codificar_texto(texto)
        bits_deteccao   = self.aplicar_deteccao(bits_brutos)    # 1º: código de detecção escolhido
        bits_hamming    = self.aplicar_hamming(bits_deteccao)   # 2º: Hamming sobre dados + código
        bits_enquadrado = self.aplicar_enquadramento(bits_hamming)

        lista_bits = [int(b) for b in bits_enquadrado]

        # Modulação dos sinais (limpos: o ruído é somado depois, pelo meio de comunicação)
        sinal_digital          = self.modular_digital(lista_bits)
        tempo, sinal_portadora = self.modular_portadora(lista_bits)

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
        t, sinal = resultado['sinal_portadora']

        payload = {
            'modulacao_digital': self.mod_digital,
            'modulacao'    : self.mod_portadora,
            'enquadramento': self.enquadramento,
            'deteccao'     : self.deteccao,
            'media_ruido'  : self.media_ruido,
            'sigma_ruido'  : self.sigma_ruido,
            'n_bits'       : len(resultado['bits_enquadrado']),   # descarta o padding do último símbolo
            'sinal_digital': np.asarray(resultado['sinal_digital']).tolist(),
            'tempo'        : t.tolist() if hasattr(t, 'tolist') else list(t),
            'sinal'        : sinal.tolist() if hasattr(sinal, 'tolist') else list(sinal),
        }

        dados = json.dumps(payload).encode('utf-8')
        tamanho = struct.pack('!I', len(dados))

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