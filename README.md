# ⚽ Mundial 2026 — Fixture & Resultados

Sitio estático para seguir el Mundial 2026 (USA · Canadá · México).

---

## Estructura

```
mundial2026/
├── index.html          ← Entry point
├── css/
│   └── main.css
├── js/
│   └── app.js
├── json/
│   ├── partidos.json       ← Fixture fase de grupos (no editar salvo corrección)
│   ├── grupos.json         ← Composición de cada grupo (no editar)
│   ├── eliminatorias.json  ← Fixture de rondas eliminatorias (no editar)
│   └── resultados.json     ← ✏️ ESTE es el que editás para cargar resultados
└── img/
    ├── logo.png
    ├── favicon-32.png
    ├── favicon-16.png
    ├── apple-touch-icon.png
    └── flags/
        ├── argentina.png
        ├── brasil.png
        └── ...             ← Una imagen por selección (28×20 px, PNG)
```

---

## Cómo cargar resultados

Editá el archivo `json/resultados.json` desde tu notebook.  
El formato es simple:

```json
{
  "partidos": {
    "m19": { "scoreH": 2, "scoreA": 0 },
    "m41": { "scoreH": 1, "scoreA": 1 }
  },
  "eliminatorias": {
    "k73": { "scoreH": 3, "scoreA": 1 }
  }
}
```

- La clave es el `id` del partido (ver `partidos.json` y `eliminatorias.json`).
- `scoreH` = goles del equipo local · `scoreA` = goles del visitante.
- Si el partido no se jugó, no incluyas la clave o usá `null`.

Después hacés commit y push 

---

## Banderas (flags)

Colocá imágenes PNG de **28×20 px** (o mayor, se escalan) en `img/flags/`.  
El nombre del archivo debe ser el nombre del país en minúsculas, sin tildes, sin puntos, con guiones:

| País           | Archivo               |
|----------------|-----------------------|
| Argentina      | `argentina.png`       |
| Rep. Checa     | `rep-checa.png`       |
| Países Bajos   | `paises-bajos.png`    |
| Bosnia y Herz. | `bosnia-y-herz.png`   |
| Costa de Marfil| `costa-de-marfil.png` |

Si la imagen no existe, se muestra el emoji de la bandera como fallback.
