# Passo a passo para instalar e debugar no Windows do cliente

## 1. Instalar Python

1. Acesse o site oficial do Python.
2. Baixe o instalador Windows 64 bits.
3. Na primeira tela do instalador, marque: **Add python.exe to PATH**.
4. Clique em **Install Now**.
5. Abra o PowerShell e valide:

```bat
python --version
pip --version
```

## 2. Instalar VS Code

1. Instale o Visual Studio Code.
2. Abra o VS Code.
3. Vá em Extensions.
4. Instale a extensão **Python**, da Microsoft.

## 3. Copiar o projeto

1. Extraia o ZIP `automotiv_bot.zip` em uma pasta simples, por exemplo:

```bat
C:\automotiv_bot
```

Evite caminho com acento, espaço ou pasta muito protegida.

## 4. Abrir o projeto no VS Code

1. Abra o VS Code.
2. Clique em **File > Open Folder**.
3. Selecione:

```bat
C:\automotiv_bot
```

## 5. Criar ambiente virtual

No terminal do VS Code, rode:

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 6. Testar somente leitura da planilha

Rode:

```bat
python main.py --dry-run
```

Esse comando não controla a tela, só valida estrutura, configuração e leitura da planilha.

## 7. Testar fluxo real

Antes de rodar:

1. Confirme se o atalho está na Área de Trabalho com o nome:

```text
MenuGRV3 - Atalho (3).lnk
```

2. Confirme que o sistema abre manualmente.
3. Feche o sistema.
4. Rode:

```bat
python main.py
```

## 8. Testar busca de cliente

Quando já quiser testar CPF/CNPJ:

```bat
python main.py --cliente "12.345.678/0001-90"
```

ou:

```bat
python main.py --cliente "12345678000190"
```

## 9. Gerar o executável

Depois que o fluxo estiver validado:

```bat
build_exe.bat
```

O executável vai ficar em:

```bat
dist\AutomotivBot\AutomotivBot.exe
```

## 10. Arquivos importantes

- `config/config.yaml`: configura senha, nome do atalho e caminho da planilha.
- `data/solicitacao_orcamento_exemplo.xlsx`: exemplo da planilha.
- `logs/automotiv_bot.log`: log da execução.
- `src/desktop_automation.py`: pontos principais da automação desktop.

## 11. Quando algo não clicar certo

Isso é esperado na primeira ida ao cliente, porque precisamos validar como o sistema expõe os controles no Windows real.

O arquivo mais provável de ajuste é:

```text
src/desktop_automation.py
```

Pontos que provavelmente serão refinados:

- Clique no menu Cadastro > Materiais > Materiais/Itens.
- Seleção de Código Interno.
- Seleção de Ativo/Inativo.
- Leitura da grid de resultado.
- Captura do código do cliente.
