# Mundial 2026 - Fixture, resultados y posiciones

Sitio web estático para seguir el Mundial 2026 desde Argentina. Muestra el fixture completo, resultados cargados, tablas de posiciones por grupo, rondas eliminatorias y una llave visual desde 16avos hasta la final.

El proyecto está hecho con HTML, CSS y JavaScript puro. No requiere build, servidor backend ni dependencias de npm: la aplicación lee archivos JSON locales y renderiza toda la interfaz en el navegador.

## Qué incluye

- Fixture de fase de grupos con 72 partidos, fechas, horarios de Argentina, sedes, ciudades y señales de TV.
- Filtros por fase, fecha, grupo y selección.
- Tablas de posiciones calculadas automáticamente a partir de `json/resultados.json`.
- Vista de eliminatorias con 32 partidos, desde 16avos de final hasta final y tercer puesto.
- Llave visual del cuadro eliminatorio, con ganadores resueltos según resultados y penales.
- Pestaña de estadísticas con goleadores, ranking general de selecciones e info de competencia.
- Resaltado especial para Argentina y para equipos clasificados.
- Banderas en PNG para cada selección, con fallback por emoji cuando falta una imagen.
- Panel `admin.html` para cargar resultados manualmente y descargar un nuevo `resultados.json`.
- Scripts y workflows para actualizar resultados desde football-data.org.

## Estructura del proyecto

```text
.
├── index.html
├── admin.html
├── css/
│   └── main.css
├── js/
│   └── app.js
├── json/
│   ├── grupos.json
│   ├── partidos.json
│   ├── eliminatorias.json
│   ├── resultados.json
│   └── stats.json
├── img/
│   ├── logo.png
│   ├── favicon-*.png
│   └── flags/
├── scripts/
│   ├── fetch_resultados.py
│   ├── fetch_eliminatorias.py
│   └── fetch_stats.py
├── .github/
│   └── workflows/
│       ├── auto-resultados.yml
│       ├── auto-eliminatorias.yml
│       └── auto-stats.yml
└── push.sh
```

## Archivos principales

`index.html` es la página pública. Carga `css/main.css` y `js/app.js`, y contiene las secciones de fixture, grupos, llaves y eliminatorias.

`js/app.js` carga los JSON, calcula posiciones, resuelve clasificados, arma los filtros, renderiza los partidos y actualiza dinámicamente las rondas eliminatorias.

`admin.html` es una herramienta local para cargar resultados de fase de grupos, eliminatorias y mejores terceros. Al guardar cambios dentro del panel, se actualiza el estado en memoria y luego se puede descargar un `resultados.json` listo para reemplazar el archivo del proyecto.

`json/resultados.json` es el archivo operativo más importante: contiene los marcadores que alimentan las posiciones, los resultados de eliminatorias, los penales y los mejores terceros.

`json/stats.json` guarda las estadísticas generadas por `scripts/fetch_stats.py`: goleadores, ranking general de selecciones e información de la competencia.

## Datos

- `json/grupos.json`: selecciones por grupo, de A a L.
- `json/partidos.json`: fixture completo de fase de grupos.
- `json/eliminatorias.json`: fixture y dependencias de las rondas eliminatorias.
- `json/resultados.json`: resultados cargados hasta el momento.
- `json/stats.json`: estadísticas actualizadas desde football-data.org.

El sitio calcula las tablas con estos criterios básicos: puntos, diferencia de gol y goles a favor. Los dos primeros de cada grupo aparecen como clasificados directos. Los mejores terceros de 16avos se cargan manualmente en la sección `terceros` de `resultados.json`.

## Formato de resultados

```json
{
  "partidos": {
    "m19": { "scoreH": 3, "scoreA": 0 }
  },
  "eliminatorias": {
    "k74": { "scoreH": 1, "scoreA": 1, "penH": 3, "penA": 4 }
  },
  "terceros": {
    "third_74": "Paraguay"
  }
}
```

- `scoreH`: goles del equipo local.
- `scoreA`: goles del equipo visitante.
- `penH`: penales convertidos por el local, solo si hubo definición por penales.
- `penA`: penales convertidos por el visitante, solo si hubo definición por penales.
- Si un partido no se jugó, no se incluye su clave.

Los IDs de fase de grupos usan el formato `m1` a `m72`. Los IDs de eliminatorias usan el formato `k73` a `k104`.

## Carga manual de resultados

1. Abrir `admin.html` en el navegador.
2. Cargar o borrar resultados desde las pestañas de fase de grupos, eliminatorias o mejores terceros.
3. Usar el botón para descargar `resultados.json`.
4. Reemplazar `json/resultados.json` con el archivo descargado.
5. Hacer commit y push para publicar los cambios.

El script `push.sh` automatiza el flujo de `git add`, `commit` y `push` para despliegues donde Netlify publica desde el repositorio.

## Actualización automática

El proyecto incluye dos workflows de GitHub Actions:

- `.github/workflows/auto-resultados.yml`: consulta resultados de fase de grupos cada 5 minutos.
- `.github/workflows/auto-eliminatorias.yml`: consulta resultados de eliminatorias cada 5 minutos.

Ambos workflows ejecutan scripts Python que consumen la API de football-data.org y actualizan `json/resultados.json` cuando encuentran cambios.

Para usarlos hace falta configurar el secreto:

```text
FOOTBALL_DATA_TOKEN
```

Los scripts también pueden ejecutarse localmente si esa variable de entorno está disponible:

```bash
python scripts/fetch_resultados.py
python scripts/fetch_eliminatorias.py
python scripts/fetch_stats.py
```

`fetch_stats.py` reescribe `json/stats.json` cada vez que se ejecuta. La pestaña **Estadísticas** lee ese archivo y muestra los datos en la interfaz pública.

## Cómo correrlo localmente

Como la app usa `fetch()` para leer JSON, conviene abrirla desde un servidor local simple:

```bash
python -m http.server 8000
```

Después abrir:

```text
http://localhost:8000/
```

El panel de administración queda disponible en:

```text
http://localhost:8000/admin.html
```

## Banderas

Las banderas están en `img/flags/`. El nombre del archivo debe coincidir con el slug generado desde el nombre del país: minúsculas, sin tildes, sin puntos y con espacios reemplazados por guiones.

Ejemplos:

| Selección | Archivo |
| --- | --- |
| Argentina | `argentina.png` |
| México | `mexico.png` |
| Países Bajos | `paises-bajos.png` |
| Rep. Checa | `rep-checa.png` |
| Costa de Marfil | `costa-de-marfil.png` |

Si una bandera no existe, la interfaz intenta mostrar un emoji como fallback.
