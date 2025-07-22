# agents.py

import os
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import StructuredTool

# Importar las herramientas desde my_tools.py
# Asegúrate de que my_tools.py esté en el mismo directorio o en una ruta accesible
from my_tools import (
    obtener_info_cripto_tool,
    obtener_info_yahoo_tool,
    obtener_historico_precios_coingecko_tool,
    obtener_historico_precios_tool,
    calcular_retorno_low_series,
    obtener_y_graficar,
    graficar_retorno_series,
    guardar_datos_json,
    save_historical_data_to_db
)

# --- Configuración del LLM (compartida por todos los agentes) ---
# Se puede parametrizar o tener LLMs diferentes por agente si fuera necesario
def get_shared_llm():
    """Inicializa y devuelve una instancia del LLM de OpenAI."""
    if "OPENAI_API_KEY" not in os.environ:
        raise ValueError("OPENAI_API_KEY no está configurada en las variables de entorno.")
    return ChatOpenAI(model="gpt-4o-mini", temperature=0)

# --- Definición de los Agentes Especializados ---

def create_asset_info_agent(llm: ChatOpenAI) -> StructuredTool:
    """
    Crea y devuelve un AgentExecutor para el Agente de Información de Activos.
    Este agente se especializa en obtener información descriptiva sobre activos.
    """
    asset_info_prompt = ChatPromptTemplate.from_messages([
        ("system", """
        Eres un experto en obtener información descriptiva y general sobre activos financieros (criptomonedas y acciones).
        Tu objetivo es proporcionar detalles como el nombre, descripción, fecha de lanzamiento/primera cotización y última actualización del activo.
        Utiliza las herramientas de CoinGecko para criptomonedas (usando su ID) y Yahoo Finance para acciones o criptomonedas (usando su ticker).
        Siempre que uses una herramienta, interpreta sus resultados y formula una respuesta comprensible y amigable para el usuario.
        Sé directo y claro. Si no puedes realizar una acción o no encuentras la información, responde amablemente explicando la limitación.
        """),
        ("human", "{messages}"),
    ])
    asset_info_tools = [
        obtener_info_cripto_tool,
        obtener_info_yahoo_tool
    ]
    return create_react_agent(llm, asset_info_tools, prompt=asset_info_prompt)

def create_historical_data_agent(llm: ChatOpenAI) -> StructuredTool:
    """
    Crea y devuelve un AgentExecutor para el Agente de Datos Históricos.
    Este agente se especializa en obtener series de tiempo de precios históricos (OHLCV).
    """
    historical_data_prompt = ChatPromptTemplate.from_messages([
        ("system", """
        Eres un experto en la recuperación de datos históricos de precios (Open, High, Low, Close, Volume) para activos financieros.
        Tu objetivo es obtener series de tiempo precisas para criptomonedas y acciones utilizando las herramientas disponibles.
        Utiliza la herramienta de CoinGecko para criptomonedas (solo OHLC) y Yahoo Finance para acciones o criptomonedas (OHLCV).
        Devuelve los datos de forma estructurada (generalmente un JSON string) para que puedan ser utilizados por otros agentes o presentados.
        Si la solicitud es para graficar, **solo obtén los datos**, no intentes graficar; el agente de visualización se encargará de ello.
        Si no encuentras los datos, infórmalo claramente.
        """),
        ("human", "{messages}"),
    ])
    historical_data_tools = [
        obtener_historico_precios_coingecko_tool,
        obtener_historico_precios_tool
    ]
    return create_react_agent(llm, historical_data_tools, prompt=historical_data_prompt)


def create_analysis_visualization_agent(llm: ChatOpenAI) -> StructuredTool:
    """
    Crea y devuelve un AgentExecutor para el Agente de Análisis y Visualización.
    Este agente se especializa en realizar cálculos sobre datos financieros y generar gráficos.
    """
    analysis_visualization_prompt = ChatPromptTemplate.from_messages([
        ("system", """
        Eres un experto en análisis de datos financieros y generación de visualizaciones.
        Tu objetivo es tomar datos de precios históricos y realizar cálculos (como retornos porcentuales) o generar gráficos claros y útiles.
        Siempre que generes un gráfico, devuelve la ruta del archivo PNG resultante.
        Si se te solicita guardar datos, utiliza la herramienta correspondiente.
        Si los datos proporcionados son insuficientes o inválidos para el análisis/graficado, informa al usuario.
        """),
        ("human", "{messages}"),
    ])
    analysis_visualization_tools = [
        calcular_retorno_low_series,
        obtener_y_graficar,
        graficar_retorno_series,
        guardar_datos_json,
        save_historical_data_to_db # <<< ¡AÑADIDO AQUÍ!
    ]
    return create_react_agent(llm, analysis_visualization_tools, prompt=analysis_visualization_prompt)
# --- Agente Supervisor (Lo definiremos con LangGraph, pero aquí puedes tener su prompt inicial) ---
def get_supervisor_prompt():
    """
    Devuelve el prompt del agente supervisor.
    Este prompt es crucial para la lógica de enrutamiento del grafo.
    """
    return ChatPromptTemplate.from_messages([
        ("system", """
        Eres el Agente Supervisor de un sistema de asistente financiero multiagente.
        Tu rol es entender la consulta del usuario y decidir qué agente especializado (o secuencia de agentes) debe manejar la tarea.
        Dirige la conversación al agente más apropiado y, si una tarea requiere múltiples pasos, orquesta la secuencia correcta.

        **Agentes disponibles y sus funciones:**
        - `asset_info_agent`: Obtiene información descriptiva (nombre, descripción, fechas) de criptomonedas o acciones.
        - `historical_data_agent`: Obtiene series de tiempo de precios históricos (OHLCV). No grafica ni analiza.
        - `analysis_visualization_agent`: Realiza análisis (ej. calcular retornos) o genera gráficos a partir de datos históricos y guarda los datos en una base de datos postgres sql.
        - `FINAL_ANSWER`: Si la respuesta ha sido completamente generada o si la consulta no requiere el uso de herramientas especializadas.

        **Tu proceso de decisión:**
        1. Evalúa la intención principal de la consulta.
        2. Determina qué agente es el más adecuado para empezar o continuar la tarea.
        3. Si la tarea está completa y tienes una respuesta coherente para el usuario (incluyendo posibles rutas de archivos de gráficos), devuelve `FINAL_ANSWER`.

        **Ejemplos de enrutamiento:**
        - "Qué es Bitcoin?": -> `asset_info_agent`
        - "Dame el precio de cierre de BTC-USD de los últimos 30 días": -> `historical_data_agent`
        - "Grafica el precio de Ethereum de los últimos 90 días": -> `historical_data_agent` (para obtener los datos, luego podría ir a `analysis_visualization_agent`)
        - "Calcula los retornos diarios de AAPL": -> `historical_data_agent` (para obtener los datos, luego podría ir a `analysis_visualization_agent`)
        - Después de obtener datos: "Ahora grafícalos": -> `analysis_visualization_agent`
        - Si la consulta ya fue respondida y quieres presentar el resultado: -> `FINAL_ANSWER`

        Responde únicamente con el nombre del agente al que deseas pasar el control (ej. `asset_info_agent`, `historical_data_agent`, `analysis_visualization_agent`, `FINAL_ANSWER`).
        """),
        ("human", "{messages}"),
    ])

# --- Función principal para inicializar todos los agentes ---
def initialize_agents():
    """
    Inicializa todos los AgentExecutors y devuelve un diccionario de ellos.
    """
    llm = get_shared_llm() # Obtener la instancia del LLM compartida

    agents = {
        "asset_info_agent": create_asset_info_agent(llm),
        "historical_data_agent": create_historical_data_agent(llm),
        "analysis_visualization_agent": create_analysis_visualization_agent(llm)
    }
    return agents

if __name__ == "__main__":
    # Este bloque es solo para probar la inicialización de los agentes
    # y los prompts si ejecutas este archivo directamente.
    print("Inicializando agentes...")
    try:
        # Asegúrate de que OPENAI_API_KEY esté configurada para esta prueba
        # os.environ["OPENAI_API_KEY"] = "sk-..." # Descomenta y reemplaza si pruebas aquí
        
        all_agents = initialize_agents()
        print("Agentes inicializados correctamente:")
        for name, agent_executor in all_agents.items():
            print(f"- {name}: {agent_executor}")

        # Ejemplo de cómo obtener el prompt del supervisor
        supervisor_prompt_template = get_supervisor_prompt()
        print("\nPrompt del Agente Supervisor:")
        print(supervisor_prompt_template.messages[0].prompt.template[:200] + "...") # Mostrar parte del system prompt

    except ValueError as e:
        print(f"Error al inicializar: {e}")
        print("Asegúrate de configurar la variable de entorno OPENAI_API_KEY.")
    except Exception as e:
        print(f"Ocurrió un error inesperado durante la inicialización: {e}")

