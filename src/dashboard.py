"""
Dashboard del tipo de cambio USD/CLP (sección 4 de la guía del Hito 3).

Junta en una sola imagen lo que un comité necesita ver en pocos segundos:
    1. El dólar con su historia, el dato más reciente destacado y la
       proyección a 24 meses con sus bandas (frente al benchmark ingenuo).
    2. Un indicador derivado: la variación del dólar en 12 meses.
    3. La evaluación fuera de muestra: pronósticos de Lasso frente al
       paseo aleatorio (benchmark ingenuo) y el dato real.
    4. La tabla de métricas fuera de muestra.

La historia del dólar se lee directamente de la base SQL (consulta 8 de
sql/04_consultas_coyuntura.sql). Los pronósticos los generan evaluacion.py y
proyeccion.py, que los guardan en data/: no hay archivos editados a mano.

Requisito: haber corrido antes evaluacion.py y proyeccion.py.
Uso desde la raíz del repositorio:
    python src/dashboard.py
"""
import matplotlib
matplotlib.use("Agg")               # guarda el dashboard sin abrir ventanas
import matplotlib.pyplot as plt
import pandas as pd
from sqlalchemy import text

import carga_db
import config

# Estilo de gráficos del curso (el mismo de coyuntura.py)
plt.rcParams.update({'figure.dpi': 110, 'font.size': 10,
                     'axes.grid': True, 'grid.alpha': 0.3,
                     'axes.spines.top': False, 'axes.spines.right': False})

COLOR_UDP   = '#800020'
COLOR_TREND = '#1f77b4'
COLOR_GRAY  = '#7f7f7f'
COLOR_LASSO = '#2ca02c'

RUTA_FIGURAS = config.RAIZ / "figuras"
RUTA_FIGURAS.mkdir(exist_ok=True)


def leer_consultas(ruta):
    """Lee un archivo .sql y devuelve la lista de consultas (separadas por ';')."""
    contenido = open(ruta, encoding="utf-8").read()
    return [c.strip() for c in contenido.split(";") if c.strip()]


def miles(x):
    """Número con punto de miles, como se escribe en Chile (1.117)."""
    return f"{x:,.0f}".replace(",", ".")


# ------------------------------------------------------------
# Bloque 1: datos
# Historia del dólar desde la base SQL (consulta 8: dólar mensual y
# promedio de 12 meses). Pronósticos y métricas desde los archivos que
# generan evaluacion.py y proyeccion.py.
# ------------------------------------------------------------
engine = carga_db.obtener_engine()
consultas = leer_consultas(config.RUTA_SQL / "04_consultas_coyuntura.sql")
with engine.connect() as conn:
    dolar = pd.read_sql(text(consultas[1]), conn, parse_dates=["mes"], index_col="mes")   # consulta 8

dolar = dolar.loc[:"2026-09"]                       # misma fecha de corte que la carga
proyeccion = pd.read_csv(config.RUTA_DATOS / "proyeccion.csv", index_col=0, parse_dates=True)
pronosticos = pd.read_csv(config.RUTA_DATOS / "pronosticos_fuera_muestra.csv",
                          index_col=0, parse_dates=True)
metricas = pd.read_csv(config.RUTA_DATOS / "metricas_fuera_muestra.csv", index_col=0)

ultimo_mes = dolar.index[-1]
dolar_hoy = dolar["dolar"].iloc[-1]
var_12m = 100 * (dolar["dolar"] / dolar["dolar"].shift(12) - 1)    # indicador derivado
fin = proyeccion.index[-1]

print(f"Dólar desde SQL: {dolar.index[0]:%Y-%m} a {ultimo_mes:%Y-%m} | "
      f"proyección hasta {fin:%Y-%m}")


# ------------------------------------------------------------
# Bloque 2: armado del dashboard (2 filas)
# Arriba, el panel principal a lo ancho: historia + proyección.
# Abajo, tres paneles de apoyo: indicador derivado, evaluación y métricas.
# ------------------------------------------------------------
fig = plt.figure(figsize=(15, 9.5))
grilla = fig.add_gridspec(2, 3, height_ratios=[1.25, 1], hspace=0.38, wspace=0.28)

# Título con las cifras clave: lo primero que se lee
fig.suptitle("Dólar observado en Chile (CLP por USD): coyuntura y proyección a 24 meses",
             fontsize=15, fontweight="bold", x=0.01, ha="left", y=0.995)
fig.text(0.01, 0.945,
         f"Último dato ({ultimo_mes:%m-%Y}): {miles(dolar_hoy)}   |   "
         f"Variación en 12 meses: {var_12m.iloc[-1]:+.1f}%   |   "
         f"Proyección central a {fin:%m-%Y}: {miles(proyeccion['central'].iloc[-1])} "
         f"(80%: {miles(proyeccion['inf_80'].iloc[-1])} a {miles(proyeccion['sup_80'].iloc[-1])})",
         fontsize=11.5, color=COLOR_UDP)

# --- Panel 1: historia, dato más reciente y proyección con bandas ---
ax1 = fig.add_subplot(grilla[0, :])
historia = dolar.loc["2012":]
ax1.plot(historia.index, historia["dolar"], color="black", lw=1.4, label="Dólar observado (promedio mensual)")
ax1.plot(historia.index, historia["prom_12m"], color=COLOR_TREND, lw=1, ls="--", label="Promedio móvil 12 meses")

# Se une el último dato a la proyección para que las bandas no queden cortadas
union = pd.DataFrame({c: [dolar_hoy] for c in proyeccion.columns}, index=[ultimo_mes])
graf = pd.concat([union, proyeccion])
ax1.fill_between(graf.index, graf["inf_95"], graf["sup_95"], color=COLOR_UDP, alpha=0.12, label="Banda 95%")
ax1.fill_between(graf.index, graf["inf_80"], graf["sup_80"], color=COLOR_UDP, alpha=0.25, label="Banda 80%")
ax1.plot(graf.index, graf["central"], color=COLOR_UDP, lw=1.8,
         label="Proyección central = benchmark ingenuo (paseo aleatorio)")
ax1.plot(graf.index, graf["con_deriva"], color=COLOR_GRAY, lw=1.2, ls=":",
         label="Escenario con deriva histórica")

# Dato más reciente destacado
ax1.scatter([ultimo_mes], [dolar_hoy], s=70, color=COLOR_UDP, zorder=5)
ax1.annotate(f"{ultimo_mes:%m-%Y}: {miles(dolar_hoy)}", xy=(ultimo_mes, dolar_hoy),
             xytext=(-120, 35), textcoords="offset points", fontsize=10, fontweight="bold",
             color=COLOR_UDP, arrowprops=dict(arrowstyle="->", color=COLOR_UDP))
ax1.axvline(ultimo_mes, color=COLOR_GRAY, lw=0.8, ls=":")
ax1.set_title("1. El dólar frente a su historia y proyección a 24 meses", loc="left", fontsize=11.5)
ax1.set_ylabel("CLP por USD")
ax1.legend(fontsize=8.5, loc="upper left", ncol=2)

# --- Panel 2: indicador derivado (variación en 12 meses) ---
ax2 = fig.add_subplot(grilla[1, 0])
v = var_12m.loc["2012":].dropna()
ax2.bar(v.index, v, width=25, color=[COLOR_UDP if x > 0 else COLOR_TREND for x in v])
ax2.axhline(0, color="black", lw=0.6)
ax2.set_title("2. Variación del dólar en 12 meses (%)", loc="left", fontsize=11.5)
ax2.annotate(f"{v.iloc[-1]:+.1f}%", xy=(v.index[-1], v.iloc[-1]), xytext=(-25, 55),
             textcoords="offset points", fontsize=9.5, fontweight="bold",
             arrowprops=dict(arrowstyle="->", color="black"))
ax2.text(0.01, 0.02, "Rojo: el peso se deprecia | Azul: se aprecia", transform=ax2.transAxes,
         fontsize=8, color=COLOR_GRAY)

# --- Panel 3: evaluación fuera de muestra (Lasso vs. benchmark ingenuo) ---
ax3 = fig.add_subplot(grilla[1, 1])
ax3.plot(pronosticos.index, pronosticos["real"], color="black", lw=1.3, label="Dato real")
ax3.plot(pronosticos.index, pronosticos["Lasso"], color=COLOR_LASSO, lw=1.2, label="Lasso")
ax3.axhline(0, color=COLOR_UDP, lw=1.2, label="Paseo aleatorio (0)")
ax3.set_title("3. Pronóstico a 1 mes vs. dato real (var. %)", loc="left", fontsize=11.5)
ax3.legend(fontsize=8.5, loc="upper right")

# --- Panel 4: tabla de métricas fuera de muestra ---
ax4 = fig.add_subplot(grilla[1, 2])
ax4.axis("off")
filas = []
for modelo, fila in metricas.iterrows():
    r2 = "—" if modelo == "Paseo aleatorio" else f"{fila['R² OOS vs RW (%)']:+.1f}%"
    p = fila["p-value CW"]
    if pd.isna(p):
        p = "—"
    elif not isinstance(p, str):
        p = f"{p:.3f}"                              # el CSV lo lee como número
    filas.append([modelo, f"{fila['RMSE']:.3f}", f"{fila['MAE']:.3f}", r2, p])
tabla = ax4.table(cellText=filas, colLabels=["Modelo", "RMSE", "MAE", "R² OOS", "p (CW)"],
                  loc="upper center", cellLoc="center", colWidths=[0.34, 0.15, 0.15, 0.18, 0.18])
tabla.auto_set_font_size(False)
tabla.set_fontsize(9)
tabla.scale(1, 1.6)
mejor = metricas["RMSE"].idxmin()
for (i, j), celda in tabla.get_celld().items():
    if i == 0:
        celda.set_facecolor("#eeeeee")
        celda.set_text_props(fontweight="bold")
    elif filas[i - 1][0] == mejor:
        celda.set_text_props(fontweight="bold", color=COLOR_LASSO)
ax4.set_title(f"4. Métricas ({pronosticos.index[0]:%m-%Y} a {pronosticos.index[-1]:%m-%Y})",
              loc="left", fontsize=11.5)
ax4.text(0.0, 0.08, "Lasso es el único con R² OOS positivo, pero la mejora no es\n"
         "significativa (Clark-West p > 0,10). R² OOS: mejora frente al\n"
         "paseo aleatorio (RW). A 1 mes, el dólar se comporta\n"
         "como un paseo aleatorio. Por eso la proyección central es el benchmark.",
         transform=ax4.transAxes, fontsize=8.8, va="bottom")

fig.text(0.01, 0.005, "Fuente: Banco Central de Chile, FRED y Caldara e Iacoviello (GPR); elaboración propia. "
         "Proyección: ARIMA(0,1,0) sobre el log del dólar. Evaluación: walk-forward con ventana expansiva.",
         fontsize=8, color=COLOR_GRAY)

fig.savefig(RUTA_FIGURAS / "13_dashboard.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  Dashboard guardado: figuras/13_dashboard.png")