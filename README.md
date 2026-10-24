# Monitor de Coyuntura y Proyección del Tipo de Cambio USD/CLP

**Ciencia de Datos para Economía (ICO09425) — Trabajo Semestral por Equipos — UDP**

## 1. Descripción

**Variable objetivo:** tipo de cambio nominal peso/dólar (dólar observado, CLP por USD), en promedio mensual.

**Pregunta de proyección:** ¿cuál será la trayectoria del tipo de cambio peso/dólar en Chile durante 2026–2028, considerando el diferencial de tasas de interés entre Chile y Estados Unidos, el precio del cobre, los flujos de capital y el contexto de riesgo internacional?

**Horizonte:** 24 meses.

**Integrantes:** Lukas Arriaza, Felipe Alviña, Javier Vidal, Matías Vidal.

## 2. Requisitos

- Python 3.12 o 3.13.
- Librerías del proyecto, listadas en `requirements.txt`.

Desde la raíz del repositorio:

```bash
py -3.13 -m venv .venv                      # crear el entorno virtual (una vez)
source .venv/Scripts/activate               # activarlo (cada vez que se abre una terminal)
python -m pip install -r requirements.txt   # instalar las librerías (una vez)
```

Si el comando `py` no existe, usar `python -m venv .venv`.

## 3. Credenciales

Las claves de las APIs se leen desde un archivo `.env` que **no se sube al repositorio** (está excluido en `.gitignore`).

1. Copiar `.env.example` y renombrar la copia como `.env`.
2. Completar con las credenciales propias de cada integrante:
   - `BCCH_USUARIO` y `BCCH_PASSWORD`: registro gratuito en https://si3.bcentral.cl/Siete/es/Siete/API
   - `FRED_API_KEY`: clave gratuita en https://fred.stlouisfed.org/docs/api/api_key.html

El índice de riesgo geopolítico (GPR) no requiere credenciales.

## 4. Reproducción

Desde la raíz del repositorio, con el entorno activo:

```bash
python src/carga_db.py --hasta 2026-09-30
python src/preparacion.py
```

**Fecha de corte: 30 de septiembre de 2026.** Fijarla hace que todos los integrantes obtengan exactamente la misma base, aunque corran la carga en días distintos.

1. `carga_db.py` descarga las 17 series desde las APIs y las carga en `data/coyuntura.db`. Debe terminar con 17 líneas `[OK]` y ninguna `[ERROR]`.
2. `preparacion.py` lee la base mediante las consultas de `sql/03_consultas_proyecto.sql`, revisa las series y guarda la base mensual preparada en `data/base_mensual.parquet`.

**Verificación de datos reales.** La base debe cargarse sin la opción `--demo`. Si la TPM aparece con valores cercanos o superiores a 100, la base contiene datos sintéticos del modo demo: borrar `data/coyuntura.db` y volver a correr la carga.

La carpeta `data/` (base de datos y archivos Parquet) existe solo en el computador de cada integrante y no se sube al repositorio.

## 5. Estructura del repositorio

```
├── README.md
├── requirements.txt
├── .env.example                  <- plantilla de credenciales (sin claves)
├── .gitignore
├── src/
│   ├── config.py                 <- catálogo de series y rutas del proyecto
│   ├── extraccion.py             <- descarga desde BCCh, FRED y GPR
│   ├── carga_db.py               <- crea la base y carga las series
│   ├── preparacion.py            <- revisión y preparación de la base mensual
│   └── exportar_powerbi.py       <- vista para Power BI (kit del curso)
├── sql/
│   ├── 01_esquema.sql            <- estructura de la base (3 tablas)
│   ├── 02_consultas_ejemplo.sql  <- consultas de ejemplo del kit
│   └── 03_consultas_proyecto.sql <- consultas propias del proyecto
├── notebooks/                    <- material de clases
├── dashboard/                    <- instrucciones para Power BI
└── data/                         <- base local (no se sube a GitHub)
```

El proyecto parte del kit de inicio del curso. Sobre el kit se agregaron: el catálogo propio de series, la fuente externa GPR (`extraccion.py` y `carga_db.py`), el tema Fiscal en el esquema, las consultas propias y el script de preparación.

## 6. Catálogo de series

Signo esperado sobre el dólar: (+) deprecia el peso; (−) aprecia el peso.

| Serie | Código | Fuente | Frec. | Rol | Mecanismo y signo esperado |
|:---|:---|:---|:---:|:---|:---|
| Tipo de cambio observado | `F073.TCO.PRE.Z.D` | BCCh | D | Objetivo | — |
| TPM | `F022.TPM.TIN.D001.NO.Z.D` | BCCh | D | Explicativa | Paridad de tasas: una TPM más alta atrae capitales (−) |
| IPC Chile (2023 = 100) | `F074.IPC.IND.Z.EP23.C.M` | BCCh | M | Explicativa | Paridad de poder de compra: más inflación en Chile (+) |
| Imacec (2018 = 100) | `F032.IMC.IND.Z.Z.EP18.Z.Z.0.M` | BCCh | M | Explicativa | Ciclo y productividad: mayor actividad relativa (−) |
| Precio del cobre | `F019.PPB.PRE.40.M` | BCCh | M | Explicativa | Commodity currency: cobre más caro trae dólares (−) |
| Exportaciones de cobre (volumen) | `F034.ECUM.FLU.COCHILCO.Z.0.M` | BCCh | M | Explicativa | Más cobre exportado aumenta la oferta de dólares (−) |
| Cuenta corriente | `F068.A.FLU.Z.0.S.N.Z.Z.Z.Z.6.0.T` | BCCh | T | Explicativa | Un déficit mayor exige financiamiento externo (+) |
| Balanza comercial | `F068.B1.VAR.T0.0.S.N.Z.Z.Z.Z.6.0.M` | BCCh | M | Explicativa | Más exportaciones netas aumentan la oferta de dólares (−) |
| Inversión extranjera directa | `F068.T6.STO.Z.IED.S.P.Z.T.Z.Z.6.0.M` | BCCh | M | Explicativa | Balance de portafolio: entradas de inversión demandan pesos (−) |
| Ingresos Gobierno Central | `F051.BT02.FLU.C.D.CLP.M` | BCCh (Dipres) | M | Explicativa | Con los gastos forma el balance fiscal |
| Gastos Gobierno Central | `F051.BT03.FLU.C.D.CLP.M` | BCCh (Dipres) | M | Explicativa | Mundell-Fleming: signo ambiguo |
| Tasa Fed Funds | `FEDFUNDS` | FRED | M | Explicativa | Alzas de la Fed generan salidas de capital (+) |
| Tesoro EE.UU. 10 años | `GS10` | FRED | M | Explicativa | Mayor rendimiento en EE.UU. atrae capitales (+) |
| IPC EE.UU. | `CPIAUCSL` | FRED | M | Explicativa | Contraparte del diferencial de inflación (−) |
| VIX | `VIXCLS` | FRED | D | Explicativa | Aversión al riesgo: el dólar actúa como refugio (+) |
| Índice dólar amplio | `DTWEXBGS` | FRED | D | Explicativa | Fortaleza global del dólar (+) |
| Riesgo geopolítico (GPR) | `GPR` | Caldara e Iacoviello | M | Explicativa | Fuga de capitales desde emergentes (+) |

Notas:
- El Hito 1 mencionaba el índice DXY. Ese índice es de ICE y no está en FRED; se usa en su lugar el índice dólar amplio de la Reserva Federal (`DTWEXBGS`), que cubre más monedas.
- Los datos fiscales provienen de la Dipres y se descargan desde la base del Banco Central, por lo que no requieren una fuente adicional.
- El GPR se descarga directamente desde el archivo público de los autores: https://www.matteoiacoviello.com/gpr.htm

## 7. Base de datos

Base SQLite (`data/coyuntura.db`) con tres tablas relacionadas, definidas en `sql/01_esquema.sql`:

| Tabla | Contenido | Llaves |
|:---|:---|:---|
| `temas` | Grupos temáticos (Actividad, Precios, Política monetaria, Sector externo, Internacional, Fiscal) | Primaria: `id_tema` |
| `series` | Catálogo: código, nombre, fuente, frecuencia, unidad y tema | Primaria: `id_serie`; foránea: `id_tema` |
| `observaciones` | Un valor por serie y fecha | Primaria: (`id_serie`, `fecha`); foránea: `id_serie` |

La llave primaria de `observaciones` impide que una serie tenga dos valores en la misma fecha. La base guarda los datos tal como vienen de las APIs; las transformaciones se hacen en las consultas y en `preparacion.py`, sin modificar los datos originales.

## 8. Consultas SQL

Archivo `sql/03_consultas_proyecto.sql`:

| # | Qué calcula | Técnica |
|:---:|:---|:---|
| 1 | Revisión: observaciones, primer y último dato de cada serie | JOIN + GROUP BY |
| 2 | Meses faltantes dentro del período de cada serie | GROUP BY |
| 3 | Todas las series en frecuencia mensual (promedio del mes) | JOIN + GROUP BY |
| 4 | Cambio en 12 meses: diferencia en puntos para tasas, variación % para el resto | Función de ventana (`LAG` con `PARTITION BY`) |
| 5 | Balance fiscal (ingresos − gastos) y su acumulado en 12 meses | GROUP BY + función de ventana |
| 6 | Diferencial de tasas TPM − Fed Funds | GROUP BY |

Las funciones de ventana se calculan dentro de cada serie (`PARTITION BY`) y en orden temporal (`ORDER BY`), sobre series ya llevadas a frecuencia mensual. `LAG(valor, 12)` retrocede 12 filas, no 12 meses: el resultado es correcto solo si la serie no tiene meses faltantes (lo revisa la consulta 2).

## 9. Decisiones de procesamiento

- **Manejo de errores en la carga.** Si una serie falla (código equivocado o API caída), `carga_db.py` informa `[ERROR]` con el motivo y continúa con las demás. Hay que contar los `[OK]`.
- **Datos faltantes en la descarga.** Los días sin dato (fines de semana y feriados en las series diarias) no se guardan en la base.
- **Diario a mensual.** Las series diarias (dólar, TPM, VIX, índice dólar) se llevan a promedio del mes en SQL (consulta 3).
- **Diagnóstico de faltantes.** Se cuentan solo los meses vacíos entre el primer y el último dato de cada serie ("huecos internos"). Un `isna().sum()` sobre la tabla completa contaría como faltantes los meses anteriores al inicio de una serie, que no son datos perdidos.
- **Período común.** Va desde el primer mes en que todas las series mensuales tienen dato hasta el último mes en que todas lo tienen. `preparacion.py` informa qué serie fija cada extremo. La cuenta corriente (trimestral) queda fuera de este cálculo.
- **Faltantes dentro del período común.** Se rellenan arrastrando el último dato conocido (`ffill`), hasta 2 meses seguidos. No se interpola, porque la interpolación usa el dato siguiente y eso introduce sesgo de anticipación al pronosticar. Si un hueco es más largo, el script lo informa para revisarlo a mano.
- **Cambios de base.** El IPC de Chile (`...EP23...`) es la serie empalmada oficial del Banco Central (base 2023 = 100) y el Imacec (`...EP18...`) viene con año de referencia 2018. `preparacion.py` revisa todos los índices y grafica su nivel y su variación mensual, marcando cualquier variación mayor a ±15% para verificar que no sea un cambio de base sin empalmar. El GPR es un solo índice, sin cambios de base.

## 10. Pendientes y limitaciones

- **Cuenta corriente.** Es trimestral. Queda pendiente llevarla a frecuencia mensual; la opción prevista es repartir el valor de cada trimestre en partes iguales entre sus tres meses, para respetar el total trimestral.
- **Valores nominales.** Los ingresos y gastos fiscales están en millones de pesos nominales. Queda pendiente deflactarlos por el IPC.
- **Estacionalidad.** El Imacec y los flujos fiscales tienen estacionalidad; queda pendiente desestacionalizarlos antes de los modelos.
- **Rezago de publicación.** La cuenta corriente y los datos fiscales se publican con meses de atraso respecto del dólar. Al usarlos como predictores hay que considerar ese rezago.
