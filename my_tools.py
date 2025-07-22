# my_tools.py

import requests
import json
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
from langchain_core.tools import StructuredTool, tool
from typing import List, Dict
import os
# --- Herramientas de CoinGecko ---

BASE_URL_COINGECKO = "https://api.coingecko.com/api/v3"

def obtener_info_cripto(coin_id: str) -> str:
    """
    Obtiene información básica de una criptomoneda desde CoinGecko.
    
    Args:
        coin_id (str): ID de la criptomoneda (ejemplo: 'bitcoin', 'ethereum').
                       Se debe usar el ID exacto de CoinGecko.
    
    Returns:
        str: JSON string con nombre, descripción, fecha de lanzamiento y última actualización,
             o un mensaje de error.
    """
    url = f"{BASE_URL_COINGECKO}/coins/{coin_id}"

    try:
        response = requests.get(url, timeout=10) # Añadir timeout para evitar esperas infinitas
        if response.status_code != 200:
            return json.dumps({
                "error": f"Error al obtener datos de {coin_id} desde CoinGecko. Código: {response.status_code}. Mensaje: {response.text}"
            }, ensure_ascii=False, indent=2)

        data = response.json()

        nombre = data.get("name", "No disponible")
        # Limitar la descripción para no sobrecargar el token context del LLM
        descripcion_raw = data.get("description", {}).get("en", "")
        descripcion = descripcion_raw.strip() if descripcion_raw else "Sin descripción."
        if len(descripcion) > 500: # Limitar la longitud de la descripción
            descripcion = descripcion[:500] + "..."

        fecha_lanzamiento = data.get("genesis_date", "No disponible")
        ultima_actualizacion = data.get("last_updated", "No disponible")

        resultado = {
            "nombre": nombre,
            "descripcion": descripcion,
            "fecha_lanzamiento": fecha_lanzamiento,
            "ultima_actualizacion": ultima_actualizacion
        }

        return json.dumps(resultado, ensure_ascii=False, indent=2)

    except requests.exceptions.Timeout:
        return json.dumps({"error": f"Tiempo de espera agotado al consultar CoinGecko para {coin_id}."}, ensure_ascii=False, indent=2)
    except requests.exceptions.RequestException as e:
        return json.dumps({"error": f"Error de red o conexión al consultar CoinGecko para {coin_id}: {str(e)}"}, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "error": f"Excepción inesperada al procesar la solicitud de CoinGecko para {coin_id}: {str(e)}"
        }, ensure_ascii=False, indent=2)

# Tool para LangChain
obtener_info_cripto_tool = StructuredTool.from_function(
    func=obtener_info_cripto,
    name="obtener_info_cripto",
    description="Obtiene el nombre, descripción, fecha de lanzamiento y última actualización de una criptomoneda dada su ID en CoinGecko (ej. 'bitcoin'), devuelve un JSON string."
)


def obtener_historico_precios_coingecko(coin_id: str, dias: int) -> str:
    """
    Obtiene histórico OHLC diario de una criptomoneda desde CoinGecko.
    Solo permite valores válidos de días (1, 7, 14, 30, 90, 180, 365).
    Devuelve un JSON string con lista de datos diarios (Date, Open, High, Low, Close, Volume=None).
    """
    # CoinGecko solo permite estos valores en el endpoint /ohlc
    valores_validos_ohlc = [1, 7, 14, 30, 90, 180, 365]
    dias_param = dias if dias in valores_validos_ohlc else 30  # Fallback seguro

    url = f"{BASE_URL_COINGECKO}/coins/{coin_id}/ohlc"
    params = {
        "vs_currency": "usd",
        "days": dias_param
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            return json.dumps([{"error": f"Error al obtener histórico de {coin_id}: {response.status_code} - {response.text}"}], ensure_ascii=False, indent=2)

        data = response.json()
        if not data:
             return json.dumps([{"error": f"No se encontraron datos históricos para {coin_id} para los últimos {dias_param} días."}], ensure_ascii=False, indent=2)

        resultados = []
        for item in data:
            timestamp_ms, open_p, high_p, low_p, close_p = item
            date_str = datetime.utcfromtimestamp(timestamp_ms / 1000).strftime('%Y-%m-%d')
            resultados.append({
                "Date": date_str,
                "Open": open_p,
                "High": high_p,
                "Low": low_p,
                "Close": close_p,
                "Volume": None  # No disponible en este endpoint de CoinGecko
            })

        return json.dumps(resultados, ensure_ascii=False, indent=2)

    except requests.exceptions.Timeout:
        return json.dumps([{"error": f"Tiempo de espera agotado al consultar histórico de {coin_id} en CoinGecko."}], ensure_ascii=False, indent=2)
    except requests.exceptions.RequestException as e:
        return json.dumps([{"error": f"Error de red o conexión al consultar histórico de {coin_id} en CoinGecko: {str(e)}"}], ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps([{"error": f"Error inesperado al obtener histórico de {coin_id} en CoinGecko: {str(e)}"}], ensure_ascii=False, indent=2)

# Tool para LangChain
obtener_historico_precios_coingecko_tool = StructuredTool.from_function(
    func=obtener_historico_precios_coingecko,
    name="obtener_historico_precios_coingecko",
    description="Obtiene histórico OHLC diario de una criptomoneda desde CoinGecko para los últimos N días válidos (1,7,14,30,90,180,365), devuelve JSON string."
)

# --- Herramientas de Yahoo Finance ---

def obtener_info_yahoo(ticker: str) -> str:
    """
    Obtiene información básica de un activo (criptomoneda o acción) desde Yahoo Finance.
    
    Args:
        ticker (str): Ticker del activo (ejemplo: 'BTC-USD', 'AAPL').
    
    Returns:
        str: JSON string con nombre, descripción, fecha de primera cotización y última actualización,
             o un mensaje de error.
    """
    try:
        cripto = yf.Ticker(ticker)
        info = cripto.info

        if not isinstance(info, dict) or not info:
            return json.dumps({"error": f"No se pudo obtener información para el ticker: {ticker}. Podría ser inválido o no encontrado."}, ensure_ascii=False, indent=2)

        nombre = info.get('shortName', info.get('longName', 'No disponible'))
        descripcion_raw = info.get('longBusinessSummary', info.get('description', ''))
        descripcion = descripcion_raw.strip() if descripcion_raw else "Sin descripción."
        if len(descripcion) > 500: # Limitar la longitud de la descripción
            descripcion = descripcion[:500] + "..."

        historico = cripto.history(period="max")

        if not historico.empty:
            fecha_primera_cotizacion = historico.index[0].strftime('%Y-%m-%d')
            ultima_actualizacion = historico.index[-1].strftime('%Y-%m-%d')
        else:
            fecha_primera_cotizacion = "No disponible"
            ultima_actualizacion = "No disponible"

        resultado = {
            "nombre": nombre,
            "descripcion": descripcion,
            "fecha_primera_cotizacion": fecha_primera_cotizacion,
            "ultima_actualizacion": ultima_actualizacion
        }

        return json.dumps(resultado, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Error al procesar la información del ticker {ticker} desde Yahoo Finance: {str(e)}"}, ensure_ascii=False, indent=2)

# Tool para LangChain
obtener_info_yahoo_tool = StructuredTool.from_function(
    func=obtener_info_yahoo,
    name="obtener_info_yahoo",
    description="Obtiene el nombre, descripción, fecha de primera cotización y última actualización de un activo dada su ticker en Yahoo Finance (ej. 'BTC-USD', 'AAPL'), devuelve un JSON string."
)


def obtener_historico_precios(ticker: str, dias: int) -> str:
    """
    Obtiene histórico OHLCV (Open, High, Low, Close, Volume) de un activo
    dada su ticker en Yahoo Finance para los últimos 'dias' días.
    Devuelve un JSON string con lista de diccionarios con columnas: Date, Open, High, Low, Close, Volume.
    """
    try:
        cripto = yf.Ticker(ticker)
        df = cripto.history(period="max")
        
        if df.empty:
            return json.dumps({"error": f"No se encontraron datos históricos para el ticker: {ticker}."}, ensure_ascii=False, indent=2)

        df = df.tail(dias)
        df = df.reset_index()

        if 'Date' in df.columns and pd.api.types.is_datetime64_any_dtype(df['Date']):
            df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')

        lista_dicts = df.to_dict(orient="records")
        return json.dumps(lista_dicts, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Error al obtener o procesar datos históricos para {ticker}: {str(e)}"}, ensure_ascii=False, indent=2)

# Tool de LangChain
obtener_historico_precios_tool = StructuredTool.from_function(
    func=obtener_historico_precios,
    name="obtener_historico_precios",
    description="Obtiene histórico OHLCV de un activo dada su ticker en Yahoo Finance para los últimos N días, devuelve JSON string."
)

@tool
def obtener_y_graficar(ticker: str, dias: int = 30, columna: str = "Close") -> str:
    """
    Obtiene datos de precios desde Yahoo Finance y genera una gráfica de la columna especificada.
    
    Args:
        ticker (str): Ticker del activo (ej. BTC-USD, AAPL).
        dias (int): Número de días recientes a graficar.
        columna (str): Columna a graficar ('Open', 'High', 'Low', 'Close', 'Volume').

    Returns:
        str: Ruta del archivo PNG generado o mensaje de error.
    """
    try:
        cripto = yf.Ticker(ticker)
        df = cripto.history(period="max")
        
        if df.empty:
            return "Error: no se encontraron datos históricos para graficar el ticker. Podría ser inválido o no haber datos disponibles."

        df = df.tail(dias).reset_index()

        if columna not in df.columns:
            return f"Error: la columna '{columna}' no existe en los datos disponibles para {ticker}. Columnas disponibles: {', '.join(df.columns.tolist())}"

        if 'Date' not in df.columns:
            return "Error: la columna de fecha no está presente en los datos."

        df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')

        plt.figure(figsize=(12, 7)) # Tamaño de figura más grande
        plt.plot(df['Date'], df[columna], label=columna, color='skyblue')
        
        # Añadir más ticks en el eje X para mejorar la legibilidad en gráficos largos
        n_ticks = min(len(df['Date']), 10) # Máximo 10 ticks o menos si hay menos datos
        plt.xticks(df['Date'].iloc[::max(1, len(df['Date']) // n_ticks)], rotation=45, ha='right')
        
        plt.xlabel("Fecha", fontsize=12)
        plt.ylabel(f"{columna} (USD)", fontsize=12)
        plt.title(f"Serie temporal de {columna} para {ticker} (Últimos {dias} días)", fontsize=14)
        plt.legend(fontsize=10)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()

        nombre_archivo = f"grafico_{ticker}_{columna}.png" # Nombre de archivo más específico
        plt.savefig(nombre_archivo, dpi=300) # Mejorar la resolución
        plt.close()

        return nombre_archivo

    except Exception as e:
        return f"Error al generar la gráfica para {ticker}: {str(e)}"

# --- Herramientas de Cálculo y Exportación ---

@tool
def calcular_retorno_low_series(precios_low: List[float]) -> str:
    """
    Calcula los retornos porcentuales diarios para una serie de precios bajos.
    Devuelve una cadena de texto legible con los retornos.
    """
    try:
        if not precios_low or len(precios_low) < 2:
            return "No hay suficientes datos para calcular retornos (se necesitan al menos 2 precios)."

        retornos = [0.0]  # El primer día no tiene retorno previo

        for i in range(1, len(precios_low)):
            anterior = precios_low[i - 1]
            actual = precios_low[i]

            if not isinstance(anterior, (int, float)) or not isinstance(actual, (int, float)):
                # Si los datos no son numéricos, se retorna un mensaje de error claro
                return "Error: Los datos de precios deben ser números para calcular retornos."
            elif anterior == 0:
                retornos.append(0.0)  # Evitar división por cero
            else:
                retorno = (actual - anterior) / anterior * 100
                retornos.append(retorno)

        # Formatea los retornos para que el LLM los pueda leer
        # Limitar la cantidad de retornos mostrados para no sobrecargar el LLM
        if len(retornos) > 20:
            formatted_retornos = [f"{r:.2f}%" for r in retornos[:10]] + ["..."] + [f"{r:.2f}%" for r in retornos[-10:]]
            return f"Retornos porcentuales diarios (primeros 10 y últimos 10): {', '.join(formatted_retornos)}"
        else:
            formatted_retornos = [f"{r:.2f}%" for r in retornos]
            return f"Retornos porcentuales diarios: {', '.join(formatted_retornos)}"

    except Exception as e:
        return f"Error al calcular retornos: {str(e)}"


@tool
def guardar_datos_json(datos: List[Dict], nombre_archivo: str = "datos_precios.json") -> str:
    """
    Guarda una lista de diccionarios (ej. datos de precios) como archivo JSON.
    
    Args:
        datos (List[Dict]): Lista de datos a guardar.
        nombre_archivo (str): Nombre del archivo de salida (ej. "bitcoin_data.json").
    
    Returns:
        str: Nombre del archivo guardado o mensaje de error.
    """
    try:
        if not isinstance(datos, list) or not all(isinstance(item, dict) for item in datos):
            return "Error: Los datos a guardar deben ser una lista de diccionarios."

        # Asegurarse de que el nombre del archivo tenga la extensión .json
        if not nombre_archivo.lower().endswith(".json"):
            nombre_archivo += ".json"

        with open(nombre_archivo, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)

        return f"Datos guardados exitosamente en el archivo: {nombre_archivo}"

    except Exception as e:
        return f"Error al guardar datos en el archivo {nombre_archivo}: {str(e)}"

@tool
def graficar_retorno_series(retornos: List[float], titulo: str = "Serie temporal de retornos porcentuales") -> str:
    """
    Grafica la serie temporal de retornos porcentuales.
    Guarda la gráfica como 'grafico_retorno.png' y devuelve el nombre del archivo o un mensaje de error.
    
    Args:
        retornos (List[float]): Lista de retornos porcentuales a graficar.
        titulo (str): Título para la gráfica.
    
    Returns:
        str: Ruta del archivo PNG generado o mensaje de error.
    """
    try:
        if not retornos or not isinstance(retornos, list):
            return "Error: La lista de retornos está vacía o no es válida para graficar."

        # Filtrar valores no numéricos si los hubiera, para evitar errores de graficado
        retornos_numericos = [r for r in retornos if isinstance(r, (int, float))]
        if not retornos_numericos:
            return "Error: No hay datos numéricos válidos en la lista de retornos para graficar."

        plt.figure(figsize=(12, 7)) # Tamaño de figura más grande
        plt.plot(retornos_numericos, label="Retornos %", color='teal', linewidth=1.5)
        plt.xlabel("Periodo", fontsize=12)
        plt.ylabel("Retorno (%)", fontsize=12)
        plt.title(titulo, fontsize=14)
        plt.legend(fontsize=10)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.axhline(0, color='gray', linestyle='--', linewidth=0.8) # Línea en 0%
        plt.tight_layout()

        nombre_archivo = "grafico_retorno.png"
        plt.savefig(nombre_archivo, dpi=300) # Mejorar la resolución
        plt.close()

        return nombre_archivo

    except Exception as e:
        return f"Error al generar la gráfica de retornos: {str(e)}"


####### tool para guardar los datos de los precios en una base de datos:
# my_tools.py (añade esto al final o en una sección de nuevas herramientas)

import psycopg2
from psycopg2 import pool
import pandas as pd
from typing import Dict, Any, List

# --- Configuración de la Base de Datos ---
# ASEGÚRATE de configurar esta URI con tus credenciales reales de PostgreSQL
# Ejemplo: "postgresql://usuario:contraseña@host:puerto/nombre_base_de_datos"
# Puedes obtenerla de las variables de entorno o de st.secrets como la API key de OpenAI
DB_URI = os.getenv("DATABASE_URL", "postgresql://primera-base:primera-base@34.130.1.177:5432/Data?sslmode=disable")

# Pool de conexiones para manejar las conexiones a la base de datos de manera eficiente
_db_pool = None

def _initialize_db_pool():
    global _db_pool
    if _db_pool is None:
        try:
            _db_pool = psycopg2.pool.SimpleConnectionPool(1, 20, DB_URI) # Min 1, Max 20 conexiones
            print("Pool de conexiones a PostgreSQL inicializado.")
        except Exception as e:
            print(f"Error al inicializar el pool de conexiones a PostgreSQL: {e}")
            raise

def _get_db_connection():
    """Obtiene una conexión del pool."""
    if _db_pool is None:
        _initialize_db_pool()
    return _db_pool.getconn()

def _return_db_connection(conn):
    """Devuelve una conexión al pool."""
    if _db_pool:
        _db_pool.putconn(conn)

def _execute_sql(sql_query: str, params=None, fetch_one=False, fetch_all=False):
    """Función auxiliar para ejecutar consultas SQL."""
    conn = None
    try:
        conn = _get_db_connection()
        cur = conn.cursor()
        cur.execute(sql_query, params)
        if fetch_one:
            return cur.fetchone()
        if fetch_all:
            return cur.fetchall()
        conn.commit() # Asegurarse de que los cambios se guarden
    except Exception as e:
        if conn:
            conn.rollback() # Revertir en caso de error
        raise e
    finally:
        if conn:
            _return_db_connection(conn)


@tool
def save_historical_data_to_db(ticker: str, data: List[Dict[str, Any]]) -> str:
    """
    Guarda datos históricos de precios de un activo en una tabla de PostgreSQL.
    Crea la tabla si no existe. La tabla se llamará 'historical_prices'.

    Args:
        ticker (str): El símbolo del ticker del activo (ej. 'BTC-USD', 'AAPL').
        data (List[Dict[str, Any]]): Una lista de diccionarios, donde cada diccionario
                                     representa una fila de datos históricos
                                     (ej. {'Date': 'YYYY-MM-DD', 'Open': ..., 'High': ..., ...}).
    Returns:
        str: Un mensaje de confirmación o error.
    """
    if not data:
        return "No hay datos para guardar en la base de datos."

    conn = None
    try:
        conn = _get_db_connection()
        cur = conn.cursor()

        # Crear la tabla si no existe
        create_table_query = f"""
        CREATE TABLE IF NOT EXISTS historical_prices (
            id SERIAL PRIMARY KEY,
            ticker VARCHAR(50) NOT NULL,
            date DATE NOT NULL,
            open NUMERIC(20, 10),
            high NUMERIC(20, 10),
            low NUMERIC(20, 10),
            close NUMERIC(20, 10),
            adj_close NUMERIC(20, 10),
            volume BIGINT,
            source VARCHAR(50), -- Para indicar si viene de Yahoo o CoinGecko
            UNIQUE (ticker, date) -- Evitar duplicados para un mismo ticker y fecha
        );
        """
        cur.execute(create_table_query)

        # Preparar la inserción de datos
        # Asumiendo que 'data' contiene diccionarios con claves como 'Date', 'Open', etc.
        # Las claves deben coincidir con los nombres de las columnas o ser mapeadas.
        insert_query = f"""
        INSERT INTO historical_prices (ticker, date, open, high, low, close, adj_close, volume, source)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (ticker, date) DO UPDATE SET
            open = EXCLUDED.open,
            high = EXCLUDED.high,
            low = EXCLUDED.low,
            close = EXCLUDED.close,
            adj_close = EXCLUDED.adj_close,
            volume = EXCLUDED.volume,
            source = EXCLUDED.source;
        """
        records_to_insert = []
        for row in data:
            # Asegúrate de que las claves del diccionario coinciden con lo que esperas
            # O adapta esto si las claves varían (ej. 'Date' vs 'date')
            # Para CoinGecko, las claves son [timestamp, open, high, low, close, volume]
            # Para Yahoo Finance, las claves son 'Date', 'Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume'
            # Necesitas estandarizar esto antes de pasar a la herramienta o dentro de ella.
            # Aquí, asumo un formato de diccionario estándar después de procesar
            # los datos de Yahoo o CoinGecko en el agente que las obtiene.

            # Ejemplo de adaptación simple si los datos vienen directamente de la herramienta Yahoo o CoinGecko
            # Esto es un placeholder; la lógica exacta dependerá de cómo obtengas el 'data' antes de llamar a esta tool
            if 'Date' in row: # Assume Yahoo Finance format
                date_str = row['Date']
                source = 'Yahoo Finance'
            elif isinstance(row, list) and len(row) == 6: # Assume CoinGecko OHLCV format
                date_ts = row[0] / 1000 # Convert ms to s
                date_str = datetime.fromtimestamp(date_ts).strftime('%Y-%m-%d')
                row = {
                    'Open': row[1], 'High': row[2], 'Low': row[3],
                    'Close': row[4], 'Volume': row[5], 'Adj Close': None # CoinGecko doesn't have Adj Close
                }
                source = 'CoinGecko'
            else:
                return f"Formato de datos no reconocido para guardar: {row}"

            records_to_insert.append((
                ticker,
                date_str, # La fecha debe ser un string 'YYYY-MM-DD' o un objeto datetime.date
                row.get('Open'),
                row.get('High'),
                row.get('Low'),
                row.get('Close'),
                row.get('Adj Close'),
                row.get('Volume'),
                source
            ))

        cur.executemany(insert_query, records_to_insert)
        conn.commit()
        num_rows_inserted = cur.rowcount
        cur.close()
        return f"Datos históricos para '{ticker}' guardados/actualizados exitosamente en PostgreSQL. {num_rows_inserted} filas afectadas."

    except Exception as e:
        if conn:
            conn.rollback() # Revertir en caso de error
        return f"Error al guardar datos históricos en PostgreSQL: {str(e)}"
    finally:
        if conn:
            _return_db_connection(conn)

 # Si tienes una lista 'toolkit' global
# O simplemente asegúrate de que esté disponible para el agente adecuado.



# --- Toolkit Completo para el Agente ---

toolkit = [
    obtener_info_cripto_tool,
    obtener_info_yahoo_tool,
    obtener_historico_precios_coingecko_tool,
    obtener_historico_precios_tool,
    guardar_datos_json,
    save_historical_data_to_db,
    calcular_retorno_low_series,
    obtener_y_graficar,
    graficar_retorno_series
]