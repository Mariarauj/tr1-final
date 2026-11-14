'''
Implementa o código de Hamming (correção de 1 bit de erro):
  - transmissor_hamming / receptor_hamming: codificam e decodificam UMA palavra.
  - transmissor_hamming_blocos / receptor_hamming_blocos: aplicam o Hamming(12,8) a cada byte,
    de modo que cada bloco corrige 1 erro por conta própria.

Nas posições que são potências de 2 (1, 2, 4, 8...) ficam os bits de paridade; as demais posições
guardam os dados.

'''

def transmissor_hamming(bits: str) -> str:
    '''
    Insere os bits de paridade do Hamming em uma sequência de dados.
    '''
    n_dados = len(bits) #quantidade de bits de dados.

    # Calcula número de bits de paridade necessários: 2^r >= n + r + 1
    r = 1 #quantidade de bits de paridade.
    while (1 << r) < (n_dados + r + 1):
        r += 1

    n_total = n_dados + r #tamanho da palavra codificada.
    codificado = [0] * n_total #palavra codificada (começa com zeros).

    # Preenche posições de dados (pula as posições de paridade)
    j = 0 #índice do próximo bit de dado.
    for i in range(1, n_total + 1):
        if i & (i - 1) != 0:   #posição que não é potência de 2 -> posição de dado.
            codificado[i - 1] = int(bits[j])
            j += 1

    # Calcula bits de paridade
    for k in range(r):
        pos_par = 1 << k       #posição do bit de paridade (1, 2, 4, 8...).
        paridade = 0
        for i in range(1, n_total + 1):
            if i & pos_par: #a paridade 'pos_par' cobre todas as posições que têm esse bit ligado.
                paridade ^= codificado[i - 1] #XOR dos bits cobertos.
        codificado[pos_par - 1] = paridade

    return ''.join(map(str, codificado))


def receptor_hamming(bits: str) -> tuple[str, int]:
    '''
    Decodifica e corrige (se necessário) uma palavra com código de Hamming.
    Retorna os dados (sem os bits de paridade) e a posição do erro (0 = nenhum erro).
    '''
    n_total = len(bits) #tamanho da palavra recebida.
    codificado = [int(b) for b in bits] #bits recebidos como lista de inteiros.

    # Calcula número de bits de paridade
    r = 0 #quantidade de bits de paridade da palavra.
    while (1 << r) < n_total:
        r += 1

    # recalcula cada bit de paridade
    pos_erro = 0 #síndrome: soma das paridades que falharam = posição do bit errado.
    for k in range(r):
        pos_par = 1 << k
        paridade = 0
        for i in range(1, n_total + 1):
            if i & pos_par:
                paridade ^= codificado[i - 1]
        if paridade != 0: #esta paridade falhou.
            pos_erro += pos_par

    # Corrige o bit errado (se tiver né)
    if 0 < pos_erro <= n_total:
        codificado[pos_erro - 1] ^= 1 #inverte o bit na posição indicada pela síndrome.

    # Remove bits de paridade
    dados = []
    for i in range(1, n_total + 1):
        if i & (i - 1) != 0:          # não é potência de 2
            dados.append(str(codificado[i - 1]))

    return ''.join(dados), pos_erro


TAMANHO_BLOCO = 8   # bits de dados por bloco -> Hamming(12,8), corrige 1 erro por bloco


def transmissor_hamming_blocos(bits: str, tam: int = TAMANHO_BLOCO) -> str:
    '''
    Aplica o Hamming a cada bloco de 'tam' bits (o último bloco é completado com zeros).
    '''
    resto = len(bits) % tam #bits que sobram no último bloco.
    if resto:
        bits += '0' * (tam - resto) #completa o último bloco com zeros (o receptor descarta depois).
    return ''.join(transmissor_hamming(bits[i:i + tam]) for i in range(0, len(bits), tam)) #codifica bloco a bloco.


def receptor_hamming_blocos(bits: str, n_dados: int, tam: int = TAMANHO_BLOCO) -> tuple[str, list[int]]:
    '''
    Decodifica bloco a bloco e descarta o padding final, usando 'n_dados' (tamanho antes do Hamming).
    Retorna os dados e a lista (bloco, posição) dos erros corrigidos.
    '''
    n_cod = len(transmissor_hamming('0' * tam)) #tamanho de um bloco codificado (12 bits para 8 de dados).
    dados, corrigidos = [], [] #dados decodificados e blocos em que houve correção.
    for b, i in enumerate(range(0, len(bits) - n_cod + 1, n_cod)):
        d, pos = receptor_hamming(bits[i:i + n_cod]) #decodifica um bloco.
        dados.append(d)
        if pos: #pos != 0: o bloco tinha um erro, que foi corrigido.
            corrigidos.append((b, pos))
    return ''.join(dados)[:n_dados], corrigidos #corta o padding do último bloco.