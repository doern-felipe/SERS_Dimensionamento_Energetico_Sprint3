"""Módulo de dimensionamento fotovoltaico da Sprint 3 do SERS.
Compatível com o banco.py e energia.py do repositório original.
Execute diretamente com: python dimensionamento_fv.py
Ou importe executar_dimensionamento(usuario) no menu principal.
"""
from __future__ import annotations
import csv, json, math
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).resolve().parent
DATA = BASE / 'datasets'


def ler_csv(nome):
    caminho = DATA / nome
    with caminho.open('r', encoding='utf-8-sig', newline='') as arquivo:
        return list(csv.DictReader(arquivo))


def numero(valor, nome, minimo=None, maximo=None):
    try:
        n = float(valor)
    except (TypeError, ValueError):
        raise ValueError(f'{nome}: informe um número válido.')
    if not math.isfinite(n):
        raise ValueError(f'{nome}: valor inválido.')
    if minimo is not None and n < minimo:
        raise ValueError(f'{nome}: deve ser maior ou igual a {minimo}.')
    if maximo is not None and n > maximo:
        raise ValueError(f'{nome}: deve ser menor ou igual a {maximo}.')
    return n


def dimensionar_baterias(consumo_diario, autonomia_dias, dod, eficiencia, bateria):
    if consumo_diario <= 0 or autonomia_dias <= 0:
        raise ValueError('Consumo e autonomia devem ser maiores que zero.')
    if not 0 < dod <= 1 or not 0 < eficiencia <= 1:
        raise ValueError('DoD e eficiência devem estar entre 0 e 1.')
    energia_util = consumo_diario * autonomia_dias
    capacidade_necessaria = energia_util / (dod * eficiencia)
    capacidade_unidade = float(bateria['energia_kwh'])
    quantidade = math.ceil(capacidade_necessaria / capacidade_unidade)
    return {'energia_autonomia_kwh': energia_util, 'capacidade_necessaria_kwh': capacidade_necessaria,
            'quantidade': quantidade, 'capacidade_instalada_kwh': quantidade * capacidade_unidade,
            'modelo': bateria['modelo'], 'fabricante': bateria['fabricante'],
            'preco': float(bateria['preco_brl']), 'autonomia_dias': autonomia_dias}


def avaliar_sistema(consumo_mensal, hsp, pr, modulo, inversores, baterias, tarifa_kwh,
                    incluir_bateria=False, autonomia_dias=1.0, dod=0.80, eficiencia_bateria=0.92):
    consumo_mensal = numero(consumo_mensal, 'Consumo mensal', 0.000001)
    hsp = numero(hsp, 'HSP', 0.000001, 12)
    pr = numero(pr, 'PR', 0.01, 1)
    tarifa_kwh = numero(tarifa_kwh, 'Tarifa', 0)
    e_dia = consumo_mensal / 30
    p_fv = e_dia / (hsp * pr)
    p_mod = numero(modulo['potencia_wp'], 'Potência do módulo', 1)
    n_mod = math.ceil(p_fv * 1000 / p_mod)
    p_inst = n_mod * p_mod / 1000
    geracao_dia = p_inst * hsp * pr
    geracao_mes = geracao_dia * 30
    atendimento = geracao_mes / consumo_mensal * 100
    # Seleção simples, com compatibilidade pela potência nominal do inversor.
    candidatos = [i for i in inversores if float(i['potencia_kw']) >= p_inst * 0.80]
    if not candidatos:
        raise ValueError('Nenhum inversor do dataset atende ao critério mínimo de potência (80% da potência FV instalada).')
    inversor = min(candidatos, key=lambda i: (abs(float(i['potencia_kw']) - p_inst), float(i['preco_brl'])))
    razao_dc_ac = p_inst / float(inversor['potencia_kw'])
    # Em um dimensionamento real, a compatibilidade elétrica exige conferir tensão/corrente,
    # janela MPPT e configuração série/paralelo conforme datasheets completos.
    custo_modulos = n_mod * float(modulo['preco_brl'])
    custo_inversor = float(inversor['preco_brl'])
    bateria = None
    custo_baterias = 0.0
    if incluir_bateria:
        bateria = dimensionar_baterias(e_dia, autonomia_dias, dod, eficiencia_bateria, baterias[0])
        custo_baterias = bateria['quantidade'] * bateria['preco']
    investimento = custo_modulos + custo_inversor + custo_baterias
    energia_compensada = min(consumo_mensal, geracao_mes)
    economia_mensal = energia_compensada * tarifa_kwh
    economia_anual = economia_mensal * 12
    payback = investimento / economia_anual if economia_anual > 0 else None
    return {'consumo_mensal_kwh': consumo_mensal, 'consumo_diario_kwh': e_dia, 'hsp': hsp, 'pr': pr,
            'potencia_necessaria_kwp': p_fv, 'modulo': modulo, 'quantidade_modulos': n_mod,
            'potencia_instalada_kwp': p_inst, 'inversor': inversor, 'razao_dc_ac': razao_dc_ac,
            'geracao_diaria_kwh': geracao_dia, 'geracao_mensal_kwh': geracao_mes,
            'atendimento_percentual_bruto': atendimento, 'energia_compensada_kwh': energia_compensada,
            'tarifa_kwh': tarifa_kwh, 'economia_mensal_brl': economia_mensal,
            'economia_anual_brl': economia_anual, 'custo_modulos_brl': custo_modulos,
            'custo_inversor_brl': custo_inversor, 'bateria': bateria, 'custo_baterias_brl': custo_baterias,
            'investimento_brl': investimento, 'payback_anos': payback,
            'observacao': 'Estimativa acadêmica: não inclui estrutura, instalação, projeto, homologação, impostos ou tarifas mínimas.'}


def imprimir_proposta(r, titulo):
    print('\n' + '=' * 68 + f'\nPROPOSTA SERS — {titulo}\n' + '=' * 68)
    print(f"Consumo: {r['consumo_mensal_kwh']:.2f} kWh/mês ({r['consumo_diario_kwh']:.2f} kWh/dia)")
    print(f"Recurso solar: HSP {r['hsp']:.2f} h/dia | PR {r['pr']:.0%}")
    print(f"Potência FV necessária: {r['potencia_necessaria_kwp']:.2f} kWp")
    m = r['modulo']; i = r['inversor']
    print(f"Módulos: {r['quantidade_modulos']} × {m['fabricante']} {m['modelo']} ({m['potencia_wp']} Wp)")
    print(f"Potência instalada: {r['potencia_instalada_kwp']:.2f} kWp")
    print(f"Inversor: {i['fabricante']} {i['modelo']} ({i['potencia_kw']} kW) | relação DC/AC {r['razao_dc_ac']:.2f}")
    print(f"Geração estimada: {r['geracao_diaria_kwh']:.2f} kWh/dia | {r['geracao_mensal_kwh']:.2f} kWh/mês")
    print(f"Atendimento teórico bruto: {r['atendimento_percentual_bruto']:.1f}%")
    print(f"Energia considerada compensada: {r['energia_compensada_kwh']:.2f} kWh/mês")
    print('\nORÇAMENTO ESTIMADO')
    print(f"Módulos: {r['quantidade_modulos']} × R$ {float(m['preco_brl']):,.2f} = R$ {r['custo_modulos_brl']:,.2f}")
    print(f"Inversor: 1 × R$ {float(i['preco_brl']):,.2f} = R$ {r['custo_inversor_brl']:,.2f}")
    if r['bateria']:
        b = r['bateria']; print(f"Baterias: {b['quantidade']} × {b['fabricante']} {b['modelo']} = R$ {r['custo_baterias_brl']:,.2f}")
        print(f"Capacidade instalada: {b['capacidade_instalada_kwh']:.2f} kWh | autonomia configurada: {b['autonomia_dias']:.1f} dia(s)")
    print(f"INVESTIMENTO ESTIMADO: R$ {r['investimento_brl']:,.2f}")
    print(f"Economia estimada: R$ {r['economia_mensal_brl']:,.2f}/mês | R$ {r['economia_anual_brl']:,.2f}/ano")
    print('Payback simples: ' + (f"{r['payback_anos']:.1f} anos" if r['payback_anos'] is not None else 'indefinido'))
    print('\nPremissas/limitações: ' + r['observacao'])
    print('A geração excedente não é tratada como receita. A energia efetivamente compensada foi limitada ao consumo mensal.')


def executar_dimensionamento(usuario=None):
    from banco import consumo, tarifa, log
    from imoveis import escolher
    if usuario is None:
        print('Este módulo deve ser chamado a partir do SERS com um usuário autenticado.')
        return
    imovel = escolher(usuario)
    if not imovel:
        return
    if not imovel['ativo']:
        print('O imóvel está inativo.'); return
    consumo_mensal, detalhes = consumo(usuario['id'], imovel['id'])
    if consumo_mensal <= 0:
        print('Não há consumo positivo calculado para esta residência. Cadastre equipamentos e horários primeiro.'); return
    modulos = ler_csv('modulos_fotovoltaicos.csv')
    inversores = ler_csv('inversores.csv')
    baterias = ler_csv('baterias.csv')
    print(f"\nResidência selecionada: {imovel['nome']} | consumo: {consumo_mensal:.2f} kWh/mês")
    print('Módulos disponíveis:')
    for idx, m in enumerate(modulos, 1): print(f"{idx}. {m['fabricante']} {m['modelo']} — {m['potencia_wp']} Wp — R$ {float(m['preco_brl']):.2f}")
    try:
        escolha = int(input('Escolha o módulo: ')) - 1
        modulo = modulos[escolha]
        hsp = numero(input('Horas de Sol Pico (HSP, h/dia) [4.5]: ') or '4.5', 'HSP', 0.001, 12)
        print('Fonte HSP: informe a localidade e valide o valor com base em fonte solar reconhecida (ex.: CRESESB/CEPEL).')
        fonte = input('Fonte/localidade da HSP: ').strip() or 'Não informada pelo operador'
        pr = numero(input('Fator de desempenho PR [0.80]: ') or '0.80', 'PR', 0.01, 1)
        if pr > 0.85: print('Atenção: PR acima de 85% é otimista; justifique com dados do projeto.')
        preco, bandeira = tarifa(imovel['regiao'])
        tarifa_usuario = input(f'Tarifa efetiva R$/kWh [{preco:.2f}]: ').strip()
        tarifa_kwh = numero(tarifa_usuario or preco, 'Tarifa', 0)
        sem = avaliar_sistema(consumo_mensal, hsp, pr, modulo, inversores, baterias, tarifa_kwh)
        com = avaliar_sistema(consumo_mensal, hsp, pr, modulo, inversores, baterias, tarifa_kwh, True,
                              numero(input('Autonomia desejada em dias [1]: ') or '1', 'Autonomia', 0.1, 30))
        imprimir_proposta(sem, 'CENÁRIO A — SEM BATERIAS')
        imprimir_proposta(com, 'CENÁRIO B — COM BATERIAS')
        print('\nCOMPARAÇÃO')
        print(f"Diferença de investimento (com baterias): R$ {com['investimento_brl']-sem['investimento_brl']:,.2f}")
        print(f"Payback sem baterias: {sem['payback_anos']:.1f} anos" if sem['payback_anos'] else 'Payback sem baterias indefinido')
        print(f"Payback com baterias: {com['payback_anos']:.1f} anos" if com['payback_anos'] else 'Payback com baterias indefinido')
        print(f'Fonte HSP registrada: {fonte}')
        resultado = {'data': datetime.now().isoformat(), 'residencia': imovel['nome'], 'fonte_hsp': fonte,
                     'cenarios': {'sem_baterias': sem, 'com_baterias': com}}
        saida = BASE / f"proposta_sers_imovel_{imovel['id']}.json"
        saida.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'Proposta técnica salva em: {saida.name}')
        log(usuario['id'], 'Dimensionamento FV Sprint 3', f"Imóvel {imovel['id']}; HSP={hsp}; PR={pr}; proposta={saida.name}")
    except (ValueError, IndexError, KeyError) as erro:
        print(f'Não foi possível concluir o dimensionamento: {erro}')


def _testes():
    ms = ler_csv('modulos_fotovoltaicos.csv'); inv = ler_csv('inversores.csv'); bat = ler_csv('baterias.csv')
    r = avaliar_sistema(300, 4.5, 0.8, ms[0], inv, bat, 0.9)
    assert r['quantidade_modulos'] == math.ceil(r['potencia_necessaria_kwp'] * 1000 / float(ms[0]['potencia_wp']))
    assert r['geracao_mensal_kwh'] > 0 and r['investimento_brl'] > 0
    rb = avaliar_sistema(300, 4.5, 0.8, ms[0], inv, bat, 0.9, True, 1)
    assert rb['bateria']['quantidade'] >= 1 and rb['investimento_brl'] > r['investimento_brl']
    for args in [(0,4.5,.8),(300,0,.8),(300,4.5,0)]:
        try: avaliar_sistema(args[0],args[1],args[2],ms[0],inv,bat,.9)
        except ValueError: pass
        else: raise AssertionError('Validação de entrada falhou')
    print('Testes do módulo FV: OK')

if __name__ == '__main__':
    _testes()
    print('\nPara executar no fluxo normal, integre executar_dimensionamento(usuario) ao menu de main.py.')
