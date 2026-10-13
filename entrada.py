def inteiro(texto, minimo=0):
    while True:
        try:
            valor = int(input(texto))
            if valor >= minimo:
                return valor
        except ValueError:
            pass
        print('Digite um número válido.')


def decimal(texto, minimo=0):
    while True:
        try:
            valor = float(input(texto).replace(',', '.'))
            if valor >= minimo:
                return valor
        except ValueError:
            pass
        print('Digite um número válido.')
