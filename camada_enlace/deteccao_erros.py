'''
Implementa:
  1. Bit de paridade par
  2. Checksum
  3. CRC

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



# 2. Checksum 
def _checksum_calcular(bits: str) -> str:
    # Padding para múltiplo de 16
    padding = (16 - len(bits) % 16) % 16
    bits_pad = bits + '0' * padding

    soma = 0
    for i in range(0, len(bits_pad), 16):
        palavra = int(bits_pad[i:i+16], 2)
        soma += palavra

        soma = (soma & 0xFFFF) + (soma >> 16)

    return format(~soma & 0xFFFF, '016b')


def transmissor_checksum(bits: str) -> str:
    #Acrescenta o checksum de 16 bits ao final da string de bits.
    return bits + _checksum_calcular(bits)


def receptor_checksum(bits: str) -> tuple[bool, str]:
    #Verifica o checksum de 16 bits.
    dado = bits[:-16]
    checksum_recebido = bits[-16:]
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
