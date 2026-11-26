"""
Modelos de pronóstico de la variación mensual del dólar (sección 3.3c).

Estima, con la muestra de entrenamiento, los modelos que después se comparan
fuera de muestra en evaluacion.py:
    1. Datos: variación mensual del dólar y separación entrenamiento / evaluación.
    2. Estacionariedad (ADF): por qué se modela la variación y no el nivel (U2-03).
    3. ACF y PACF: cuánta memoria tiene el dólar (U2-03, U4-02).
    4. ARIMA: orden elegido por AIC y BIC, diagnóstico con Ljung-Box (U2-03).

Requisito: haber corrido antes preparacion.py.
Uso desde la raíz del repositorio:
    python src/modelos.py
"""
import itertools
import warnings

import matplotlib
matplotlib.use("Agg")              # guarda los gráficos sin abrir ventanas
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller

import config

warnings.filterwarnings("ignore")  # avisos de convergencia de ARIMA

# Estilo de gráficos del curso (el mismo de coyuntura.py)
plt.rcParams.update({'figure.dpi': 110, 'font.size': 10.5,
                     'axes.grid': True, 'grid.alpha': 0.3,
                     'axes.spines.top': False, 'axes.spines.right': False})

COLOR_UDP   = '#800020'
COLOR_TREND = '#1f77b4'
COLOR_GRAY  = '#7f7f7f'

RUTA_FIGURAS = config.RAIZ / "figuras"
RUTA_FIGURAS.mkdir(exist_ok=True)

FIN_ENTRENAMIENTO = "2021-12"      # entrenamiento: 2012-2021 | evaluación: 2022 en adelante


def guardar(fig, nombre):
    """Guarda un gráfico en figuras/ y cierra la figura."""
    fig.savefig(RUTA_FIGURAS / nombre, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Gráfico guardado: figuras/{nombre}")


# ------------------------------------------------------------
# Bloque 1: datos
# Variable objetivo: variación % mensual del dólar (100 x diferencia del log).
# Entrenamiento: 2012-2021, para estimar y elegir los modelos.
# Evaluación: 2022 en adelante, que los modelos NO ven al estimarse.
# Todas las decisiones de este archivo (orden del ARIMA, etc.) se toman solo
# con el entrenamiento, para no usar información del futuro.
# ------------------------------------------------------------
base = pd.read_parquet(config.RUTA_DATOS / "base_mensual.parquet")

dolar_nivel = np.log(base["dolar"])
dolar_var = (100 * dolar_nivel.diff()).dropna().rename("dolar_var")

train = dolar_var.loc[:FIN_ENTRENAMIENTO]
test = dolar_var.loc[pd.Timestamp(FIN_ENTRENAMIENTO) + pd.DateOffset(months=1):]

print(f"Variable objetivo: variación % mensual del dólar ({len(dolar_var)} meses)")
print(f"  - Entrenamiento: {train.index.min():%Y-%m} a {train.index.max():%Y-%m} ({len(train)} meses)")
print(f"  - Evaluación:    {test.index.min():%Y-%m} a {test.index.max():%Y-%m} ({len(test)} meses)")


# ------------------------------------------------------------
# Bloque 2: estacionariedad (test ADF, igual que en U2-03)
# H0: raíz unitaria (no estacionaria). Si p < 0,05 se rechaza: estacionaria.
# Se espera que el nivel del dólar NO sea estacionario y su variación SÍ.
# Esto justifica modelar la variación: con niveles, la regresión puede ser
# espuria (U2-05).
# ------------------------------------------------------------
def test_adf(serie, nombre):
    resultado = adfuller(serie.dropna(), autolag='AIC')
    conclusion = "ESTACIONARIA (rechaza H0)" if resultado[1] < 0.05 else "NO ESTACIONARIA (no rechaza H0)"
    # Un p-value nunca es cero: si es muy chico se informa como "< 0,001"
    p_texto = "< 0.001" if resultado[1] < 0.001 else f"{resultado[1]:.3f}"
    print(f"  {nombre:<32} estadístico = {resultado[0]:7.3f}   p-value = {p_texto}   -> {conclusion}")


print("\nTest ADF (entrenamiento):")
test_adf(dolar_nivel.loc[:FIN_ENTRENAMIENTO], "Dólar en nivel (log)")
test_adf(train, "Variación mensual del dólar")


# ------------------------------------------------------------
# Bloque 3: ACF y PACF de la variación del dólar
# Muestran cuánta memoria tiene el dólar. Barras fuera de la banda azul
# (95%) indican rezagos que podrían servir para el ARIMA. Si casi todas
# están dentro, el dólar casi no tiene memoria y la caminata aleatoria
# será difícil de superar.
# ------------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
plot_acf(train, lags=24, ax=axes[0], color=COLOR_UDP,
         title="ACF: variación mensual del dólar (2012-2021)")
plot_pacf(train, lags=24, ax=axes[1], color=COLOR_UDP, method="ywm",
          title="PACF: variación mensual del dólar (2012-2021)")
for ax in axes:
    ax.axhline(0, color="black", lw=0.5)
    ax.set_xlabel("Rezago (meses)")
fig.text(0.01, -0.03, "Banda sombreada: intervalo de 95%. Fuente: Banco Central de Chile.",
         fontsize=8, color=COLOR_GRAY)
fig.tight_layout()
guardar(fig, "10_acf_pacf_dolar.png")

print("\nAutocorrelación de la variación del dólar (entrenamiento):")
print("  " + "   ".join(f"rezago {k}: {train.autocorr(k):+.2f}" for k in (1, 2, 3, 12)))


# ------------------------------------------------------------
# Bloque 4: ARIMA (U2-03)
# Como la variación ya es estacionaria, se estima ARIMA(p, 0, q) sobre ella
# (equivale a ARIMA(p, 1, q) sobre el log del dólar). Se prueban p y q de 0 a 2
# y se elige por AIC y por BIC, solo con el entrenamiento.
# ARIMA(0,0,0) es "solo una constante": si gana, el dólar no tiene memoria útil.
# ------------------------------------------------------------
resultados = []
for p, q in itertools.product(range(3), range(3)):
    modelo = ARIMA(train, order=(p, 0, q)).fit()
    resultados.append({"orden": f"ARIMA({p},0,{q})", "p": p, "q": q,
                       "AIC": round(modelo.aic, 2), "BIC": round(modelo.bic, 2)})

tabla_arima = pd.DataFrame(resultados).sort_values("AIC").reset_index(drop=True)
print("\nModelos ARIMA candidatos (entrenamiento), ordenados por AIC:")
print(tabla_arima.to_string(index=False))

mejor_aic = tuple(tabla_arima.loc[tabla_arima["AIC"].idxmin(), ["p", "q"]].astype(int))
mejor_bic = tuple(tabla_arima.loc[tabla_arima["BIC"].idxmin(), ["p", "q"]].astype(int))
print(f"\nMejor por AIC: ARIMA({mejor_aic[0]},0,{mejor_aic[1]})   "
      f"Mejor por BIC: ARIMA({mejor_bic[0]},0,{mejor_bic[1]})")

# Coeficientes del AR(1) y del elegido por AIC
ar1 = ARIMA(train, order=(1, 0, 0)).fit()
elegido = ARIMA(train, order=(mejor_aic[0], 0, mejor_aic[1])).fit()
print(f"\nAR(1): phi_1 = {ar1.params['ar.L1']:.3f} (p-value {ar1.pvalues['ar.L1']:.3f})")
print(f"ARIMA({mejor_aic[0]},0,{mejor_aic[1]}) elegido por AIC, coeficientes:")
print(elegido.params.drop("sigma2").round(3).to_string())

# Diagnóstico: los residuos del modelo elegido deben ser ruido blanco
lb = acorr_ljungbox(elegido.resid, lags=[6, 12], return_df=True)
print(f"\nTest de Ljung-Box sobre los residuos del ARIMA({mejor_aic[0]},0,{mejor_aic[1]}):")
print(lb.round(4).to_string())
if (lb["lb_pvalue"] > 0.05).all():
    print("-> p > 0,05: residuos compatibles con ruido blanco (no queda memoria sin capturar).")
else:
    print("-> Hay estructura no capturada en algún rezago: revisar la especificación.")
