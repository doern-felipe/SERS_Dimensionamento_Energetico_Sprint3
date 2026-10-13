# SERS — Sprint 3: Dimensionamento Fotovoltaico Residencial

Extensão em Python para o repositório SERS existente. O módulo reutiliza as funções `consumo`, `tarifa`, `log` e `escolher` dos módulos atuais, sem substituir o cadastro de residência/equipamentos da Sprint 2.

## O que está incluído
- Recuperação do imóvel selecionado e consumo calculado pelo SERS.
- Dimensionamento de potência FV, quantidade de módulos e potência instalada.
- Consulta de módulos, inversores e baterias em CSV separados da lógica.
- Estimativa de geração diária/mensal, atendimento da demanda e energia considerada compensada.
- Cenários com e sem baterias, orçamento, economia e payback simples.
- Validações básicas e testes automatizados do motor de cálculo.
- Salvamento da proposta em JSON.

## Importante sobre os dados
Os CSVs contêm **dados demonstrativos**, identificados como tais, para que o software possa ser testado sem apresentar preços/modelos fictícios como reais. Antes da entrega, substituam por equipamentos reais, datasheets/cotações verificáveis e fontes com data de consulta. A HSP deve ser definida para a localidade da residência e sua fonte registrada durante o fluxo.

O seletor de inversor faz uma triagem preliminar por potência. A compatibilidade elétrica real exige verificar tensão e corrente do arranjo, número de módulos por string, janela MPPT e datasheet completo. Não aleguem compatibilidade de engenharia com os dados demonstrativos.

## Instalação e integração
1. Copie `dimensionamento_fv.py` e a pasta `datasets/` para a raiz do projeto SERS, ao lado de `main.py`, `banco.py`, `energia.py` e `imoveis.py`.
2. No `main.py`, adicione uma opção ao menu autenticado, por exemplo `Dimensionamento FV (Sprint 3)`, e encaminhe-a para:

```python
from dimensionamento_fv import executar_dimensionamento
# Dentro do menu, quando o usuário escolher a opção de FV:
executar_dimensionamento(usuario)
```

Use a variável real que representa o usuário autenticado no `main.py`. Não crie um segundo cadastro de residência.
3. Execute os testes isolados:

```bash
python dimensionamento_fv.py
```

4. Execute a aplicação original pelo comando habitual (`python main.py`) e teste o fluxo integrado com uma residência que já tenha equipamentos e consumo calculado.

## Fórmulas usadas
- Consumo diário: `E_dia = E_mês / 30`
- Potência FV necessária: `P_FV = E_dia / (HSP × PR)`
- Módulos: `N = teto(P_FV × 1000 / potência_do_módulo_Wp)`
- Potência instalada: `P_inst = N × potência_do_módulo_Wp / 1000`
- Geração mensal estimada: `P_inst × HSP × PR × 30`
- Energia compensada estimada: `min(consumo_mensal, geração_mensal)`
- Economia mensal simplificada: `energia_compensada × tarifa`
- Payback simples: `investimento / economia_anual`
- Capacidade nominal de bateria: `energia_para_autonomia / (DoD × eficiência)`; quantidade arredondada para cima.

## Limitações conhecidas
- Não é projeto executivo de engenharia nem simulação de fluxo de energia horária.
- O cálculo econômico é simplificado: não modela regras regulatórias de compensação, custo de disponibilidade, degradação, O&M, financiamento, impostos, custo de instalação/estrutura, nem variação tarifária.
- A bateria é dimensionada com base no consumo diário médio total; para backup real, é necessário definir cargas críticas e perfil horário.
- A seleção de inversor é uma triagem preliminar por potência e não substitui a verificação de datasheet.
- O relatório JSON é exportação básica; PDF pode ser acrescentado se o grupo precisar.
