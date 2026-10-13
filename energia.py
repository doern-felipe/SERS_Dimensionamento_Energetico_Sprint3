from datetime import datetime
from banco import conectar, log, consumo, tarifa
from entrada import decimal, inteiro
from imoveis import escolher

PAINEL_W = 550
HORAS_SOL = 4
FATOR_RENDIMENTO = 0.80


def geracao_por_painel():
    return PAINEL_W * HORAS_SOL * 30 * FATOR_RENDIMENTO / 1000


def calcular_grafico(detalhes, titulo='Consumo por equipamento', arquivo='grafico_consumo.png'):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print('Para gerar gráficos, instale: pip install matplotlib')
        return False

    if not detalhes:
        print('Não há equipamentos para gerar o gráfico.')
        return False

    nomes = [x[0] for x in detalhes]
    valores = [x[5] for x in detalhes]
    plt.figure(figsize=(8, 5))
    plt.bar(nomes, valores)
    plt.title(titulo)
    plt.ylabel('kWh/mês')
    plt.xticks(rotation=30, ha='right')
    plt.tight_layout()
    plt.savefig(arquivo)
    plt.close()
    print(f'Gráfico criado: {arquivo}')
    return True


def dimensionar(usuario, mostrar_grafico=False):
    item = escolher(usuario)
    if not item:
        return
    if not item['ativo']:
        print('O imóvel está inativo.')
        return

    total, detalhes = consumo(usuario['id'], item['id'])
    preco, bandeira = tarifa(item['regiao'])
    solar = min(item['solar_kwh'], total)
    sem = total * preco
    com = max(0, total - solar) * preco

    print(
        f"\n--- DIMENSIONAMENTO ---\nImóvel: {item['nome']}\n"
        f"Consumo estimado: {total:.2f} kWh/mês\n"
        f"Tarifa: R$ {preco:.2f}/kWh\nBandeira: {bandeira}\n"
        f"Custo sem solar: R$ {sem:.2f}\nCusto com solar: R$ {com:.2f}\n"
        f"Economia solar: R$ {sem - com:.2f}")

    print('\nEquipamentos:')
    for x in detalhes:
        print(f'- {x[0]} ({x[1]}): {x[5]:.2f} kWh/mês')

    banco = conectar()
    banco.execute('INSERT INTO cobrancas(imovel_id,data,kwh,valor) VALUES(?,?,?,?)',
                  (item['id'], datetime.now().isoformat(), total, com))
    banco.commit()
    banco.close()
    log(usuario['id'], 'Dimensionamento realizado',
        f'Consumo estimado: {total:.2f} kWh; custo: R$ {com:.2f}')

    if mostrar_grafico:
        calcular_grafico(detalhes)


def solar(usuario):
    item = escolher(usuario)
    if not item:
        return
    if not item['ativo']:
        print('O imóvel está inativo.')
        return

    quantidade = inteiro('Quantidade de painéis solares: ', 0)
    geracao = quantidade * geracao_por_painel()
    banco = conectar()
    banco.execute('UPDATE imoveis SET solar_paineis=?, solar_kwh=? WHERE id=? AND usuario_id=?',
                  (quantidade, geracao, item['id'], usuario['id']))
    banco.commit()
    banco.close()
    log(usuario['id'], 'Configuração solar alterada',
        f'{quantidade} painel(is); geração estimada: {geracao:.2f} kWh/mês')
    print(f'Painéis atualizados. Geração estimada: {geracao:.2f} kWh/mês.')
    print(f'Considerado: painel de {PAINEL_W} W, {HORAS_SOL} h de sol/dia e rendimento de {FATOR_RENDIMENTO:.0%}.')


def calcular_recomendacao_solar(consumo_mensal):
    if consumo_mensal <= 0:
        return 0, 0, 0
    por_painel = geracao_por_painel()
    quantidade = int((consumo_mensal + por_painel - 1) // por_painel)
    geracao = quantidade * por_painel
    potencia_total = quantidade * PAINEL_W
    return quantidade, potencia_total, geracao


def testar_solar():
    try:
        assert round(geracao_por_painel(), 2) == 52.8
        quantidade, potencia, geracao = calcular_recomendacao_solar(100)
        assert quantidade == 2
        assert potencia == 1100
        assert round(geracao, 2) == 105.6
        quantidade, potencia, geracao = calcular_recomendacao_solar(0)
        assert quantidade == 0
        assert potencia == 0
        assert geracao == 0
        print('Testes automatizados de energia solar: OK')
        return True
    except AssertionError:
        print('Testes automatizados de energia solar: FALHOU')
        return False


def grafico_solar(usuario):
    item = escolher(usuario)
    if not item or not item['ativo']:
        print('O imóvel precisa estar ativo.')
        return

    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print('Para gerar gráficos, instale: pip install matplotlib')
        return

    total, _ = consumo(usuario['id'], item['id'])
    solar = min(item['solar_kwh'], total)
    preco, _ = tarifa(item['regiao'])
    sem = total * preco
    com = max(0, total - solar) * preco

    plt.figure(figsize=(7, 5))
    plt.bar(['Sem solar', 'Com solar'], [sem, com])
    plt.title('Custo mensal com e sem energia solar')
    plt.ylabel('R$')
    plt.tight_layout()
    arquivo = f'grafico_solar_{item["id"]}.png'
    plt.savefig(arquivo)
    plt.close()
    print(f'Gráfico criado: {arquivo}')


def consumo_mensal(usuario):
    item = escolher(usuario)
    if not item or not item['ativo']:
        print('O imóvel precisa estar ativo.')
        return

    mes = input('Mês (AAAA-MM): ').strip()
    kwh = decimal('Consumo em kWh: ')
    try:
        datetime.strptime(mes, '%Y-%m')
    except ValueError:
        print('Use um mês válido no formato AAAA-MM.')
        return

    banco = conectar()
    banco.execute('INSERT INTO consumos(imovel_id,mes,kwh) VALUES(?,?,?)',
                  (item['id'], mes, kwh))
    banco.commit()
    banco.close()
    verificar_alerta(usuario['id'], item['id'])
    log(usuario['id'], 'Consumo mensal cadastrado', f'Mês: {mes}; consumo: {kwh:.2f} kWh')
    print('Consumo cadastrado.')


def verificar_alerta(usuario_id, imovel_id):
    banco = conectar()
    dados = banco.execute(
        'SELECT kwh FROM consumos WHERE imovel_id=? ORDER BY mes DESC',
        (imovel_id,)).fetchall()
    if len(dados) >= 2:
        atual = dados[0]['kwh']
        media = sum(x['kwh'] for x in dados[1:]) / len(dados[1:])
        if atual > media:
            banco.execute(
                'INSERT INTO notificacoes(usuario_id,imovel_id,mensagem,data) VALUES(?,?,?,?)',
                (usuario_id, imovel_id,
                 f'Consumo atual ({atual:.2f} kWh) acima da média anterior ({media:.2f} kWh).',
                 datetime.now().isoformat()))
            banco.commit()
    banco.close()


def historico(usuario):
    item = escolher(usuario)
    if not item:
        return
    banco = conectar()
    dados = banco.execute(
        'SELECT mes,kwh FROM consumos WHERE imovel_id=? ORDER BY mes',
        (item['id'],)).fetchall()
    banco.close()
    print('\n--- HISTÓRICO ---')
    if not dados:
        print('Nenhum consumo registrado.')
        return
    for x in dados:
        print(f"{x['mes']} - {x['kwh']:.2f} kWh")
    media = sum(x['kwh'] for x in dados) / len(dados)
    maior = max(dados, key=lambda x: x['kwh'])
    print(f'Média mensal: {media:.2f} kWh')
    print(f"Maior consumo: {maior['kwh']:.2f} kWh em {maior['mes']}")
