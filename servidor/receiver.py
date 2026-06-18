"""
Receptor — Lado RX do pipeline de simulação.
Demodula o sinal recebido e aplica inversamente toda a cadeia de protocolos:
  sinal portadora → demodulação → desenquadramento → detecção de erros
  → correção Hamming → bits → texto
"""
import json
import socket
import struct
import threading

import numpy as np

from auxiliar import bits_para_texto
from camada_enlace.hamming import receptor_hamming
from camada_enlace.deteccao_erros import (
    receptor_paridade,
    receptor_checksum,
    receptor_crc,
)
from camada_enlace.enquadramento import (
    receptor_contagem,
    receptor_insercao_bytes,
    receptor_insercao_bits,
)
from camada_fisica.demodulacao import (
    demod_ask, demod_fsk, demod_qpsk, demod_qam16,
)

HOST = '127.0.0.1'
PORT = 5000


class Receiver:
    """Gerencia o servidor TCP e aplica o pipeline RX a cada mensagem."""

    def __init__(self, callback_ui):
        """
        Parâmetros:
        - callback_ui: função chamada com strings de log para atualizar a UI
        """
        self.callback_ui = callback_ui

    def iniciar(self):
        """Inicia o servidor TCP em thread separada."""
        thread = threading.Thread(target=self._executar_servidor, daemon=True)
        thread.start()

    # ------------------------------------------------------------------
    # Servidor TCP
    # ------------------------------------------------------------------

    def _executar_servidor(self):
        servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            servidor.bind((HOST, PORT))
            servidor.listen(5)
            self._log(f'Servidor aguardando conexões em {HOST}:{PORT}…\n')

            transmissao = 0
            while True:
                conn, addr = servidor.accept()
                transmissao += 1
                self._log(f'\n{"─"*70}')
                self._log(f'  TRANSMISSÃO #{transmissao}  |  origem: {addr}')
                self._log(f'{"─"*70}\n')
                try:
                    self._processar_conexao(conn)
                except Exception as exc:
                    self._log(f'[ERRO] {exc}\n')
                finally:
                    conn.close()
        except Exception as exc:
            self._log(f'[ERRO FATAL DO SERVIDOR] {exc}\n')
        finally:
            servidor.close()

    def _receber_exato(self, conn: socket.socket, n: int) -> bytes:
        """Garante que exatamente n bytes sejam lidos da conexão."""
        buf = b''
        while len(buf) < n:
            pacote = conn.recv(n - len(buf))
            if not pacote:
                raise ConnectionError(f'Conexão encerrada — esperava {n} bytes, recebeu {len(buf)}')
            buf += pacote
        return buf

    def _processar_conexao(self, conn: socket.socket):
        # Lê tamanho dos dados (4 bytes big-endian)
        cabecalho = self._receber_exato(conn, 4)
        tamanho = struct.unpack('!I', cabecalho)[0]

        # Recebe payload completo
        dados_brutos = self._receber_exato(conn, tamanho)

        payload = json.loads(dados_brutos.decode('utf-8'))

        nome        = payload.get('nome', 'Desconhecido')
        modulacao   = payload.get('modulacao', 'ASK')
        enquadr     = payload.get('enquadramento', 'Contagem de Caracteres')
        deteccao    = payload.get('deteccao', 'CRC')
        tempo       = np.array(payload.get('tempo', []))
        sinal       = np.array(payload.get('sinal', []))

        self._log(f'De: {nome}\n')
        self._log(f'Modulação por portadora : {modulacao}\n')
        self._log(f'Enquadramento           : {enquadr}\n')
        self._log(f'Detecção de erros       : {deteccao}\n\n')

        # ---- Demodulação ----
        if modulacao == 'ASK':
            bits_int = demod_ask(tempo, sinal)
        elif modulacao == 'FSK':
            bits_int = demod_fsk(tempo, sinal)
        elif modulacao == 'QPSK':
            bits_int = demod_qpsk(tempo, sinal)
        elif modulacao == '16-QAM':
            bits_int = demod_qam16(tempo, sinal)
        else:
            raise ValueError(f'Modulação desconhecida: {modulacao}')

        bits = ''.join(map(str, bits_int))
        self._log(f'Bits demodulados : {self._resumo(bits)}\n')

        # ---- Desenquadramento ----
        if enquadr == 'Contagem de Caracteres':
            bits_desenq = receptor_contagem(bits)
        elif enquadr == 'Inserção de Bytes':
            bits_desenq = receptor_insercao_bytes(bits)
        else:                                       # Inserção de Bits
            bits_desenq = receptor_insercao_bits(bits)

        if bits_desenq == -1:
            self._log('[AVISO] Erro no desenquadramento — quadro inválido.\n')
            return
        self._log(f'Após desenquadramento : {self._resumo(bits_desenq)}\n')

        # ---- Detecção de erros ----
        if deteccao == 'Paridade Par':
            valido, bits_sem_det = receptor_paridade(bits_desenq)
            self._log(f'Paridade : {"✓ válida" if valido else "✗ ERRO DETECTADO"}\n')
        elif deteccao == 'Checksum':
            valido, bits_sem_det = receptor_checksum(bits_desenq)
            self._log(f'Checksum : {"✓ válido" if valido else "✗ ERRO DETECTADO"}\n')
        else:                                       # CRC-32
            valido, bits_sem_det = receptor_crc(bits_desenq)
            self._log(f'CRC-32 : {"✓ válido" if valido else "✗ ERRO DETECTADO"}\n')

        if not valido:
            self._log('[AVISO] Erro de integridade detectado — tentando corrigir via Hamming…\n')

        self._log(f'Bits sem detecção : {self._resumo(bits_sem_det)}\n')

        # ---- Correção de erros (Hamming) ----
        try:
            bits_corrigidos, pos_erro = receptor_hamming(bits_sem_det)
            if pos_erro > 0:
                self._log(
                    f'Hamming : erro corrigido na posição {pos_erro} ✓\n'
                )
            else:
                self._log('Hamming : nenhum erro encontrado ✓\n')
            self._log(f'Bits corrigidos : {self._resumo(bits_corrigidos)}\n')
        except Exception as exc:
            self._log(f'[ERRO Hamming] {exc}\n')
            bits_corrigidos = bits_sem_det

        # ---- Conversão final para texto ----
        texto = bits_para_texto(bits_corrigidos)
        self._log(f'\n✉  Mensagem recebida: "{texto}"\n')

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _log(self, msg: str):
        self.callback_ui(msg)

    @staticmethod
    def _resumo(s: str, max_len: int = 80) -> str:
        return s[:max_len] + ('…' if len(s) > max_len else '')
