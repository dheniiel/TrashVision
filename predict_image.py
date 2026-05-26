import os

# Mostra onde o script está sendo executado
print("Diretório atual:", os.getcwd())

# Busca todos os arquivos .pt no computador (a partir da pasta atual)
for root, dirs, files in os.walk('.'):
    for file in files:
        if file.endswith('.pt'):
            print(os.path.join(root, file))

