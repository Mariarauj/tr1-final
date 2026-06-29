def transmissor_hamming(bits: str) -> str:
    n_dados = len(bits)

    # Calcula número de bits de paridade necessários: 2^r >= n + r + 1
    r = 1
    while (1 << r) < (n_dados + r + 1):
        r += 1

    n_total = n_dados + r
    codificado = [0] * n_total

    # Preenche posições de dados (pula as posições de paridade)
    j = 0
    for i in range(1, n_total + 1):
        if i & (i - 1) != 0:   
            codificado[i - 1] = int(bits[j])
            j += 1

    # Calcula bits de paridade
    for k in range(r):
        pos_par = 1 << k       
        paridade = 0
        for i in range(1, n_total + 1):
            if i & pos_par:
                paridade ^= codificado[i - 1]
        codificado[pos_par - 1] = paridade

    return ''.join(map(str, codificado))


def receptor_hamming(bits: str) -> tuple[str, int]:
    #Decodifica e corrige (se necessário) uma mensagem com código de Hamming.

    n_total = len(bits)
    codificado = [int(b) for b in bits]

    # Calcula número de bits de paridade
    r = 0
    while (1 << r) < n_total:
        r += 1

    # Síndrome: recalcula cada bit de paridade
    pos_erro = 0
    for k in range(r):
        pos_par = 1 << k
        paridade = 0
        for i in range(1, n_total + 1):
            if i & pos_par:
                paridade ^= codificado[i - 1]
        if paridade != 0:
            pos_erro += pos_par

    # Corrige o bit errado (se tiver né)
    if 0 < pos_erro <= n_total:
        codificado[pos_erro - 1] ^= 1

    # Remove bits de paridade
    dados = []
    for i in range(1, n_total + 1):
        if i & (i - 1) != 0:          # não é potência de 2
            dados.append(str(codificado[i - 1]))

    return ''.join(dados), pos_erro
