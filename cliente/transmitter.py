"""
Transmissor - Lado TX do pipeline de simulação.
Encapsula toda a cadeia de processamento:
  texto → bits → Hamming → detecção de erros → enquadramento
  → modulação digital → modulação por portadora → ruído gaussiano → envio TCP
"""
import json
import socket
import struct

import numpy as np

from auxiliar import texto_para_bits
from camada_enlace.hamming import transmissor_hamming
from camada_enlace.deteccao_erros import (
    transmissor_paridade,
    transmissor_checksum,
    transmissor_crc,
)
from camada_enlace.enquadramento import (
    transmissor_contagem,
    transmissor_insercao_bytes,
    transmissor_insercao_bits,
)
from camada_fisica.modulacao import (
    nrz_polar, manchester, bipolar,
    ask, fsk, qpsk, qam16,
)
from camada_fisica.ruido import adicionar_ruido_gaussiano

HOST = '127.0.0.1'
PORT = 5000


class Transmitter:
    """Gerencia o pipeline completo de transmissão."""

    def __init__(
        self,
        mod_digital: str = 'NRZ-Polar',
        mod_portadora: str = 'ASK',
        enquadramento: str = 'Contagem de Caracteres',
        deteccao: str = 'CRC',
        sigma_ruido: float = 0.05,
    ):
        self.mod_digital   = mod_digital
        self.mod_portadora = mod_portadora
        self.enquadramento = enquadramento
        self.deteccao      = deteccao
        self.sigma_ruido   = sigma_ruido

    # ------------------------------------------------------------------
    # Pipeline de codificação (TX)
    # ------------------------------------------------------------------

    def codificar_texto(self, texto: str) -> str:
        """Texto → string de bits."""
        return texto_para_bits(texto)

    def aplicar_hamming(self, bits: str) -> str:
        """Adiciona bits de paridade Hamming."""
        return transmissor_hamming(bits)

    def aplicar_deteccao(self, bits: str) -> str:
        """Adiciona bits de detecção de erros."""
        if self.deteccao == 'Paridade Par':
            return transmissor_paridade(bits)
        elif self.deteccao == 'Checksum':
            return transmissor_checksum(bits)
        else:                                   # CRC-32 (padrão)
            return transmissor_crc(bits)

    def aplicar_enquadramento(self, bits: str) -> str:
        """Enquadra os bits. Contagem e Inserção de Bytes exigem múltiplo de 8."""
        # Padding para múltiplo de 8 (necessário para enquadramento por bytes)
        resto = len(bits) % 8
        if resto != 0:
            bits = bits + '0' * (8 - resto)

        if self.enquadramento == 'Contagem de Caracteres':
            return transmissor_contagem(bits)
        elif self.enquadramento == 'Inserção de Bytes':
            return transmissor_insercao_bytes(bits)
        else:                                   # Inserção de Bits
            return transmissor_insercao_bits(bits)

    def modular_digital(self, bits: list[int]) -> np.ndarray:
        """Modulação digital (banda-base)."""
        if self.mod_digital == 'Manchester':
            return manchester(bits)
        elif self.mod_digital == 'Bipolar':
            return bipolar(bits)
        else:                                   # NRZ-Polar (padrão)
            return nrz_polar(bits)

    def modular_portadora(self, bits: list[int]) -> tuple:
        """Modulação por portadora."""
        if self.mod_portadora == 'FSK':
            return fsk(bits)
        elif self.mod_portadora == 'QPSK':
            return qpsk(bits)
        elif self.mod_portadora == '16-QAM':
            return qam16(bits)
        else:                                   # ASK (padrão)
            return ask(bits)

    # ------------------------------------------------------------------
    # Pipeline completo
    # ------------------------------------------------------------------

    def processar(self, texto: str) -> dict:
        """
        Executa a cadeia completa TX e retorna dicionário com
        todas as etapas intermediárias e os sinais produzidos.

        O ruído gaussiano n(0, σ) é aplicado sobre os sinais analógicos
        (após modulação), conforme diagrama do enunciado.
        """
        bits_brutos     = self.codificar_texto(texto)
        bits_hamming    = self.aplicar_hamming(bits_brutos)
        bits_deteccao   = self.aplicar_deteccao(bits_hamming)
        bits_enquadrado = self.aplicar_enquadramento(bits_deteccao)

        lista_bits = [int(b) for b in bits_enquadrado]

        # Modulação dos sinais analógicos
        sinal_digital        = self.modular_digital(lista_bits)
        tempo, sinal_portadora = self.modular_portadora(lista_bits)

        # Ruído gaussiano n(0, σ) sobre os sinais analógicos — meio de comunicação
        sinal_digital_ruidoso   = adicionar_ruido_gaussiano(sinal_digital,   self.sigma_ruido)
        sinal_portadora_ruidosa = adicionar_ruido_gaussiano(sinal_portadora, self.sigma_ruido)

        return {
            'texto'          : texto,
            'bits_brutos'    : bits_brutos,
            'bits_hamming'   : bits_hamming,
            'bits_deteccao'  : bits_deteccao,
            'bits_enquadrado': bits_enquadrado,
            'bits_ruidosos'  : bits_enquadrado,          # mantido para exibição na UI
            'sinal_digital'  : sinal_digital_ruidoso,
            'sinal_portadora': (tempo, sinal_portadora_ruidosa),
        }

    # ------------------------------------------------------------------
    # Envio via TCP
    # ------------------------------------------------------------------

    def enviar(self, resultado: dict, nome: str):
        """
        Serializa e envia os dados ao servidor receptor via TCP.
        O sinal de portadora (com ruído) é enviado junto com os metadados
        necessários para que o receptor possa demodular e decodificar.
        """
        t, sinal = resultado['sinal_portadora']

        payload = {
            'nome'         : nome,
            'modulacao'    : self.mod_portadora,
            'enquadramento': self.enquadramento,
            'deteccao'     : self.deteccao,
            'tempo'        : t.tolist() if hasattr(t, 'tolist') else list(t),
            'sinal'        : sinal.tolist() if hasattr(sinal, 'tolist') else list(sinal),
        }

        dados = json.dumps(payload).encode('utf-8')
        tamanho = struct.pack('!I', len(dados))

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((HOST, PORT))
                sock.sendall(tamanho)
                sock.sendall(dados)
        except ConnectionRefusedError:
            raise ConnectionRefusedError(
                f'Não foi possível conectar ao servidor em {HOST}:{PORT}. '
                'Certifique-se de que o servidor está em execução.'
            )