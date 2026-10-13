import banco
import usuarios
import imoveis
import equipamentos
import energia
import extras

DB = banco.DB


def conectar():
    banco.DB = DB
    return banco.conectar()


def criar_banco():
    banco.DB = DB
    banco.criar_banco()


def senha_hash(senha):
    return banco.hash_senha(senha)


def senha_certa(senha, salva):
    return banco.senha_certa(senha, salva)


def calcular_consumo(imovel_id, usuario_id=None):
    banco.DB = DB
    if usuario_id is None:
        banco_local = banco.conectar()
        item = banco_local.execute('SELECT usuario_id FROM imoveis WHERE id=?', (imovel_id,)).fetchone()
        banco_local.close()
        if not item:
            return None, []
        usuario_id = item['usuario_id']
    return banco.consumo(usuario_id, imovel_id)


def menu(usuario):
    opcoes = {
        '1': imoveis.cadastrar,
        '2': imoveis.listar,
        '3': imoveis.editar,
        '4': imoveis.excluir,
        '5': equipamentos.cadastrar,
        '6': equipamentos.listar,
        '7': equipamentos.editar,
        '8': equipamentos.remover,
        '9': energia.dimensionar,
        '10': energia.solar,
        '11': energia.grafico_solar,
        '12': energia.consumo_mensal,
        '13': energia.historico,
        '14': extras.notificacoes,
        '15': extras.historico_cobrancas,
        '16': extras.logs_usuario,
        '17': extras.relatorio,
        '18': extras.tarifas,
        '19': energia.testar_solar,
        '20': extras.historico_pdf,
        '21': extras.recomendacao_solar_pdf
    }
    while True:
        print('''\n=== SERS ===
1 - Cadastrar imóvel
2 - Listar imóveis
3 - Editar imóvel
4 - Inativar imóvel
5 - Cadastrar equipamento
6 - Listar equipamentos
7 - Editar equipamento
8 - Remover equipamento
9 - Dimensionamento
10 - Configurar energia solar
11 - Gráfico da energia solar
12 - Cadastrar consumo mensal
13 - Histórico de consumo
14 - Alertas
15 - Histórico de cobranças
16 - Logs
17 - Gerar relatório PDF
18 - Configurar tarifas (admin)
19 - Testes automatizados de energia solar
20 - Gerar PDF do histórico completo
21 - Gerar PDF de recomendação solar
0 - Sair''')
        op = input('Escolha: ')
        if op == '0':
            return
        if op in opcoes:
            opcoes[op](usuario)
        else:
            print('Opção inválida.')


def main():
    banco.criar_banco()
    banco.criar_admin()
    while True:
        print('\n=== SISTEMA DE ESTIMATIVA ENERGÉTICA ===\n1 - Cadastrar usuário\n2 - Login\n0 - Sair')
        op = input('Escolha: ')
        if op == '1':
            usuarios.cadastro()
        elif op == '2':
            usuario = usuarios.login()
            if usuario:
                menu(usuario)
        elif op == '0':
            print('Programa encerrado.')
            break
        else:
            print('Opção inválida.')


if __name__ == '__main__':
    main()
