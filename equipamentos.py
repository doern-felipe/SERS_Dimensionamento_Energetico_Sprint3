from banco import conectar, log
from entrada import inteiro, decimal
from imoveis import escolher


def cadastrar(usuario):
    item = escolher(usuario)
    if not item or not item['ativo']:
        print('O imóvel precisa estar ativo.')
        return

    print('\n1 - Usar aparelho do catálogo\n2 - Cadastrar aparelho personalizado')
    op = input('Opção: ')
    banco = conectar()

    if op == '1':
        dados = banco.execute('SELECT * FROM equipamentos ORDER BY nome').fetchall()
        for x in dados:
            print(f"{x['id']} - {x['nome']} - {x['potencia']} W")
        eid = inteiro('ID do equipamento: ', 1)
        equipamento = banco.execute('SELECT * FROM equipamentos WHERE id=?', (eid,)).fetchone()
        if not equipamento:
            banco.close()
            print('Equipamento não encontrado.')
            return
    elif op == '2':
        nome = input('Nome: ').strip()
        categoria = input('Categoria: ').strip()
        potencia = decimal('Potência (W): ', .01)
        if not nome or not categoria:
            banco.close()
            print('Nome e categoria são obrigatórios.')
            return
        banco.execute('INSERT INTO equipamentos(nome,categoria,potencia) VALUES(?,?,?)',
                      (nome, categoria, potencia))
        eid = banco.execute('SELECT last_insert_rowid()').fetchone()[0]
        equipamento = {'potencia': potencia}
    else:
        banco.close()
        print('Opção inválida.')
        return

    comodo = input('Cômodo: ').strip()
    quantidade = inteiro('Quantidade: ', 1)
    horas = decimal('Horas de uso por dia: ')

    if not comodo or horas > 24:
        banco.close()
        print('Cômodo obrigatório e horas devem estar entre 0 e 24.')
        return

    banco.execute('INSERT INTO usos(imovel_id,equipamento_id,comodo,quantidade,horas,potencia) VALUES(?,?,?,?,?,?)',
                  (item['id'], eid, comodo, quantidade, horas, equipamento['potencia']))
    banco.commit()
    banco.close()
    log(usuario['id'], 'Equipamento associado ao imóvel', f'{equipamento["potencia"]} W; quantidade: {quantidade}; horas/dia: {horas}; cômodo: {comodo}')
    print('Equipamento cadastrado no imóvel.')


def listar(usuario):
    item = escolher(usuario)
    if not item:
        return
    banco = conectar()
    dados = banco.execute(
        '''SELECT usos.id,equipamentos.nome,equipamentos.potencia,usos.comodo,
                  usos.quantidade,usos.horas,usos.ativo
           FROM usos JOIN equipamentos ON equipamentos.id=usos.equipamento_id
           WHERE usos.imovel_id=?''', (item['id'],)).fetchall()
    banco.close()
    print('\n--- EQUIPAMENTOS ---')
    if not dados:
        print('Nenhum equipamento cadastrado.')
    for x in dados:
        print(f"{x['id']} - {x['nome']} | {x['comodo']} | {x['quantidade']} un. | "
              f"{x['horas']} h/dia | {'Ativo' if x['ativo'] else 'Inativo'}")


def editar(usuario):
    item = escolher(usuario)
    if not item or not item['ativo']:
        print('O imóvel precisa estar ativo.')
        return

    listar(usuario)
    uso_id = inteiro('ID do equipamento que deseja editar: ', 1)
    banco = conectar()
    uso = banco.execute(
        '''SELECT usos.*, equipamentos.nome, equipamentos.potencia AS potencia_catalogo
           FROM usos JOIN equipamentos ON equipamentos.id=usos.equipamento_id
           WHERE usos.id=? AND usos.imovel_id=? AND usos.ativo=1''',
        (uso_id, item['id'])).fetchone()

    if not uso:
        banco.close()
        print('Equipamento não encontrado ou inativo.')
        return

    comodo = input(f"Cômodo [{uso['comodo']}]: ").strip() or uso['comodo']
    quantidade_texto = input(f"Quantidade [{uso['quantidade']}]: ").strip()
    horas_texto = input(f"Horas/dia [{uso['horas']}]: ").strip()
    potencia_texto = input(f"Potência [{uso['potencia']} W]: ").strip()

    try:
        quantidade = int(quantidade_texto) if quantidade_texto else uso['quantidade']
        horas = float(horas_texto.replace(',', '.')) if horas_texto else uso['horas']
        potencia = float(potencia_texto.replace(',', '.')) if potencia_texto else uso['potencia']
    except ValueError:
        banco.close()
        print('Valor inválido.')
        return

    if quantidade < 1 or horas < 0 or horas > 24 or potencia <= 0:
        banco.close()
        print('Quantidade, horas ou potência inválidas.')
        return

    banco.execute('UPDATE usos SET comodo=?, quantidade=?, horas=?, potencia=? WHERE id=? AND imovel_id=?',
                  (comodo, quantidade, horas, potencia, uso_id, item['id']))
    banco.commit()
    banco.close()
    log(usuario['id'], 'Equipamento alterado', f'ID: {uso_id}; quantidade: {quantidade}; horas/dia: {horas}; potência: {potencia} W; cômodo: {comodo}')
    print('Equipamento alterado com sucesso.')


def remover(usuario):
    item = escolher(usuario)
    if not item or not item['ativo']:
        print('O imóvel precisa estar ativo.')
        return
    listar(usuario)
    uso = inteiro('ID do equipamento: ', 1)
    banco = conectar()
    banco.execute('UPDATE usos SET ativo=0 WHERE id=? AND imovel_id=?', (uso, item['id']))
    banco.commit()
    banco.close()
    log(usuario['id'], 'Equipamento removido', f'ID do uso: {uso}')
    print('Equipamento removido.')
