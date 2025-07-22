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
Crea y activa un entorno virtual:

bash
Copiar
Editar
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
.venv\Scripts\activate      # Windows
Instala dependencias:

bash
Copiar
Editar
pip install -r requirements.txt
⚙️ Configuración
Clave de OpenAI
Crea un archivo api_key.txt en la raíz (añádelo a .gitignore) con tu clave:

Copiar
Editar
sk-...
Conexión a PostgreSQL
Crea data_postgres.txt con:

txt
Copiar
Editar
PG_HOST=localhost
PG_PORT=5432
PG_USER=usuario
PG_PASS=contraseña
PG_DB=nombre_db
Checkpoints de LangGraph
Define en checkpointer.txt:

txt
Copiar
Editar
table=checkpoints
schema=public
Tip: Si prefieres variables de entorno, usa un .env y python‑dotenv.

▶️ Uso
Arranca la app de Streamlit:

bash
Copiar
Editar
streamlit run app.py
Abre en tu navegador:

arduino
Copiar
Editar
http://localhost:8501
Selecciona un agente, introduce la consulta (símbolo de ticker o nombre), ¡y consulta tus datos!

📂 Estructura del proyecto
bash
Copiar
Editar
├── agents.py          # Definición de agentes y prompts
├── graph.py           # Orquestación con LangGraph
├── my_tools.py        # Wrappers y funciones de análisis JSON/DB
├── app.py             # Interfaz Streamlit
├── requirements.txt
├── api_key.txt        # (git‑ignored) OpenAI API key
├── data_postgres.txt  # (git‑ignored) Credenciales Postgres
├── checkpointer.txt   # (git‑ignored) Configuración de checkpoints
└── .gitignore
🧹 Buenas prácticas
Incluye __pycache__/, .venv/, y archivos sensibles en .gitignore.

No subas nunca tu clave de API ni credenciales.

Documenta cada nuevo agente o herramienta que añadas.

🤝 Contribuciones
Haz un fork

Crea una rama (git checkout -b feature/nombre)

Envía tus commits (git commit -m "Descripción")

Abre un Pull Request

📄 Licencia
Este proyecto está bajo la licencia MIT. Véase el archivo LICENSE para más detalles.
