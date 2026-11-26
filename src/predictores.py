"""
Variables y rezagos que usan los modelos (modelos.py y evaluacion.py).

Las transformaciones son las mismas de relaciones.py: todo en variaciones,
para evitar regresiones espurias con series en niveles (U2-05).
Solo se usan rezagos (t-1, t-2, ...): para pronosticar el dólar de un mes
solo puede usarse información de meses anteriores.
"""
import numpy as np
import pandas as pd


def var_pct(serie):
    """Variación % mensual: 100 x diferencia del logaritmo."""
    return 100 * np.log(serie).diff()


def transformar(base):
    """Lleva las series de la base común a variaciones (como en relaciones.py)."""
    return pd.DataFrame({
        "dolar":        var_pct(base["dolar"]),                  # variable objetivo
        "cobre":        var_pct(base["cobre"]),
        "indice_dolar": var_pct(base["indice_dolar"]),
        "diferencial":  base["diferencial_tasas"].diff(),        # puntos porcentuales
        "tpm":          base["tpm"].diff(),
        "fed_funds":    base["fed_funds"].diff(),
        "ust10":        base["ust10"].diff(),
        "vix":          var_pct(base["vix"]),
        "gpr":          var_pct(base["gpr"]),
        "inflacion_cl": var_pct(base["ipc_cl"]),
        "imacec_12m":   100 * np.log(base["imacec"]).diff(12),
        "balanza":      base["balanza_comercial"],               # millones de USD
        "ied":          base["ied"],                             # millones de USD
        "ied_12m":      base["ied"].rolling(12).sum(),
    })


# Camino econométrico (MCO): las candidatas de relaciones.py, con el rezago
# en que anticipan al dólar con el signo esperado, más el propio rezago del
# dólar (componente autorregresiva, como en U2-05).
# nombre: (variable, rezago, signo esperado)
VARIABLES_MCO = {
    "dolar_l1":   ("dolar", 1, "+"),
    "balanza_l1": ("balanza", 1, "-"),
    "cobre_l1":   ("cobre", 1, "-"),
    "ust10_l6":   ("ust10", 6, "+"),
}


def matriz_mco(datos):
    """Predictores del MCO: cada variable con su rezago."""
    return pd.DataFrame({nombre: datos[var].shift(k) for nombre, (var, k, _) in VARIABLES_MCO.items()})


def matriz_lasso(datos, rezagos=range(1, 7)):
    """Camino de ciencia de datos: todas las variables con rezagos de 1 a 6 meses (como en U4-03)."""
    return pd.DataFrame({f"{col}_l{k}": datos[col].shift(k) for col in datos.columns for k in rezagos})