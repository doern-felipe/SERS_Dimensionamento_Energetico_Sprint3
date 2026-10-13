import sqlite3
import hashlib
import secrets
from datetime import datetime

DB = 'sers.db'
BANDEIRAS = {'Verde': 0, 'Amarela': 0.03, 'Vermelha': 0.10}
CATALOGO = [
    ('Geladeira', 'Cozinha', 150), ('Ar-condicionado', 'Climatização', 1200),
    ('Chuveiro elétrico', 'Banheiro', 5500), ('Televisão', 'Lazer', 120),
    ('Lâmpada LED', 'Iluminação', 10), ('Computador', 'Escritório', 300),
    ('Micro-ondas', 'Cozinha', 1400), ('Máquina de lavar', 'Lavanderia', 500)
]


def conectar():
    banco = sqlite3.connect(DB)
    banco.row_factory = sqlite3.Row
    return banco


def criar_banco():
    banco = conectar()
    banco.executescript('''
    CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, email TEXT UNIQUE NOT NULL, senha TEXT NOT NULL, admin INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS imoveis (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER NOT NULL, nome TEXT NOT NULL, endereco TEXT NOT NULL, moradores INTEGER DEFAULT 0, regiao TEXT DEFAULT 'SP', solar_kwh REAL DEFAULT 0, solar_paineis INTEGER DEFAULT 0, ativo INTEGER DEFAULT 1);
    CREATE TABLE IF NOT EXISTS equipamentos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, categoria TEXT NOT NULL, potencia REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS usos (id INTEGER PRIMARY KEY AUTOINCREMENT, imovel_id INTEGER NOT NULL, equipamento_id INTEGER NOT NULL, comodo TEXT NOT NULL, quantidade INTEGER NOT NULL, horas REAL NOT NULL, potencia REAL NOT NULL, ativo INTEGER DEFAULT 1);
    CREATE TABLE IF NOT EXISTS tarifas (regiao TEXT PRIMARY KEY, tarifa REAL NOT NULL, bandeira TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS consumos (id INTEGER PRIMARY KEY AUTOINCREMENT, imovel_id INTEGER NOT NULL, mes TEXT NOT NULL, kwh REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS cobrancas (id INTEGER PRIMARY KEY AUTOINCREMENT, imovel_id INTEGER NOT NULL, data TEXT NOT NULL, kwh REAL NOT NULL, valor REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER, acao TEXT NOT NULL, detalhes TEXT DEFAULT '', data TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS notificacoes (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER NOT NULL, imovel_id INTEGER NOT NULL, mensagem TEXT NOT NULL, data TEXT NOT NULL, lida INTEGER DEFAULT 0);
    ''')
    for nome, categoria, potencia in CATALOGO:
        if not banco.execute('SELECT id FROM equipamentos WHERE nome=?', (nome,)).fetchone():
            banco.execute('INSERT INTO equipamentos(nome,categoria,potencia) VALUES(?,?,?)',
                          (nome, categoria, potencia))
    if not banco.execute('SELECT regiao FROM tarifas').fetchone():
        banco.execute("INSERT INTO tarifas VALUES ('SP',0.90,'Verde'),('RJ',0.95,'Amarela')")
    colunas = banco.execute('PRAGMA table_info(imoveis)').fetchall()
    nomes = [x['name'] for x in colunas]
    if 'solar_paineis' not in nomes:
        banco.execute('ALTER TABLE imoveis ADD COLUMN solar_paineis INTEGER DEFAULT 0')

    colunas = banco.execute('PRAGMA table_info(logs)').fetchall()
    nomes = [x['name'] for x in colunas]
    if 'detalhes' not in nomes:
        banco.execute("ALTER TABLE logs ADD COLUMN detalhes TEXT DEFAULT ''")

    colunas = banco.execute('PRAGMA table_info(usos)').fetchall()
    nomes = [x['name'] for x in colunas]
    if 'potencia' not in nomes:
        banco.execute('ALTER TABLE usos ADD COLUMN potencia REAL NOT NULL DEFAULT 0')
        banco.execute('UPDATE usos SET potencia=(SELECT potencia FROM equipamentos WHERE equipamentos.id=usos.equipamento_id)')
    banco.commit()
    banco.close()


def hash_senha(senha):
    salt = secrets.token_hex(16)
    valor = hashlib.pbkdf2_hmac('sha256', senha.encode(), salt.encode(), 100000)
    return salt + '$' + valor.hex()


def senha_certa(senha, salva):
    try:
        salt, hash_salvo = salva.split('$')
        valor = hashlib.pbkdf2_hmac('sha256', senha.encode(), salt.encode(), 100000)
        return secrets.compare_digest(valor.hex(), hash_salvo)
    except ValueError:
        return False


def log(usuario_id, acao, detalhes=''):
    banco = conectar()
    banco.execute('INSERT INTO logs(usuario_id,acao,detalhes,data) VALUES(?,?,?,?)',
                  (usuario_id, acao, detalhes, datetime.now().isoformat()))
    banco.commit()
    banco.close()


def imovel(usuario_id, imovel_id):
    banco = conectar()
    item = banco.execute(
        'SELECT * FROM imoveis WHERE id=? AND usuario_id=?',
        (imovel_id, usuario_id)).fetchone()
    banco.close()
    return item


def consumo(usuario_id, imovel_id):
    item = imovel(usuario_id, imovel_id)
    if not item:
        return None, []

    banco = conectar()
    dados = banco.execute(
        '''SELECT usos.*, equipamentos.nome, equipamentos.potencia AS potencia_catalogo
           FROM usos JOIN equipamentos ON equipamentos.id=usos.equipamento_id
           WHERE usos.imovel_id=? AND usos.ativo=1''',
        (imovel_id,)).fetchall()
    banco.close()

    detalhes = []
    for x in dados:
        potencia = x['potencia'] if x['potencia'] > 0 else x['potencia_catalogo']
        kwh = potencia * x['quantidade'] * x['horas'] * 30 / 1000
        detalhes.append((x['nome'], x['comodo'], x['quantidade'], potencia, x['horas'], kwh))
    return sum(x[5] for x in detalhes), detalhes


def tarifa(regiao):
    banco = conectar()
    x = banco.execute('SELECT * FROM tarifas WHERE regiao=?', (regiao,)).fetchone()
    banco.close()
    if not x:
        return 0.90, 'Verde'
    return x['tarifa'] * (1 + BANDEIRAS.get(x['bandeira'], 0)), x['bandeira']


def criar_admin():
    banco = conectar()
    if not banco.execute('SELECT id FROM usuarios WHERE email=?', ('admin@sers.local',)).fetchone():
        banco.execute('INSERT INTO usuarios(nome,email,senha,admin) VALUES(?,?,?,1)',
                      ('Administrador', 'admin@sers.local', hash_senha('admin123')))
        banco.commit()
    banco.close()
