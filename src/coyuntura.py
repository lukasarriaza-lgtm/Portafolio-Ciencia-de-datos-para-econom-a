"""
Análisis de coyuntura del tipo de cambio USD/CLP.

Describe dónde está hoy el dólar frente a su historia, con las consultas
de sql/04_consultas_coyuntura.sql (y la consulta 4 de 03_consultas_proyecto.sql):
    1. Lectura de datos desde SQL.
    2. El dólar frente a su historia (nivel, promedio y rango de 12 meses).
    3. Dólar nominal frente a dólar real (tipo de cambio real, TCR).
    4. Variaciones y volatilidad del dólar.

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
proyecto  = leer_consultas(config.RUTA_SQL / "03_consultas_proyecto.sql")

with engine.connect() as conn:
    tcr   = pd.read_sql(text(coyuntura[0]), conn, parse_dates=["mes"], index_col="mes")   # consulta 7
    dolar = pd.read_sql(text(coyuntura[1]), conn, parse_dates=["mes"], index_col="mes")   # consulta 8
    cambios = pd.read_sql(text(proyecto[3]), conn, parse_dates=["mes"])                    # consulta 4

# Variación en 12 meses del dólar (consulta 4: variación % para el dólar)
dolar["var_anual"] = (cambios[cambios["nombre"].str.startswith("Tipo de cambio")]
                      .set_index("mes")["cambio_12m"])

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


# ------------------------------------------------------------
# Bloque 3: dólar nominal frente a dólar real
# El dólar nominal sube también por la inflación: si en Chile los precios
# suben más que en EE.UU., el peso pierde valor sin que Chile se vuelva
# más barato para el mundo. El TCR descuenta esa diferencia de inflación:
#     TCR = dólar x IPC EE.UU. / IPC Chile   (consulta 7)
# Para compararlos, el dólar nominal se lleva al mismo índice que el TCR
# (promedio 2018 = 100).
# ------------------------------------------------------------
tcr["dolar_indice"] = 100 * tcr["dolar"] / tcr.loc["2018", "dolar"].mean()

ultimo_tcr  = tcr.index.max()
tcr_hoy     = tcr.loc[ultimo_tcr, "tcr"]
nominal_hoy = tcr.loc[ultimo_tcr, "dolar_indice"]
prom_tcr    = tcr["tcr"].mean()
pct_tcr     = (tcr["tcr"] <= tcr_hoy).mean() * 100

fig, ax = plt.subplots(figsize=(11, 4.5))
ax.plot(tcr.index, tcr["dolar_indice"], color=COLOR_GRAY, lw=1.5, label="Dólar nominal")
ax.plot(tcr.index, tcr["tcr"], color=COLOR_UDP, lw=1.8, label="Tipo de cambio real (TCR)")
ax.axhline(100, color="black", lw=0.8)
ax.axhline(prom_tcr, color=COLOR_TREND, ls="--", lw=1.2,
           label=f"Promedio del TCR {tcr.index.min():%Y}-{ultimo_tcr:%Y}: {prom_tcr:.0f}")
ax.set_title(f"Dólar nominal y tipo de cambio real, {tcr.index.min():%Y}-{ultimo_tcr:%Y}")
ax.set_ylabel("Índice (promedio 2018 = 100)")
ax.legend(loc="upper left", fontsize=9)
fig.text(0.01, -0.02, "Fuente: Banco Central de Chile (dólar observado, IPC) y FRED (IPC de EE.UU.). "
         "TCR = dólar x IPC EE.UU. / IPC Chile.", fontsize=8, color=COLOR_GRAY)
guardar(fig, "02_dolar_nominal_real.png")

print(f"\nDólar nominal y real ({ultimo_tcr:%Y-%m}, índice 2018 = 100):")
print(f"  - Dólar nominal:          {nominal_hoy:.1f} ({nominal_hoy - 100:+.1f}% frente a 2018)")
print(f"  - TCR:                    {tcr_hoy:.1f} ({tcr_hoy - 100:+.1f}% frente a 2018)")
print(f"  - Diferencia:             {nominal_hoy - tcr_hoy:.1f} puntos que explica la mayor inflación de Chile")
print(f"  - TCR promedio histórico: {prom_tcr:.1f} (hoy {100 * (tcr_hoy / prom_tcr - 1):+.1f}% sobre el promedio)")
print(f"  - Percentil del TCR:      {pct_tcr:.0f}")
print(f"  - Máximo del TCR:         {tcr['tcr'].max():.1f} ({tcr['tcr'].idxmax():%Y-%m})")
print(f"  - Mínimo del TCR:         {tcr['tcr'].min():.1f} ({tcr['tcr'].idxmin():%Y-%m})")


# ------------------------------------------------------------
# Bloque 4: variaciones y volatilidad del dólar
# Variación anual: cuánto subió o bajó frente al mismo mes del año anterior
# (consulta 4). Volatilidad: desviación estándar de la variación mensual
# en los últimos 12 meses (consulta 8): mide cuánto se mueve el dólar,
# no hacia dónde. Sube en episodios de estrés (2020 y 2022-2023).
# ------------------------------------------------------------
dolar["volatilidad_12m"] = dolar["var_mensual"].rolling(12).std()

var_anual_hoy = dolar.loc[ultimo, "var_anual"]
vol_hoy       = dolar.loc[ultimo, "volatilidad_12m"]
vol_prom      = dolar["volatilidad_12m"].mean()
pct_vol       = (dolar["volatilidad_12m"].dropna() <= vol_hoy).mean() * 100

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True)

colores = [COLOR_UDP if v >= 0 else COLOR_TREND for v in dolar["var_anual"].fillna(0)]
ax1.bar(dolar.index, dolar["var_anual"], width=25, color=colores)
ax1.axhline(0, color="black", lw=0.8)
ax1.set_title("Variación del dólar en 12 meses")
ax1.set_ylabel("%")
ax1.text(0.01, 0.92, "Rojo: el peso se deprecia. Azul: el peso se aprecia.",
         transform=ax1.transAxes, fontsize=9, color=COLOR_GRAY)

ax2.plot(dolar.index, dolar["volatilidad_12m"], color=COLOR_UDP, lw=1.8, label="Volatilidad de 12 meses")
ax2.axhline(vol_prom, color=COLOR_TREND, ls="--", lw=1.2, label=f"Promedio: {vol_prom:.1f} pp")
ax2.set_title("Volatilidad del dólar: desviación estándar de la variación mensual, últimos 12 meses")
ax2.set_ylabel("Puntos porcentuales")
ax2.legend(loc="upper left", fontsize=9)
fig.text(0.01, -0.01, FUENTE_DOLAR + " Variación anual: consulta 4. Variación mensual: consulta 8.",
         fontsize=8, color=COLOR_GRAY)
fig.tight_layout()
guardar(fig, "03_dolar_variaciones_volatilidad.png")

print(f"\nVariaciones y volatilidad del dólar ({ultimo:%Y-%m}):")
print(f"  - Variación mensual:      {dolar.loc[ultimo, 'var_mensual']:+.2f}%")
print(f"  - Variación en 12 meses:  {var_anual_hoy:+.2f}%")
print(f"  - Volatilidad 12 meses:   {vol_hoy:.2f} pp (promedio histórico {vol_prom:.2f} pp, percentil {pct_vol:.0f})")
print(f"  - Mayor alza en 12 meses: {dolar['var_anual'].max():+.1f}% ({dolar['var_anual'].idxmax():%Y-%m})")
print(f"  - Mayor baja en 12 meses: {dolar['var_anual'].min():+.1f}% ({dolar['var_anual'].idxmin():%Y-%m})")
print(f"  - Volatilidad máxima:     {dolar['volatilidad_12m'].max():.2f} pp ({dolar['volatilidad_12m'].idxmax():%Y-%m})")
