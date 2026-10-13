import os
import tempfile
from banco import conectar, log, consumo, tarifa
from energia import calcular_recomendacao_solar, PAINEL_W, HORAS_SOL, FATOR_RENDIMENTO
from imoveis import escolher


def notificacoes(usuario):
    banco = conectar()
    dados = banco.execute('SELECT * FROM notificacoes WHERE usuario_id=? ORDER BY data DESC',
                          (usuario['id'],)).fetchall()
    banco.execute('UPDATE notificacoes SET lida=1 WHERE usuario_id=?', (usuario['id'],))
    banco.commit()
    banco.close()
    print('\n--- ALERTAS ---')
    if not dados:
        print('Nenhum alerta.')
    for x in dados:
        print(f"{x['data'][:19]} - {x['mensagem']}")


def historico_cobrancas(usuario):
    item = escolher(usuario)
    if not item:
        return
    banco = conectar()
    dados = banco.execute(
        '''SELECT data,kwh,valor FROM cobrancas
           WHERE imovel_id=? ORDER BY data DESC''', (item['id'],)).fetchall()
    banco.close()

    print('\n--- HISTÓRICO DE COBRANÇAS ---')
    if not dados:
        print('Nenhuma cobrança registrada.')
        return
    for x in dados:
        print(f"{x['data'][:19]} | {x['kwh']:.2f} kWh | R$ {x['valor']:.2f}")


def logs_usuario(usuario):
    banco = conectar()
    dados = banco.execute(
        'SELECT acao,detalhes,data FROM logs WHERE usuario_id=? ORDER BY data DESC',
        (usuario['id'],)).fetchall()
    banco.close()
    print('\n--- LOGS ---')
    if not dados:
        print('Nenhum log encontrado.')
    for x in dados:
        detalhes = f" | {x['detalhes']}" if x['detalhes'] else ''
        print(f"{x['data'][:19]} - {x['acao']}{detalhes}")


def gerar_grafico_relatorio(detalhes, arquivo):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print('Para gerar gráficos, instale: pip install matplotlib')
        return False

    if not detalhes:
        return False

    nomes = [x[0] for x in detalhes]
    valores = [x[5] for x in detalhes]
    plt.figure(figsize=(8, 5))
    plt.bar(nomes, valores)
    plt.title('Consumo por equipamento')
    plt.ylabel('kWh/mês')
    plt.xticks(rotation=30, ha='right')
    plt.tight_layout()
    plt.savefig(arquivo)
    plt.close()
    return True


def testar_relatorio():
    """Teste simples para verificar se PDF e gráfico podem ser criados."""
    try:
        from reportlab.pdfgen import canvas
        import matplotlib.pyplot as plt
    except ImportError:
        return False

    pasta = tempfile.gettempdir()
    pdf_teste = os.path.join(pasta, 'sers_teste.pdf')
    grafico_teste = os.path.join(pasta, 'sers_teste.png')

    pdf = canvas.Canvas(pdf_teste)
    pdf.drawString(50, 800, 'Teste SERS')
    pdf.save()

    plt.figure()
    plt.bar(['Teste'], [1])
    plt.savefig(grafico_teste)
    plt.close()

    ok = os.path.exists(pdf_teste) and os.path.exists(grafico_teste)
    if os.path.exists(pdf_teste):
        os.remove(pdf_teste)
    if os.path.exists(grafico_teste):
        os.remove(grafico_teste)
    return ok


def relatorio(usuario):
    item = escolher(usuario)
    if not item:
        return
    if not item['ativo']:
        print('O imóvel está inativo.')
        return

    opcao = input('Deseja executar o teste automático do relatório? (s/n): ').strip().lower()
    if opcao == 's':
        if testar_relatorio():
            print('Teste automático do relatório: OK')
        else:
            print('Teste automático do relatório: FALHOU')
            return

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError:
        print('Para gerar PDF, instale: pip install reportlab')
        return

    total, detalhes = consumo(usuario['id'], item['id'])
    preco, bandeira = tarifa(item['regiao'])
    solar = min(item['solar_kwh'], total)
    valor_sem = total * preco
    valor_com = max(0, total - solar) * preco

    arquivo = f'relatorio_imovel_{item["id"]}.pdf'
    grafico = f'grafico_relatorio_{item["id"]}.png'
    tem_grafico = gerar_grafico_relatorio(detalhes, grafico)

    pdf = canvas.Canvas(arquivo, pagesize=A4)
    y = 800
    pdf.setFont('Helvetica-Bold', 16)
    pdf.drawString(50, y, 'SERS - Relatório Energético')
    y -= 30
    pdf.setFont('Helvetica', 11)

    textos = [
        f"Imóvel: {item['nome']}",
        f'Consumo estimado: {total:.2f} kWh/mês',
        f'Custo sem solar: R$ {valor_sem:.2f}',
        f'Custo com solar: R$ {valor_com:.2f}',
        f'Economia solar: R$ {valor_sem - valor_com:.2f}',
        f'Bandeira: {bandeira}',
        'Equipamentos:'
    ]

    for texto in textos:
        pdf.drawString(50, y, texto)
        y -= 20

    for x in detalhes:
        pdf.drawString(60, y, f'{x[0]} - {x[5]:.2f} kWh/mês')
        y -= 18
        if y < 250:
            pdf.showPage()
            y = 800

    if tem_grafico:
        if y < 400:
            pdf.showPage()
            y = 800
        pdf.drawImage(grafico, 50, y - 300, width=500, height=280)

    pdf.save()
    if os.path.exists(grafico):
        os.remove(grafico)
    log(usuario['id'], 'Relatório PDF gerado')
    print(f'Relatório criado: {arquivo}')


def historico_pdf(usuario):
    item = escolher(usuario)
    if not item:
        return

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError:
        print('Para gerar PDF, instale: pip install reportlab')
        return

    banco = conectar()
    logs = banco.execute(
        'SELECT acao, detalhes, data FROM logs WHERE usuario_id=? ORDER BY data',
        (usuario['id'],)).fetchall()
    cobrancas = banco.execute(
        'SELECT data, kwh, valor FROM cobrancas WHERE imovel_id=? ORDER BY data',
        (item['id'],)).fetchall()
    banco.close()

    arquivo = f'historico_completo_{item["id"]}.pdf'
    pdf = canvas.Canvas(arquivo, pagesize=A4)
    y = 800

    def linha(texto, tamanho=10):
        nonlocal y
        if y < 60:
            pdf.showPage()
            y = 800
        pdf.setFont('Helvetica', tamanho)
        pdf.drawString(50, y, texto[:105])
        y -= 16

    pdf.setFont('Helvetica-Bold', 16)
    pdf.drawString(50, y, 'SERS - Histórico Completo de Alterações')
    y -= 30
    linha(f'Imóvel: {item["nome"]}', 11)
    linha(f'Endereço: {item["endereco"]}', 11)
    linha('')
    linha('ALTERAÇÕES REGISTRADAS', 12)

    if logs:
        for x in logs:
            detalhes = f' | {x["detalhes"]}' if x['detalhes'] else ''
            linha(f'{x["data"][:19]} - {x["acao"]}{detalhes}')
    else:
        linha('Nenhuma alteração registrada.')

    linha('')
    linha('HISTÓRICO DE COBRANÇAS', 12)
    if cobrancas:
        for x in cobrancas:
            linha(f'{x["data"][:19]} - {x["kwh"]:.2f} kWh - R$ {x["valor"]:.2f}')
    else:
        linha('Nenhuma cobrança registrada.')

    pdf.save()
    log(usuario['id'], 'Histórico completo em PDF gerado', f'Imóvel: {item["nome"]}')
    print(f'PDF criado: {arquivo}')


def recomendacao_solar_pdf(usuario):
    item = escolher(usuario)
    if not item:
        return
    if not item['ativo']:
        print('O imóvel está inativo.')
        return

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError:
        print('Para gerar PDF, instale: pip install reportlab')
        return

    total, _ = consumo(usuario['id'], item['id'])
    quantidade, potencia_total, geracao = calcular_recomendacao_solar(total)
    preco, bandeira = tarifa(item['regiao'])
    custo_sem = total * preco
    custo_com = max(0, total - geracao) * preco

    arquivo = f'recomendacao_solar_{item["id"]}.pdf'
    pdf = canvas.Canvas(arquivo, pagesize=A4)
    y = 800
    pdf.setFont('Helvetica-Bold', 16)
    pdf.drawString(50, y, 'SERS - Recomendação de Sistema Solar')
    y -= 30
    pdf.setFont('Helvetica', 11)

    textos = [
        f'Imóvel: {item["nome"]}',
        f'Consumo mensal estimado: {total:.2f} kWh',
        f'Painéis recomendados: {quantidade}',
        f'Potência total estimada: {potencia_total} W',
        f'Geração mensal estimada: {geracao:.2f} kWh',
        f'Tarifa considerada: R$ {preco:.2f}/kWh',
        f'Bandeira: {bandeira}',
        f'Custo estimado sem solar: R$ {custo_sem:.2f}',
        f'Custo estimado com a geração recomendada: R$ {custo_com:.2f}',
        '',
        'Critério utilizado:',
        f'- Painel padrão de {PAINEL_W} W',
        f'- {HORAS_SOL} horas de sol por dia',
        f'- Rendimento estimado de {FATOR_RENDIMENTO:.0%}',
        '- A recomendação é uma estimativa simplificada para o projeto.',
        '- O dimensionamento definitivo deve considerar as condições reais do local.'
    ]

    for texto in textos:
        if y < 60:
            pdf.showPage()
            y = 800
            pdf.setFont('Helvetica', 11)
        pdf.drawString(50, y, texto)
        y -= 22

    pdf.save()
    log(usuario['id'], 'Recomendação solar em PDF gerada',
        f'{quantidade} painel(is) para {total:.2f} kWh/mês')
    print(f'PDF criado: {arquivo}')


def tarifas(usuario):
    if not usuario['admin']:
        print('Acesso somente para administrador.')
        return
    banco = conectar()
    dados = banco.execute('SELECT * FROM tarifas ORDER BY regiao').fetchall()
    banco.close()
    print('\n--- TARIFAS ---')
    for x in dados:
        print(f"{x['regiao']} - R$ {x['tarifa']:.2f} - {x['bandeira']}")

    from entrada import decimal
    regiao = input('Região para alterar: ').strip().upper()
    valor = decimal('Tarifa R$/kWh: ')
    op = input('1 - Verde\n2 - Amarela\n3 - Vermelha\nBandeira: ')
    bandeira = {'1': 'Verde', '2': 'Amarela', '3': 'Vermelha'}.get(op)
    if not bandeira:
        print('Bandeira inválida.')
        return

    banco = conectar()
    banco.execute(
        '''INSERT INTO tarifas(regiao,tarifa,bandeira) VALUES(?,?,?)
           ON CONFLICT(regiao) DO UPDATE SET tarifa=excluded.tarifa,bandeira=excluded.bandeira''',
        (regiao, valor, bandeira))
    banco.commit()
    banco.close()
    log(usuario['id'], 'Tarifa alterada', f'{regiao}: R$ {valor:.2f}; bandeira: {bandeira}')
    print('Tarifa atualizada.')
