# -*- coding: utf-8 -*-
import os
import re
import json
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, inspect

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain.prompts import ChatPromptTemplate

from my_tools import toolkit, save_historical_data_to_db
with open("api_key.txt") as archivo:
  apikey = archivo.read()
os.environ["OPENAI_API_KEY"] = apikey 

# ─── 1. Definición directa de la URI de la base histórica ────────────────────
with open("data_postgres.txt") as archivo:
  HIST_DB_URI = archivo.read()
os.environ["DATABASE_URL"] = HIST_DB_URI  # para save_historical_data_to_db

with open("checkpointer.txt") as archivo:
  check_pointer_db = archivo.read()
os.environ["checkpointerdb"] = check_pointer_db  # para save_historical_data_to_db



# ─── 2. Carga de la API Key ───────────────────────────────────────────────────
def load_openai_key():
    if key := os.getenv("OPENAI_API_KEY"):
        return key
    try:
        return st.secrets["OPENAI_API_KEY"]
    except Exception:
        st.error("❌ La clave OPENAI_API_KEY no está configurada.")
        st.stop()

os.environ["OPENAI_API_KEY"] = load_openai_key()

# ─── 3. Inicialización del LLM y del agente ───────────────────────────────────
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
try:
    _ = llm.invoke([HumanMessage(content="Hola")], timeout=10)
    st.sidebar.success("✅ Conexión con OpenAI OK")
except Exception as e:
    st.sidebar.error("❌ Falló conexión con OpenAI")
    st.sidebar.exception(e)
    st.stop()

memory = MemorySaver()
prompt = ChatPromptTemplate.from_messages([
    ("system", """
Eres un asistente experto en análisis financiero, criptomonedas y mercados bursátiles.
Usa las herramientas disponibles y responde de forma clara y concisa.
"""),
    ("human", "{messages}")
])
agent = create_react_agent(llm, toolkit, checkpointer=memory, prompt=prompt)

# ─── 4. Estado de la conversación ──────────────────────────────────────────────
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

def add_message(role: str, content: str):
    st.session_state.chat_history.append({"role": role, "content": content})

# ─── 5. Procesamiento de la consulta ───────────────────────────────────────────
def process_query(query: str):
    add_message("user", query)
    final_text = ""
    images: list[str] = []
    tool_outputs: list[str] = []

    for step in agent.stream(
        {"messages": [HumanMessage(content=query)]},
        config={"configurable": {"thread_id": "chat1"}}
    ):
        # Capturar salidas de herramientas
        for msg in step.get("tools", {}).get("messages", []):
            if isinstance(msg, ToolMessage):
                text = msg.content.strip()
                tool_outputs.append(text)
                if text.lower().endswith(".png") and os.path.exists(text):
                    images.append(text)

        # Capturar la respuesta final del agente
        for msg in reversed(step.get("agent", {}).get("messages", [])):
            if isinstance(msg, AIMessage) and msg.content:
                final_text = msg.content
                break

    add_message("assistant", final_text or "⚠️ No se obtuvo respuesta.")
    return final_text, images, tool_outputs

# ─── 6. Función auxiliar para extraer ticker de la consulta ──────────────────
def extract_ticker(query: str) -> str:
    # Busca algo como 'BTC-USD' o 'ETH-USD'
    m = re.search(r"\b([A-Za-z0-9]+-[A-Za-z0-9]+)\b", query)
    return m.group(1) if m else ""

# ─── 7. Interfaz principal ────────────────────────────────────────────────────
st.set_page_config(page_title="📊 Asistente Financiero IA", layout="wide")
st.title("📊 Asistente Financiero IA")
st.image("logo_app.PNG", width=150)

if user_query := st.chat_input("¿Qué quieres consultar hoy?"):
    with st.spinner("🔄 Procesando tu consulta..."):
        final_text, imgs, tool_outputs = process_query(user_query)

    # Mostrar imágenes generadas
    for img in imgs:
        st.image(img, caption=os.path.basename(img))

    # Procesar salidas de herramientas
    persisted = False
    for out in tool_outputs:
        low = out.lower()
        # Mensajes de error
        if "error" in low:
            st.error(out)
            continue
        # Mensajes de confirmación de persistencia (si la función se llama)
        if any(word in low for word in ["guardado", "persistido", "exitoso"]):
            st.success(f"📦 {out}")
            persisted = True
            continue
        # Intentar parsear JSON de histórico
        if out.strip().startswith("[") and out.strip().endswith("]"):
            try:
                records = json.loads(out)
                ticker = extract_ticker(user_query)
                if ticker and isinstance(records, list):
                    msg = save_historical_data_to_db(ticker, records)
                    st.success(f"📦 Persistencia automática: {msg}")
                    persisted = True
                else:
                    st.info("⚠️ Datos históricos detectados, pero no pude extraer el ticker.")
                continue
            except json.JSONDecodeError:
                st.info("📊 Datos recibidos (no JSON):")
                st.info(out)
                continue
        # Otro output de herramienta (por ejemplo JSON de tabla)
        st.info(out)

    # Si no se persistió nada
    if not persisted:
        st.info("ℹ️ No se detectó intento de persistencia en esta consulta.")

# Renderizar TODO el historial de chat
for msg in st.session_state.chat_history:
    st.chat_message(msg["role"]).write(msg["content"])

# ─── 8. Panel de administración ────────────────────────────────────────────────
with st.sidebar.expander("⚙️ Ver datos históricos guardados"):
    engine = create_engine(HIST_DB_URI)
    inspector = inspect(engine)
    tables = inspector.get_table_names(schema="public")
    st.write("Tablas en la DB histórica:", tables)
    if "historical_prices" in tables:
        df = pd.read_sql_query(
            "SELECT * FROM public.historical_prices ORDER BY date DESC LIMIT 50",
            con=engine
        )
        st.dataframe(df)
    else:
        st.warning("La tabla `historical_prices` no existe.")

st.markdown("---")
st.caption("💾 Los datos históricos se guardan automáticamente cuando se detecta un JSON de precios.")
