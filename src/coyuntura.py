"""
Análisis de coyuntura del tipo de cambio USD/CLP.

Describe dónde está hoy el dólar frente a su historia, con las consultas
de sql/04_consultas_coyuntura.sql (y la consulta 4 de 03_consultas_proyecto.sql):
    1. Lectura de datos desde SQL.
    2. El dólar frente a su historia (nivel, promedio y rango de 12 meses).
    3. Dólar nominal frente a dólar real (tipo de cambio real, TCR).
    4. Variaciones y volatilidad del dólar.
    5. Indicadores de contexto: los que, según el Hito 1, mueven el dólar.
    6. Estacionalidad: ¿hay que desestacionalizar el dólar? (y el Imacec, que sí).
    7. Cuenta corriente (trimestral), como contexto externo.

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
from statsmodels.tsa.seasonal import STL, seasonal_decompose

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
COLOR_SA    = '#2ca02c'   # series desestacionalizadas

MESES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

# Episodios que movieron el dólar (para marcarlos en los gráficos)
EPISODIOS = {
    "2019-10-01": "Estallido social",
    "2020-03-01": "Pandemia",
    "2022-07-01": "Intervención BCCh",
}

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
    series  = pd.read_sql(text(proyecto[2]), conn, parse_dates=["mes"])                    # consulta 3
    tasas   = pd.read_sql(text(proyecto[5]), conn, parse_dates=["mes"], index_col="mes")   # consulta 6

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
for fecha, nombre in EPISODIOS.items():
    ax.axvline(pd.Timestamp(fecha), color=COLOR_GRAY, ls=":", lw=1)
    ax.text(pd.Timestamp(fecha), dolar["dolar"].min(), f" {nombre}", rotation=90,
            fontsize=8, color=COLOR_GRAY, va="bottom")
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

# Cuánto subió el dólar en cada episodio: del mes anterior al máximo de los 3 meses siguientes
print("\nEl dólar en cada episodio (del mes anterior al máximo de los 3 meses siguientes):")
for fecha, nombre in EPISODIOS.items():
    fecha = pd.Timestamp(fecha)
    antes = dolar["dolar"].loc[:fecha - pd.DateOffset(months=1)].iloc[-1]
    ventana = dolar["dolar"].loc[fecha:fecha + pd.DateOffset(months=3)]
    print(f"  - {nombre:<18} ({fecha:%Y-%m}): {antes:,.0f} -> {ventana.max():,.0f} "
          f"({100 * (ventana.max() / antes - 1):+.1f}%, máximo en {ventana.idxmax():%Y-%m})")


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


# ------------------------------------------------------------
# Bloque 5: indicadores de contexto
# Las variables que, según el Hito 1, mueven el dólar. Signo esperado
# sobre el dólar: (+) lo sube (deprecia el peso), (-) lo baja.
#   - Cobre (-): más caro, más dólares entran a Chile.
#   - Índice dólar amplio (+): un dólar fuerte en el mundo también sube en Chile.
#   - Diferencial TPM - Fed (-): tasas más altas en Chile atraen capitales.
#   - VIX (+): en episodios de miedo, los inversores se refugian en el dólar.
#   - Balanza comercial (-): más exportaciones netas, más oferta de dólares.
#   - IED (-): más inversión extranjera, más dólares que se cambian a pesos.
# Balanza e IED son flujos mensuales muy irregulares (un solo proyecto
# minero mueve un mes). Por eso se muestran también como suma de 12 meses:
# es el contraste entre los dos tratamientos de la IED.
# ------------------------------------------------------------
contexto = series.pivot(index="mes", columns="nombre", values="valor")
contexto = pd.DataFrame({
    "cobre":        contexto["Precio del cobre refinado BML"],
    "indice_dolar": contexto["Índice dólar amplio (Fed)"],
    "diferencial":  tasas["diferencial_tasas"],
    "vix":          contexto["Índice de volatilidad VIX"],
    "balanza":      contexto["Balanza comercial"],
    "ied":          contexto["Inversión extranjera directa, pasivos (flujo)"],
}).loc[dolar.index.min():ultimo]
contexto["balanza_12m"] = contexto["balanza"].rolling(12).sum()
contexto["ied_12m"]     = contexto["ied"].rolling(12).sum()

# (columna, título, unidad, signo esperado sobre el dólar)
PANELES = [
    ("cobre",        "Precio del cobre",                    "USD por libra",           "(-)"),
    ("indice_dolar", "Índice dólar amplio (Fed)",           "Índice ene-2006 = 100",   "(+)"),
    ("diferencial",  "Diferencial de tasas TPM - Fed Funds", "Puntos porcentuales",     "(-)"),
    ("vix",          "Índice de volatilidad VIX",           "Índice",                  "(+)"),
    ("balanza",      "Balanza comercial",                   "Millones de USD",         "(-)"),
    ("ied",          "Inversión extranjera directa (pasivos)", "Millones de USD",       "(-)"),
]

fig, axes = plt.subplots(3, 2, figsize=(13, 10), sharex=True)
for ax, (col, titulo, unidad, signo) in zip(axes.flat, PANELES):
    if col in ("balanza", "ied"):
        ax.bar(contexto.index, contexto[col], width=25, color=COLOR_GRAY, alpha=0.6, label="Mensual")
        ax2 = ax.twinx()
        ax2.plot(contexto.index, contexto[f"{col}_12m"], color=COLOR_UDP, lw=1.8, label="Suma 12 meses (eje der.)")
        ax2.set_ylabel("Suma 12 meses, millones de USD", fontsize=8)
        ax2.spines["top"].set_visible(False)
        ax2.grid(False)
        ax.legend(loc="upper left", fontsize=8)
        ax2.legend(loc="lower left", fontsize=8)
    else:
        ax.plot(contexto.index, contexto[col], color=COLOR_UDP, lw=1.6)
        ax.axhline(contexto[col].mean(), color=COLOR_TREND, ls="--", lw=1, label="Promedio")
        ax.legend(loc="upper left", fontsize=8)
    if col == "diferencial":
        ax.axhline(0, color="black", lw=0.8)
    ax.set_title(f"{titulo}  {signo}", fontsize=11)
    ax.set_ylabel(unidad, fontsize=9)
fig.suptitle(f"Indicadores de contexto del dólar, {contexto.index.min():%Y}-{ultimo:%Y}"
             "   (entre paréntesis, efecto esperado sobre el dólar)", fontsize=12)
fig.text(0.01, -0.01, "Fuente: Banco Central de Chile (cobre, TPM, balanza comercial, IED) y FRED "
         "(índice dólar, Fed Funds, VIX). Promedios mensuales.", fontsize=8, color=COLOR_GRAY)
fig.tight_layout()
guardar(fig, "04_indicadores_contexto.png")

# Tabla resumen: dónde está cada indicador hoy frente a su historia
filas = []
for col, titulo, unidad, signo in PANELES:
    serie = contexto[f"{col}_12m"] if col in ("balanza", "ied") else contexto[col]
    serie = serie.dropna()
    hoy = serie.iloc[-1]
    filas.append({"indicador": titulo + (" (suma 12m)" if col in ("balanza", "ied") else ""),
                  "último": round(hoy, 2),
                  "promedio": round(serie.mean(), 2),
                  "percentil": round((serie <= hoy).mean() * 100),
                  "hace 12 meses": round(serie.iloc[-13], 2),
                  "signo sobre el dólar": signo})
resumen = pd.DataFrame(filas).set_index("indicador")
print(f"\nIndicadores de contexto ({ultimo:%Y-%m}):")
print(resumen.to_string())


# ------------------------------------------------------------
# Bloque 6: estacionalidad
# La pauta pide desestacionalizar "cuando corresponda". Como en U2-04, se
# mide el efecto calendario típico de cada mes con seasonal_decompose
# (multiplicativo): un factor de 1,02 es "2% sobre el promedio del año".
#   - Dólar: si el efecto de cada mes es muy chico, NO hay que desestacionalizar.
#   - Imacec: tiene estacionalidad fuerte (diciembre alto, febrero bajo), así
#     que se desestacionaliza con STL, como en la clase.
# Se usa el período común (desde 2012), con años completos.
# ------------------------------------------------------------
imacec = series[series["nombre"] == "Imacec (índice)"].set_index("mes")["valor"].loc["2012":]
dolar_comun = dolar["dolar"].loc["2012":]

efecto = pd.DataFrame(index=MESES)
for nombre, serie in [("Dólar", dolar_comun), ("Imacec", imacec)]:
    factor = seasonal_decompose(serie, model="multiplicative", period=12).seasonal
    efecto[nombre] = ((factor.groupby(factor.index.month).mean() - 1) * 100).values

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4), sharey=True)
for ax, nombre in [(ax1, "Dólar"), (ax2, "Imacec")]:
    colores = [COLOR_SA if v > 0 else COLOR_ALERT for v in efecto[nombre]]
    ax.bar(efecto.index, efecto[nombre], color=colores)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_title(f"{nombre}: efecto calendario típico de cada mes")
ax1.set_ylabel("% sobre o bajo el promedio del año")
fig.text(0.01, -0.03, "Fuente: Banco Central de Chile. Descomposición clásica multiplicativa "
         "(seasonal_decompose, período 12), 2012-" + f"{ultimo:%Y}.", fontsize=8, color=COLOR_GRAY)
fig.tight_layout()
guardar(fig, "05_estacionalidad_dolar_imacec.png")

print("\nEfecto calendario típico de cada mes (% sobre o bajo el promedio del año):")
print(efecto.round(2).T.to_string())
print(f"  - Dólar:  el mes más alejado del promedio se aleja {efecto['Dólar'].abs().max():.1f}%, menos que "
      f"su movimiento típico de un mes ({dolar['var_mensual'].abs().mean():.1f}%) -> no se desestacionaliza.")
print(f"  - Imacec: de {efecto['Imacec'].min():+.1f}% a {efecto['Imacec'].max():+.1f}% -> sí se desestacionaliza.")

# Imacec desestacionalizado con STL (igual que en U2-04)
stl = STL(imacec, period=12, seasonal=13, robust=True).fit()
imacec_sa = imacec - stl.seasonal

fig, ax = plt.subplots(figsize=(11, 4))
ax.plot(imacec.loc["2022":], color=COLOR_GRAY, marker="o", ms=3, lw=1.2, label="Original")
ax.plot(imacec_sa.loc["2022":], color=COLOR_SA, lw=2.5, label="Desestacionalizado (STL)")
ax.set_title("Imacec original y desestacionalizado, 2022-" + f"{imacec.index.max():%Y}")
ax.set_ylabel("Índice 2018 = 100")
ax.legend(loc="upper left", fontsize=9)
fig.text(0.01, -0.02, "Fuente: Banco Central de Chile. STL (período 12, seasonal 13, robusto).",
         fontsize=8, color=COLOR_GRAY)
guardar(fig, "06_imacec_desestacionalizado.png")

comparacion = pd.DataFrame({"m/m original (%)": imacec.pct_change() * 100,
                            "m/m desestacionalizado (%)": imacec_sa.pct_change() * 100}).tail(6).round(2)
comparacion.index = comparacion.index.strftime("%Y-%m")
print("\nImacec: variación mensual original y desestacionalizada (últimos 6 meses):")
print(comparacion.to_string())


# ------------------------------------------------------------
# Bloque 7: cuenta corriente (trimestral)
# Queda fuera de la base común porque es trimestral (ver preparacion.py),
# pero es contexto clave: un déficit significa que Chile necesita
# financiamiento externo, y eso presiona al alza al dólar si se encarece.
# Se muestra cada trimestre y la suma de los últimos 4 trimestres (un año).
# ------------------------------------------------------------
cc = series[series["nombre"] == "Cuenta corriente"].set_index("mes")["valor"]
cc_anual = cc.rolling(4).sum()

fig, ax = plt.subplots(figsize=(11, 4))
colores = [COLOR_SA if v >= 0 else COLOR_ALERT for v in cc]
ax.bar(cc.index, cc, width=70, color=colores, alpha=0.7, label="Trimestral")
ax.plot(cc_anual.index, cc_anual, color=COLOR_UDP, lw=2, label="Suma de 4 trimestres")
ax.axhline(0, color="black", lw=0.8)
ax.set_title(f"Cuenta corriente de Chile, {cc.index.min():%Y}-{cc.index.max():%Y}")
ax.set_ylabel("Millones de USD")
ax.legend(loc="lower left", fontsize=9)
fig.text(0.01, -0.02, "Fuente: Banco Central de Chile, balanza de pagos. Verde: superávit. Rojo: déficit.",
         fontsize=8, color=COLOR_GRAY)
guardar(fig, "07_cuenta_corriente.png")

trimestre = f"{cc.index.max().year}-T{(cc.index.max().month - 1) // 3 + 1}"
print(f"\nCuenta corriente (último trimestre: {trimestre}):")
print(f"  - Último trimestre:       {cc.iloc[-1]:,.0f} millones de USD")
print(f"  - Suma de 4 trimestres:   {cc_anual.iloc[-1]:,.0f} millones de USD "
      f"(hace un año: {cc_anual.iloc[-5]:,.0f})")
print(f"  - Promedio anual {cc.index.min():%Y}-{cc.index.max():%Y}: {cc_anual.mean():,.0f} millones de USD")
