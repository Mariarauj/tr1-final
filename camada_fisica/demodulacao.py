import numpy as np
from camada_fisica.modulacao import _CONSTELACAO_QPSK, _CONSTELACAO_16QAM_INV

# Demodulação digital (Banda base)
def demod_nrz_polar(sinal: np.ndarray) -> list[int]:
    amostras_por_bit = 100
    bits = []
    for i in range(0, len(sinal), amostras_por_bit):
        segmento = sinal[i:i + amostras_por_bit]
        if len(segmento) < amostras_por_bit:
            break
        bits.append(1 if np.mean(segmento) >= 0 else 0)
    return bits


def demod_manchester(sinal: np.ndarray) -> list[int]:
    amostras_por_bit = 200 #100 pra cada, baby
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
    f1, f0 = 2, 1
    amostras_por_bit = 100
    bits = []
    dt = tempo[1] - tempo[0] if len(tempo) > 1 else 0.01

    for i in range(0, len(sinal), amostras_por_bit):
        segmento = sinal[i:i + amostras_por_bit]
        if len(segmento) < amostras_por_bit:
            break
        fft = np.abs(np.fft.fft(segmento)) #Fast Fourier Transform
        freqs = np.fft.fftfreq(len(segmento), d=dt) #qual frequencia corresponde a cada amplitude da FFT
        mask = freqs > 0 #ignora frequencias negativas
        freq_dom = freqs[mask][np.argmax(fft[mask])] #armax = posição da maior amplitude e freq_dom = retorna sua frequencia correspondente
        bits.append(1 if abs(freq_dom - f1) < abs(freq_dom - f0) else 0)
    return bits


def demod_qpsk(tempo: np.ndarray, sinal: np.ndarray) -> list[int]:
    fs = 1000
    f_portadora = 10
    duracao_simbolo = 0.1
    amostras_por_simbolo = int(duracao_simbolo * fs)
    bits = []

    #_inv = {v: k for k, v in _CONSTELACAO_QPSK.items()}

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
