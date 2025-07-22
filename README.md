# Agente‑Financiero‑IA

Asistente financiero modular basado en LangChain, LangGraph y Streamlit que permite:

- 📈 Consultar información y series históricas de criptomonedas y acciones.  
- ⚙️ Orquestar flujos de trabajo mediante grafos de ejecución.  
- 📊 Generar visualizaciones interactivas.  
- 💾 Persistir datos en PostgreSQL para auditoría y análisis posteriores.

---

## 📋 Tabla de contenidos

1. [Características](#-características)  
2. [Tecnologías](#-tecnologías)  
3. [Requisitos](#-requisitos)  
4. [Instalación](#-instalación)  
5. [Configuración](#-configuración)  
6. [Uso](#-uso)  
7. [Estructura del proyecto](#-estructura-del-proyecto)  
8. [Buenas prácticas](#-buenas-prácticas)  
9. [Contribuciones](#-contribuciones)  
10. [Licencia](#-licencia)  

---

## ✨ Características

- **Multi‑agente**  
  Cada agente está especializado en tareas (CoinGecko, Yahoo Finance, análisis de series, persistencia).  
- **Orquestación por grafos**  
  LangGraph coordina flujos, checkpoints en PostgreSQL y ramificaciones de lógica.  
- **Interfaz web**  
  Dashboard interactivo con Streamlit para chat, selección de activos y visualizaciones.  
- **Análisis cuantitativo**  
  Cálculo de retornos diarios, formato JSON estructurado, exportación de datos.  
- **Persistencia segura**  
  SQLAlchemy/psycopg2 para almacenar datos y checkpoints en base de datos.  

---

## 🛠️ Tecnologías

- **Lenguaje:** Python >= 3.8  
- **Orquestación LLM:** LangChain, LangGraph  
- **Modelo:** OpenAI GPT‑4o‑mini  
- **Web UI:** Streamlit  
- **Análisis de datos:** pandas, yfinance, requests  
- **Visualización:** matplotlib  
- **Base de datos:** PostgreSQL (via SQLAlchemy + psycopg2)  

---

## ✅ Requisitos

- Python 3.8 o superior  
- Cuenta y clave de OpenAI  
- Servidor PostgreSQL accesible  

---

## 🚀 Instalación

1. Clona el repositorio:  
   ```bash
   git clone https://github.com/mattx76/Agente‑Financiero‑IA.git
   cd Agente‑Financiero‑IA
