"""
Evaluación fuera de muestra de los modelos del dólar (sección 3.3d).

Compara, con pronósticos a un mes que nunca usan información del futuro,
los modelos estimados en modelos.py:
    1. Datos: variable objetivo, predictores y meses de evaluación (2022 en adelante).
    2. Walk-forward con ventana expansiva: en cada mes se re-estima cada modelo
       solo con los meses anteriores y se pronostica el mes siguiente (U4-02 a U4-06).
    3. Métricas: RMSE, MAE, R² fuera de muestra frente al paseo aleatorio (U2-05)
       y test de Clark-West (U4-03).
    4. Estabilidad: errores por subperíodo.
    5. Gráfico de pronósticos contra el dato real.

Requisito: haber corrido antes preparacion.py.
Uso desde la raíz del repositorio:
    python src/evaluacion.py
"""
import warnings

import matplotlib
matplotlib.use("Agg")               # guarda los gráficos sin abrir ventanas
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import norm
from sklearn.linear_model import LassoCV
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.arima.model import ARIMA

import config
import predictores

warnings.filterwarnings("ignore")  # avisos de convergencia de ARIMA y Lasso

# Estilo de gráficos del curso (el mismo de coyuntura.py)
plt.rcParams.update({'figure.dpi': 110, 'font.size': 10.5,
                     'axes.grid': True, 'grid.alpha': 0.3,
                     'axes.spines.top': False, 'axes.spines.right': False})

COLOR_UDP   = '#800020'
COLOR_TREND = '#1f77b4'
COLOR_GRAY  = '#7f7f7f'

RUTA_FIGURAS = config.RAIZ / "figuras"
RUTA_FIGURAS.mkdir(exist_ok=True)

FIN_ENTRENAMIENTO = "2021-12"      # el mismo corte de modelos.py


def guardar(fig, nombre):
    """Guarda un gráfico en figuras/ y cierra la figura."""
    fig.savefig(RUTA_FIGURAS / nombre, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Gráfico guardado: figuras/{nombre}")


def texto_p(p):
    """Un p-value nunca es cero: si es muy chico se informa como '< 0.001'."""
    return "< 0.001" if p < 0.001 else f"{p:.3f}"


# ------------------------------------------------------------
# Bloque 1: datos
# Las mismas transformaciones y predictores de modelos.py (predictores.py).
# Los meses de evaluación son 2022-01 en adelante: ningún modelo los vio
# al elegirse en modelos.py.
# ------------------------------------------------------------
base = pd.read_parquet(config.RUTA_DATOS / "base_mensual.parquet")
datos = predictores.transformar(base)

y = datos["dolar"].dropna()                       # variación % mensual del dólar
X_mco = predictores.matriz_mco(datos)             # 4 predictores elegidos con teoría
X_lasso = predictores.matriz_lasso(datos)         # 84 predictores (14 variables x 6 rezagos)

meses_eval = y.loc[pd.Timestamp(FIN_ENTRENAMIENTO) + pd.DateOffset(months=1):].index

print(f"Meses de evaluación: {meses_eval.min():%Y-%m} a {meses_eval.max():%Y-%m} "
      f"({len(meses_eval)} pronósticos por modelo)")


# ------------------------------------------------------------
# Bloque 2: walk-forward con ventana expansiva (U4-02 a U4-06)
# Para cada mes t de la evaluación:
#   1. se toman SOLO los datos anteriores a t,
#   2. se re-estima cada modelo con ellos,
#   3. se pronostica la variación del dólar en t,
#   4. se guarda el pronóstico junto al dato real.
# La ventana crece un mes cada vez (expansiva). Así cada pronóstico se hace
# como si estuviéramos en ese momento, sin mirar el futuro.
# Modelos:
#   - Paseo aleatorio (RW): el dólar no cambia -> variación pronosticada = 0 (U2-05).
#   - Media histórica: promedio de las variaciones pasadas = ARIMA(0,0,0), elegido por BIC.
#   - AR(1): ARIMA(1,0,0), elegido por AIC en modelos.py.
#   - MCO: dólar, balanza y cobre t-1 y bono a 10 años t-6 (camino econométrico).
#   - Lasso: 84 predictores; lambda elegido de nuevo en cada mes (camino de ciencia de datos).
# ------------------------------------------------------------
def pronostico_regresion(X, t):
    """Pronóstico de MCO para el mes t, estimado con los meses anteriores a t."""
    tabla = pd.concat([y, X], axis=1).dropna().loc[:t - pd.DateOffset(months=1)]
    modelo = sm.OLS(tabla["dolar"], sm.add_constant(tabla[X.columns])).fit()
    return float(modelo.params["const"] + modelo.params[X.columns] @ X.loc[t])


def pronostico_lasso(X, t):
    """Pronóstico de Lasso para el mes t, estimado con los meses anteriores a t."""
    tabla = pd.concat([y, X], axis=1).dropna().loc[:t - pd.DateOffset(months=1)]
    lasso = make_pipeline(StandardScaler(),
                          LassoCV(alphas=np.logspace(-3, 2, 50),
                                  cv=TimeSeriesSplit(n_splits=5), max_iter=20000))
    lasso.fit(tabla[X.columns], tabla["dolar"])
    return float(lasso.predict(X.loc[[t]])[0])


filas = []
for t in meses_eval:
    pasado = y.loc[:t - pd.DateOffset(months=1)]              # solo información disponible en t-1
    ar1 = ARIMA(pasado.to_numpy(), order=(1, 0, 0)).fit()
    filas.append({
        "mes": t,
        "real": y.loc[t],
        "Paseo aleatorio": 0.0,
        "Media histórica": pasado.mean(),
        "AR(1)": float(np.asarray(ar1.forecast(1))[0]),
        "MCO": pronostico_regresion(X_mco, t),
        "Lasso": pronostico_lasso(X_lasso, t),
    })

pronosticos = pd.DataFrame(filas).set_index("mes")
MODELOS = ["Paseo aleatorio", "Media histórica", "AR(1)", "MCO", "Lasso"]

print("\nÚltimos 6 pronósticos (variación % mensual del dólar):")
print(pronosticos.tail(6).round(2).to_string())



# ------------------------------------------------------------
# Bloque 3: métricas fuera de muestra
#   - RMSE y MAE: tamaño promedio del error (menor es mejor).
#   - R² fuera de muestra frente al paseo aleatorio (Campbell-Thompson, U2-05):
#       R²_OOS = 1 - suma(error del modelo²) / suma(error del RW²)
#     Positivo: el modelo pronostica mejor que "el dólar no cambia".
#     Negativo: pronostica peor.
#   - Test de Clark-West (U4-03): ¿la mejora frente al RW es significativa?
#     H0: el modelo no pronostica mejor que el RW. Es de una cola: solo
#     interesa si el modelo es MEJOR. Corrige el ruido que agrega estimar
#     parámetros, que perjudica a los modelos más grandes.
# ------------------------------------------------------------
def clark_west(real, pron_modelo, pron_rw):
    """Estadístico y p-value (una cola) del test de Clark-West."""
    f = (real - pron_rw) ** 2 - ((real - pron_modelo) ** 2 - (pron_rw - pron_modelo) ** 2)
    estadistico = f.mean() / (f.std(ddof=1) / np.sqrt(len(f)))
    return estadistico, 1 - norm.cdf(estadistico)


errores = pronosticos[MODELOS].rsub(pronosticos["real"], axis=0)   # real - pronóstico
sce_rw = (errores["Paseo aleatorio"] ** 2).sum()

metricas = []
for m in MODELOS:
    fila = {"modelo": m,
            "RMSE": np.sqrt((errores[m] ** 2).mean()),
            "MAE": errores[m].abs().mean(),
            "R² OOS vs RW (%)": 100 * (1 - (errores[m] ** 2).sum() / sce_rw)}
    if m == "Paseo aleatorio":
        fila.update({"Clark-West": np.nan, "p-value CW": ""})
    else:
        cw, p = clark_west(pronosticos["real"], pronosticos[m], pronosticos["Paseo aleatorio"])
        fila.update({"Clark-West": cw, "p-value CW": texto_p(p)})
    metricas.append(fila)

tabla_metricas = pd.DataFrame(metricas).set_index("modelo")
print(f"\nMétricas fuera de muestra ({meses_eval.min():%Y-%m} a {meses_eval.max():%Y-%m}):")
print(tabla_metricas.round(3).to_string())

mejor = tabla_metricas["RMSE"].idxmin()
print(f"\nMenor RMSE: {mejor}")
ganan = [m for m in MODELOS[1:] if tabla_metricas.loc[m, "R² OOS vs RW (%)"] > 0]
if ganan:
    print("Modelos con R² OOS positivo (mejores que el paseo aleatorio): " + ", ".join(ganan))
else:
    print("Ningún modelo supera al paseo aleatorio: el dólar se comporta como un paseo aleatorio "
          "a un mes, resultado habitual en tipos de cambio.")


# ------------------------------------------------------------
# Bloque 4: estabilidad por subperíodo
# Un modelo puede ganar solo en un período (por ejemplo, un año de shocks).
# Se calcula el RMSE de cada modelo relativo al del RW en cada subperíodo:
# menor que 1 = mejor que el paseo aleatorio en ese tramo.
# ------------------------------------------------------------
SUBPERIODOS = {"2022": ("2022-01", "2022-12"),
               "2023-2024": ("2023-01", "2024-12"),
               "2025-2026": ("2025-01", "2026-12")}

relativo = {}
for nombre, (ini, fin) in SUBPERIODOS.items():
    tramo = errores.loc[ini:fin]
    rmse = np.sqrt((tramo ** 2).mean())
    relativo[f"{nombre} ({len(tramo)} m)"] = rmse / rmse["Paseo aleatorio"]

tabla_sub = pd.DataFrame(relativo)
print("\nRMSE relativo al paseo aleatorio por subperíodo (< 1 = mejor que el RW):")
print(tabla_sub.round(3).to_string())


# ------------------------------------------------------------
# Bloque 5: gráfico de pronósticos contra el dato real
# ------------------------------------------------------------
fig, ax = plt.subplots(figsize=(12, 4.5))
ax.plot(pronosticos.index, pronosticos["real"], color="black", lw=1.6, label="Dato real")
estilos = {"Media histórica": (COLOR_GRAY, "--"), "AR(1)": (COLOR_TREND, "-"),
           "MCO": (COLOR_UDP, "-"), "Lasso": ("#2ca02c", "-")}
for m, (color, linea) in estilos.items():
    ax.plot(pronosticos.index, pronosticos[m], color=color, ls=linea, lw=1.1, label=m)
ax.axhline(0, color="black", lw=0.6, ls=":", label="Paseo aleatorio (0)")
ax.set_title("Variación mensual del dólar: pronósticos a un mes fuera de muestra")
ax.set_ylabel("Variación % mensual")
ax.legend(ncol=3, fontsize=8.5, loc="upper right")
fig.text(0.01, -0.03, "Walk-forward con ventana expansiva desde 2012. "
         "Fuente: Banco Central de Chile, FRED y elaboración propia.",
         fontsize=8, color=COLOR_GRAY)
fig.tight_layout()
guardar(fig, "11_pronosticos_fuera_muestra.png")