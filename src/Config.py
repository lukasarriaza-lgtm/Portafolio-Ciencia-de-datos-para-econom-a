"""
Configuración central del proyecto.

Las credenciales se leen desde el archivo .env (NUNCA subir credenciales a GitHub).
Copien .env.example a .env y completen sus claves.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Rutas del proyecto
RAIZ = Path(__file__).resolve().parents[1]
RUTA_DATOS = RAIZ / "data"
RUTA_DB = RUTA_DATOS / "coyuntura.db"
RUTA_SQL = RAIZ / "sql"

# Cargar credenciales desde .env
load_dotenv(RAIZ / ".env")

# --- Banco Central de Chile ---
# Registro gratuito en: https://si3.bcentral.cl/Siete/es/Siete/API
BCCH_USUARIO = os.getenv("BCCH_USUARIO", "")
BCCH_PASSWORD = os.getenv("BCCH_PASSWORD", "")

# --- FRED (Reserva Federal de St. Louis) ---
# API key gratuita en: https://fred.stlouisfed.org/docs/api/api_key.html
FRED_API_KEY = os.getenv("FRED_API_KEY", "")

# ============================================================
# CATÁLOGO DE SERIES DEL PROYECTO
# Cada equipo debe editar este catálogo con sus propias series.
# Los códigos del BCCh se buscan en https://si3.bcentral.cl/siete
# (el código aparece en la ficha de cada serie).
# ============================================================
SERIES_BCCH = [
    # (codigo, nombre, frecuencia, unidad, id_tema)
    # Signo esperado sobre el dólar: (+) deprecia el peso, (-) aprecia el peso
    # Rol: la primera serie es la variable objetivo; todas las demás son explicativas

    # VARIABLE OBJETIVO: precio de un dólar en pesos chilenos
    ("F073.TCO.PRE.Z.D", "Tipo de cambio observado (CLP/USD)", "D", "CLP/USD", 5),

    # Paridad de tasas (UIP): una TPM más alta frente a la Fed atrae capitales (-)
    ("F022.TPM.TIN.D001.NO.Z.D", "Tasa de Política Monetaria (TPM)", "D", "% anual", 4),

    # Paridad de poder de compra: más inflación en Chile que en EE.UU. deprecia el peso (+)
    ("F074.IPC.IND.Z.EP23.C.M", "IPC general (índice)", "M", "índice 2023=100", 2),

    # Ciclo y productividad (Balassa-Samuelson): mayor actividad relativa aprecia el peso (-)
    ("F032.IMC.IND.Z.Z.EP18.Z.Z.0.M", "Imacec (índice)", "M", "índice 2018=100", 1),

    # Commodity currency: un cobre más caro trae más dólares a Chile (-)
    ("F019.PPB.PRE.40.M", "Precio del cobre refinado BML", "M", "USD/libra", 5),

    # Volumen exportado: más cobre vendido aumenta la oferta de dólares (-)
    ("F034.ECUM.FLU.COCHILCO.Z.0.M", "Exportaciones de cobre (volumen)", "M", "toneladas", 5),

    # Posición externa: un déficit mayor exige financiamiento externo y deprecia el peso
    ("F068.A.FLU.Z.0.S.N.Z.Z.Z.Z.6.0.T", "Cuenta corriente", "Q", "millones USD", 5),

    # Más exportaciones netas aumentan la oferta de dólares (-)
    ("F068.B1.VAR.T0.0.S.N.Z.Z.Z.Z.6.0.M", "Balanza comercial", "M", "verificar en la BDE", 5),

    # Balance de portafolio: entradas de inversión directa demandan pesos (-)
    ("F068.T6.STO.Z.IED.S.P.Z.T.Z.Z.6.0.M", "Inversión extranjera directa", "M", "verificar en la BDE", 5),

    # Con los gastos forma el balance fiscal: un déficit persistente resta credibilidad (+)
    ("F051.BT02.FLU.C.D.CLP.M", "Ingresos totales Gobierno Central", "M", "millones CLP", 7),

    # Mundell-Fleming: más gasto sube tasas (-), pero si es insostenible deprecia el peso (+)
    ("F051.BT03.FLU.C.D.CLP.M", "Gastos totales Gobierno Central", "M", "millones CLP", 7),
]

SERIES_FRED = [
    # (codigo, nombre, frecuencia, unidad, id_tema)

    # Alzas de la Fed generan salidas de capital desde emergentes (+)
    ("FEDFUNDS", "Tasa Fed Funds (EE.UU.)", "M", "% anual", 6),

    # Mayor rendimiento del Tesoro a 10 años atrae capitales hacia EE.UU. (+)
    ("GS10", "Tasa Tesoro EE.UU. 10 años", "M", "% anual", 6),

    # Contraparte del diferencial de inflación: más inflación en EE.UU. aprecia el peso (-)
    ("CPIAUCSL", "IPC Estados Unidos (índice)", "M", "índice 1982-84=100", 6),

    # Aversión al riesgo: en episodios de estrés el dólar actúa como refugio (+)
    ("VIXCLS", "Índice de volatilidad VIX", "D", "índice", 6),

    # Fortaleza global del dólar (índice amplio, sustituto del DXY) (+)
    ("DTWEXBGS", "Índice dólar amplio (Fed)", "D", "índice ene-2006=100", 6),
]

# ------------------------------------------------------------
# Fuente externa (sin API): se descarga directo desde la URL del archivo
# ------------------------------------------------------------
URL_GPR = "https://www.matteoiacoviello.com/gpr_files/data_gpr_export.xls"

SERIES_OTRAS = [
    # (codigo, nombre, frecuencia, unidad, id_tema)

    # Más riesgo geopolítico provoca fuga de capitales desde emergentes (+)
    ("GPR", "Índice de Riesgo Geopolítico (Caldara e Iacoviello)", "M", "índice", 6),
]