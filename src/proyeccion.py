"""
Proyección del dólar a 24 meses con bandas de incertidumbre (sección 3.4).

Usa el resultado de evaluacion.py: a un mes, ningún modelo supera de forma
significativa al paseo aleatorio. Por eso la proyección central es un paseo
aleatorio, estimado como ARIMA(0,1,0) sobre el log del dólar (U2-03):
    1. Datos: log del dólar con toda la muestra (2012 a hoy).
    2. Proyección central: ARIMA(0,1,0) y bandas de 80% y 95%.
    3. Escenario alternativo: paseo aleatorio con deriva (media histórica).
    4. Señal de corto plazo: pronóstico de Lasso para el próximo mes (U4-03).
    5. Gráfico de la proyección.

Requisito: haber corrido antes preparacion.py.
Uso desde la raíz del repositorio:
    python src/proyeccion.py
"""
import warnings

import matplotlib
matplotlib.use("Agg")               # guarda los gráficos sin abrir ventanas
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LassoCV
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.arima.model import ARIMA

import config
import predictores

warnings.filterwarnings("ignore")  # avisos de statsmodels y Lasso

# Estilo de gráficos del curso (el mismo de coyuntura.py)
plt.rcParams.update({'figure.dpi': 110, 'font.size': 10.5,
                     'axes.grid': True, 'grid.alpha': 0.3,
                     'axes.spines.top': False, 'axes.spines.right': False})

COLOR_UDP   = '#800020'
COLOR_TREND = '#1f77b4'
COLOR_GRAY  = '#7f7f7f'

RUTA_FIGURAS = config.RAIZ / "figuras"
RUTA_FIGURAS.mkdir(exist_ok=True)

HORIZONTE = 24                      # meses a proyectar


def guardar(fig, nombre):
    """Guarda un gráfico en figuras/ y cierra la figura."""
    fig.savefig(RUTA_FIGURAS / nombre, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Gráfico guardado: figuras/{nombre}")


# ------------------------------------------------------------
# Bloque 1: datos
# Ahora se usa TODA la muestra: ya no se evalúa, se proyecta el futuro real.
# Se trabaja con el log del dólar para que las bandas sean porcentuales
# y el dólar proyectado nunca sea negativo.
# ------------------------------------------------------------
base = pd.read_parquet(config.RUTA_DATOS / "base_mensual.parquet")

log_dolar = np.log(base["dolar"]).dropna().asfreq("MS")    # frecuencia mensual (inicio de mes)
ultimo_mes = log_dolar.index[-1]
dolar_hoy = np.exp(log_dolar.iloc[-1])

print(f"Dólar observado: {log_dolar.index[0]:%Y-%m} a {ultimo_mes:%Y-%m} ({len(log_dolar)} meses)")
print(f"Último dato ({ultimo_mes:%Y-%m}): {dolar_hoy:.1f} pesos por dólar")


# ------------------------------------------------------------
# Bloque 2: proyección central con ARIMA(0,1,0) = paseo aleatorio (U2-03)
# El ARIMA(0,1,0) dice que el cambio mensual del log del dólar es ruido:
#   log(dólar_t) = log(dólar_t-1) + error
# El mejor pronóstico es el último valor y la incertidumbre crece con la
# raíz del horizonte: a 24 meses es ~4,9 veces la de un mes (raíz de 24).
# Las bandas de 80% y 95% salen de get_forecast().conf_int().
# Se vuelve a pesos con la exponencial (el centro es la mediana).
# ------------------------------------------------------------
rw = ARIMA(log_dolar, order=(0, 1, 0)).fit()
pron_rw = rw.get_forecast(HORIZONTE)

proyeccion = pd.DataFrame({
    "central": np.exp(pron_rw.predicted_mean),
    "inf_95": np.exp(pron_rw.conf_int(alpha=0.05).iloc[:, 0]),
    "inf_80": np.exp(pron_rw.conf_int(alpha=0.20).iloc[:, 0]),
    "sup_80": np.exp(pron_rw.conf_int(alpha=0.20).iloc[:, 1]),
    "sup_95": np.exp(pron_rw.conf_int(alpha=0.05).iloc[:, 1]),
})

vol_mensual = 100 * np.sqrt(rw.params["sigma2"])
print(f"\nARIMA(0,1,0): volatilidad mensual estimada = {vol_mensual:.2f}% "
      f"(a 24 meses: {vol_mensual * np.sqrt(HORIZONTE):.1f}%)")


# ------------------------------------------------------------
# Bloque 3: escenario alternativo con deriva (media histórica)
# Mismo modelo, pero con una tendencia: el promedio de las variaciones
# mensuales de 2012-2026. Es la "media histórica" de evaluacion.py llevada
# a 24 meses: qué pasaría si el peso siguiera depreciándose a su ritmo
# histórico. En la evaluación no le ganó al paseo aleatorio, por eso es un
# escenario y no la proyección central.
# ------------------------------------------------------------
con_deriva = ARIMA(log_dolar, order=(0, 1, 0), trend="t").fit()
pron_deriva = con_deriva.get_forecast(HORIZONTE)
proyeccion["con_deriva"] = np.exp(pron_deriva.predicted_mean)

deriva = 100 * (pron_deriva.predicted_mean.iloc[0] - log_dolar.iloc[-1])
print(f"Deriva histórica: {deriva:+.2f}% mensual")

hitos = [pd.Timestamp(m) for m in ["2026-12-01", "2027-06-01", "2027-12-01", "2028-06-01"]]
hitos = [m for m in hitos if m in proyeccion.index] + [proyeccion.index[-1]]
tabla = proyeccion.loc[hitos].round(0)
tabla.index = tabla.index.strftime("%Y-%m")
print("\nProyección del dólar (pesos por dólar):")
print(tabla.to_string())
print("  central: paseo aleatorio | inf/sup_80 y inf/sup_95: bandas de 80% y 95% | "
      "con_deriva: escenario con la tendencia histórica")



# ------------------------------------------------------------
# Bloque 4: señal de corto plazo de Lasso (U4-03)
# Lasso fue el único modelo con R² fuera de muestra positivo, aunque no
# significativo. Solo puede pronosticar el próximo mes, porque usa datos ya
# observados (rezagos). No sirve para 24 meses: para eso habría que
# pronosticar también la balanza, el cobre, etc. Se informa como señal.
# ------------------------------------------------------------
proximo_mes = ultimo_mes + pd.DateOffset(months=1)
datos = predictores.transformar(base)
datos = datos.reindex(datos.index.append(pd.DatetimeIndex([proximo_mes])))   # agrega el mes a pronosticar
X_lasso = predictores.matriz_lasso(datos)

tabla_lasso = pd.concat([datos["dolar"], X_lasso], axis=1).dropna()
lasso = make_pipeline(StandardScaler(),
                      LassoCV(alphas=np.logspace(-3, 2, 50),
                              cv=TimeSeriesSplit(n_splits=5), max_iter=20000))
lasso.fit(tabla_lasso[X_lasso.columns], tabla_lasso["dolar"])

if X_lasso.loc[[proximo_mes]].isna().any(axis=None):
    print(f"\nLasso: faltan datos para pronosticar {proximo_mes:%Y-%m}.")
else:
    senal = float(lasso.predict(X_lasso.loc[[proximo_mes]])[0])
    print(f"\nSeñal de Lasso para {proximo_mes:%Y-%m}: variación de {senal:+.2f}% "
          f"(dólar ≈ {dolar_hoy * np.exp(senal / 100):.0f})")
    inf, sup = proyeccion["inf_80"].iloc[0], proyeccion["sup_80"].iloc[0]
    dentro = inf <= dolar_hoy * np.exp(senal / 100) <= sup
    print(f"  Banda de 80% del paseo aleatorio para ese mes: {inf:.0f} a {sup:.0f} -> "
          + ("la señal queda dentro: es un sesgo, no un cambio de escenario."
             if dentro else "la señal queda fuera: revisar los fundamentales de ese mes."))


# ------------------------------------------------------------
# Bloque 5: gráfico de la proyección
# Historia desde 2018, proyección central, bandas de 80% y 95% y el
# escenario con deriva.
# ------------------------------------------------------------
historia = np.exp(log_dolar.loc["2018":])
# Se une el último dato a la proyección para que las líneas no queden cortadas
union = pd.DataFrame({c: [dolar_hoy] for c in proyeccion.columns}, index=[ultimo_mes])
graf = pd.concat([union, proyeccion])

fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(historia.index, historia, color="black", lw=1.5, label="Dólar observado")
ax.fill_between(graf.index, graf["inf_95"], graf["sup_95"], color=COLOR_UDP, alpha=0.12,
                label="Banda 95%")
ax.fill_between(graf.index, graf["inf_80"], graf["sup_80"], color=COLOR_UDP, alpha=0.25,
                label="Banda 80%")
ax.plot(graf.index, graf["central"], color=COLOR_UDP, lw=1.8, label="Proyección central (paseo aleatorio)")
ax.plot(graf.index, graf["con_deriva"], color=COLOR_TREND, lw=1.3, ls="--",
        label="Escenario con deriva histórica")
ax.axvline(ultimo_mes, color=COLOR_GRAY, lw=0.8, ls=":")
ax.set_title(f"Dólar observado y proyección a {HORIZONTE} meses (pesos por dólar)")
ax.set_ylabel("Pesos por dólar")
ax.legend(fontsize=8.5, loc="upper left")
fig.text(0.01, -0.03, "Proyección: ARIMA(0,1,0) sobre el log del dólar, muestra 2012-2026. "
         "Fuente: Banco Central de Chile y elaboración propia.", fontsize=8, color=COLOR_GRAY)
fig.tight_layout()
guardar(fig, "12_proyeccion_dolar.png")


# ------------------------------------------------------------
# Bloque 6: guardar la proyección para el dashboard
# Se guarda en data/ (no se sube a GitHub: se regenera con el código).
# ------------------------------------------------------------
proyeccion.to_csv(config.RUTA_DATOS / "proyeccion.csv")
print("  Proyección guardada en data/proyeccion.csv (la usa dashboard.py)")