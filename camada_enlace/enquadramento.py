'''
Implementa os tipos de enquadramento (um quadro por vez):
  1. Contagem de caracteres
  2. Inserção de bytes (flags + ESC byte)
  3. Inserção de bits  (flag 01111110 + bit stuffing)

Cada protocolo tem duas funções:
  - quadro_...     : monta UM quadro a partir da carga útil (payload) recebida.
  - ler_quadro_... : lê UM quadro que começa em uma posição do fluxo e devolve (payload, nova posição),
                     ou None se o quadro for inválido.

A divisão da mensagem em quadros de até 'tamanho_quadro' bytes e o EDC de cada quadro ficam em quadros.py.
Todas as funções trabalham com strings de bits ('0' e '1').

'''

TAMANHO_QUADRO_PADRAO = 8     # tamanho máximo de quadro padrão, em bytes de dados.
TAMANHO_QUADRO_MAX    = 255   # o cabeçalho da contagem de caracteres tem 1 byte, então conta até 255.


def tamanho_quadro_valido(tamanho_quadro) -> bool:
    '''
    Confere se o tamanho máximo de quadro é um inteiro entre 1 e 255 bytes.
    '''
    return isinstance(tamanho_quadro, int) and 1 <= tamanho_quadro <= TAMANHO_QUADRO_MAX



# 1. Contagem de caracteres ---------------------------------------------------------------
# Quadro = 1 byte de cabeçalho (quantidade de bytes de DADOS do quadro) + carga útil.
# Se a carga útil tiver bits a mais que os dados (o EDC do entrelaçamento), o receptor recebe essa
# quantidade em 'bits_extra'; assim o cabeçalho conta sempre até 255 bytes de dados.

def quadro_contagem(payload: str, n_bytes_dados: int) -> str:
    '''
    Coloca na frente da carga útil 1 byte (cabeçalho) com a quantidade de bytes de dados do quadro.
    '''
    return format(n_bytes_dados, '08b') + payload #cabeçalho escrito em 8 bits + carga útil.


def ler_quadro_contagem(bits: str, pos: int, bits_extra: int = 0) -> tuple[str, int] | None:
    '''
    Lê o cabeçalho, extrai a quantidade de bits indicada por ele (mais 'bits_extra') e descarta o cabeçalho.
    '''
    if pos + 8 > len(bits): #não há nem o byte de cabeçalho.
        return None

    n = int(bits[pos:pos + 8], 2) #converte o cabeçalho para número: quantos bytes de dados vêm a seguir.
    inicio = pos + 8 #a carga útil começa depois do cabeçalho.
    fim = inicio + n * 8 + bits_extra #posição onde a carga útil termina.
    if fim > len(bits): #o cabeçalho diz que há mais bits do que realmente chegaram -> quadro inválido.
        return None

    return bits[inicio:fim], fim



# 2. Inserção de bytes ---------------------------------------------------------------------

_FLAG_IB  = '00100110'   # '&' (0x26): byte que marca o início e o fim de cada quadro.
_ESC_IB   = '00011011'   # ESC (0x1B): byte de escape, colocado antes de dados iguais à flag ou ao ESC.


def quadro_insercao_bytes(payload: str) -> str:
    '''
    O quadro é delimitado por uma flag no início e outra no fim.
    Se um byte da carga útil for igual à flag ou ao ESC, um ESC é inserido antes dele (byte stuffing).
    '''
    corpo = '' #conteúdo do quadro, já com os escapes.
    for i in range(0, len(payload), 8):
        byte = payload[i:i + 8] #byte atual da carga útil.
        if byte == _FLAG_IB or byte == _ESC_IB: #dado igual à flag ou ao ESC poderia confundir o receptor.
            corpo += _ESC_IB #insere um ESC antes dele.
        corpo += byte

    return _FLAG_IB + corpo + _FLAG_IB #quadro = flag + corpo + flag.


def ler_quadro_insercao_bytes(bits: str, pos: int) -> tuple[str, int] | None:
    '''
    Confere a flag inicial e percorre os bytes até a flag final: ao encontrar um ESC, mantém o byte seguinte como dado.
    '''
    if bits[pos:pos + 8] != _FLAG_IB: #o quadro precisa começar por uma flag.
        return None

    payload = '' #armazena os dados extraídos, sem flags e sem escapes.
    idx = pos + 8 #posição do byte que está sendo lido (depois da flag inicial).

    while idx + 8 <= len(bits):
        byte = bits[idx:idx + 8] #byte atual.

        if byte == _ESC_IB: #ESC: o byte seguinte é um dado e não deve ser interpretado.
            prox = bits[idx + 8:idx + 16] #byte protegido pelo ESC.
            if prox not in (_FLAG_IB, _ESC_IB):
                return None #ESC seguido de um byte que não precisava de escape -> erro.
            payload += prox #guarda o byte protegido (flag ou ESC dos dados).
            idx += 16 #pula o ESC e o byte protegido.
        elif byte == _FLAG_IB: #flag final: o quadro terminou.
            return payload, idx + 8
        else:
            payload += byte #byte comum de dados.
            idx += 8

    return None #os bits acabaram antes da flag final -> quadro inválido.



# 3. Inserção de bits (bit stuffing) -------------------------------------------------------

_FLAG_BITS = '01111110' #flag que delimita o quadro (seis 1 seguidos entre dois 0).

def _stuff(dados: str) -> str:
    '''
    Após cinco bits 1 seguidos, insere um bit 0 (bit stuffing), para que os dados nunca imitem a flag.
    '''
    stuffed = '' #dados já com os bits de stuffing.
    contagem_uns = 0 #quantidade de bits 1 seguidos até agora.

    for bit in dados:
        stuffed += bit
        if bit == '1':
            contagem_uns += 1
            if contagem_uns == 5: #cinco 1 seguidos...
                stuffed += '0'   #...insere um 0 para prevenir uma flag acidental.
                contagem_uns = 0
        else:
            contagem_uns = 0 #um bit 0 quebra a sequência de 1.

    return stuffed


def _destuff(dados_stuffed: str) -> str:
    '''
    Remove o bit 0 inserido após cada sequência de cinco bits 1.
    '''
    destuffed = '' #dados originais, sem os bits de stuffing.
    contagem_uns = 0 #quantidade de bits 1 seguidos até agora.
    i = 0 #posição do bit que está sendo lido.
    while i < len(dados_stuffed):
        bit = dados_stuffed[i]
        if bit == '1':
            contagem_uns += 1
            destuffed += bit
            if contagem_uns == 5: #depois de cinco 1, o próximo bit (0) foi inserido pelo transmissor...
                i += 1            #...então ele é pulado.
                contagem_uns = 0
        else:
            contagem_uns = 0
            destuffed += bit
        i += 1

    return destuffed


def quadro_insercao_bits(payload: str) -> str:
    '''
    O quadro é delimitado por uma flag no início e outra no fim, e a carga útil recebe bit stuffing.
    '''
    return _FLAG_BITS + _stuff(payload) + _FLAG_BITS #quadro = flag + dados com stuffing + flag.


def ler_quadro_insercao_bits(bits: str, pos: int) -> tuple[str, int] | None:
    '''
    Confere a flag inicial, localiza a flag final, descarta-as e remove o bit 0 inserido após cada sequência de cinco 1.
    '''
    if bits[pos:pos + 8] != _FLAG_BITS: #o quadro precisa começar por uma flag.
        return None

    fim = bits.find(_FLAG_BITS, pos + 8) #posição da flag final (a primeira depois da inicial).
    if fim == -1: #falta o delimitador final -> quadro inválido.
        return None

    return _destuff(bits[pos + 8:fim]), fim + 8 #dados entre as duas flags, sem o stuffing.