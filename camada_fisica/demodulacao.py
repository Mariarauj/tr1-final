import numpy as np
from camada_fisica.modulacao import (
    FS, F_PORTADORA, DURACAO_SIMBOLO, _CONSTELACAO_8PSK, _CONSTELACAO_32QAM,
)

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
    amostras_por_bit = 100   # 2 metades de 50 amostras (igual ao modulador)
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
        bits.append(0 if abs(np.mean(segmento)) < 0.5 else 1)   # níveis 0 e ±V: limiar V/2
    return bits



# Demodulação por Portadora
def demod_ask(tempo: np.ndarray, sinal: np.ndarray) -> list[int]:
    # Detecção coerente: correlaciona cada bit com a portadora (mesma amplitude e frequência do
    # modulador). O resultado estima a amplitude recebida (≈ A para bit 1, ≈ 0 para bit 0) e o
    # ruído gaussiano tem média zero nela, ao contrário da média do valor absoluto, que o ruído eleva.
    A, f = 1, 2
    amostras_por_bit = 100
    limiar = A / 2
    bits = []
    for i in range(0, len(sinal), amostras_por_bit):
        segmento = sinal[i:i + amostras_por_bit]
        if len(segmento) < amostras_por_bit:
            break
        t_seg = tempo[i:i + amostras_por_bit]
        amplitude = 2 * np.mean(segmento * np.sin(2 * np.pi * f * t_seg))
        bits.append(1 if amplitude > limiar else 0)
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


def _demodular_constelacao(tempo: np.ndarray, sinal: np.ndarray, constelacao: dict) -> list[int]:
    # Correlaciona cada símbolo com cos/sen para recuperar (I, Q) e decide pelo ponto mais próximo.
    amostras_por_simbolo = int(DURACAO_SIMBOLO * FS)
    bits = []

    for i in range(0, len(sinal) - amostras_por_simbolo + 1, amostras_por_simbolo):
        seg = sinal[i:i + amostras_por_simbolo]
        t_seg = tempo[i:i + amostras_por_simbolo]
        I = 2 * np.mean(seg * np.cos(2 * np.pi * F_PORTADORA * t_seg))
        Q = -2 * np.mean(seg * np.sin(2 * np.pi * F_PORTADORA * t_seg))

        # Decisão por mínima distância
        simbolo = min(constelacao,
                      key=lambda c: (I - constelacao[c][0]) ** 2 + (Q - constelacao[c][1]) ** 2)
        bits.extend(int(b) for b in simbolo)
    return bits


def demod_psk8(tempo: np.ndarray, sinal: np.ndarray) -> list[int]:
    return _demodular_constelacao(tempo, sinal, _CONSTELACAO_8PSK)


def demod_qam32(tempo: np.ndarray, sinal: np.ndarray) -> list[int]:
    return _demodular_constelacao(tempo, sinal, _CONSTELACAO_32QAM)