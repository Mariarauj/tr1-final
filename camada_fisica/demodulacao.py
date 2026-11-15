'''
Implementa as demodulações digitais (NRZ-Polar, Manchester, Bipolar)
            e as demodulações por portadora (ASK, FSK, 8PSK, 32-QAM).

As funções recebem os valores numéricos do sinal (já com o ruído do canal) e retornam o trem de bits
estimado (lista de 0s e 1s). Cada demodulador é o inverso do modulador correspondente em modulacao.py.

'''
import numpy as np #facilita operações matemáticas e manipulação de sinais.
from camada_fisica.modulacao import (
    FS, F_PORTADORA, DURACAO_BIT, _CONSTELACAO_8PSK, _CONSTELACAO_32QAM,
)

# Demodulação digital (Banda base) --------------------------------------------------------

def demod_nrz_polar(sinal: np.ndarray) -> list[int]:
    '''
    Calcula a média de cada bit: média positiva = bit 1 e média negativa = bit 0.
    '''
    amostras_por_bit = 100 #mesma quantidade de amostras por bit usada na modulação.
    bits = [] #lista vazia para armazenar os bits recuperados.
    for i in range(0, len(sinal), amostras_por_bit):
        segmento = sinal[i:i + amostras_por_bit] #amostras de um bit.
        if len(segmento) < amostras_por_bit: #segmento incompleto no final do sinal é ignorado.
            break
        bits.append(1 if np.mean(segmento) >= 0 else 0) #a média atenua o ruído (que tem média zero).
    return bits


def demod_manchester(sinal: np.ndarray) -> list[int]:
    '''
    Compara a média das duas metades de cada bit: primeira > segunda = bit 1 (transição +V -> -V).
    '''
    amostras_por_bit = 100   # 2 metades de 50 amostras (igual ao modulador)
    bits = []
    for i in range(0, len(sinal), amostras_por_bit):
        segmento = sinal[i:i + amostras_por_bit] #amostras de um bit.
        if len(segmento) < amostras_por_bit:
            break
        metade = amostras_por_bit // 2 #posição que divide o bit em duas metades.
        primeira = np.mean(segmento[:metade]) #média da primeira metade.
        segunda = np.mean(segmento[metade:]) #média da segunda metade.
        bits.append(1 if primeira > segunda else 0) #o sentido da transição define o bit.
    return bits


def demod_bipolar(sinal: np.ndarray) -> list[int]:
    '''
    Média próxima de 0 = bit 0; média próxima de +V ou -V = bit 1.
    '''
    amostras_por_bit = 100
    bits = []
    for i in range(0, len(sinal), amostras_por_bit):
        segmento = sinal[i:i + amostras_por_bit]
        if len(segmento) < amostras_por_bit:
            break
        bits.append(0 if abs(np.mean(segmento)) < 0.5 else 1)   # níveis 0 e ±V: limiar V/2
    return bits



# Demodulação por Portadora ----------------------------------------------------------------

def demod_ask(tempo: np.ndarray, sinal: np.ndarray) -> list[int]:
    '''
    Detecção coerente: correlaciona cada bit com a portadora (mesma amplitude e frequência do
    modulador). O resultado estima a amplitude recebida (≈ A para bit 1, ≈ 0 para bit 0) e o
    ruído gaussiano tem média zero nela, ao contrário da média do valor absoluto, que o ruído eleva.
    '''
    A, f = 1, 2 #amplitude e frequência usadas na modulação.
    amostras_por_bit = 100
    limiar = A / 2 #limiar de decisão: metade da amplitude.
    bits = []
    for i in range(0, len(sinal), amostras_por_bit):
        segmento = sinal[i:i + amostras_por_bit] #amostras de um bit.
        if len(segmento) < amostras_por_bit:
            break
        t_seg = tempo[i:i + amostras_por_bit] #instantes de tempo correspondentes.
        amplitude = 2 * np.mean(segmento * np.sin(2 * np.pi * f * t_seg)) #correlação com a portadora = amplitude estimada.
        bits.append(1 if amplitude > limiar else 0) #acima do limiar = bit 1.
    return bits


def demod_fsk(tempo: np.ndarray, sinal: np.ndarray) -> list[int]:
    '''
    Encontra a frequência dominante de cada bit (via FFT) e escolhe a frequência mais próxima: f1 = bit 1, f0 = bit 0.
    '''
    f1, f0 = 2, 1 #frequências usadas na modulação para os bits 1 e 0.
    amostras_por_bit = 100
    bits = []
    dt = tempo[1] - tempo[0] if len(tempo) > 1 else 0.01 #intervalo entre amostras.

    for i in range(0, len(sinal), amostras_por_bit):
        segmento = sinal[i:i + amostras_por_bit]
        if len(segmento) < amostras_por_bit:
            break
        fft = np.abs(np.fft.fft(segmento)) #Fast Fourier Transform
        freqs = np.fft.fftfreq(len(segmento), d=dt) #qual frequencia corresponde a cada amplitude da FFT
        mask = freqs > 0 #ignora frequencias negativas
        freq_dom = freqs[mask][np.argmax(fft[mask])] #armax = posição da maior amplitude e freq_dom = retorna sua frequencia correspondente
        bits.append(1 if abs(freq_dom - f1) < abs(freq_dom - f0) else 0) #bit 1 se a frequência dominante está mais perto de f1.
    return bits


def _demodular_constelacao(tempo: np.ndarray, sinal: np.ndarray, constelacao: dict) -> list[int]:
    '''
    Correlaciona cada símbolo com cos/sen para recuperar (I, Q) e decide pelo ponto mais próximo.
    '''
    bits_por_simbolo = len(next(iter(constelacao))) #quantidade de bits de cada símbolo (3 no 8PSK e 5 no 32-QAM).
    amostras_por_simbolo = int(bits_por_simbolo * DURACAO_BIT * FS) #quantidade de amostras de um símbolo (100 por bit).
    bits = []

    for i in range(0, len(sinal) - amostras_por_simbolo + 1, amostras_por_simbolo):
        seg = sinal[i:i + amostras_por_simbolo] #amostras de um símbolo.
        t_seg = tempo[i:i + amostras_por_simbolo] #instantes de tempo correspondentes.
        I = 2 * np.mean(seg * np.cos(2 * np.pi * F_PORTADORA * t_seg)) #componente em fase (I).
        Q = -2 * np.mean(seg * np.sin(2 * np.pi * F_PORTADORA * t_seg)) #componente em quadratura (Q).

        # Decisão por mínima distância
        simbolo = min(constelacao,
                      key=lambda c: (I - constelacao[c][0]) ** 2 + (Q - constelacao[c][1]) ** 2) #ponto da constelação mais perto de (I, Q).
        bits.extend(int(b) for b in simbolo) #converte o código do símbolo ('010', por exemplo) em bits.
    return bits


def demod_psk8(tempo: np.ndarray, sinal: np.ndarray) -> list[int]:
    '''
    8PSK: recupera 3 bits por símbolo.
    '''
    return _demodular_constelacao(tempo, sinal, _CONSTELACAO_8PSK)


def demod_qam32(tempo: np.ndarray, sinal: np.ndarray) -> list[int]:
    '''
    32-QAM: recupera 5 bits por símbolo.
    '''
    return _demodular_constelacao(tempo, sinal, _CONSTELACAO_32QAM)