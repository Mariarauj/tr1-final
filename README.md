# Simulador TR1 — Teleinformática e Redes 1

Simulador das camadas de **enlace** e **física** de uma rede de comunicação,
implementando enquadramento, detecção/correção de erros, modulação digital
e modulação por portadora.

---

## Estrutura do Projeto

```
tr1-final/
├── main_cliente.py          # Ponto de entrada do Transmissor (TX)
├── main_servidor.py         # Ponto de entrada do Receptor   (RX)
├── script.sh                # Script de setup e execução
├── requirements.txt
├── auxiliar.py              # Conversões texto ↔ bits
├── camada_fisica/
│   ├── modulacao.py         # NRZ-Polar, Manchester, Bipolar, ASK, FSK, QPSK, 16-QAM
│   ├── demodulacao.py       # Demodulação de todos os tipos acima
│   └── ruido.py             # Ruído gaussiano e inversão de bit aleatória
├── camada_enlace/
│   ├── enquadramento.py     # Contagem de caracteres, Inserção de bytes, Inserção de bits
│   ├── deteccao_erros.py    # Paridade par, Checksum 16-bit, CRC-32 (IEEE 802.3)
│   └── hamming.py           # Código de Hamming (codificação e correção)
├── cliente/
│   ├── transmitter.py       # Pipeline TX completo
│   └── ui_cliente.py        # Interface GTK3 do Transmissor
└── servidor/
    ├── receiver.py          # Pipeline RX completo + servidor TCP
    └── ui_servidor.py       # Interface GTK3 do Receptor
```

---

## Protocolos Implementados

### Camada Física — Modulação Digital
| Protocolo   | Descrição                                     |
|-------------|-----------------------------------------------|
| NRZ-Polar   | bit 1 → +V, bit 0 → −V                        |
| Manchester  | bit 1 → alta→baixa, bit 0 → baixa→alta        |
| Bipolar     | bit 0 → 0V, bit 1 → alterna +V/−V (AMI)       |

### Camada Física — Modulação por Portadora
| Protocolo | Descrição                                      |
|-----------|------------------------------------------------|
| ASK       | bit 1 → senoide, bit 0 → silêncio              |
| FSK       | bit 1 → f₁=2 Hz, bit 0 → f₀=1 Hz              |
| QPSK      | 2 bits/símbolo, 4 pontos de constelação        |
| 16-QAM    | 4 bits/símbolo, 16 pontos de constelação       |

### Camada de Enlace — Enquadramento
| Protocolo             | Descrição                                    |
|-----------------------|----------------------------------------------|
| Contagem de Caracteres| Cabeçalho de 1 byte indica tamanho do quadro |
| Inserção de Bytes     | FLAG + ESC para delimitação e escape         |
| Inserção de Bits      | Flag 01111110 + bit stuffing após 5 uns      |

### Camada de Enlace — Detecção de Erros
| Protocolo   | Descrição                                     |
|-------------|-----------------------------------------------|
| Paridade Par| 1 bit de paridade ao final da mensagem        |
| Checksum    | Soma em complemento de 1 (16 bits)            |
| CRC-32      | Polinômio IEEE 802.3 (0x04C11DB7)             |

### Camada de Enlace — Correção de Erros
| Protocolo | Descrição                                      |
|-----------|------------------------------------------------|
| Hamming   | Detecta e corrige 1 bit de erro por mensagem   |

---

## Como Executar

### Pré-requisitos
- Python 3.10+
- GTK3 (`sudo apt install python3-gi gir1.2-gtk-3.0` no Ubuntu/Debian)

### Opção 1 — Script automático
```bash
bash script.sh ambos      # inicia servidor e depois o cliente
bash script.sh servidor   # só o servidor
bash script.sh cliente    # só o cliente
```

### Opção 2 — Manual (dois terminais)
**Terminal 1 (Receptor):**
```bash
python main_servidor.py
```

**Terminal 2 (Transmissor):**
```bash
python main_cliente.py
```

---

## Pipeline de Simulação

```
[TX] texto → bits → Hamming → Detecção Erros → Enquadramento → Ruído
     → Modulação Digital (gráfico) → Modulação Portadora → TCP →

[RX] TCP → Demodulação → Desenquadramento → Verificação Detecção
     → Correção Hamming → bits → texto
```
