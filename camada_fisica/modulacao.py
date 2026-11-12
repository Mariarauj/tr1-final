'''
Implementa modulações digitais (NRZ-Polar, Manchester, Bipolar)
            modulações por portadora (ASK, FSK, 8PSK, 32-QAM).

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

# Modulações por constelação (8PSK e 32-QAM) -------------------------------------------------

FS              = 1000   # taxa de amostragem (Hz)
F_PORTADORA     = 10     # frequência da portadora (Hz): 1 ciclo completo por símbolo
DURACAO_SIMBOLO = 0.1    # segundos por símbolo

# 8PSK: 3 bits por símbolo, 8 fases espaçadas de 45° (amplitude 1) com código Gray
_GRAY_8PSK = ['000', '001', '011', '010', '110', '111', '101', '100']
_CONSTELACAO_8PSK = {
    cod: (np.cos(k * np.pi / 4), np.sin(k * np.pi / 4))
    for k, cod in enumerate(_GRAY_8PSK)
}

# 32-QAM: 5 bits por símbolo, grade 6x6 em formato de cruz (sem os 4 cantos) = 32 pontos
_NIVEIS_QAM32 = [-5, -3, -1, 1, 3, 5]
_PONTOS_32QAM = [(i, q) for i in _NIVEIS_QAM32 for q in _NIVEIS_QAM32
                 if not (abs(i) == 5 and abs(q) == 5)]
_CONSTELACAO_32QAM = {f'{idx:05b}': ponto for idx, ponto in enumerate(_PONTOS_32QAM)}


def _modular_constelacao(dados: list[int], bits_por_simbolo: int, constelacao: dict) -> tuple[np.ndarray, np.ndarray]:
    # Agrupa os bits em símbolos e transmite cada um como I·cos(2πft) - Q·sen(2πft).
    bits_str = ''.join(map(str, dados))
    bits_str += '0' * (-len(bits_str) % bits_por_simbolo)   # padding até completar o último símbolo

    simbolos = [bits_str[i:i + bits_por_simbolo] for i in range(0, len(bits_str), bits_por_simbolo)]
    amostras_por_simbolo = int(DURACAO_SIMBOLO * FS)
    t = np.arange(len(simbolos) * amostras_por_simbolo) / FS
    sinal = np.zeros_like(t)

    for i, s in enumerate(simbolos):
        I, Q = constelacao[s]
        inicio = i * amostras_por_simbolo
        fim = inicio + amostras_por_simbolo
        sinal[inicio:fim] = (
            I * np.cos(2 * np.pi * F_PORTADORA * t[inicio:fim])
            - Q * np.sin(2 * np.pi * F_PORTADORA * t[inicio:fim])
        )
    return t, sinal


def psk8(dados: list[int]) -> tuple[np.ndarray, np.ndarray]:
    # 8PSK: 3 bits por símbolo.
    return _modular_constelacao(dados, 3, _CONSTELACAO_8PSK)


def qam32(dados: list[int]) -> tuple[np.ndarray, np.ndarray]:
    # 32-QAM: 5 bits por símbolo.
    return _modular_constelacao(dados, 5, _CONSTELACAO_32QAM)