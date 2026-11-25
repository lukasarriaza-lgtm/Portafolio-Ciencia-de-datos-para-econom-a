"""
Análisis de coyuntura del tipo de cambio USD/CLP.

Describe dónde está hoy el dólar frente a su historia, con las consultas
de sql/04_consultas_coyuntura.sql (y la consulta 4 de 03_consultas_proyecto.sql):
    1. Lectura de datos desde SQL.
    2. El dólar frente a su historia (nivel, promedio y rango de 12 meses).

Los gráficos se guardan en figuras/ para usarlos en el informe.

Requisito: haber corrido antes la carga de datos.
Uso desde la raíz del repositorio:
    python src/coyuntura.py
"""
import matplotlib
matplotlib.use("Agg")              # guarda los gráficos sin abrir ventanas
import matplotlib.pyplot as plt
import pandas as pd
from sqlalchemy import text

import carga_db
import config

# Estilo de gráficos del curso (el mismo de preparacion.py)
plt.rcParams.update({'figure.dpi': 110, 'font.size': 10.5,
                     'axes.grid': True, 'grid.alpha': 0.3,
                     'axes.spines.top': False, 'axes.spines.right': False})

COLOR_UDP   = '#800020'   # serie principal
COLOR_TREND = '#1f77b4'   # promedios y referencias
COLOR_ALERT = '#d62728'   # alertas
COLOR_GRAY  = '#7f7f7f'   # series de fondo

RUTA_FIGURAS = config.RAIZ / "figuras"
RUTA_FIGURAS.mkdir(exist_ok=True)

FUENTE_DOLAR = "Fuente: Banco Central de Chile, dólar observado (promedio mensual de datos diarios)."


def leer_consultas(ruta):
    """Lee un archivo .sql y devuelve la lista de consultas (separadas por ';')."""
    contenido = open(ruta, encoding="utf-8").read()
    return [c.strip() for c in contenido.split(";") if c.strip()]


def guardar(fig, nombre):
    """Guarda un gráfico en figuras/ y cierra la figura."""
    fig.savefig(RUTA_FIGURAS / nombre, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Gráfico guardado: figuras/{nombre}")


# ------------------------------------------------------------
# Bloque 1: leer los datos desde SQL
# Consulta 7: tipo de cambio real.
# Consulta 8: dólar mensual, variación mensual y rango de 12 meses.
# ------------------------------------------------------------
engine = carga_db.obtener_engine()
coyuntura = leer_consultas(config.RUTA_SQL / "04_consultas_coyuntura.sql")

with engine.connect() as conn:
    tcr   = pd.read_sql(text(coyuntura[0]), conn, parse_dates=["mes"], index_col="mes")   # consulta 7
    dolar = pd.read_sql(text(coyuntura[1]), conn, parse_dates=["mes"], index_col="mes")   # consulta 8

print(f"Dólar mensual: {dolar.index.min():%Y-%m} a {dolar.index.max():%Y-%m} ({len(dolar)} meses)")


# ------------------------------------------------------------
# Bloque 2: el dólar frente a su historia
# ¿Está caro o barato frente a su promedio? ¿En qué parte de su rango
# del último año está? Se usa toda la historia disponible (desde 2010).
# ------------------------------------------------------------
ultimo      = dolar.index.max()
valor_hoy   = dolar.loc[ultimo, "dolar"]
promedio    = dolar["dolar"].mean()
percentil   = (dolar["dolar"] <= valor_hoy).mean() * 100     # % de meses con un dólar menor o igual
fecha_max   = dolar["dolar"].idxmax()
fecha_min   = dolar["dolar"].idxmin()

fig, ax = plt.subplots(figsize=(11, 4.5))
ax.fill_between(dolar.index, dolar["min_12m"], dolar["max_12m"],
                color=COLOR_GRAY, alpha=0.2, label="Rango de los últimos 12 meses")
ax.plot(dolar.index, dolar["dolar"], color=COLOR_UDP, lw=1.8, label="Dólar observado")
ax.axhline(promedio, color=COLOR_TREND, ls="--", lw=1.2,
           label=f"Promedio {dolar.index.min():%Y}-{ultimo:%Y}: {promedio:,.0f}")
ax.scatter([ultimo], [valor_hoy], color=COLOR_UDP, zorder=5)
ax.annotate(f"{ultimo:%Y-%m}: {valor_hoy:,.0f}", (ultimo, valor_hoy),
            xytext=(-30, -32), textcoords="offset points", fontsize=9,
            arrowprops=dict(arrowstyle="-", color=COLOR_GRAY))
ax.scatter([fecha_max], [dolar["dolar"].max()], color=COLOR_ALERT, zorder=5)
ax.annotate(f"Máximo: {dolar['dolar'].max():,.0f} ({fecha_max:%Y-%m})",
            (fecha_max, dolar["dolar"].max()), xytext=(-150, 5), textcoords="offset points", fontsize=9)
ax.set_title(f"Tipo de cambio USD/CLP, {dolar.index.min():%Y}-{ultimo:%Y}")
ax.set_ylabel("Pesos por dólar (CLP/USD)")
ax.legend(loc="upper left", fontsize=9)
fig.text(0.01, -0.02, FUENTE_DOLAR, fontsize=8, color=COLOR_GRAY)
guardar(fig, "01_dolar_historia.png")

# Lectura del gráfico, con los números para el informe
print(f"\nEl dólar frente a su historia ({ultimo:%Y-%m}):")
print(f"  - Último dato:            {valor_hoy:,.1f} CLP/USD")
print(f"  - Promedio histórico:     {promedio:,.1f} ({100 * (valor_hoy / promedio - 1):+.1f}% sobre el promedio)")
print(f"  - Percentil histórico:    {percentil:.0f} (el dólar estuvo más bajo en el {percentil:.0f}% de los meses)")
print(f"  - Rango de 12 meses:      {dolar.loc[ultimo, 'min_12m']:,.1f} a {dolar.loc[ultimo, 'max_12m']:,.1f}"
      f" (promedio {dolar.loc[ultimo, 'prom_12m']:,.1f})")
print(f"  - Máximo histórico:       {dolar['dolar'].max():,.1f} ({fecha_max:%Y-%m})")
print(f"  - Mínimo histórico:       {dolar['dolar'].min():,.1f} ({fecha_min:%Y-%m})")
