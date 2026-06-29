def texto_para_bits(texto: str) -> str:
    #Converte uma string de texto em uma string de bits (codificação ASCII/UTF-8).

    return ''.join(format(ord(c), '08b') for c in texto)


def bits_para_texto(bits: str) -> str:
    #Converte uma string de bits em texto (decodificação ASCII).
    #Ignora bytes incompletos ao final.

    texto = ''
    for i in range(0, len(bits) - len(bits) % 8, 8):
        byte = bits[i:i+8]
        try:
            texto += chr(int(byte, 2))
        except ValueError:
            pass

    return texto
