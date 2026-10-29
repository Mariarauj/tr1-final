'''
Implementa modulações digitais (NRZ-Polar, Manchester, Bipolar)
            modulações por portadora (ASK, FSK, QPSK, 16-QAM).

As funções devem receber um trem de bits (0s e 1s) - 'dados' - e retornar valores numéricos representando o sinal modulado.

'''
import numpy as np #facilita operações matemáticas e consequente manipulação de sinais.

# Modulações Digitais (banda-base) -------------------------------------------------------------

def nrz_polar(dados: list[int]) -> np.ndarray: 
    '''
    Os bits 0 serão representados como -V e os bits 1 como +V.
    '''
    V = 1 #define a amplitude do sinal
    amostras_por_bit = 100 #define 100 amostras por bit.
    sinal = np.array([-V if bit == 0 else V for bit in dados]) #define o sinal -V e V para bit 0 e V para bit 1.
    return np.repeat(sinal, amostras_por_bit).astype(float) #repete cada elemento do sinal 100x -> [1, -1] = [1, 1, ..., 1, -1, -1, ..., -1]


def manchester(dados: list[int]) -> np.ndarray: 
    '''
    Os bits serão definidos como uma transição entre +V e -V ou -V para +V.
    Cada bit é representado por duas amostras, uma para cada metade do período do bit.

    '''  
    V = 1 #define a amplitude do sinal
    amostras_por_transicao = 50 #define 50 amostras por transição (cada bit seguirá com 100 amostras).
    sinal = [] #lista vazia para armazenar o sinal modulado.
    for bit in dados:
        if bit == 1:
            sinal.extend([V, -V]) #para bit 1, adiciona V = 1 para a primeira metade do período e -V = -1 para a segunda metade do período.
        else:
            sinal.extend([-V, V]) #para bit 0, adiciona -V = -1 para a primeira metade do período e V = 1 para a segunda metade do período.
    return np.repeat(np.array(sinal, dtype=float), amostras_por_transicao)


def bipolar(dados: list[int]) -> np.ndarray:
    '''
    Os bits 0 serão definidos por V = 0 e os bits 1 como uma alternância entre +V e -V.
    '''
    V = 1 #define a amplitude do sinal
    amostras_por_bit = 100 #define 100 amostras por bit.
    estado = 1 #define a polaridade do próximo bit 1.
    sinal = []
    for bit in dados:
        if bit == 0:
            sinal.append(0) #para bit 0 o sinal será 0
        else:
            sinal.append(estado * V) #para bit 1, define o sinal como +V se estado = 1 e -V se estado = -1.
            estado *= -1 #inverte a polaridade do próximo bit 1.
    return np.repeat(np.array(sinal, dtype=float), amostras_por_bit) 



# Modulações por Portadora -----------------------------------------------------------------

def ask(dados: list[int]) -> tuple[np.ndarray, np.ndarray]:
    '''
    Os bits 1 serão definidos pela presença de sinal e os bits 0 pela ausencia dele.
    '''
    A = 1
    f = 2     
    amostras_por_bit = 100
    tempo_total = []
    sinal = []
    for i, bit in enumerate(dados):
        t = np.linspace(i, i + 1, amostras_por_bit, endpoint=False)
        if bit == 1:
            sinal.extend(A * np.sin(2 * np.pi * f * t))
        else:
            sinal.extend(np.zeros(amostras_por_bit))
        tempo_total.extend(t)
    return np.array(tempo_total), np.array(sinal)


def fsk(dados: list[int]) -> tuple[np.ndarray, np.ndarray]:
    A = 1
    f1, f0 = 2, 1
    amostras_por_bit = 100
    tempo_total = []
    sinal = []
    for i, bit in enumerate(dados):
        t = np.linspace(i, i + 1, amostras_por_bit, endpoint=False)
        freq = f1 if bit == 1 else f0
        sinal.extend(A * np.sin(2 * np.pi * freq * t))
        tempo_total.extend(t)
    return np.array(tempo_total), np.array(sinal)

_CONSTELACAO_QPSK = {
    '00': ( 1,  1),
    '01': (-1,  1),
    '10': (-1, -1),
    '11': ( 1, -1),
}

def qpsk(dados: list[int]) -> tuple[np.ndarray, np.ndarray]:
    bits_str = ''.join(map(str, dados))
    # Padding para múltiplo de 2
    if len(bits_str) % 2 != 0:
        bits_str += '0'

    simbolos = [bits_str[i:i+2] for i in range(0, len(bits_str), 2)]
    fs = 1000 
    f_portadora = 10
    duracao_simbolo = 0.1   # cada 0,1 segundo transmite 2 bits
    t = np.arange(0, len(simbolos) * duracao_simbolo, 1 / fs)
    sinal = np.zeros_like(t)

    for i, s in enumerate(simbolos):
        I, Q = _CONSTELACAO_QPSK[s]
        inicio = int(i * duracao_simbolo * fs)
        fim = int((i + 1) * duracao_simbolo * fs)
        sinal[inicio:fim] = (
            I * np.cos(2 * np.pi * f_portadora * t[inicio:fim])
            - Q * np.sin(2 * np.pi * f_portadora * t[inicio:fim])
        )
    return t, sinal


# Constelação 16-QAM - 16 símbolos (le-se: 4 bits por símbolo)
_NIVEIS_QAM16 = [-3, -1, 1, 3]
_CONSTELACAO_16QAM: dict[str, tuple[int, int]] = {}
idx = 0
for _i in _NIVEIS_QAM16:
    for _q in _NIVEIS_QAM16:
        _CONSTELACAO_16QAM[f'{idx:04b}'] = (_i, _q)
        idx += 1

_CONSTELACAO_16QAM_INV = {v: k for k, v in _CONSTELACAO_16QAM.items()}

def qam16(dados: list[int]) -> tuple[np.ndarray, np.ndarray]:
    #16-QAM: 4 bits por símbolo, 16 pontos na constelação.
    #Retorna (tempo, sinal).
    
    bits_str = ''.join(map(str, dados))
    # Padding para múltiplo de 4
    padding = (4 - len(bits_str) % 4) % 4
    bits_str += '0' * padding

    simbolos = [bits_str[i:i+4] for i in range(0, len(bits_str), 4)]
    fs = 1000
    f_portadora = 10
    duracao_simbolo = 0.1
    t = np.arange(0, len(simbolos) * duracao_simbolo, 1 / fs)
    sinal = np.zeros_like(t)

    for i, s in enumerate(simbolos):
        I, Q = _CONSTELACAO_16QAM[s]
        inicio = int(i * duracao_simbolo * fs)
        fim = int((i + 1) * duracao_simbolo * fs)
        sinal[inicio:fim] = (
            I * np.cos(2 * np.pi * f_portadora * t[inicio:fim])
            - Q * np.sin(2 * np.pi * f_portadora * t[inicio:fim])
        )
    return t, sinal
