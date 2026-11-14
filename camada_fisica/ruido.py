'''
Implementa o ruído do meio de comunicação (AWGN - Additive White Gaussian Noise).

O ruído é somado diretamente aos valores elétricos (V) do sinal: y = x + n, com n ~ N(média, sigma).

'''
import numpy as np #facilita operações matemáticas e geração de números aleatórios.

# Níveis de ruído do canal: (média μ, desvio padrão σ) em volts.
# Com 100 amostras por bit o demodulador faz uma média que atenua o ruído, por isso os σ são altos.
NIVEIS_RUIDO = {
    'Baixo': (0.0, 0.2),   # sinal quase limpo, sem erros de bit
    'Médio': (0.0, 2.0),   # começam a aparecer erros de bit (principalmente na portadora)
    'Alto' : (0.0, 5.0),   # muitos erros de bit, inclusive na banda-base
}


def adicionar_ruido_gaussiano(sinal: np.ndarray, media: float = 0.0, sigma: float = 0.05) -> np.ndarray:
    '''
    Meio de comunicação (AWGN): soma n ~ N(media, sigma) a cada amostra do sinal.
    '''
    ruido = np.random.normal(media, sigma, sinal.shape) #sorteia um valor de ruído para cada amostra.
    return sinal + ruido #sinal ruidoso = sinal original + ruído.