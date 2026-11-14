'''
Implementa:
  1. Bit de paridade par
  2. Checksum
  3. CRC
  4. Entrelaçamento de bits (paridade por coluna)

O transmissor recebe uma string de bits e devolve os mesmos bits com o código de verificação anexado.
O receptor recebe os bits com o código e devolve (valido, dados): se a integridade foi confirmada
e os bits originais, já sem o código.

'''

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



# 2. Checksum (palavras de 8 bits, soma em complemento de 1) ------------------------------

def _checksum_calcular(bits: str) -> str:
    '''
    Soma todas as palavras de 8 bits (devolvendo o 'vai-um' para a soma) e inverte o resultado.
    '''
    padding = (8 - len(bits) % 8) % 8 #zeros necessários para completar a última palavra de 8 bits.
    bits_pad = bits + '0' * padding #o padding existe só dentro do cálculo; ele não é transmitido.

    soma = 0 #acumulador da soma das palavras.
    for i in range(0, len(bits_pad), 8):
        soma += int(bits_pad[i:i+8], 2) #soma a palavra de 8 bits atual.
        soma = (soma & 0xFF) + (soma >> 8)      #se passou de 8 bits, o 'vai-um' volta para a soma.

    return format(~soma & 0xFF, '08b') #complemento de 1 (inverte os bits), escrito em 8 bits.


def transmissor_checksum(bits: str) -> str:
    '''
    Acrescenta o checksum de 8 bits ao final da string de bits.
    '''
    return bits + _checksum_calcular(bits)


def receptor_checksum(bits: str) -> tuple[bool, str]:
    '''
    Recalcula o checksum dos dados e compara com os 8 bits recebidos.
    '''
    dado = bits[:-8] #dados, sem o checksum.
    checksum_recebido = bits[-8:] #os 8 últimos bits são o checksum enviado.
    checksum_calculado = _checksum_calcular(dado) #checksum calculado sobre os dados recebidos.
    return (checksum_recebido == checksum_calculado, dado)



# 3. CRC-32 (IEEE 802.3) -------------------------------------------------------------------

_CRC32_POLINOMIO = 0x04C11DB7 #polinômio gerador do CRC-32 (padrão IEEE 802).
_CRC32_XOR_OUT   = 0xFFFFFFFF #máscara de 32 bits: isola o resto da divisão e inverte o resultado.


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

    crc = (msg & _CRC32_XOR_OUT) ^ _CRC32_XOR_OUT #resto da divisão (32 bits finais), invertido.
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
# Os bits formam uma matriz de 8 COLUNAS (uma linha por byte). Em vez de enviar linha por
# linha, o transmissor envia coluna por coluna (de cima para baixo), e ao fim de cada coluna
# vai o seu bit de paridade par. Uma rajada de erros fica espalhada em colunas diferentes.
# Se o número de bits não for múltiplo de 8, a última linha fica incompleta (só existem as
# primeiras k células): não há padding, pois o receptor deduz o formato pelo tamanho total
# (tamanho = dados + 8 bits de paridade).

def _colunas(bits: str) -> list[str]:
    '''
    Separa os bits em 8 colunas: a coluna c contém os bits nas posições c, c+8, c+16...
    '''
    return [bits[c::8] for c in range(8)]


def transmissor_entrelacamento(bits: str) -> str:
    '''
    Envia a matriz coluna por coluna, com a paridade par de cada coluna ao final dela.
    '''
    saida = [] #colunas já com a paridade.
    for coluna in _colunas(bits):
        paridade = '1' if coluna.count('1') % 2 else '0' #paridade par da coluna.
        saida.append(coluna + paridade) #coluna = bits da coluna + bit de paridade.
    return ''.join(saida)


def receptor_entrelacamento(bits: str) -> tuple[bool, str]:
    '''
    Separa as colunas, confere a paridade de cada uma e reconstrói a ordem original dos bits.
    '''
    n_dados = len(bits) - 8 #total = dados + 8 bits de paridade (um por coluna).
    if n_dados < 0: #não há bits suficientes nem para a paridade.
        return (False, '')

    linhas, resto = divmod(n_dados, 8)    #as 'resto' primeiras colunas têm uma célula a mais (última linha incompleta).
    colunas, valido, pos = [], True, 0 #colunas lidas, resultado da verificação e posição atual na string.
    for c in range(8):
        tam = linhas + (1 if c < resto else 0) #quantidade de bits de dados desta coluna.
        coluna, paridade = bits[pos:pos + tam], bits[pos + tam] #bits da coluna e a paridade que veio logo depois.
        pos += tam + 1 #avança para a próxima coluna.
        colunas.append(coluna)
        if ('1' if coluna.count('1') % 2 else '0') != paridade: #paridade recalculada diferente da recebida.
            valido = False

    # reconstrói a ordem original: bit i está na coluna i % 8, posição i // 8
    dado = ''.join(colunas[i % 8][i // 8] for i in range(n_dados))
    return (valido, dado)