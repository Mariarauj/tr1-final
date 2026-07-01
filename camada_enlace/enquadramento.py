'''
Implementa os três tipos de enquadramento exigidos:
  1. Contagem de caracteres
  2. Inserção de bytes (flags + ESC byte)
  3. Inserção de bits  (flag 01111110 + bit stuffing)

'''

#Retorna -1 em caso de erro
# 1. Contagem de caracteres
def transmissor_contagem(bits: str, tamanho_quadro: int = 6) -> str:
    if len(bits) % 8 != 0:
        return '-1'

    lista_bytes = [bits[i:i+8] for i in range(0, len(bits), 8)]
    total = len(lista_bytes)
    quadros = []

    i = 0
    while i < total:
        bloco = lista_bytes[i:i + tamanho_quadro]
        cabecalho = format(len(bloco), '08b')
        quadros.append(cabecalho + ''.join(bloco))
        i += tamanho_quadro

    return ''.join(quadros)


def receptor_contagem(bits: str) -> str:
    if len(bits) % 8 != 0:
        return '-1'

    conteudo = ''
    num_bytes = len(bits) // 8
    idx = 0

    while idx < num_bytes:
        cabecalho = bits[idx*8:(idx+1)*8]
        n = int(cabecalho, 2)
        idx += 1
        if idx + n > num_bytes:
            return '-1'
        for _ in range(n):
            conteudo += bits[idx*8:(idx+1)*8]
            idx += 1

    return conteudo


# 2. Inserção de bytes
_FLAG_IB  = '00100110'   # '&' (0x26)
_ESC_IB   = '00011011'   # ESC (0x1B)


def transmissor_insercao_bytes(bits: str, tamanho_quadro: int = 6) -> str:
    if len(bits) % 8 != 0:
        return '-1'

    lista_bytes = [bits[i:i+8] for i in range(0, len(bits), 8)]
    quadros = ''

    while lista_bytes:
        bloco = lista_bytes[:tamanho_quadro]
        lista_bytes = lista_bytes[tamanho_quadro:]

        corpo = ''
        for byte in bloco:
            if byte == _FLAG_IB or byte == _ESC_IB:
                corpo += _ESC_IB
            corpo += byte

        quadros += _FLAG_IB + corpo + _FLAG_IB

    return quadros


def receptor_insercao_bytes(bits: str) -> str:
    if len(bits) % 8 != 0:
        return '-1'

    conteudo = ''
    num_bytes = len(bits) // 8
    idx = 0

    while idx < num_bytes:
        byte = bits[idx*8:(idx+1)*8]
        prox  = bits[(idx+1)*8:(idx+2)*8]

        if byte == _ESC_IB:
            if prox in (_FLAG_IB, _ESC_IB):
                conteudo += prox
                idx += 2
            else:
                return '-1'
        elif byte == _FLAG_IB:
            idx += 1
        else:
            conteudo += byte
            idx += 1

    return conteudo

# 3. Inserção de bits (bit stuffing)
_FLAG_BITS = '01111110' 

def transmissor_insercao_bits(bits: str) -> str:   
    stuffed = ''
    contagem_uns = 0

    for bit in bits:
        stuffed += bit
        if bit == '1':
            contagem_uns += 1
            if contagem_uns == 5:
                stuffed += '0'   #Prevenir erros!!!!!
                contagem_uns = 0
        else:
            contagem_uns = 0

    return _FLAG_BITS + stuffed + _FLAG_BITS


def receptor_insercao_bits(bits: str) -> str:    
    flag = _FLAG_BITS

    inicio = bits.find(flag)
    if inicio == -1:
        return '-1'
    fim = bits.rfind(flag)
    if fim == inicio:
        return '-1'

    dados_stuffed = bits[inicio + len(flag):fim]

    # Remove bits de stuffing
    destuffed = ''
    contagem_uns = 0
    i = 0
    while i < len(dados_stuffed):
        bit = dados_stuffed[i]
        if bit == '1':
            contagem_uns += 1
            destuffed += bit
            if contagem_uns == 5:
                i += 1        
                contagem_uns = 0
        else:
            contagem_uns = 0
            destuffed += bit
        i += 1

    return destuffed
