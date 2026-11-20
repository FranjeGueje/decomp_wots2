# Mod de traducción al español — Way of the Samurai 2

Este mod traduce al español de España el port nativo de *Way of the Samurai 2* (侍道2).
No cambia el código del juego: solo sustituye archivos de datos mediante el sistema de mods del proyecto (`mods/README.md`).

> **Necesitas tu propia copia del juego** (el disco NTSC-U, `SLUS-208.93`). Este repositorio **no contiene nada del disco**: ni textos originales en inglés, ni la fuente, ni los archivos del mod ya generados. Solo incluye **tu traducción** y las **herramientas** que la inyectan en los archivos del juego. Los archivos del mod se generan en tu máquina a partir de tu disco.

## Qué añade este mod

Respecto a la rama principal (`master`), la rama `espanol` solo **añade** archivos (salvo el `.gitignore`), y no toca `src/`, `include/`, `lib/` ni `config/`.

| Qué                               | Archivos                                                                                                                                |
| --------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| Traducciones (`translations/es/`) | 190: menús, scripts, datos, tareas NPC (37 tandas) y el glosario                                                                        |
| Herramientas (`tools/`)           | 6: `spanish_font.py`, `spanish_text.py`, `spanish_script.py`, `spanish_data.py`, `spanish_task.py` y `font_info.py` (analiza la fuente) |
| Documentación (`docs/spanish/`)   | 6 archivos, del `01` al `06`                                                                                                            |
| `.gitignore`                      | única modificación de algo existente                                                                                                    |
| Mod (`mods/espanol/mod.ini`)      | la definición del mod; los archivos que reemplazan a los del juego se generan (ver más abajo)                                           |

### Qué está traducido

- **Menús** (321 líneas con texto).
- **Historia y tiendas:** las 2.818 cadenas de los scripts, incluidas las 29 tiendas y el herrero.
- **Datos:** objetos y accesorios, títulos de rango, frases de tienda, roles de personajes,
  tarjeta de memoria, teclado de nombre (con ñ, tildes y `¡ ¿`) y la narración de la intro y los finales.
- **Fuente:** se añaden `¿`, `»` y `º` (el juego ya trae las vocales acentuadas, `ñ`, `ü`, `¡` y `«`).
- **Conversaciones con NPC y trabajos** (`alltask`): las 7.596 cadenas de las tareas en uso, en 37 tandas: trabajos (`work_*`), personajes principales (`main_*`), rumores (`news_*`), magistrados, matones (`evil_*`) y vecinos (`normal_*`).

### Qué no está traducido

- Las 14 cadenas de tareas sin uso (`38_sin_uso`) y 221 cadenas en japonés de tareas que el juego nunca muestra.
- Los rótulos dibujados en texturas (menú del título, «PAUSE», «Settings», letreros de tienda…).
- La página «Enhancements» del port, los nombres de espadas y técnicas (romanizados, a propósito) y los créditos (son vídeo).

El estado exacto de las tareas de NPC se ve con `python3 -I tools/spanish_task.py list`.

## Requisitos

- Tu copia del juego, y el port compilado y funcionando (ver más abajo).
- `python3` **3.10 o superior** y **NumPy** (`pip install numpy` o `sudo apt install python3-numpy`): es la única librería de terceros. Ejecuta las herramientas con `python3 -I`.
- El disco extraído en `extracted/VOLUME.DAT` dentro de la raíz del repositorio (ver el paso 1). Sin él, las herramientas fallan con `FileNotFoundError`.
- `cmake` y un compilador, para compilar el port (y para que `check` construya `solc`, el compilador de scripts Sol, si no existe aún).

## Paso 1 — Compilar el port

Desde la raíz del repositorio (Debian / Ubuntu / Pop!_OS):

```bash
# 1. Dependencias
sudo apt install build-essential cmake ninja-build libsdl2-dev libgl-dev libarchive-dev ffmpeg

# 2. Compilar
cmake -B build -G Ninja && ninja -C build

# 3. Entregarle tu imagen del disco la primera vez
./build/wots2 "Way of the Samurai 2.iso"
```

La primera vez, el lanzador descomprime los archivos del juego en `extracted/` (unos 1,5 GB) y arranca el juego. Después basta `./build/wots2`. Las herramientas de traducción leen `extracted/VOLUME.DAT`.

> Si ya tienes los archivos extraídos en otra carpeta, puedes crear un enlace simbólico `extracted` en la raíz del repositorio que apunte a ella. Git lo ignora.

## Paso 2 — Generar la traducción

Cada herramienta lee tu disco (`extracted/VOLUME.DAT`) y la traducción de `translations/es/`, y escribe los archivos del mod en `mods/espanol/files/Us/...`. Ejecuta, en este orden y desde la raíz del repositorio:

```bash
# 1. La fuente con ¿ » º (hazlo primero: las demás herramientas miden el ancho con ella)
python3 -I tools/spanish_font.py

# 2. Menús
python3 -I tools/spanish_text.py build

# 3. Historia y tiendas (scripts Sol)
python3 -I tools/spanish_script.py build

# 4. Datos: objetos, tiendas, teclado de nombre, finales, tarjeta de memoria…
python3 -I tools/spanish_data.py build

# 5. Conversaciones y trabajos de los NPC
python3 -I tools/spanish_task.py build
```

Comprobar que todo está bien (opcional, recomendado tras tocar una traducción):

```bash
python3 -I tools/spanish_text.py check     # 0 errores; avisos de ancho en pantallas sin revisar
python3 -I tools/spanish_script.py check   # compila cada script (construye solc si falta)
python3 -I tools/spanish_data.py check
python3 -I tools/spanish_task.py check
```

`check` vigila `%s` y `\n`, los iconos de botón, los caracteres que falten en la fuente, los límites de longitud y el ancho de cada línea frente al hueco de la pantalla.

Resultado: unos 157 archivos (≈ 6 MB) en `mods/espanol/files/`. **Esa carpeta no se sube a git**: se genera en cada máquina porque contiene datos derivados del disco.

## Paso 3 — Instalar el mod

El mod ya está dentro del repositorio: `mods/espanol/mod.ini` lo deja **activado**
(`enabled = 1`). Una vez generados sus archivos (paso 2), el juego lo carga solo al arrancar:

```bash
./build/wots2
```

En el terminal debe aparecer algo como `[mods] espanol: loaded (Español)`. Si solo ves `nothing to load`, es que aún no has generado los archivos del paso 2.

Otros casos:

- **Con el paquete ya compilado** (Releases): copia la carpeta `mods/espanol/` completa, con su `files/` ya generado, dentro de la carpeta `mods/` del paquete y arranca `wots2` como siempre.
- **Desactivarlo:** pon `enabled = 0` en `mods/espanol/mod.ini`, o ejecuta una vez
  `WOTS2_MOD_ESPANOL=0 ./build/wots2`. Para ejecutar sin ningún mod: `WOTS2_MODS=0 ./build/wots2`.
- **Mods en otra carpeta:** `WOTS2_MODS=<carpeta> ./build/wots2`.
- **Convive con los demás mods** (widescreen, resolución, FPS, iluminación moderna).

Las partidas ya empezadas pueden mostrar restos en inglés, porque el nombre y el mensaje del trabajo en curso se guardan dentro de la partida.

## Cómo está organizado el trabajo

```
translations/es/
  menutext.tsv            menús (id → español)
  script/**/*.tsv         historia y tiendas
  data/**/*.tsv           objetos, tiendas, finales, tarjeta de memoria…
  task/*.tsv              conversaciones y trabajos de los NPC (por tandas)
  GLOSSARY.md             términos y decisiones de estilo
  original/               (ignorado por git) el inglés extraído de tu disco, para traducir
tools/spanish_*.py        extract / check / build / show de cada tipo de archivo
docs/spanish/01..06       formato, flujo de trabajo y reglas de estilo
```

Los `.tsv` solo contienen `id<TAB>español`, sin el texto inglés. Para seguir traduciendo:

1. `python3 -I tools/spanish_task.py list` muestra qué tandas faltan.
2. `python3 -I tools/spanish_task.py extract <tanda>` deja el inglés de la tanda en
   `translations/es/original/task/` (ignorado por git).
3. Escribe `translations/es/task/<tanda>.tsv` y pasa `check <tanda>` hasta 0 errores.
4. `build` y prueba en el juego.

Las reglas de estilo (trato de usted y de tú por personaje, protagonista masculino, PV/PR, caja normal, límites de ancho) están en `translations/es/GLOSSARY.md` y en `docs/spanish/`.

## Decisiones de la traducción

- **Protagonista masculino.** Kyojiro, Kasumi, Otomi y Nami, en femenino.
- **Vida y resistencia:** PV y PR (puntos de vida y de resistencia).
- **Caja normal** en diálogos y opciones; el original va en mayúsculas.
- **Nombres propios, espadas, técnicas y títulos de tasación del herrero** se dejan romanizados u originales.
- **`¿`, `»`, `º`:** se dibujan con códigos privados (U+E000–U+E002) para no romper los iconos de botón que el juego dibuja con los códigos normales.

## Aviso legal

Este repositorio no contiene binarios, recursos ni datos del disco. Es un proyecto
independiente, no comercial, de preservación e investigación, sin relación con Acquire, Spike o Capcom. Debes tener el juego para usarlo.
