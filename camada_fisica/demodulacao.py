'''
Implementa demodulação para ASK, FSK, QPSK e 16-QAM.

'''

import numpy as np
from camada_fisica.modulacao import _CONSTELACAO_QPSK, _CONSTELACAO_16QAM_INV



# Demodulação Digital (banda-base)
def demod_nrz_polar(sinal: np.ndarray) -> list[int]:
    #NRZ-Polar: divide o sinal em blocos de 100 amostras e decide por limiar.

    amostras_por_bit = 100
    bits = []
    for i in range(0, len(sinal), amostras_por_bit):
        segmento = sinal[i:i + amostras_por_bit]
        if len(segmento) < amostras_por_bit:
            break
        bits.append(1 if np.mean(segmento) >= 0 else 0)
    return bits


def demod_manchester(sinal: np.ndarray) -> list[int]:
    #Manchester: cada bit ocupa 2 amostras; detecta transição alta→baixa (1) ou baixa→alta (0).
   
    # 200 amostras por bit (100 para cada metade)
    amostras_por_bit = 200
    bits = []
    for i in range(0, len(sinal), amostras_por_bit):
        segmento = sinal[i:i + amostras_por_bit]
        if len(segmento) < amostras_por_bit:
            break
        metade = amostras_por_bit // 2
        primeira = np.mean(segmento[:metade])
        segunda = np.mean(segmento[metade:])
        bits.append(1 if primeira > segunda else 0)
    return bits


def demod_bipolar(sinal: np.ndarray) -> list[int]:
    #Bipolar (AMI): limiar zero — qualquer valor ≠ 0 é bit 1.

    amostras_por_bit = 100
    bits = []
    for i in range(0, len(sinal), amostras_por_bit):
        segmento = sinal[i:i + amostras_por_bit]
        if len(segmento) < amostras_por_bit:
            break
        bits.append(0 if abs(np.mean(segmento)) < 0.1 else 1)
    return bits



# Demodulação por Portadora
def demod_ask(tempo: np.ndarray, sinal: np.ndarray) -> list[int]:
    #ASK: compara energia média de cada segmento com limiar de 0,5.
  
    amostras_por_bit = 100
    limiar = 0.5
    bits = []
    for i in range(0, len(sinal), amostras_por_bit):
        segmento = sinal[i:i + amostras_por_bit]
        if len(segmento) < amostras_por_bit:
            break
        bits.append(1 if np.mean(np.abs(segmento)) > limiar else 0)
    return bits


def demod_fsk(tempo: np.ndarray, sinal: np.ndarray) -> list[int]:
    #FSK: FFT por segmento para identificar frequência dominante.
    #f1=2 Hz → bit 1, f0=1 Hz → bit 0.

    f1, f0 = 2, 1
    amostras_por_bit = 100
    bits = []
    dt = tempo[1] - tempo[0] if len(tempo) > 1 else 0.01

    for i in range(0, len(sinal), amostras_por_bit):
        segmento = sinal[i:i + amostras_por_bit]
        if len(segmento) < amostras_por_bit:
            break
        fft = np.abs(np.fft.fft(segmento))
        freqs = np.fft.fftfreq(len(segmento), d=dt)
        mask = freqs > 0
        freq_dom = freqs[mask][np.argmax(fft[mask])]
        bits.append(1 if abs(freq_dom - f1) < abs(freq_dom - f0) else 0)
    return bits


def demod_qpsk(tempo: np.ndarray, sinal: np.ndarray) -> list[int]:
    #QPSK: correlação com portadoras I e Q; busca o símbolo mais próximo.
    #Retorna lista de bits (2 bits por símbolo).
  
    fs = 1000
    f_portadora = 10
    duracao_simbolo = 0.1
    amostras_por_simbolo = int(duracao_simbolo * fs)
    bits = []

    _inv = {v: k for k, v in _CONSTELACAO_QPSK.items()}

    for i in range(0, len(sinal) - amostras_por_simbolo + 1, amostras_por_simbolo):
        seg = sinal[i:i + amostras_por_simbolo]
        t_seg = tempo[i:i + amostras_por_simbolo]
        I = 2 * np.mean(seg * np.cos(2 * np.pi * f_portadora * t_seg))
        Q = -2 * np.mean(seg * np.sin(2 * np.pi * f_portadora * t_seg))

        # Decisão por mínima distância
        menor_dist = float('inf')
        simbolo = '00'
        for s, (Ir, Qr) in _CONSTELACAO_QPSK.items():
            d = (I - Ir) ** 2 + (Q - Qr) ** 2
            if d < menor_dist:
                menor_dist = d
                simbolo = s
        bits.extend([int(b) for b in simbolo])
    return bits


def demod_qam16(tempo: np.ndarray, sinal: np.ndarray) -> list[int]:
    #16-QAM: correlação com portadoras I e Q; busca o símbolo mais próximo.
    #Retorna lista de bits (4 bits por símbolo).
  
    fs = 1000
    f_portadora = 10
    duracao_simbolo = 0.1
    amostras_por_simbolo = int(duracao_simbolo * fs)
    bits = []

    for i in range(0, len(sinal) - amostras_por_simbolo + 1, amostras_por_simbolo):
        seg = sinal[i:i + amostras_por_simbolo]
        t_seg = tempo[i:i + amostras_por_simbolo]
        I = 2 * np.mean(seg * np.cos(2 * np.pi * f_portadora * t_seg))
        Q = -2 * np.mean(seg * np.sin(2 * np.pi * f_portadora * t_seg))

        menor_dist = float('inf')
        simbolo = '0000'
        for (Ir, Qr), cod in _CONSTELACAO_16QAM_INV.items():
            d = (I - Ir) ** 2 + (Q - Qr) ** 2
            if d < menor_dist:
                menor_dist = d
                simbolo = cod
        bits.extend([int(b) for b in simbolo])
    return bits
