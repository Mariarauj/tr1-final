'''
Implementa modulações digitais (NRZ-Polar, Manchester, Bipolar)
            modulações por portadora (ASK, FSK, QPSK, 16-QAM).

'''
import numpy as np

# Modulações Digitais (banda-base)
def nrz_polar(dados: list[int]) -> np.ndarray:
    #Coleta 100 amostras por bit.
    
    V = 1
    amostras_por_bit = 100
    sinal = np.array([-V if bit == 0 else V for bit in dados])
    return np.repeat(sinal, amostras_por_bit).astype(float)


def manchester(dados: list[int]) -> np.ndarray:   
    V = 1
    sinal = []
    for bit in dados:
        if bit == 1:
            sinal.extend([V, -V])
        else:
            sinal.extend([-V, V])
    return np.array(sinal, dtype=float)


def bipolar(dados: list[int]) -> np.ndarray:
    V = 1
    estado = 1
    sinal = []
    for bit in dados:
        if bit == 0:
            sinal.append(0)
        else:
            sinal.append(estado * V)
            estado *= -1
    return np.repeat(np.array(sinal, dtype=float), 100)



# Modulações por Portadora
def ask(dados: list[int]) -> tuple[np.ndarray, np.ndarray]:
    A = 1
    f = 2          # Hz
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
    duracao_simbolo = 0.1   # segundos
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
