"""
Camada de Enlace - Detecção de Erros
Implementa:
  1. Bit de paridade par
  2. Checksum (16 bits, soma em complemento de 1)
  3. CRC (polinômio CRC-32, IEEE 802.3)
"""


# ---------------------------------------------------------------------------
# 1. Bit de paridade par
# ---------------------------------------------------------------------------

def transmissor_paridade(bits: str) -> str:
    """
    Acrescenta ao final da string de bits um bit de paridade PAR.
    O bit de paridade é '1' se o número de '1' nos dados for ímpar
    (tornando a contagem total par), e '0' caso contrário.

    Parâmetros:
    - bits: string de bits de dado

    Retorno:
    - string de bits com o bit de paridade ao final
    """
    bit_par = '1' if bits.count('1') % 2 != 0 else '0'
    return bits + bit_par


def receptor_paridade(bits: str) -> tuple[bool, str]:
    """
    Verifica o bit de paridade par.

    Parâmetros:
    - bits: string de bits com bit de paridade ao final

    Retorno:
    - (valido, dados): valido=True se paridade correta, dados sem o bit de paridade
    """
    dado = bits[:-1]
    bit_recebido = bits[-1]
    bit_esperado = '1' if dado.count('1') % 2 != 0 else '0'
    return (bit_recebido == bit_esperado, dado)


# ---------------------------------------------------------------------------
# 2. Checksum (16 bits, complemento de 1)
# ---------------------------------------------------------------------------

def _checksum_calcular(bits: str) -> str:
    """Calcula checksum de 16 bits por soma em complemento de 1."""
    # Padding para múltiplo de 16
    padding = (16 - len(bits) % 16) % 16
    bits_pad = bits + '0' * padding

    soma = 0
    for i in range(0, len(bits_pad), 16):
        palavra = int(bits_pad[i:i+16], 2)
        soma += palavra
        # Carry around
        soma = (soma & 0xFFFF) + (soma >> 16)

    return format(~soma & 0xFFFF, '016b')


def transmissor_checksum(bits: str) -> str:
    """
    Acrescenta o checksum de 16 bits ao final da string de bits.

    Parâmetros:
    - bits: string de bits de dado

    Retorno:
    - string de bits com checksum de 16 bits ao final
    """
    return bits + _checksum_calcular(bits)


def receptor_checksum(bits: str) -> tuple[bool, str]:
    """
    Verifica o checksum de 16 bits.

    Parâmetros:
    - bits: string de bits com checksum de 16 bits ao final

    Retorno:
    - (valido, dados): valido=True se checksum correto, dados sem o checksum
    """
    dado = bits[:-16]
    checksum_recebido = bits[-16:]
    checksum_calculado = _checksum_calcular(dado)
    return (checksum_recebido == checksum_calculado, dado)


# ---------------------------------------------------------------------------
# 3. CRC-32 (IEEE 802.3)
# ---------------------------------------------------------------------------

_CRC32_POLINOMIO = 0x04C11DB7
_CRC32_XOR_OUT   = 0xFFFFFFFF


def _crc32_calcular(bits: str) -> str:
    """Calcula o CRC-32 de acordo com IEEE 802.3."""
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
    """
    Acrescenta o CRC-32 (IEEE 802.3) ao final da string de bits.

    Parâmetros:
    - bits: string de bits de dado

    Retorno:
    - string de bits com CRC-32 de 32 bits ao final
    """
    return bits + _crc32_calcular(bits)


def receptor_crc(bits: str) -> tuple[bool, str]:
    """
    Verifica o CRC-32 (IEEE 802.3).

    Parâmetros:
    - bits: string de bits com CRC-32 ao final

    Retorno:
    - (valido, dados): valido=True se CRC correto, dados sem os 32 bits de CRC
    """
    dado = bits[:-32]
    crc_recebido = bits[-32:]
    crc_calculado = _crc32_calcular(dado)
    return (crc_recebido == crc_calculado, dado)
