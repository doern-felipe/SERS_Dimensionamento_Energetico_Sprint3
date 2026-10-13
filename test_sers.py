import os
import tempfile
import unittest

import main
import banco
import energia


class TestSERS(unittest.TestCase):
    def setUp(self):
        self.arquivo = tempfile.NamedTemporaryFile(delete=False).name
        main.DB = self.arquivo
        banco.DB = self.arquivo
        main.criar_banco()

    def tearDown(self):
        os.remove(self.arquivo)

    def criar_imovel(self):
        banco_db = main.conectar()
        banco_db.execute("INSERT INTO usuarios(nome,email,senha) VALUES('Teste','teste@email.com','x')")
        usuario = banco_db.execute('SELECT id FROM usuarios LIMIT 1').fetchone()[0]
        banco_db.execute("INSERT INTO imoveis(usuario_id,nome,endereco) VALUES(?,?,?)",
                         (usuario, 'Casa', 'Rua A'))
        imovel = banco_db.execute('SELECT id FROM imoveis LIMIT 1').fetchone()[0]
        equipamento = banco_db.execute('SELECT id FROM equipamentos LIMIT 1').fetchone()[0]
        banco_db.execute('''INSERT INTO usos(imovel_id,equipamento_id,comodo,quantidade,horas,potencia)
                            VALUES(?,?,?,?,?,?)''', (imovel, equipamento, 'Sala', 2, 3, 150))
        banco_db.commit()
        banco_db.close()
        return usuario, imovel, equipamento

    def test_formula(self):
        consumo = 100 * 2 * 3 * 30 / 1000
        self.assertEqual(consumo, 18)

    def test_senha(self):
        senha = main.senha_hash('123456')
        self.assertTrue(main.senha_certa('123456', senha))
        self.assertFalse(main.senha_certa('654321', senha))

    def test_catalogo(self):
        banco_db = main.conectar()
        total = banco_db.execute('SELECT COUNT(*) FROM equipamentos').fetchone()[0]
        banco_db.close()
        self.assertGreaterEqual(total, 8)

    def test_calculo_imovel(self):
        usuario, imovel, _ = self.criar_imovel()
        total, detalhes = main.calcular_consumo(imovel, usuario)
        self.assertEqual(total, 27)
        self.assertEqual(len(detalhes), 1)

    def test_update_equipamento(self):
        usuario, imovel, equipamento = self.criar_imovel()
        banco_db = main.conectar()
        banco_db.execute('UPDATE usos SET quantidade=?, horas=? WHERE imovel_id=?', (4, 5, imovel))
        banco_db.execute('UPDATE usos SET potencia=? WHERE imovel_id=?', (200, imovel))
        banco_db.commit()
        banco_db.close()
        total, _ = main.calcular_consumo(imovel, usuario)
        self.assertEqual(total, 120)


    def test_energia_solar(self):
        self.assertEqual(energia.geracao_por_painel(), 52.8)
        quantidade, potencia, geracao = energia.calcular_recomendacao_solar(100)
        self.assertEqual(quantidade, 2)
        self.assertEqual(potencia, 1100)
        self.assertEqual(geracao, 105.6)

    def test_recomendacao_zero(self):
        quantidade, potencia, geracao = energia.calcular_recomendacao_solar(0)
        self.assertEqual(quantidade, 0)
        self.assertEqual(potencia, 0)
        self.assertEqual(geracao, 0)

    def test_seguranca_imovel(self):
        usuario1, imovel, _ = self.criar_imovel()
        banco_db = main.conectar()
        banco_db.execute("INSERT INTO usuarios(nome,email,senha) VALUES('Outro','outro@email.com','x')")
        usuario2 = banco_db.execute("SELECT id FROM usuarios WHERE email='outro@email.com'").fetchone()[0]
        banco_db.close()
        total, detalhes = main.calcular_consumo(imovel, usuario2)
        self.assertIsNone(total)
        self.assertEqual(detalhes, [])


if __name__ == '__main__':
    unittest.main()
