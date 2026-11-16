'''
Monta e desmonta os QUADROS da camada de enlace: enquadramento + EDC de cada quadro.

Transmissor: a mensagem é dividida em blocos de até 'tamanho_quadro' bytes (o último pode ser menor). Cada
bloco vira um quadro, pelo enquadramento escolhido, e recebe o seu próprio EDC (código de detecção de erros).
Receptor: lê os quadros um a um, confere o EDC de cada um e informa quais chegaram com erro.

Onde fica o EDC de cada quadro:
  - Paridade, Checksum e CRC: calculado sobre o quadro inteiro (cabeçalho ou flags + dados) e anexado
    logo depois dele (depois da flag final, ou do último byte, no caso da contagem de caracteres).
  - Entrelaçamento: a matriz (colunas + paridades) é a carga útil do quadro, dentro das flags/contagem.

O enquadramento sozinho (deteccao=None) gera apenas os quadros, sem EDC.

'''
from camada_enlace.enquadramento import (
    quadro_contagem, ler_quadro_contagem,
    quadro_insercao_bytes, ler_quadro_insercao_bytes,
    quadro_insercao_bits, ler_quadro_insercao_bits,
    tamanho_quadro_valido,
)
from camada_enlace.deteccao_erros import (
    payload_do_quadro, edc_do_quadro, verificar_quadro, tamanho_sufixo_edc, tamanho_extra_payload,
)


def _montar_um_quadro(enquadramento: str, payload: str, n_bytes_dados: int) -> str:
    '''
    Monta um quadro com o enquadramento escolhido.
    '''
    if enquadramento == 'Contagem de Caracteres':
        return quadro_contagem(payload, n_bytes_dados)
    elif enquadramento == 'Inserção de Bytes':
        return quadro_insercao_bytes(payload)
    else:                                       # Inserção de Bits
        return quadro_insercao_bits(payload)


def _ler_um_quadro(enquadramento: str, bits: str, pos: int, bits_extra: int):
    '''
    Lê o quadro que começa em 'pos' com o enquadramento escolhido: devolve (carga útil, nova posição) ou None.
    '''
    if enquadramento == 'Contagem de Caracteres':
        return ler_quadro_contagem(bits, pos, bits_extra)
    elif enquadramento == 'Inserção de Bytes':
        return ler_quadro_insercao_bytes(bits, pos)
    else:                                       # Inserção de Bits
        return ler_quadro_insercao_bits(bits, pos)


def montar_quadros(bits: str, enquadramento: str, tamanho_quadro: int,
                   deteccao: str | None = None, tam_edc: int = 0) -> str:
    '''
    Divide os bits em quadros de até 'tamanho_quadro' bytes, enquadra cada um e (se 'deteccao' for dada)
    anexa o EDC de cada quadro. Retorna '-1' em caso de erro.
    '''
    if len(bits) % 8 != 0 or not tamanho_quadro_valido(tamanho_quadro): #só é possível enquadrar bytes completos, com tamanho de quadro válido.
        return '-1'

    passo = tamanho_quadro * 8 #quantidade de bits de dados de um quadro cheio.
    fluxo = '' #sequência final de quadros.
    for i in range(0, len(bits), passo):
        dados = bits[i:i + passo] #dados deste quadro (o último pode ser menor).
        if deteccao is None:
            payload = dados #sem detecção: só o enquadramento.
        else:
            payload = payload_do_quadro(deteccao, dados, tam_edc) #no entrelaçamento, a matriz com as paridades.
        quadro = _montar_um_quadro(enquadramento, payload, len(dados) // 8)
        sufixo = '' if deteccao is None else edc_do_quadro(deteccao, quadro, tam_edc) #EDC calculado sobre o quadro inteiro.
        fluxo += quadro + sufixo #quadro + EDC.

    return fluxo


def desmontar_quadros(bits: str, enquadramento: str,
                      deteccao: str | None = None, tam_edc: int = 0) -> tuple[str, list[int], int]:
    '''
    Lê o fluxo quadro a quadro, confere o EDC de cada um (se 'deteccao' for dada) e junta os dados.
    Retorna (dados, números dos quadros com erro de EDC, quantidade de quadros lidos).
    Os dados são '-1' se o fluxo não puder ser separado em quadros.
    '''
    bits_extra = 0 if deteccao is None else tamanho_extra_payload(deteccao, tam_edc) #bits da carga útil além dos dados.
    tam_sufixo = 0 if deteccao is None else tamanho_sufixo_edc(deteccao, tam_edc) #bits de EDC depois do quadro.

    dados, com_erro, lidos, pos = '', [], 0, 0 #dados extraídos, quadros com erro, quadros lidos e posição no fluxo.
    while pos < len(bits):
        quadro = _ler_um_quadro(enquadramento, bits, pos, bits_extra) #carga útil e fim do quadro.
        if quadro is None: #não foi possível delimitar o quadro.
            return '-1', com_erro, lidos
        payload, fim = quadro
        sufixo = bits[fim:fim + tam_sufixo] #EDC que vem depois do quadro.
        if len(sufixo) != tam_sufixo: #o fluxo acabou antes do EDC.
            return '-1', com_erro, lidos
        lidos += 1

        if deteccao is None:
            dados += payload
        else:
            valido, dados_quadro = verificar_quadro(deteccao, bits[pos:fim], payload, sufixo, tam_edc)
            if not valido:
                com_erro.append(lidos) #quadro com EDC diferente do esperado.
            dados += dados_quadro
        pos = fim + tam_sufixo #o próximo quadro começa depois do EDC.

    return dados, com_erro, lidos