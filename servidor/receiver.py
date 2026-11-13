'''
Decodifica o sinal:
  sinal portadora - ruído AWGN do canal - demodulação - desenquadramento - correção Hamming - detecção de erros - bits - texto
  
'''
import json
import socket
import struct
import threading

import numpy as np

from auxiliar import bits_para_texto, receber_exato
from camada_enlace.hamming import receptor_hamming
from camada_enlace.deteccao_erros import (
    receptor_paridade,
    receptor_checksum,
    receptor_crc,
)
from camada_enlace.enquadramento import (
    receptor_contagem,
    receptor_entrelacamento,
    receptor_insercao_bytes,
    receptor_insercao_bits,
)
from camada_fisica.demodulacao import (
    demod_nrz_polar, demod_manchester, demod_bipolar,
    demod_ask, demod_fsk, demod_psk8, demod_qam32,
)
from camada_fisica.ruido import adicionar_ruido_gaussiano

HOST = '127.0.0.1'
PORT = 5000


class Receiver:
    #Gerencia o servidor TCP e aplica o pipeline RX a cada mensagem.
    def __init__(self, callback_ui): #callback_ui: função chamada com strings de log para atualizar a UI
        self.callback_ui = callback_ui

    def iniciar(self):
        #Inicia o servidor TCP em thread separada.
        thread = threading.Thread(target=self._executar_servidor, daemon=True)
        thread.start()

    
    # Servidor TCP
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

    def _processar_conexao(self, conn: socket.socket):
        # Lê tamanho dos dados (4 bytes big-endian)
        tamanho = struct.unpack('!I', receber_exato(conn, 4))[0]

        # Recebe payload completo (sinais LIMPOS vindos do transmissor)
        payload = json.loads(receber_exato(conn, tamanho).decode('utf-8'))

        mod_digital = payload.get('modulacao_digital', 'NRZ-Polar')
        modulacao   = payload.get('modulacao', 'ASK')
        enquadr     = payload.get('enquadramento', 'Contagem de Caracteres')
        deteccao    = payload.get('deteccao', 'CRC')
        tempo       = np.array(payload.get('tempo', []))
        digital_limpo   = np.array(payload.get('sinal_digital', []))
        portadora_limpa = np.array(payload.get('sinal', []))
        media       = payload.get('media_ruido', 0.0)
        sigma       = payload.get('sigma_ruido', 0.05)
        n_bits      = payload.get('n_bits')   # nº de bits úteis (sem o padding do último símbolo)

        self._log(f'Modulação digital       : {mod_digital}\n')
        self._log(f'Modulação por portadora : {modulacao}\n')
        self._log(f'Enquadramento           : {enquadr}\n')
        self._log(f'Detecção de erros       : {deteccao}\n')

        # Meio de comunicação: soma AWGN n ~ N(μ, σ) aos valores (V) de cada sinal (sorteios independentes)
        sinal_digital   = adicionar_ruido_gaussiano(digital_limpo, media, sigma)
        sinal_portadora = adicionar_ruido_gaussiano(portadora_limpa, media, sigma)
        self._log(f'Ruído AWGN aplicado     : μ = {media:.2f} V, σ = {sigma:.2f} V\n\n')

        resposta = {
            'banda_base': self._novo_caminho(sinal_digital),
            'portadora' : self._novo_caminho(sinal_portadora, tempo),
        }

        # Os dois caminhos físicos (banda-base e portadora) compartilham a mesma cadeia de enlace
        try:
            self._executar_caminho(
                f'BANDA-BASE ({mod_digital})', resposta['banda_base'],
                lambda: self._demodular_digital(mod_digital, sinal_digital),
                n_bits, enquadr, deteccao)

            self._executar_caminho(
                f'PORTADORA ({modulacao})', resposta['portadora'],
                lambda: self._demodular_portadora(modulacao, tempo, sinal_portadora),
                n_bits, enquadr, deteccao)

        finally:
            self._enviar_resposta(conn, resposta)

    @staticmethod
    def _novo_caminho(sinal: np.ndarray, tempo: np.ndarray | None = None) -> dict:
        # Resultado de um caminho físico, devolvido ao cliente.
        caminho = {'sinal_ruidoso': sinal.tolist(), 'bits_ruidosos': '', 'texto': None, 'erro': None}
        if tempo is not None:
            caminho['tempo'] = tempo.tolist()
        return caminho

    def _executar_caminho(self, titulo, resultado, demodular, n_bits, enquadr, deteccao):
        # Demodula o sinal do caminho e desfaz o enlace; uma falha aqui não impede o outro caminho.
        self._log(f'── {titulo} ──\n')
        try:
            bits = ''.join(map(str, demodular()))[:n_bits]
            resultado['bits_ruidosos'] = bits    # o que chegou do canal, antes de qualquer tratamento
            self._log(f'Bits demodulados : {self._resumo(bits)}\n')
            self._desfazer_enlace(bits, enquadr, deteccao, resultado)

        except Exception as exc:
            resultado['erro'] = str(exc)
            self._log(f'[ERRO] {exc}\n')

        self._log('\n')

    def _demodular_digital(self, nome: str, sinal: np.ndarray) -> list[int]:
        # Decodificação banda-base.
        if nome == 'NRZ-Polar':
            return demod_nrz_polar(sinal)

        elif nome == 'Manchester':
            return demod_manchester(sinal)

        elif nome == 'Bipolar':
            return demod_bipolar(sinal)

        raise ValueError(f'Modulação digital desconhecida: {nome}')

    def _demodular_portadora(self, nome: str, tempo: np.ndarray, sinal: np.ndarray) -> list[int]:
        # Demodulação por portadora.
        if nome == 'ASK':
            return demod_ask(tempo, sinal)

        elif nome == 'FSK':
            return demod_fsk(tempo, sinal)

        elif nome == '8PSK':
            return demod_psk8(tempo, sinal)

        elif nome == '32-QAM':
            return demod_qam32(tempo, sinal)

        raise ValueError(f'Modulação desconhecida: {nome}')

    def _desfazer_enlace(self, bits: str, enquadr: str, deteccao: str, resultado: dict):
        # Cadeia RX comum aos dois caminhos: desenquadramento - detecção - correção - texto.

        #Desenquadramento
        if enquadr == 'Contagem de Caracteres':
            bits_desenq = receptor_contagem(bits)

        elif enquadr == 'Entrelaçamento de Bits':
            bits_desenq = receptor_entrelacamento(bits)

        elif enquadr == 'Inserção de Bytes':
            bits_desenq = receptor_insercao_bytes(bits)

        else:
            bits_desenq = receptor_insercao_bits(bits)

        if bits_desenq == '-1':
            resultado['erro'] = 'quadro inválido no desenquadramento'
            self._log('[AVISO] Erro no desenquadramento — quadro inválido.\n')
            return

        self._log(f'Após desenquadramento : {self._resumo(bits_desenq)}\n')
        if len(bits_desenq) < 8:
            resultado['erro'] = 'quadro curto demais (cabeçalho de padding ausente)'
            self._log('[AVISO] Quadro muito curto — cabeçalho de padding ausente.\n')
            return

        pad_len = int(bits_desenq[:8], 2)
        bits_desenq = bits_desenq[8:]
        if pad_len > 0:
            bits_desenq = bits_desenq[:-pad_len]

        #Correção de erros (Hamming): desfaz a última codificação aplicada pelo transmissor
        try:
            bits_corrigidos, pos_erro = receptor_hamming(bits_desenq)
            if pos_erro > 0:
                self._log(
                    f'Hamming : erro corrigido na posição {pos_erro} ✓\n'
                )
            else:
                self._log('Hamming : nenhum erro encontrado ✓\n')
            self._log(f'Bits corrigidos : {self._resumo(bits_corrigidos)}\n')

        except Exception as exc:
            self._log(f'[ERRO Hamming] {exc}\n')
            bits_corrigidos = bits_desenq

        #Detecção de erros: confere a integridade depois da correção
        if deteccao == 'Paridade Par':
            valido, bits_sem_det = receptor_paridade(bits_corrigidos)
            self._log(f'Paridade : {"✓ válida" if valido else "✗ ERRO DETECTADO"}\n')

        elif deteccao == 'Checksum':
            valido, bits_sem_det = receptor_checksum(bits_corrigidos)
            self._log(f'Checksum : {"✓ válido" if valido else "✗ ERRO DETECTADO"}\n')

        else:
            valido, bits_sem_det = receptor_crc(bits_corrigidos)
            self._log(f'CRC-32 : {"✓ válido" if valido else "✗ ERRO DETECTADO"}\n')

        if not valido:
            resultado['erro'] = 'erro de integridade detectado e não corrigido'
            self._log('[AVISO] Erro de integridade detectado mesmo após o Hamming — mensagem possivelmente corrompida.\n')

        self._log(f'Bits sem detecção : {self._resumo(bits_sem_det)}\n')

        #Conversão final para texto
        texto = bits_para_texto(bits_sem_det)
        resultado['texto'] = texto
        self._log(f'\n✉  Mensagem recebida: "{texto}"\n')

    def _enviar_resposta(self, conn: socket.socket, resposta: dict):
        # Devolve ao transmissor, para cada caminho, o sinal ruidoso, os bits ruidosos e o texto decodificado.
        dados = json.dumps(resposta).encode('utf-8')
        conn.sendall(struct.pack('!I', len(dados)) + dados)

    #little funções auxiliares
    def _log(self, msg: str):
        self.callback_ui(msg)

    @staticmethod
    def _resumo(s: str, max_len: int = 80) -> str:
        return s[:max_len] + ('…' if len(s) > max_len else '')