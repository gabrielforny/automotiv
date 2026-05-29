# Robô Automotiv

Projeto inicial da automação do sistema Automotiv/GRV.

## Rodar com interface

```bat
run_interface.bat
```

Ou:

```bat
python main.py --gui
```

## Testar apenas leitura da planilha

```bat
python main.py --dry-run --excel "C:\caminho\da\planilha.xlsx"
```

## Rodar fluxo real

```bat
python main.py --excel "C:\caminho\da\planilha.xlsx"
```

## Observações

- A leitura da planilha aceita variações no cabeçalho com quebra de linha, acentos e espaços.
- A automação usa `pywinauto` primeiro, pois é mais estável para sistemas Windows.
- Quando o sistema não expuser controles, usaremos fallback por imagem com `pyautogui`.
- O site fallback configurado é `https://www.automotivdobrasil.com.br`.


## Debug no VS Code

Abra a pasta do projeto no VS Code, selecione o interpretador `.venv`, coloque breakpoints e aperte F5.
Foram adicionadas três configurações prontas:

- Automotiv - Interface
- Automotiv - Testar leitura da planilha
- Automotiv - Rodar real

Na interface, a planilha é opcional. Se o campo ficar vazio, o robô usa `excel.default_path` do `config/config.yaml`.
