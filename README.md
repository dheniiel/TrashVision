# 🗑️ TrashVision

Sistema de detecção de resíduos em imagens, vídeos e câmera em tempo real utilizando visão computacional e deep learning.

---

## 📌 Sobre o Projeto

O **TrashVision** é uma aplicação desktop desenvolvida em Python que utiliza um modelo de detecção de objetos treinado com o dataset do Roboflow para identificar e classificar diferentes classes de lixo em:

- 🖼️ **Imagens** estáticas
- 🎬 **Vídeos** pré-gravados
- 📷 **Câmera em tempo real**

A interface gráfica foi construída com **Tkinter**, tornando o uso simples e acessível diretamente no desktop.

---

## 🛠️ Tecnologias Utilizadas

| Tecnologia | Descrição |
|---|---|
| Python | Linguagem principal do projeto |
| Tkinter | Interface gráfica desktop |
| YOLOv11 (Ultralytics) | Modelo de detecção de objetos |
| OpenCV | Processamento de imagens e vídeos |
| Roboflow | Dataset de treinamento do modelo |
| NumPy | Manipulação de arrays e dados numéricos |

---

## 📋 Pré-requisitos

- Ambiente virtual (`venv` recomendado)
- Câmera (opcional, para detecção em tempo real)

---

## ▶️ Como Usar

Com o ambiente virtual ativado, execute a aplicação:

```bash
python main.py
```

A interface gráfica será aberta. A partir dela você pode:

- Carregar o **modelo** que vai ser usado
- Carregar uma **imagem** para detectar resíduos
- Carregar um **vídeo** para processar frame a frame
- Ativar a **câmera** para detecção em tempo real

---
