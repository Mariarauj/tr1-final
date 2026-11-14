'''
Implementa:
  1. Bit de paridade par
  2. Checksum
  3. CRC
  4. Entrelaçamento de bits (paridade por coluna)

'''

# 1. Bit de paridade par
def transmissor_paridade(bits: str) -> str:
    bit_par = '1' if bits.count('1') % 2 != 0 else '0'
    return bits + bit_par


def receptor_paridade(bits: str) -> tuple[bool, str]:
    dado = bits[:-1]
    bit_recebido = bits[-1]
    bit_esperado = '1' if dado.count('1') % 2 != 0 else '0'
    return (bit_recebido == bit_esperado, dado)



# 2. Checksum (palavras de 8 bits, soma em complemento de 1)
def _checksum_calcular(bits: str) -> str:
    # Padding para múltiplo de 8 (só dentro do cálculo; não é transmitido)
    padding = (8 - len(bits) % 8) % 8
    bits_pad = bits + '0' * padding

    soma = 0
    for i in range(0, len(bits_pad), 8):
        soma += int(bits_pad[i:i+8], 2)
        soma = (soma & 0xFF) + (soma >> 8)      # vai-um volta para a soma

    return format(~soma & 0xFF, '08b')


def transmissor_checksum(bits: str) -> str:
    #Acrescenta o checksum de 8 bits ao final da string de bits.
    return bits + _checksum_calcular(bits)


def receptor_checksum(bits: str) -> tuple[bool, str]:
    #Verifica o checksum de 8 bits.
    dado = bits[:-8]
    checksum_recebido = bits[-8:]
    checksum_calculado = _checksum_calcular(dado)
    return (checksum_recebido == checksum_calculado, dado)



# 3. CRC-32 (IEEE 802.3)
_CRC32_POLINOMIO = 0x04C11DB7
_CRC32_XOR_OUT   = 0xFFFFFFFF


def _crc32_calcular(bits: str) -> str:
    if not bits:
        return '0' * 32

    msg = int(bits, 2)
    msg <<= 32

    n = len(bits)
    for i in range(n):
        if msg & (1 << (n + 31 - i)):
            msg ^= _CRC32_POLINOMIO << (n - 1 - i)

    crc = (msg & _CRC32_XOR_OUT) ^ _CRC32_XOR_OUT
    return format(crc, '032b')


def transmissor_crc(bits: str) -> str:
    #Acrescenta o CRC-32
    return bits + _crc32_calcular(bits)


def receptor_crc(bits: str) -> tuple[bool, str]:
    #Verifica o CRC-32

    dado = bits[:-32]
    crc_recebido = bits[-32:]
    crc_calculado = _crc32_calcular(dado)
    return (crc_recebido == crc_calculado, dado)



# 4. Entrelaçamento de bits (paridade por coluna)
# Os bits formam uma matriz de 8 COLUNAS (uma linha por byte). Em vez de enviar linha por
# linha, o transmissor envia coluna por coluna (de cima para baixo), e ao fim de cada coluna
# vai o seu bit de paridade par. Uma rajada de erros fica espalhada em colunas diferentes.
# Se o número de bits não for múltiplo de 8, a última linha fica incompleta (só existem as
# primeiras k células): não há padding, pois o receptor deduz o formato pelo tamanho total
# (tamanho = dados + 8 bits de paridade).
def _colunas(bits: str) -> list[str]:
    return [bits[c::8] for c in range(8)]


def transmissor_entrelacamento(bits: str) -> str:
    saida = []
    for coluna in _colunas(bits):
        paridade = '1' if coluna.count('1') % 2 else '0'
        saida.append(coluna + paridade)
    return ''.join(saida)


def receptor_entrelacamento(bits: str) -> tuple[bool, str]:
    n_dados = len(bits) - 8
    if n_dados < 0:
        return (False, '')

    linhas, resto = divmod(n_dados, 8)    # as `resto` primeiras colunas têm uma célula a mais
    colunas, valido, pos = [], True, 0
    for c in range(8):
        tam = linhas + (1 if c < resto else 0)
        coluna, paridade = bits[pos:pos + tam], bits[pos + tam]
        pos += tam + 1
        colunas.append(coluna)
        if ('1' if coluna.count('1') % 2 else '0') != paridade:
            valido = False

    # reconstrói a ordem original: bit i está na coluna i % 8, posição i // 8
    dado = ''.join(colunas[i % 8][i // 8] for i in range(n_dados))
    return (valido, dado)