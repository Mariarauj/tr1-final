import numpy as np
import random

# Taxa de erro de bit (probabilidade de um bit ser invertido)
TAXA_ERRO = 0.3


def adicionar_ruido_gaussiano(sinal: np.ndarray, sigma: float = 0.05) -> np.ndarray:
    # Adiciona ruído gaussiano ao sinal contínuo.

    ruido = np.random.normal(0, sigma, len(sinal))
    return sinal + ruido


def inverter_bit_aleatorio(bits_str: str) -> str:
    # Simula erro no canal digital invertendo um bit aleatório

    if not bits_str:
        return bits_str
    copia = list(bits_str)
    if random.random() < TAXA_ERRO:
        i = random.randint(0, len(copia) - 1)
        copia[i] = '1' if copia[i] == '0' else '0'
    return ''.join(copia)
