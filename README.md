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
│   ├── modulacao.py         # NRZ-Polar, Manchester, Bipolar, ASK, FSK, 8PSK, 32-QAM
│   ├── demodulacao.py       # Demodulação de todos os tipos acima
│   └── ruido.py             # Ruído gaussiano (AWGN) e níveis de ruído
├── camada_enlace/
│   ├── enquadramento.py     # Contagem de caracteres, Inserção de bytes, Inserção de bits (um quadro por vez)
│   ├── quadros.py           # Monta/desmonta os quadros: enquadramento + EDC de cada quadro
│   ├── deteccao_erros.py    # Paridade par, Checksum, CRC, Entrelaçamento de bits (EDC configurável)
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
| 8PSK      | 3 bits/símbolo, 8 pontos de constelação        |
| 32-QAM    | 5 bits/símbolo, 32 pontos de constelação       |

### Camada de Enlace — Enquadramento
| Protocolo             | Descrição                                    |
|-----------------------|----------------------------------------------|
| Contagem de Caracteres| Cabeçalho de 1 byte indica tamanho do quadro |
| Inserção de Bytes     | FLAG + ESC para delimitação e escape         |
| Inserção de Bits      | Flag 01111110 + bit stuffing após 5 uns      |

O **tamanho máximo do quadro** (1 a 255 bytes de dados, padrão 8) vale para os três protocolos; o
último quadro pode ser menor. Na inserção de bits cada quadro tem as suas flags e o *stuffing*
recomeça a cada quadro. O receptor não precisa conhecer o tamanho: os quadros se delimitam sozinhos.
Na contagem de caracteres o cabeçalho conta os bytes de **dados** do quadro.

### Camada de Enlace — Detecção de Erros
| Protocolo   | Descrição                                     | Tamanho do EDC (bits) |
|-------------|-----------------------------------------------|-----------------------|
| Paridade Par| 1 bit de paridade por quadro                  | 1 (fixo)              |
| Checksum    | Soma em complemento de 1 (palavras de N bits) | 8 (padrão), 16, 32    |
| CRC         | CRC-32 do IEEE 802 (0x04C11DB7), definido pelo enunciado | 32 (fixo) |
| Entrelaçamento de bits | Matriz de N colunas enviada coluna a coluna, com paridade par por coluna | 8 (padrão), 16, 32 |

O **EDC é calculado para cada quadro**. Na paridade, no checksum e no CRC ele cobre o quadro inteiro
(cabeçalho ou flags + dados) e é anexado logo depois dele; no entrelaçamento a matriz (colunas + paridades) é a carga
útil do quadro. O receptor confere o EDC de cada quadro e informa **quais quadros** chegaram com erro.
O **tamanho do EDC** é escolhido na interface (as opções mudam conforme a detecção; paridade e CRC têm
tamanho fixo) e vai no pacote para o receptor separar o código dos dados.

### Camada de Enlace — Correção de Erros
| Protocolo | Descrição                                      |
|-----------|------------------------------------------------|
| Hamming   | Hamming(12,8) por byte: corrige 1 bit de erro por bloco |

O **Hamming** e a **detecção de erros** podem ser desativados na interface (caixas "Controle de Erros"),
mas nunca os dois ao mesmo tempo: o que sobrar ativo fica travado.

### Meio de Comunicação — Ruído
Níveis predefinidos (média μ = 0 V): Baixo (σ = 0,2 V), Médio (σ = 2,0 V) e Alto (σ = 5,0 V). A opção
**Ruído Personalizado** libera os campos de média μ e desvio padrão σ.

---

## Como Executar

### Ambiente Virtual
```bash
python3 -m venv venv                                  # cria o ambiente virtual
source venv/bin/activate                              # ativa o ambiente (na pasta do projeto)
pip install --no-cache-dir -r requirements.txt        # instala as dependências
```

### Pré-requisitos
- Python 3.10+
- GTK3 (`sudo apt install python3-gi gir1.2-gtk-3.0` no Ubuntu/Debian)

### Opção 1 — Script automático
```bash
bash script.sh ambos      # inicia servidor e depois o cliente
bash script.sh servidor   # executa apenas o servidor
bash script.sh cliente    # executa apenas o cliente
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
[TX] texto → bits → quadros (enquadramento) com o EDC de cada quadro (detecção) → Hamming
     → Modulação Digital (banda-base) e Modulação por Portadora (em paralelo)

[Canal] soma o ruído AWGN (μ, σ) a cada sinal

[RX] Demodulação → Correção Hamming → quadro a quadro: desenquadramento + conferência do EDC → bits → texto

```