"""
Preparación de la base mensual del proyecto.

Lee la base ya llevada a frecuencia mensual en SQL (consulta 3 de
sql/03_consultas_proyecto.sql) y la deja lista para el análisis:
    1. Formato ancho: una columna por serie.
    2. Diagnóstico: primer dato, último dato y huecos de cada serie.
    3. Revisión de cambios de base en los índices (con gráfico).
    4. Período común y tratamiento de faltantes.
    5. Guarda la base en data/ (Parquet).

Requisito: haber corrido antes la carga de datos.
Uso desde la raíz del repositorio:
    python src/carga_db.py --hasta 2026-09-30
    python src/preparacion.py
"""
import matplotlib.pyplot as plt
import pandas as pd
from sqlalchemy import text

import carga_db
import config

# Estilo de gráficos del curso
plt.rcParams.update({'figure.dpi': 110, 'font.size': 10.5,
                     'axes.grid': True, 'grid.alpha': 0.3,
                     'axes.spines.top': False, 'axes.spines.right': False})

COLOR_UDP   = '#800020'   # serie principal
COLOR_ALERT = '#d62728'   # alertas
COLOR_GRAY  = '#7f7f7f'   # series de fondo

# Nombres cortos para trabajar (una columna por serie)
NOMBRES = {
    "F073.TCO.PRE.Z.D": "dolar",
    "F022.TPM.TIN.D001.NO.Z.D": "tpm",
    "F074.IPC.IND.Z.EP23.C.M": "ipc_cl",
    "F032.IMC.IND.Z.Z.EP18.Z.Z.0.M": "imacec",
    "F019.PPB.PRE.40.M": "cobre",
    "F034.ECUM.FLU.COCHILCO.Z.0.M": "export_cobre_ton",
    "F068.A.FLU.Z.0.S.N.Z.Z.Z.Z.6.0.T": "cuenta_corriente",
    "F068.B1.VAR.T0.0.S.N.Z.Z.Z.Z.6.0.M": "balanza_comercial",
    "F068.T6.STO.Z.IED.S.P.Z.T.Z.Z.6.0.M": "ied",
    "F051.BT02.FLU.C.D.CLP.M": "ingresos_fiscales",
    "F051.BT03.FLU.C.D.CLP.M": "gastos_fiscales",
    "FEDFUNDS": "fed_funds",
    "GS10": "ust10",
    "CPIAUCSL": "ipc_eeuu",
    "VIXCLS": "vix",
    "DTWEXBGS": "indice_dolar",
    "GPR": "gpr",
}


def leer_consultas(ruta):
    """Lee un archivo .sql y devuelve la lista de consultas (separadas por ';')."""
    contenido = open(ruta, encoding="utf-8").read()
    return [c.strip() for c in contenido.split(";") if c.strip()]


# ------------------------------------------------------------
# Bloque 1: leer la base mensual desde SQL y pasarla a formato ancho
# ------------------------------------------------------------
engine = carga_db.obtener_engine()
consultas = leer_consultas(config.RUTA_SQL / "03_consultas_proyecto.sql")

with engine.connect() as conn:
    largo = pd.read_sql(text(consultas[2]), conn, parse_dates=["mes"])   # consulta 3: series mensuales

mensual = (largo.pivot(index="mes", columns="id_serie", values="valor")
                .rename(columns=NOMBRES)
                .reindex(columns=list(NOMBRES.values()))      # mismo orden que el catálogo
                .rename_axis(index="fecha", columns=None))

print(f"Base mensual: {mensual.shape[0]} meses x {mensual.shape[1]} series")
print(mensual.tail())


# ------------------------------------------------------------
# Bloque 2: diagnóstico de cada serie
# ------------------------------------------------------------
def huecos_internos(serie):
    """Meses sin dato ENTRE el primer y el último dato de la serie."""
    return serie.loc[serie.first_valid_index():serie.last_valid_index()].isna().sum()

diagnostico = pd.DataFrame({
    'primer dato':     mensual.apply(lambda s: s.first_valid_index()),
    'último dato':     mensual.apply(lambda s: s.last_valid_index()),
    'meses con dato':  mensual.count(),
    'huecos internos': mensual.apply(huecos_internos),
})
print("\nDiagnóstico de las series:")
print(diagnostico)


# ------------------------------------------------------------
# Bloque 3: revisión de cambios de base en los índices
# Un cambio de base sin empalmar aparece como un salto de un mes a otro
# que no corresponde a ningún cambio real (ej. IPC de 134 a 101).
# ------------------------------------------------------------
INDICES = {
    'ipc_cl':       'IPC Chile (2023 = 100)',
    'imacec':       'Imacec (2018 = 100)',
    'ipc_eeuu':     'IPC EE.UU. (1982-84 = 100)',
    'indice_dolar': 'Índice dólar amplio (ene-2006 = 100)',
    'gpr':          'Riesgo geopolítico GPR',
}
UMBRAL = 15            # % de variación mensual que consideramos sospechosa
CAMBIO_CANASTA = '2024-01-01'   # último cambio de canasta del IPC (INE)

variacion_mm = mensual[list(INDICES)].pct_change(fill_method=None) * 100

saltos = variacion_mm[variacion_mm.abs() > UMBRAL].stack().dropna().round(1)
if saltos.empty:
    print(f"\nNingún índice tiene variaciones mensuales mayores a ±{UMBRAL}%.")
else:
    print(f"\nMeses con variaciones mayores a ±{UMBRAL}% (revisar si es un cambio de base):")
    print(saltos)

fig, axes = plt.subplots(len(INDICES), 2, figsize=(14, 3 * len(INDICES)), sharex=True)
for (ax1, ax2), (col, titulo) in zip(axes, INDICES.items()):
    # Izquierda: nivel del índice (un cambio de base se ve como un escalón)
    ax1.plot(mensual[col], color=COLOR_UDP, lw=2)
    ax1.axvline(pd.Timestamp(CAMBIO_CANASTA), color='black', ls='--', lw=1)
    ax1.set_title(titulo, fontweight='bold')

    # Derecha: variación mensual, con el umbral de alerta
    colores = [COLOR_ALERT if abs(v) > UMBRAL else COLOR_GRAY for v in variacion_mm[col].fillna(0)]
    ax2.bar(variacion_mm.index, variacion_mm[col], width=20, color=colores)
    ax2.axhline(UMBRAL, color=COLOR_ALERT, ls=':', lw=1)
    ax2.axhline(-UMBRAL, color=COLOR_ALERT, ls=':', lw=1)
    ax2.axhline(0, color='black', lw=0.8)
    ax2.axvline(pd.Timestamp(CAMBIO_CANASTA), color='black', ls='--', lw=1)
    ax2.set_title(f'{titulo}: variación m/m (%)', fontweight='bold')

fig.suptitle('Revisión de cambios de base (línea negra discontinua: cambio de canasta del IPC, ene-2024)',
             fontweight='bold', y=1.0)
plt.tight_layout()
plt.show()


# ------------------------------------------------------------
# Bloque 4: período común y datos faltantes
# ------------------------------------------------------------
# La cuenta corriente es trimestral: queda fuera del cálculo del período
# común y no se rellena (pendiente: pasarla a mensual).
PENDIENTES = ['cuenta_corriente']
MENSUALES = [c for c in mensual.columns if c not in PENDIENTES]

# El período común parte cuando empieza la última serie y termina cuando termina la primera
inicio = diagnostico.loc[MENSUALES, 'primer dato'].max()
fin    = diagnostico.loc[MENSUALES, 'último dato'].min()
print(f"\nPeríodo común: {inicio:%Y-%m} a {fin:%Y-%m}")
print(f"  - lo inicia:   {diagnostico.loc[MENSUALES, 'primer dato'].idxmax()}")
print(f"  - lo termina:  {diagnostico.loc[MENSUALES, 'último dato'].idxmin()}")

comun = mensual.loc[inicio:fin].copy()      # copia recortada; 'mensual' conserva toda la historia

# Faltantes dentro del período común: se arrastra el último dato conocido,
# como máximo 2 meses. No se interpola porque interpolar usa el dato siguiente
# (sesgo de anticipación al pronosticar).
faltantes_antes = comun[MENSUALES].isna().sum()
comun[MENSUALES] = comun[MENSUALES].ffill(limit=2)
faltantes_despues = comun[MENSUALES].isna().sum()

tratamiento = pd.DataFrame({
    'faltantes':      faltantes_antes,
    'rellenados':     faltantes_antes - faltantes_despues,
    'siguen vacíos':  faltantes_despues,
})
print("\nFaltantes dentro del período común:")
print(tratamiento[tratamiento['faltantes'] > 0] if tratamiento['faltantes'].any()
      else "  Ninguna serie tiene faltantes en el período común.")

if faltantes_despues.any():
    print("\nATENCIÓN: quedan huecos de más de 2 meses seguidos; revisar esas series a mano.")

print(f"\nBase común: {comun.shape[0]} meses x {comun.shape[1]} series")


# ------------------------------------------------------------
# Bloque 5: guardar la base preparada
# Se guarda en Parquet, como en U2-06, para leerla en el análisis sin
# repetir este proceso. Queda en data/, que no se sube a GitHub: cada
# integrante la genera corriendo este archivo.
# ------------------------------------------------------------
comun.to_parquet(config.RUTA_DATOS / 'base_mensual.parquet')       # período común, lista para analizar
mensual.to_parquet(config.RUTA_DATOS / 'mensual_completa.parquet') # toda la historia, sin recortar

print(f"\nGuardado en {config.RUTA_DATOS}:")
print("  - base_mensual.parquet      (período común)")
print("  - mensual_completa.parquet  (historia completa)")
