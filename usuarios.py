import sqlite3
from banco import conectar, hash_senha, senha_certa, log


def cadastro():
    print('\n--- CADASTRO ---')
    nome = input('Nome: ').strip();
    email = input('E-mail: ').strip().lower();
    senha = input('Senha (mínimo 6 caracteres): ')
    if len(nome) < 2 or '@' not in email or len(senha) < 6:
        print('Dados inválidos.');
        return
    banco = conectar()
    try:
        banco.execute('INSERT INTO usuarios(nome,email,senha) VALUES(?,?,?)', (nome, email, hash_senha(senha)))
        banco.commit();
        print('Cadastro realizado.')
    except sqlite3.IntegrityError:
        print('Esse e-mail já está cadastrado.')
    banco.close()


def login():
    print('\n--- LOGIN ---')
    email = input('E-mail: ').strip().lower();
    senha = input('Senha: ')
    banco = conectar();
    usuario = banco.execute('SELECT * FROM usuarios WHERE email=?', (email,)).fetchone();
    banco.close()
    if usuario and senha_certa(senha, usuario['senha']):
        print('Login realizado.');
        return usuario
    print('E-mail ou senha incorretos.')
