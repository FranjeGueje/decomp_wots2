# Mod en español, paso 2: glifos nuevos ¿ » º

Herramienta: `tools/spanish_font.py`. Lee `Font/Samu2.Fnt` y `Font/Samu2.Pim` de
`extracted/VOLUME.DAT` (o `--fnt`/`--pim`) y escribe la fuente modificada en
`mods/espanol/files/Us/Font/` (o `--out DIR`). Es determinista: dos ejecuciones dan
los mismos bytes. `--png DIR` deja vistas previas (`glyphs.png`, `text.png` y
`text_without_mapping.png`, lo que saldría sin sustituir los códigos).

```
python3 -I tools/spanish_font.py              # genera la fuente del mod
python3 -I tools/spanish_font.py --png /tmp/p # y además las vistas previas
```

Los archivos generados **no están en git**: son la fuente del disco con 3 glifos
añadidos, y nada del disco va al repositorio (`.gitignore` los excluye). Hay que
ejecutar la herramienta una vez después de clonar. Sin ellos el mod `espanol`
arranca igual, pero dice `nothing to load`.

## Mapa de códigos

Los códigos reales de `¿` (U+00BF), `»` (U+00BB) y `º` (U+00BA) **no se tocan**: la
fuente del juego los dibuja como iconos (botón ✕, ↓, ↑) y los textos originales los
usan así. Los glifos nuevos van en el área de uso privado:

| carácter | código en el juego | cómo está dibujado | tamaño | posición (textura 1) |
|---|---|---|---|---|
| `¿` | **U+E000** | el `?` de la fuente girado 180°, en las filas de tinta del `¡` (cuelga bajo la línea igual que él) | 10×21 | (0, 221) |
| `»` | **U+E001** | el `«` de la fuente espejado (rectángulo completo: el espacio que `«` deja detrás, `»` lo deja delante) | 8×17 | (22, 221) |
| `º` | **U+E002** | la `o` de la fuente reducida por promedio de área al tamaño y sitio de la `ª` de la fuente (sin subrayado, como la `ª`) | 6×9 | (44, 221) |

Ya existían y se escriben tal cual: `á é í ó ú Á É Í Ó Ú ñ Ñ ü Ü ¡ « ª`. `«` no
necesita código nuevo (U+00AB ya es la comilla), y `»` sale de él, así que el par es
coherente.

Detalles: textura 1 del `.Pim` (512×512, 8 bits, una paleta), celdas de 22 px como
el resto (`u = 22·n`, `v = 1 + 22·10`), solo índices de la rampa gris 206..255 que
usan las letras latinas (el `º` se cuantiza a los niveles que usan las letras),
`clut 0`, sin el bit de color fijo (se pintan en el color del texto). En el `.Fnt`
las tres entradas se insertan en orden (tras U+9F8D, antes de U+FF01) y el contador
pasa de 2499 a 2502. Solo cambian 123 bytes del `.Pim`.

## Cómo usarlos

Al generar los textos traducidos (paso 3), escribir el español normal y pasar cada
cadena por la sustitución antes de guardarla en UTF-16:

```python
import sys; sys.path.insert(0, "tools")
from spanish_font import to_game, NEW_GLYPHS     # {"¿": 0xE000, "»": 0xE001, "º": 0xE002}
line = to_game("¿Quieres salir? «Sí», dijo. Calle nº 3")
```

En un `.sol` en UTF-8 también se pueden escribir los caracteres U+E000..U+E002
directamente (son invisibles en casi todos los editores; mejor generarlos con
`to_game`).

## Verificación

- En el juego: un mod de prueba con `menu/menutext.txt` cambiado (no incluido) mostró
  en la pantalla de Settings «¿Barras de color?», «¿Subtítulos? «sí»», «¡Vibración! 1º»
  y «Cámara» nº 2» con los glifos nuevos, en el color de los botones, y el juego
  arranca normalmente con la fuente modificada (`[mods] espanol: loaded (Español)`).
- Observación para el paso 3: los botones de Settings tienen ancho fijo y los textos
  más largos que el inglés se salen; habrá que vigilar las longitudes.
