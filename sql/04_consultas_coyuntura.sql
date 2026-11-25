-- ============================================================
-- Consultas del Hito 3: coyuntura del tipo de cambio USD/CLP
-- Base: data/coyuntura.db (tablas temas, series, observaciones)
--
-- Continúan la numeración de sql/03_consultas_proyecto.sql.
-- Las lee src/coyuntura.py (separadas por punto y coma, por eso
-- los comentarios no deben llevar ese signo).
-- ============================================================


-- ------------------------------------------------------------
-- Consulta 7 (JOIN + GROUP BY + ventana): tipo de cambio real
-- TCR = dólar x IPC EE.UU. / IPC Chile, en índice promedio 2018 = 100.
-- Sube: el peso se deprecia en términos reales (Chile más barato).
-- Baja: el peso se aprecia en términos reales.
-- Solo meses con los tres datos (falta oct-2025 del IPC EE.UU.).
-- ------------------------------------------------------------
WITH mensual AS (
    SELECT id_serie,
           strftime('%Y-%m-01', fecha) AS mes,
           AVG(valor)                  AS valor
    FROM observaciones
    WHERE id_serie IN ('F073.TCO.PRE.Z.D',           -- dólar observado
                       'F074.IPC.IND.Z.EP23.C.M',    -- IPC Chile
                       'CPIAUCSL')                   -- IPC EE.UU.
    GROUP BY id_serie, mes
),
tres AS (
    SELECT d.mes,
           d.valor  AS dolar,
           cl.valor AS ipc_cl,
           us.valor AS ipc_eeuu,
           d.valor * us.valor / cl.valor AS tcr_bruto
    FROM mensual AS d
    JOIN mensual AS cl ON cl.mes = d.mes AND cl.id_serie = 'F074.IPC.IND.Z.EP23.C.M'
    JOIN mensual AS us ON us.mes = d.mes AND us.id_serie = 'CPIAUCSL'
    WHERE d.id_serie = 'F073.TCO.PRE.Z.D'
)
SELECT mes,
       ROUND(dolar, 2) AS dolar,
       ipc_cl,
       ipc_eeuu,
       ROUND(100.0 * tcr_bruto
             / AVG(CASE WHEN mes LIKE '2018%' THEN tcr_bruto END) OVER (), 2) AS tcr
FROM tres
ORDER BY mes;


-- ------------------------------------------------------------
-- Consulta 8 (ventana): dólar mensual, variación y rango de 12 meses
-- var_mensual: variación % frente al mes anterior.
-- prom_12m, min_12m, max_12m: promedio, mínimo y máximo de los
-- últimos 12 meses (solo cuando la ventana tiene 12 meses).
-- ------------------------------------------------------------
WITH dolar AS (
    SELECT strftime('%Y-%m-01', fecha) AS mes,
           AVG(valor)                  AS dolar
    FROM observaciones
    WHERE id_serie = 'F073.TCO.PRE.Z.D'
    GROUP BY mes
)
SELECT mes,
       ROUND(dolar, 2) AS dolar,
       ROUND(100.0 * (dolar / LAG(dolar, 1) OVER (ORDER BY mes) - 1), 2) AS var_mensual,
       CASE WHEN COUNT(*) OVER w = 12 THEN ROUND(AVG(dolar) OVER w, 2) END AS prom_12m,
       CASE WHEN COUNT(*) OVER w = 12 THEN ROUND(MIN(dolar) OVER w, 2) END AS min_12m,
       CASE WHEN COUNT(*) OVER w = 12 THEN ROUND(MAX(dolar) OVER w, 2) END AS max_12m
FROM dolar
WINDOW w AS (ORDER BY mes ROWS BETWEEN 11 PRECEDING AND CURRENT ROW)
ORDER BY mes;
