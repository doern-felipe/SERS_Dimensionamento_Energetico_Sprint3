from banco import conectar, imovel, log
from entrada import inteiro


def listar(usuario):
    banco = conectar();
    dados = banco.execute('SELECT * FROM imoveis WHERE usuario_id=? ORDER BY id', (usuario['id'],)).fetchall();
    banco.close()
    print('\n--- IMÓVEIS ---')
    if not dados: print('Nenhum imóvel cadastrado.')
    for x in dados: print(f"{x['id']} - {x['nome']} | {x['endereco']} | {'Ativo' if x['ativo'] else 'Inativo'}")
    return dados


def escolher(usuario):
    listar(usuario);
    item = imovel(usuario['id'], inteiro('ID do imóvel: ', 1))
    if not item: print('Imóvel não encontrado.')
    return item


def cadastrar(usuario):
    print('\n--- NOVO IMÓVEL ---')
    nome = input('Nome/identificação: ').strip();
    endereco = input('Endereço: ').strip();
    moradores = inteiro('Número de moradores: ');
    regiao = input('Região/UF (ex: SP): ').strip().upper()
    if not nome or not endereco: print('Nome e endereço são obrigatórios.'); return
    banco = conectar();
    banco.execute('INSERT INTO imoveis(usuario_id,nome,endereco,moradores,regiao) VALUES(?,?,?,?,?)',
                  (usuario['id'], nome, endereco, moradores, regiao));
    banco.commit();
    banco.close();
    log(usuario['id'], 'Imóvel cadastrado', f'Nome: {nome}; endereço: {endereco}; região: {regiao}');
    print('Imóvel cadastrado.')


def editar(usuario):
    item = escolher(usuario)
    if not item: return
    nome = input(f"Nome [{item['nome']}]: ").strip() or item['nome'];
    endereco = input(f"Endereço [{item['endereco']}]: ").strip() or item['endereco'];
    regiao = input(f"Região [{item['regiao']}]: ").strip().upper() or item['regiao']
    banco = conectar();
    banco.execute('UPDATE imoveis SET nome=?,endereco=?,regiao=? WHERE id=? AND usuario_id=?',
                  (nome, endereco, regiao, item['id'], usuario['id']));
    banco.commit();
    banco.close();
    log(usuario['id'], 'Imóvel alterado', f'Nome: {nome}; endereço: {endereco}; região: {regiao}');
    print('Imóvel alterado.')


def excluir(usuario):
    item = escolher(usuario)
    if not item: return
    banco = conectar();
    banco.execute('UPDATE imoveis SET ativo=0 WHERE id=? AND usuario_id=?', (item['id'], usuario['id']));
    banco.execute('UPDATE usos SET ativo=0 WHERE imovel_id=?', (item['id'],));
    banco.commit();
    banco.close();
    log(usuario['id'], 'Imóvel inativado', f'Imóvel ID: {item["id"]}; nome: {item["nome"]}');
    print('Imóvel inativado.')
