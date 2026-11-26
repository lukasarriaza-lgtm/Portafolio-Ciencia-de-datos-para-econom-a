"""
Análisis exploratorio de relaciones entre el dólar y sus predictores.

Responde dos preguntas (sección 3.3b del enunciado):
    1. ¿Qué variables se mueven junto al dólar en el mismo mes? (rezago 0)
       Confirma o descarta los mecanismos del Hito 1.
    2. ¿Alguna variable ANTICIPA al dólar? (rezagos de 1 a 12 meses)
       Solo el pasado sirve para pronosticar: esto decide qué entra a los modelos.

Usa la base común (data/base_mensual.parquet, 2012 en adelante), la misma de los
modelos. Los gráficos se guardan en figuras/.

Requisito: haber corrido antes preparacion.py.
Uso desde la raíz del repositorio:
    python src/relaciones.py
"""
import matplotlib
matplotlib.use("Agg")              # guarda los gráficos sin abrir ventanas
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config

# Estilo de gráficos del curso (el mismo de coyuntura.py)
plt.rcParams.update({'figure.dpi': 110, 'font.size': 10.5,
                     'axes.grid': True, 'grid.alpha': 0.3,
                     'axes.spines.top': False, 'axes.spines.right': False})

COLOR_UDP   = '#800020'
COLOR_TREND = '#1f77b4'
COLOR_GRAY  = '#7f7f7f'

RUTA_FIGURAS = config.RAIZ / "figuras"
RUTA_FIGURAS.mkdir(exist_ok=True)

MAX_REZAGO = 12


def guardar(fig, nombre):
    """Guarda un gráfico en figuras/ y cierra la figura."""
    fig.savefig(RUTA_FIGURAS / nombre, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Gráfico guardado: figuras/{nombre}")


# ------------------------------------------------------------
# Bloque 1: llevar las series a variaciones
# Si se correlacionan NIVELES, dos series que suben con el tiempo salen
# correlacionadas aunque no tengan relación (correlación espuria). Por eso:
#   - Precios e índices (dólar, cobre, índice dólar, VIX, GPR, IPC):
#     variación % mensual (100 x diferencia del logaritmo).
#   - Tasas (diferencial, TPM, Fed, bono a 10 años): cambio en puntos porcentuales.
#   - Imacec: variación en 12 meses (no está desestacionalizado).
#   - Balanza comercial e IED: ya son flujos (millones de USD por mes).
#     La IED va en dos versiones para contrastar: flujo mensual y suma de 12 meses.
# ------------------------------------------------------------
base = pd.read_parquet(config.RUTA_DATOS / "base_mensual.parquet")


def var_pct(serie):
    return 100 * np.log(serie).diff()


# (nombre en el gráfico, serie transformada, signo esperado sobre el dólar, mecanismo)
CANDIDATAS = {
    "Cobre":                 (var_pct(base["cobre"]),              "-", "Más dólares por exportaciones"),
    "Índice dólar amplio":   (var_pct(base["indice_dolar"]),       "+", "Dólar fuerte en el mundo"),
    "Diferencial TPM - Fed": (base["diferencial_tasas"].diff(),    "-", "Tasas altas atraen capitales"),
    "TPM":                   (base["tpm"].diff(),                  "-", "Política monetaria local"),
    "Fed Funds":             (base["fed_funds"].diff(),            "+", "Política monetaria de EE.UU."),
    "Bono EE.UU. 10 años":   (base["ust10"].diff(),                "+", "Tasas largas en EE.UU."),
    "VIX":                   (var_pct(base["vix"]),                "+", "Refugio en el dólar"),
    "Riesgo geopolítico":    (var_pct(base["gpr"]),                "+", "Refugio en el dólar"),
    "Inflación Chile":       (var_pct(base["ipc_cl"]),             "+", "Pérdida de valor del peso"),
    "Imacec (12 meses)":     (100 * np.log(base["imacec"]).diff(12), "-", "Crecimiento atrae capitales"),
    "Balanza comercial":     (base["balanza_comercial"],           "-", "Oferta de dólares"),
    "IED (flujo mensual)":   (base["ied"],                         "-", "Entrada de inversión"),
    "IED (suma 12 meses)":   (base["ied"].rolling(12).sum(),       "-", "Entrada de inversión"),
}

dolar = var_pct(base["dolar"])
print(f"Variable objetivo: variación % mensual del dólar, {dolar.dropna().index.min():%Y-%m} "
      f"a {dolar.index.max():%Y-%m} ({dolar.notna().sum()} meses)")


# ------------------------------------------------------------
# Bloque 2: correlaciones con rezagos
# Para cada variable X y cada rezago k: corr(dólar en t, X en t-k).
#   - k = 0: se mueven juntos en el mismo mes (explica, pero no pronostica).
#   - k >= 1: X anticipa al dólar (sirve para pronosticar).
# Umbral de significancia aproximado (95%): 2 / raíz(n).
# El primer renglón es el propio dólar: su autocorrelación (base del AR/ARIMA).
# ------------------------------------------------------------
def correlaciones(x, y, max_rezago):
    """Correlación de y(t) con x(t-k) para k = 0..max_rezago."""
    return pd.Series({k: y.corr(x.shift(k)) for k in range(max_rezago + 1)})


tabla = pd.DataFrame({"Dólar (su propio pasado)": correlaciones(dolar, dolar, MAX_REZAGO)}).T
tabla.loc["Dólar (su propio pasado)", 0] = np.nan          # consigo mismo en t no aporta
for nombre, (serie, _, _) in CANDIDATAS.items():
    tabla.loc[nombre] = correlaciones(serie, dolar, MAX_REZAGO)

n = dolar.notna().sum()
umbral = 2 / np.sqrt(n)
print(f"Umbral de significancia (95%): |correlación| > {umbral:.2f}")


# ------------------------------------------------------------
# Bloque 3: gráfico de correlaciones del mismo mes (rezago 0)
# ¿Se cumplen los signos esperados del Hito 1?
# ------------------------------------------------------------
mismo_mes = tabla[0].drop("Dólar (su propio pasado)").sort_values()
signos = {nombre: s for nombre, (_, s, _) in CANDIDATAS.items()}

fig, ax = plt.subplots(figsize=(10, 6))
colores = [COLOR_UDP if abs(v) > umbral else COLOR_GRAY for v in mismo_mes]
ax.barh(mismo_mes.index, mismo_mes, color=colores)
for y, (nombre, v) in enumerate(mismo_mes.items()):
    cumple = "sí" if np.sign(v) == (1 if signos[nombre] == "+" else -1) else "no"
    ax.text(v + (0.01 if v >= 0 else -0.01), y, f"esperado ({signos[nombre]}), cumple: {cumple}",
            va="center", ha="left" if v >= 0 else "right", fontsize=8, color=COLOR_GRAY)
for u in (-umbral, umbral):
    ax.axvline(u, color=COLOR_TREND, ls="--", lw=1)
ax.axvline(0, color="black", lw=0.8)
ax.set_xlim(-1, 1)
ax.set_xlabel("Correlación con la variación mensual del dólar (mismo mes)")
ax.set_title(f"¿Qué se mueve junto al dólar? Correlaciones del mismo mes, "
             f"{dolar.dropna().index.min():%Y}-{dolar.index.max():%Y}")
fig.text(0.01, -0.02, f"Rojo: significativa al 95% (|r| > {umbral:.2f}, líneas punteadas). "
         "Variaciones % mensuales; tasas en cambio de puntos; balanza e IED en millones de USD. "
         "Fuente: BCCh y FRED.", fontsize=8, color=COLOR_GRAY)
guardar(fig, "08_correlaciones_mismo_mes.png")


# ------------------------------------------------------------
# Bloque 4: mapa de calor variable x rezago
# Rojo: X y el dólar se mueven en la misma dirección. Azul: en direcciones
# opuestas. Con asterisco, las significativas. La columna 0 explica; las
# columnas 1 a 12 son las que sirven para pronosticar.
# ------------------------------------------------------------
fig, ax = plt.subplots(figsize=(12, 7))
im = ax.imshow(tabla.values.astype(float), cmap="RdBu_r", vmin=-0.6, vmax=0.6, aspect="auto")
ax.set_xticks(range(MAX_REZAGO + 1), [str(k) for k in range(MAX_REZAGO + 1)])
ax.set_yticks(range(len(tabla)), tabla.index)
ax.grid(False)
for i in range(len(tabla)):
    for j in range(MAX_REZAGO + 1):
        v = tabla.iat[i, j]
        if pd.notna(v):
            marca = "*" if abs(v) > umbral else ""
            ax.text(j, i, f"{v:.2f}{marca}", ha="center", va="center", fontsize=7.5,
                    color="white" if abs(v) > 0.35 else "black")
ax.axvline(0.5, color="black", lw=1.5)
ax.set_xlabel("Rezago k (meses): correlación del dólar en t con la variable en t-k")
ax.set_title("Correlaciones con rezagos: ¿qué variable anticipa al dólar?")
fig.colorbar(im, ax=ax, label="Correlación", shrink=0.8)
fig.text(0.01, -0.02, f"* significativa al 95% (|r| > {umbral:.2f}). A la izquierda de la línea, el mismo "
         "mes; a la derecha, rezagos útiles para pronosticar. Fuente: BCCh y FRED.",
         fontsize=8, color=COLOR_GRAY)
guardar(fig, "09_mapa_calor_rezagos.png")


# ------------------------------------------------------------
# Bloque 5: resumen para el informe y los modelos
# Para cada variable: correlación del mismo mes, si cumple el signo, y el
# rezago (1 a 12) con la correlación más fuerte. Las que tienen un rezago
# significativo son candidatas a entrar a los modelos con ese rezago.
# ------------------------------------------------------------
filas = []
for nombre, (_, signo, mecanismo) in CANDIDATAS.items():
    r0 = tabla.loc[nombre, 0]
    rezagos = tabla.loc[nombre, 1:]
    k = rezagos.abs().astype(float).idxmax()
    filas.append({
        "variable": nombre,
        "signo esperado": signo,
        "r mismo mes": round(r0, 2),
        "cumple signo": "sí" if np.sign(r0) == (1 if signo == "+" else -1) else "no",
        "mejor rezago": k,
        "r en ese rezago": round(rezagos[k], 2),
        "anticipa (signif.)": "sí" if abs(rezagos[k]) > umbral else "no",
        "signo ok en rezago": "sí" if np.sign(rezagos[k]) == (1 if signo == "+" else -1) else "no",
        "mecanismo": mecanismo,
    })
resumen = pd.DataFrame(filas).set_index("variable")

propio = tabla.loc["Dólar (su propio pasado)", 1:]
print(f"\nAutocorrelación del dólar: rezago 1 = {propio[1]:.2f} "
      f"({'significativa' if abs(propio[1]) > umbral else 'no significativa'})")

print("\nResumen de relaciones (variación mensual del dólar):")
print(resumen.drop(columns="mecanismo").to_string())

mismo_mes_sig = resumen[resumen["r mismo mes"].abs() > umbral].index.tolist()
print(f"\nSe mueven con el dólar en el mismo mes (significativas): {', '.join(mismo_mes_sig)}")

# Más candidatos, más oportunidades de engañarse con el ruido (U4-05): con
# muchas pruebas, algunas salen "significativas" por azar. Por eso se usan dos
# caminos, como en la clase:
#   - Camino econométrico (MCO): solo las que anticipan al dólar con el signo
#     que predice el mecanismo económico.
#   - Camino de ciencia de datos (Lasso): todas las variables; Lasso decide.
# La evaluación fuera de muestra decide cuál pronostica mejor.
n_pruebas = len(CANDIDATAS) * MAX_REZAGO
print(f"\nOjo: se hicieron {n_pruebas} pruebas con rezagos; al 95% se esperan unas "
      f"{0.05 * n_pruebas:.0f} 'significativas' solo por azar.")
anticipan = resumen[resumen["anticipa (signif.)"] == "sí"]
candidatas = anticipan[anticipan["signo ok en rezago"] == "sí"]
descartadas = anticipan[anticipan["signo ok en rezago"] == "no"]
print("Candidatas para el camino econométrico (MCO): anticipan al dólar con el signo esperado:")
for nombre, fila in candidatas.iterrows():
    print(f"  - {nombre}: rezago {fila['mejor rezago']}, r = {fila['r en ese rezago']:+.2f} ({fila['mecanismo']})")
if candidatas.empty:
    print("  - Ninguna: el pasado anticipa poco al dólar (típico de un mercado cambiario).")
print("Significativas pero con el signo contrario al esperado (sin mecanismo, no entran al MCO):")
for nombre, fila in descartadas.iterrows():
    print(f"  - {nombre}: rezago {fila['mejor rezago']}, r = {fila['r en ese rezago']:+.2f}")
print("Todas las variables (incluidas estas) entran al camino de ciencia de datos (Lasso), "
      "que decide con los datos. Un coeficiente cero en Lasso no significa que la variable "
      "no importe (U4-03).")
