-- ============================================================
-- Consultas del proyecto: tipo de cambio USD/CLP
-- Base: data/coyuntura.db (tablas temas, series, observaciones)
--
-- Las consultas 1 y 2 revisan la base. Las consultas 3 a 6 preparan
-- los datos para el análisis: frecuencia mensual, variaciones,
-- balance fiscal y diferencial de tasas.
-- ============================================================


-- ------------------------------------------------------------
-- Consulta 1 (JOIN + GROUP BY): revisión de la base
-- Para cada tema y serie: cuántos datos hay, desde y hasta cuándo.
-- n_obs = 0 indica una extracción fallida, un desde reciente indica
-- historia insuficiente y un hasta antiguo una serie descontinuada.
-- ------------------------------------------------------------
SELECT t.tema,
       s.nombre,
       s.frecuencia,
       COUNT(o.valor) AS n_obs,
       MIN(o.fecha)   AS desde,
       MAX(o.fecha)   AS hasta
FROM temas AS t
LEFT JOIN series AS s        ON s.id_tema  = t.id_tema
LEFT JOIN observaciones AS o ON o.id_serie = s.id_serie
GROUP BY t.tema, s.nombre, s.frecuencia
ORDER BY t.tema, n_obs;


-- ------------------------------------------------------------
-- Consulta 2 (GROUP BY): meses faltantes dentro del período
-- Compara los meses que deberían tener dato (entre la primera y la
-- última fecha) con los meses que realmente tienen dato.
-- faltantes = 0 significa que la serie no tiene huecos.
-- La cuenta corriente queda fuera porque es trimestral.
-- ------------------------------------------------------------
WITH meses AS (
    SELECT id_serie,
           strftime('%Y-%m', fecha) AS mes
    FROM observaciones
    GROUP BY id_serie, mes
)
SELECT s.nombre,
       s.frecuencia,
       MIN(m.mes) AS desde,
       MAX(m.mes) AS hasta,
       COUNT(*)   AS meses_con_dato,
       (CAST(strftime('%Y', MAX(m.mes) || '-01') AS INTEGER)
          - CAST(strftime('%Y', MIN(m.mes) || '-01') AS INTEGER)) * 12
     + (CAST(strftime('%m', MAX(m.mes) || '-01') AS INTEGER)
          - CAST(strftime('%m', MIN(m.mes) || '-01') AS INTEGER)) + 1
       - COUNT(*) AS faltantes
FROM meses AS m
JOIN series AS s ON s.id_serie = m.id_serie
WHERE s.frecuencia IN ('D', 'M')
GROUP BY s.nombre, s.frecuencia
ORDER BY faltantes DESC, s.nombre;


-- ------------------------------------------------------------
-- Consulta 3 (JOIN + GROUP BY): todas las series en frecuencia mensual
-- Las series diarias (dólar, TPM, VIX, índice dólar) se llevan a
-- promedio del mes. Las mensuales quedan igual (un solo dato por mes).
-- La cuenta corriente queda con un dato por trimestre.
-- ------------------------------------------------------------
SELECT s.id_serie,
       s.nombre,
       s.frecuencia                      AS frecuencia_original,
       strftime('%Y-%m-01', o.fecha)     AS mes,
       ROUND(AVG(o.valor), 4)            AS valor,
       COUNT(*)                          AS n_datos_en_el_mes
FROM observaciones AS o
JOIN series AS s ON s.id_serie = o.id_serie
GROUP BY s.id_serie, s.nombre, s.frecuencia, mes
ORDER BY s.nombre, mes;


-- ------------------------------------------------------------
-- Consulta 4 (función de ventana): cambio en 12 meses de cada serie
-- Primero lleva todo a mensual (bloque WITH) y después compara cada
-- mes con el mismo mes del año anterior, DENTRO de cada serie
-- (PARTITION BY) y en orden temporal (ORDER BY mes).
--   - Tasas (% anual): diferencia en puntos porcentuales.
--   - Resto: variación porcentual.
-- Supuesto: la serie no tiene meses faltantes (ver consulta 2), porque
-- LAG(valor, 12) retrocede 12 filas, no 12 meses.
-- ------------------------------------------------------------
WITH mensual AS (
    SELECT o.id_serie,
           strftime('%Y-%m-01', o.fecha) AS mes,
           AVG(o.valor)                  AS valor
    FROM observaciones AS o
    GROUP BY o.id_serie, mes
)
SELECT s.nombre,
       s.unidad,
       m.mes,
       ROUND(m.valor, 4) AS valor,
       CASE
           WHEN s.unidad = '% anual'
               THEN ROUND(m.valor - LAG(m.valor, 12) OVER (
                        PARTITION BY m.id_serie ORDER BY m.mes), 2)
           ELSE ROUND(100.0 * (m.valor / LAG(m.valor, 12) OVER (
                        PARTITION BY m.id_serie ORDER BY m.mes) - 1), 2)
       END AS cambio_12m
FROM mensual AS m
JOIN series AS s ON s.id_serie = m.id_serie
WHERE s.frecuencia IN ('D', 'M')
ORDER BY s.nombre, m.mes;


-- ------------------------------------------------------------
-- Consulta 5 (GROUP BY + función de ventana): balance fiscal
-- Balance mensual = ingresos - gastos del Gobierno Central.
-- Como los flujos fiscales son muy estacionales (diciembre concentra
-- gasto), se agrega el balance acumulado en 12 meses.
-- Unidad: millones de pesos nominales.
-- ------------------------------------------------------------
WITH fiscal AS (
    SELECT fecha,
           SUM(CASE WHEN id_serie = 'F051.BT02.FLU.C.D.CLP.M' THEN valor END) AS ingresos,
           SUM(CASE WHEN id_serie = 'F051.BT03.FLU.C.D.CLP.M' THEN valor END) AS gastos
    FROM observaciones
    WHERE id_serie IN ('F051.BT02.FLU.C.D.CLP.M', 'F051.BT03.FLU.C.D.CLP.M')
    GROUP BY fecha
    HAVING ingresos IS NOT NULL AND gastos IS NOT NULL
)
SELECT fecha,
       ingresos,
       gastos,
       ingresos - gastos AS balance_mensual,
       -- solo se calcula cuando hay 12 meses completos hacia atrás
       CASE
           WHEN COUNT(*) OVER (ORDER BY fecha ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) = 12
               THEN SUM(ingresos - gastos) OVER (
                        ORDER BY fecha ROWS BETWEEN 11 PRECEDING AND CURRENT ROW)
       END AS balance_12m
FROM fiscal
ORDER BY fecha;


-- ------------------------------------------------------------
-- Consulta 6 (GROUP BY): diferencial de tasas Chile - EE.UU.
-- Mecanismo de paridad de tasas (UIP): TPM promedio del mes menos
-- la tasa Fed Funds, en puntos porcentuales.
-- ------------------------------------------------------------
WITH tasas AS (
    SELECT strftime('%Y-%m-01', fecha) AS mes,
           AVG(CASE WHEN id_serie = 'F022.TPM.TIN.D001.NO.Z.D' THEN valor END) AS tpm,
           AVG(CASE WHEN id_serie = 'FEDFUNDS'                 THEN valor END) AS fed_funds
    FROM observaciones
    WHERE id_serie IN ('F022.TPM.TIN.D001.NO.Z.D', 'FEDFUNDS')
    GROUP BY mes
)
SELECT mes,
       ROUND(tpm, 2)             AS tpm,
       ROUND(fed_funds, 2)       AS fed_funds,
       ROUND(tpm - fed_funds, 2) AS diferencial_tasas
FROM tasas
WHERE tpm IS NOT NULL AND fed_funds IS NOT NULL
ORDER BY mes
