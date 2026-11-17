'''
Implementa:
  1. Bit de paridade par
  2. Checksum
  3. CRC
  4. Entrelaçamento de bits (paridade por coluna)

O transmissor recebe uma string de bits e devolve os mesmos bits com o código de verificação (EDC) anexado.
O receptor recebe os bits com o código e devolve (valido, dados): se a integridade foi confirmada
e os bits originais, já sem o código.

Essas funções protegem uma sequência qualquer de bits. Quem as usa é quadros.py, por meio das funções do
fim deste arquivo, aplicando-as a UM quadro de cada vez: cada quadro tem o seu próprio EDC.

O tamanho do EDC (em bits) é configurável, dentro das opções de cada protocolo:
  - Paridade par : 1 bit (fixo, é a própria definição do código)
  - Checksum     : 8, 16 ou 32 bits (tamanho da palavra somada = tamanho do resultado)
  - CRC          : 32 bits (fixo: o enunciado define o polinômio gerador CRC-32 do padrão IEEE 802)
  - Entrelaçamento: 8, 16 ou 32 bits (um bit de paridade por coluna = quantidade de colunas; múltiplos de 8
                    para que a carga útil do quadro continue sendo formada por bytes inteiros)

'''

# Tamanhos de EDC aceitos por cada detecção (o padrão de cada uma está em EDC_PADRAO).
TAMANHOS_EDC = {
    'Paridade Par'          : [1],
    'Checksum'              : [8, 16, 32],
    'CRC'                   : [32],
    'Entrelaçamento de Bits': [8, 16, 32],
}

# Tamanho de EDC padrão de cada detecção.
EDC_PADRAO = {
    'Paridade Par'          : 1,
    'Checksum'              : 8,
    'CRC'                   : 32,
    'Entrelaçamento de Bits': 8,
}


def edc_valido(deteccao: str, tamanho_edc: int) -> bool:
    '''
    Confere se 'tamanho_edc' é uma opção válida para a detecção escolhida.
    '''
    return tamanho_edc in TAMANHOS_EDC.get(deteccao, [])

# 1. Bit de paridade par -------------------------------------------------------------------

def transmissor_paridade(bits: str) -> str:
    '''
    Acrescenta 1 bit ao final para que a quantidade total de bits 1 seja par.
    '''
    bit_par = '1' if bits.count('1') % 2 != 0 else '0' #se a quantidade de 1 é ímpar, o bit de paridade é 1.
    return bits + bit_par #dados + bit de paridade.


def receptor_paridade(bits: str) -> tuple[bool, str]:
    '''
    Recalcula a paridade dos dados e compara com o bit recebido.
    '''
    dado = bits[:-1] #todos os bits, menos o último.
    bit_recebido = bits[-1] #o último bit é a paridade enviada.
    bit_esperado = '1' if dado.count('1') % 2 != 0 else '0' #paridade calculada sobre os dados recebidos.
    return (bit_recebido == bit_esperado, dado) #válido se a paridade recebida for igual à calculada.



# 2. Checksum (palavras de 'tam' bits, soma em complemento de 1) --------------------------

def _checksum_calcular(bits: str, tam: int = 8) -> str:
    '''
    Soma todas as palavras de 'tam' bits (devolvendo o 'vai-um' para a soma) e inverte o resultado.
    '''
    mascara = (1 << tam) - 1 #tam bits em 1: isola uma palavra.
    padding = (tam - len(bits) % tam) % tam #zeros necessários para completar a última palavra.
    bits_pad = bits + '0' * padding #o padding existe só dentro do cálculo; ele não é transmitido.

    soma = 0 #acumulador da soma das palavras.
    for i in range(0, len(bits_pad), tam):
        soma += int(bits_pad[i:i+tam], 2) #soma a palavra atual.
        soma = (soma & mascara) + (soma >> tam)      #se passou de 'tam' bits, o 'vai-um' volta para a soma.

    return format(~soma & mascara, f'0{tam}b') #complemento de 1 (inverte os bits), escrito em 'tam' bits.


def transmissor_checksum(bits: str, tam: int = 8) -> str:
    '''
    Acrescenta o checksum de 'tam' bits ao final da string de bits.
    '''
    return bits + _checksum_calcular(bits, tam)


def receptor_checksum(bits: str, tam: int = 8) -> tuple[bool, str]:
    '''
    Recalcula o checksum dos dados e compara com os 'tam' bits recebidos.
    '''
    dado = bits[:-tam] #dados, sem o checksum.
    checksum_recebido = bits[-tam:] #os 'tam' últimos bits são o checksum enviado.
    checksum_calculado = _checksum_calcular(dado, tam) #checksum calculado sobre os dados recebidos.
    return (checksum_recebido == checksum_calculado, dado)



# 3. CRC-32 (IEEE 802.3) -------------------------------------------------------------------

_CRC32_POLINOMIO = 0x04C11DB7 #polinômio gerador do CRC-32 (padrão IEEE 802).
_CRC32_MASCARA   = 0xFFFFFFFF #máscara de 32 bits: isola o resto da divisão.


def _crc32_calcular(bits: str) -> str:
    '''
    Divide (em módulo 2) os dados deslocados em 32 bits pelo polinômio gerador; o resto é o CRC.
    '''
    if not bits: #sem dados, o CRC é só zeros.
        return '0' * 32

    msg = int(bits, 2) #transforma a string de bits em um número inteiro.
    msg <<= 32 #abre espaço para os 32 bits do CRC (acrescenta 32 zeros à direita).

    n = len(bits) #quantidade de bits de dados.
    for i in range(n):
        if msg & (1 << (n + 31 - i)): #se o bit mais significativo atual é 1...
            msg ^= _CRC32_POLINOMIO << (n - 1 - i) #...faz o XOR com o polinômio alinhado a esse bit.

    crc = msg & _CRC32_MASCARA #resto da divisão (os 32 bits finais) é o CRC.
    return format(crc, '032b') #escreve o CRC em 32 bits.


def transmissor_crc(bits: str) -> str:
    '''
    Acrescenta o CRC-32 ao final da string de bits.
    '''
    return bits + _crc32_calcular(bits)


def receptor_crc(bits: str) -> tuple[bool, str]:
    '''
    Recalcula o CRC-32 dos dados e compara com os 32 bits recebidos.
    '''
    dado = bits[:-32] #dados, sem o CRC.
    crc_recebido = bits[-32:] #os 32 últimos bits são o CRC enviado.
    crc_calculado = _crc32_calcular(dado) #CRC calculado sobre os dados recebidos.
    return (crc_recebido == crc_calculado, dado)



# 4. Entrelaçamento de bits (paridade por coluna) ------------------------------------------
# Os bits formam uma matriz de 'colunas' COLUNAS (uma linha por 'colunas' bits; com 8 colunas, um byte
# por linha). Em vez de enviar linha por linha, o transmissor envia coluna por coluna (de cima para
# baixo), e ao fim de cada coluna vai o seu bit de paridade par. Uma rajada de erros fica espalhada
# em colunas diferentes. O EDC tem 'colunas' bits (um por coluna).
# Se o número de bits não for múltiplo de 'colunas', a última linha fica incompleta (só existem as
# primeiras k células): não há padding, pois o receptor deduz o formato pelo tamanho total
# (tamanho = dados + 'colunas' bits de paridade).

def _colunas(bits: str, colunas: int = 8) -> list[str]:
    '''
    Separa os bits em 'colunas' colunas: a coluna c contém os bits nas posições c, c+colunas, c+2*colunas...
    '''
    return [bits[c::colunas] for c in range(colunas)]


def transmissor_entrelacamento(bits: str, colunas: int = 8) -> str:
    '''
    Envia a matriz coluna por coluna, com a paridade par de cada coluna ao final dela.
    '''
    saida = [] #colunas já com a paridade.
    for coluna in _colunas(bits, colunas):
        paridade = '1' if coluna.count('1') % 2 else '0' #paridade par da coluna.
        saida.append(coluna + paridade) #coluna = bits da coluna + bit de paridade.
    return ''.join(saida)


def receptor_entrelacamento(bits: str, colunas: int = 8) -> tuple[bool, str]:
    '''
    Separa as colunas, confere a paridade de cada uma e reconstrói a ordem original dos bits.
    '''
    n_dados = len(bits) - colunas #total = dados + 'colunas' bits de paridade (um por coluna).
    if n_dados < 0: #não há bits suficientes nem para a paridade.
        return (False, '')

    linhas, resto = divmod(n_dados, colunas)    #as 'resto' primeiras colunas têm uma célula a mais (última linha incompleta).
    lista, valido, pos = [], True, 0 #colunas lidas, resultado da verificação e posição atual na string.
    for c in range(colunas):
        tam = linhas + (1 if c < resto else 0) #quantidade de bits de dados desta coluna.
        coluna, paridade = bits[pos:pos + tam], bits[pos + tam] #bits da coluna e a paridade que veio logo depois.
        pos += tam + 1 #avança para a próxima coluna.
        lista.append(coluna)
        if ('1' if coluna.count('1') % 2 else '0') != paridade: #paridade recalculada diferente da recebida.
            valido = False

    # reconstrói a ordem original: bit i está na coluna i % colunas, posição i // colunas
    dado = ''.join(lista[i % colunas][i // colunas] for i in range(n_dados))
    return (valido, dado)



# 5. EDC de UM quadro (usado por quadros.py) -----------------------------------------------
# Paridade, checksum e CRC calculam o EDC sobre o QUADRO INTEIRO (cabeçalho ou flags + dados), o que
# protege também a delimitação, e o EDC é anexado logo depois do quadro. No entrelaçamento a matriz
# inteira (colunas + paridades) substitui os dados e vai dentro do quadro, como carga útil.

def payload_do_quadro(deteccao: str, dados: str, tam_edc: int) -> str:
    '''
    Devolve a carga útil do quadro: no entrelaçamento, a matriz com as paridades; nos demais, os próprios dados.
    '''
    if deteccao == 'Entrelaçamento de Bits':
        return transmissor_entrelacamento(dados, tam_edc)
    return dados


def edc_do_quadro(deteccao: str, quadro: str, tam_edc: int) -> str:
    '''
    Calcula o EDC que será anexado depois do quadro ('' no entrelaçamento, cujo EDC fica dentro do quadro).
    '''
    if deteccao == 'Paridade Par':
        completo = transmissor_paridade(quadro)
    elif deteccao == 'Checksum':
        completo = transmissor_checksum(quadro, tam_edc)
    elif deteccao == 'CRC':
        completo = transmissor_crc(quadro)
    else:
        return '' #entrelaçamento: não há EDC fora do quadro.

    return completo[len(quadro):] #o EDC são os bits que foram acrescentados ao quadro.


def verificar_quadro(deteccao: str, quadro: str, payload: str, sufixo: str, tam_edc: int) -> tuple[bool, str]:
    '''
    Confere a integridade de um quadro recebido e devolve (valido, dados do quadro, sem o EDC).
    '''
    if deteccao == 'Entrelaçamento de Bits':
        return receptor_entrelacamento(payload, tam_edc) #confere as paridades das colunas da carga útil.

    completo = quadro + sufixo #quadro + EDC, como o receptor de cada protocolo espera.
    if deteccao == 'Paridade Par':
        valido, _ = receptor_paridade(completo)
    elif deteccao == 'Checksum':
        valido, _ = receptor_checksum(completo, tam_edc)
    else:
        valido, _ = receptor_crc(completo)
    return (valido, payload) #o EDC recalculado sobre o quadro é igual ao recebido?


def tamanho_sufixo_edc(deteccao: str, tam_edc: int) -> int:
    '''
    Quantidade de bits de EDC que vêm depois do quadro (0 no entrelaçamento, cujo EDC fica dentro do quadro).
    '''
    return 0 if deteccao == 'Entrelaçamento de Bits' else tam_edc


def tamanho_extra_payload(deteccao: str, tam_edc: int) -> int:
    '''
    Quantidade de bits que a carga útil do quadro tem além dos dados (só o entrelaçamento acrescenta bits).
    '''
    return tam_edc if deteccao == 'Entrelaçamento de Bits' else 0