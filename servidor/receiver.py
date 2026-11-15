'''
Decodifica o sinal:
  sinal portadora - ruído AWGN do canal - demodulação - correção Hamming - detecção de erros - desenquadramento - bits - texto
  
'''
import json
import socket
import struct
import threading

import numpy as np

from auxiliar import bits_para_texto, receber_exato
from camada_enlace.hamming import receptor_hamming_blocos
from camada_enlace.deteccao_erros import (
    receptor_paridade,
    receptor_checksum,
    receptor_crc,
    receptor_entrelacamento,
    EDC_PADRAO, edc_valido,
)
from camada_enlace.enquadramento import (
    receptor_contagem,
    receptor_insercao_bytes,
    receptor_insercao_bits,
)
from camada_fisica.demodulacao import (
    demod_nrz_polar, demod_manchester, demod_bipolar,
    demod_ask, demod_fsk, demod_psk8, demod_qam32,
)
from camada_fisica.ruido import adicionar_ruido_gaussiano

# Endereço e porta do servidor TCP (o transmissor usa os mesmos valores).
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
        # Cria o socket TCP do servidor e permite reutilizar a porta ao reiniciar.
        servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            # Liga o servidor à porta e fica aguardando conexões do transmissor.
            servidor.bind((HOST, PORT))
            servidor.listen(5)
            self._log(f'Servidor aguardando conexões em {HOST}:{PORT}…\n')

            # Laço principal: aceita uma conexão por transmissão e processa a mensagem recebida.
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

        # Lê do pacote os protocolos escolhidos no cliente, os sinais limpos e os tamanhos (n_dados, n_bits).
        mod_digital = payload.get('modulacao_digital', 'NRZ-Polar')
        modulacao   = payload.get('modulacao', 'ASK')
        enquadr     = payload.get('enquadramento', 'Contagem de Caracteres')
        deteccao    = payload.get('deteccao', 'CRC')
        tam_quadro  = payload.get('tamanho_quadro')   # só para exibição: cada protocolo de enquadramento delimita os quadros sozinho
        tam_edc     = payload.get('tamanho_edc', EDC_PADRAO.get(deteccao, 32))   # bits do EDC no fim dos dados
        if not edc_valido(deteccao, tam_edc):
            raise ValueError(f'Tamanho de EDC inválido para {deteccao}: {tam_edc} bits')
        tempo       = np.array(payload.get('tempo', []))
        digital_limpo   = np.array(payload.get('sinal_digital', []))
        portadora_limpa = np.array(payload.get('sinal', []))
        media       = payload.get('media_ruido', 0.0)
        sigma       = payload.get('sigma_ruido', 0.05)
        n_dados     = payload.get('n_dados')
        self._esperada = payload.get('mensagem', '')   # só para exibição/comparação no simulador
        n_bits      = payload.get('n_bits')   # nº de bits úteis (sem o padding do último símbolo)

        # Mostra no log os parâmetros da transmissão.
        self._log(f'Modulação digital       : {mod_digital}\n')
        self._log(f'Modulação por portadora : {modulacao}\n')
        self._log(f'Enquadramento           : {enquadr}\n')
        if tam_quadro is not None:
            self._log(f'Tamanho máximo do quadro: {tam_quadro} byte(s)\n')
        self._log(f'Detecção de erros       : {deteccao}\n')
        self._log(f'Tamanho do EDC          : {tam_edc} bit(s)\n')

        # Meio de comunicação: soma AWGN n ~ N(μ, σ) aos valores (V) de cada sinal (sorteios independentes)
        sinal_digital   = adicionar_ruido_gaussiano(digital_limpo, media, sigma)
        sinal_portadora = adicionar_ruido_gaussiano(portadora_limpa, media, sigma)
        self._log(f'Ruído AWGN aplicado     : μ = {media:.2f} V, σ = {sigma:.2f} V\n\n')

        # Cria a resposta (um resultado por caminho físico) que será devolvida ao cliente.
        resposta = {
            'banda_base': self._novo_caminho(sinal_digital),
            'portadora' : self._novo_caminho(sinal_portadora, tempo),
        }

        # Os dois caminhos físicos (banda-base e portadora) compartilham a mesma cadeia de enlace
        try:
            self._executar_caminho(
                f'BANDA-BASE ({mod_digital})', resposta['banda_base'],
                lambda: self._demodular_digital(mod_digital, sinal_digital),
                n_bits, n_dados, enquadr, deteccao, tam_edc)

            self._executar_caminho(
                f'PORTADORA ({modulacao})', resposta['portadora'],
                lambda: self._demodular_portadora(modulacao, tempo, sinal_portadora),
                n_bits, n_dados, enquadr, deteccao, tam_edc)

        finally:
            # Mesmo que um caminho falhe, o cliente sempre recebe a resposta.
            self._enviar_resposta(conn, resposta)

    @staticmethod
    def _novo_caminho(sinal: np.ndarray, tempo: np.ndarray | None = None) -> dict:
        # Resultado de um caminho físico, devolvido ao cliente.
        caminho = {'sinal_ruidoso': sinal.tolist(), 'bits_ruidosos': '', 'texto': None, 'erro': None}
        if tempo is not None:
            caminho['tempo'] = tempo.tolist()
        return caminho

    def _executar_caminho(self, titulo, resultado, demodular, n_bits, n_dados, enquadr, deteccao, tam_edc):
        # Demodula o sinal do caminho e desfaz o enlace; uma falha aqui não impede o outro caminho.
        self._log(f'── {titulo} ──\n')
        self._log(f'  - Mensagem esperada: {self._esperada}\n')
        try:
            bits = ''.join(map(str, demodular()))[:n_bits]
            resultado['bits_ruidosos'] = bits    # o que chegou do canal, antes de qualquer tratamento
            self._log(f'  - Bits recebidos: {self._resumo(bits)}\n')
            self._desfazer_enlace(bits, n_dados, enquadr, deteccao, tam_edc, resultado)

        except Exception as exc:
            resultado['erro'] = str(exc)
            self._log(f'  - Mensagem recebida: [ERRO] {exc}\n')

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

    def _desfazer_enlace(self, bits: str, n_dados: int, enquadr: str, deteccao: str, tam_edc: int, resultado: dict):
        # Cadeia RX comum aos dois caminhos: Hamming - detecção - desenquadramento - texto.
        # Hamming: primeiro a ser desfeito; protege o quadro inteiro (flags inclusive)
        bits_corrigidos, corrigidos = receptor_hamming_blocos(bits, n_dados)
        if corrigidos:
            diag_hamming = (f'{len(corrigidos)} bloco(s) com erro corrigido '
                            f'(bloco, posição): {corrigidos}')
        else:
            diag_hamming = 'nenhum erro encontrado'
        self._log(f'  - Diagnóstico do Hamming: {diag_hamming}\n')

        # Detecção de erros: confere a integridade depois da correção (o EDC tem 'tam_edc' bits)
        if deteccao == 'Paridade Par':
            nome, (valido, bits_sem_det) = 'Paridade', receptor_paridade(bits_corrigidos)
        elif deteccao == 'Checksum':
            nome, (valido, bits_sem_det) = f'Checksum de {tam_edc} bits', receptor_checksum(bits_corrigidos, tam_edc)
        elif deteccao == 'Entrelaçamento de Bits':
            nome, (valido, bits_sem_det) = (f'Entrelaçamento ({tam_edc} colunas, paridade por coluna)',
                                            receptor_entrelacamento(bits_corrigidos, tam_edc))
        else:
            nome, (valido, bits_sem_det) = 'CRC-32', receptor_crc(bits_corrigidos)

        if valido:
            self._log(f'  - Diagnóstico da detecção de erros: {nome} válido, nenhum erro detectado\n')
        else:
            resultado['erro'] = 'erro de integridade detectado e não corrigido'
            self._log(f'  - Diagnóstico da detecção de erros: {nome} ERRO DETECTADO '
                      '(mensagem possivelmente corrompida)\n')

        # Desenquadramento
        if enquadr == 'Contagem de Caracteres':
            bits_desenq = receptor_contagem(bits_sem_det)
        elif enquadr == 'Inserção de Bytes':
            bits_desenq = receptor_insercao_bytes(bits_sem_det)
        else:
            bits_desenq = receptor_insercao_bits(bits_sem_det)

        if bits_desenq == '-1':
            resultado['erro'] = 'quadro inválido no desenquadramento'
            self._log(f'  - Bits tratados: {self._resumo(bits_sem_det)} (desenquadramento falhou)\n')
            self._log('  - Mensagem recebida: [ERRO] quadro inválido no desenquadramento\n')
            return

        self._log(f'  - Bits tratados: {self._resumo(bits_desenq)}\n')

        texto = bits_para_texto(bits_desenq)
        resultado['texto'] = texto
        self._log(f'  - Mensagem recebida: {texto}\n')

    def _enviar_resposta(self, conn: socket.socket, resposta: dict):
        # Devolve ao transmissor, para cada caminho, o sinal ruidoso, os bits ruidosos e o texto decodificado.
        # Serializa a resposta em JSON e envia com o tamanho (4 bytes) na frente.
        dados = json.dumps(resposta).encode('utf-8')
        conn.sendall(struct.pack('!I', len(dados)) + dados)

    #little funções auxiliares
    def _log(self, msg: str):
        self.callback_ui(msg)

    @staticmethod
    def _resumo(s: str, max_len: int = 80) -> str:
        return s[:max_len] + ('…' if len(s) > max_len else '')