import numpy as np

# Níveis de ruído do canal: (média μ, desvio padrão σ) em volts.
# Com 100 amostras por bit o demodulador faz uma média que atenua o ruído, por isso os σ são altos.
NIVEIS_RUIDO = {
    'Baixo': (0.0, 0.5),   # sinal visivelmente ruidoso, praticamente sem erros de bit
    'Médio': (0.0, 2.0),   # começam a aparecer erros de bit
    'Alto' : (0.0, 5.0),   # muitos erros de bit
}


def adicionar_ruido_gaussiano(sinal: np.ndarray, media: float = 0.0, sigma: float = 0.05) -> np.ndarray:
    # Meio de comunicação (AWGN): soma n ~ N(media, sigma) diretamente aos valores elétricos (V) do sinal.

    ruido = np.random.normal(media, sigma, sinal.shape)
    return sinal + ruido