'''
Implementa os tipos de enquadramento:
  1. Contagem de caracteres
  2. Inserção de bytes (flags + ESC byte)
  3. Inserção de bits  (flag 01111110 + bit stuffing)

Todas as funções trabalham com strings de bits ('0' e '1') e retornam '-1' em caso de erro.
Os bits que chegam são sempre múltiplos de 8, pois o texto é convertido em bytes (ASCII).

'''

#Retorna -1 em caso de erro

# 1. Contagem de caracteres ---------------------------------------------------------------

def transmissor_contagem(bits: str, tamanho_quadro: int = 6) -> str:
    '''
    Divide os bytes em quadros de até 'tamanho_quadro' bytes e coloca na frente de cada
    quadro 1 byte (cabeçalho) com a quantidade de bytes do quadro.
    '''
    if len(bits) % 8 != 0: #só é possível enquadrar bytes completos.
        return '-1'

    lista_bytes = [bits[i:i+8] for i in range(0, len(bits), 8)] #separa a string de bits em bytes de 8 bits.
    total = len(lista_bytes) #quantidade total de bytes a enquadrar.
    quadros = [] #lista vazia para armazenar os quadros prontos.

    i = 0 #posição do primeiro byte do quadro atual.
    while i < total:
        bloco = lista_bytes[i:i + tamanho_quadro] #pega até 'tamanho_quadro' bytes (o último quadro pode ser menor).
        cabecalho = format(len(bloco), '08b') #cabeçalho = quantidade de bytes do quadro, escrita em 8 bits.
        quadros.append(cabecalho + ''.join(bloco)) #quadro = cabeçalho + bytes de dados.
        i += tamanho_quadro #avança para o próximo quadro.

    return ''.join(quadros) #junta todos os quadros em uma única sequência de bits.


def receptor_contagem(bits: str) -> str:
    '''
    Lê o cabeçalho de cada quadro, extrai a quantidade de bytes indicada e descarta o cabeçalho.
    '''
    if len(bits) % 8 != 0: #o fluxo deve ter bytes completos.
        return '-1'

    conteudo = '' #armazena os dados extraídos, sem os cabeçalhos.
    num_bytes = len(bits) // 8 #quantidade total de bytes recebidos.
    idx = 0 #posição (em bytes) que está sendo lida.

    while idx < num_bytes:
        cabecalho = bits[idx*8:(idx+1)*8] #lê o byte de cabeçalho do quadro.
        n = int(cabecalho, 2) #converte o cabeçalho para número: quantos bytes de dados vêm a seguir.
        idx += 1 #pula o cabeçalho.
        if idx + n > num_bytes: #o cabeçalho diz que há mais bytes do que realmente chegaram -> quadro inválido.
            return '-1'
        for _ in range(n):
            conteudo += bits[idx*8:(idx+1)*8] #copia os n bytes de dados do quadro.
            idx += 1

    return conteudo


# 2. Inserção de bytes ---------------------------------------------------------------------

_FLAG_IB  = '00100110'   # '&' (0x26): byte que marca o início e o fim de cada quadro.
_ESC_IB   = '00011011'   # ESC (0x1B): byte de escape, colocado antes de dados iguais à flag ou ao ESC.


def transmissor_insercao_bytes(bits: str, tamanho_quadro: int = 6) -> str:
    '''
    Cada quadro (até 'tamanho_quadro' bytes) é delimitado por uma flag no início e outra no fim.
    Se um byte de dados for igual à flag ou ao ESC, um ESC é inserido antes dele (byte stuffing).
    '''
    if len(bits) % 8 != 0: #só é possível enquadrar bytes completos.
        return '-1'

    lista_bytes = [bits[i:i+8] for i in range(0, len(bits), 8)] #separa a string de bits em bytes.
    quadros = '' #armazena a sequência final de quadros.

    while lista_bytes:
        bloco = lista_bytes[:tamanho_quadro] #pega os bytes do quadro atual.
        lista_bytes = lista_bytes[tamanho_quadro:] #remove esses bytes da lista.

        corpo = '' #conteúdo do quadro, já com os escapes.
        for byte in bloco:
            if byte == _FLAG_IB or byte == _ESC_IB: #dado igual à flag ou ao ESC poderia confundir o receptor.
                corpo += _ESC_IB #insere um ESC antes dele.
            corpo += byte

        quadros += _FLAG_IB + corpo + _FLAG_IB #quadro = flag + corpo + flag.

    return quadros


def receptor_insercao_bytes(bits: str) -> str:
    '''
    Percorre os bytes: descarta as flags e, ao encontrar um ESC, mantém o byte seguinte como dado.
    '''
    if len(bits) % 8 != 0: #o fluxo deve ter bytes completos.
        return '-1'

    conteudo = '' #armazena os dados extraídos, sem flags e sem escapes.
    num_bytes = len(bits) // 8 #quantidade total de bytes recebidos.
    idx = 0 #posição (em bytes) que está sendo lida.

    while idx < num_bytes:
        byte = bits[idx*8:(idx+1)*8] #byte atual.
        prox  = bits[(idx+1)*8:(idx+2)*8] #byte seguinte (usado quando o atual é um ESC).

        if byte == _ESC_IB: #ESC: o byte seguinte é um dado e não deve ser interpretado.
            if prox in (_FLAG_IB, _ESC_IB):
                conteudo += prox #guarda o byte protegido (flag ou ESC dos dados).
                idx += 2 #pula o ESC e o byte protegido.
            else:
                return '-1' #ESC seguido de um byte que não precisava de escape -> erro.
        elif byte == _FLAG_IB: #flag de início/fim de quadro: não faz parte dos dados.
            idx += 1
        else:
            conteudo += byte #byte comum de dados.
            idx += 1

    return conteudo


# 3. Inserção de bits (bit stuffing) -------------------------------------------------------

_FLAG_BITS = '01111110' #flag que delimita o quadro (seis 1 seguidos entre dois 0).

def transmissor_insercao_bits(bits: str) -> str:
    '''
    Após cinco bits 1 seguidos nos dados, insere um bit 0 (bit stuffing), para que os dados
    nunca imitem a flag. O quadro é delimitado por uma flag no início e outra no fim.
    '''
    stuffed = '' #dados já com os bits de stuffing.
    contagem_uns = 0 #quantidade de bits 1 seguidos até agora.

    for bit in bits:
        stuffed += bit
        if bit == '1':
            contagem_uns += 1
            if contagem_uns == 5: #cinco 1 seguidos...
                stuffed += '0'   #...insere um 0 para prevenir uma flag acidental.
                contagem_uns = 0
        else:
            contagem_uns = 0 #um bit 0 quebra a sequência de 1.

    return _FLAG_BITS + stuffed + _FLAG_BITS #quadro = flag + dados com stuffing + flag.


def receptor_insercao_bits(bits: str) -> str:
    '''
    Localiza as flags, descarta-as e remove o bit 0 inserido após cada sequência de cinco 1.
    '''
    flag = _FLAG_BITS

    inicio = bits.find(flag) #posição da primeira flag.
    if inicio == -1: #nenhuma flag encontrada -> quadro inválido.
        return '-1'
    fim = bits.rfind(flag) #posição da última flag.
    if fim == inicio: #só existe uma flag -> falta o delimitador final.
        return '-1'

    dados_stuffed = bits[inicio + len(flag):fim] #bits entre a primeira e a última flag.

    # Remove bits de stuffing
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