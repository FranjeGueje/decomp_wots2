# Mod en español, paso 3: el texto de los menús

Herramienta: `tools/spanish_text.py`. Traducción: `translations/es/menutext.tsv`.
Glosario: `translations/es/GLOSSARY.md`.

## Formato del original

`Us/menu/menutext.txt` (lo lee `TextTable_Parse`, `src/engine/text_table.cpp`):

- UTF-16LE con BOM; cada línea termina en **CR** solo (no CR LF), también la última.
- 411 líneas. El juego pide las cadenas **por número de línea** (`TextTable_Find(id)`),
  así que la versión traducida tiene las mismas líneas en el mismo orden.
- Dentro de una línea, los dos caracteres `\n` son un salto de línea.
- Las líneas que solo tienen `.` son relleno (ids que nada usa): se dejan intactas.
- Hay líneas que no son texto: espacios (`1`, `6`…), `/`, `%`, iconos de botón
  (`④`, `③`…) y piezas de la notación de técnicas (`＋`, `←`, `「`…).
- Algunas cadenas **se pegan a otras** y su espacio inicial o final importa:
  `' Next'` (239), `' failed'` (316, va tras el nombre del trabajo),
  `"You didn't receive your pay for "` (317, va delante), `' Exit'` (318, tras el nombre de
  la zona), `' and '` (367), `'Date : '`… (159–162). El orden de las piezas lo fija el
  código, así que la traducción se adapta («Te quedas sin paga: » + trabajo,
  trabajo + « (fracaso)»).
- `%s` (376–378) se sustituyen en orden: el primero es siempre el primer argumento, no
  se pueden intercambiar.

## Archivo de traducción

`translations/es/menutext.tsv`, UTF-8: `id<TAB>texto`; `#` comenta. Solo el español: el
inglés sale del disco cada vez. Se escribe español normal, con `¿ » º` reales: `build`
los cambia por los códigos de la fuente del paso 2 (`to_game`, U+E000..U+E002). Un id
que falta se queda en inglés.

## Flujo de trabajo

```
python3 -I tools/spanish_font.py          # una vez: la fuente con ¿ » º (paso 2)
python3 -I tools/spanish_text.py extract  # el original, id<TAB>inglés, en
                                          # translations/es/original/menutext.tsv (ignorado)
# editar translations/es/menutext.tsv
python3 -I tools/spanish_text.py check    # errores y avisos
python3 -I tools/spanish_text.py show 106 107   # id, ancho en px, inglés y español
python3 -I tools/spanish_text.py build    # mods/espanol/files/Us/menu/menutext.txt
```

`--orig FILE` usa un `menutext.txt` extraído en vez de `extracted/VOLUME.DAT`. Con una
traducción vacía, `build` reproduce el archivo del disco byte a byte (comprobado).

`check` da **error** (sale con 1) si: cambian los `%s`/`%d`; cambian los iconos de botón
(①–⑥, flechas, ○●, y los códigos Latin-1 que la fuente dibuja como iconos); hay una
barra invertida que no es `\n`; cambian los espacios de los extremos; se traduce una línea
de relleno; o falta algún carácter en la fuente. Da **aviso** si cambia el número de `\n`,
si queda una línea con palabras sin traducir, o si la cadena traducida es **más ancha**
que la inglesa (anchos de glifo de la `.Fnt` modificada; el ancho es el avance, sin
kerning; con varias líneas cuenta la más ancha).

El ancho inglés es una cota prudente: muchos sitios tienen más hueco. `ROOM` en la
herramienta guarda, por id, el ancho comprobado en el juego; esos ids solo avisan si lo
superan.

## Nada del disco en git

Generado (ignorado en `.gitignore`): `mods/espanol/files/` entero (fuente y
`menutext.txt`, que lleva el relleno y las líneas inglesas) y `translations/*/original/`.
Tras clonar: `spanish_font.py` y `spanish_text.py build`.

## Verificación en el juego

Con `WOTS2_MODS` apuntando a un directorio con solo `espanol`, entrada programada
(`WOTS2_INPUT`) y capturas (`WOTS2_SHOTS`):

- **Opciones** (título → Settings) y su página de sonido: «Barras de color» (123 px) se salía
  del botón; «Prueba sonidos» (114 px) cabe. Se dejó «Barras color» y «Salida audio».
  Hueco de los botones de la izquierda: ~116 px.
- **Menú de pausa**: «Ver estado», «Opciones», «Volver al juego» con hueco de sobra
  (los botones caben ~150 px; el menú de casa «Echar una cabezada», 155 px, se acortó a
  «Echar la siesta»).
- **Ver estado**: «Fecha : 21 de agosto Mañana», «Lugar : Puerta Otemon», PV/PR/Dur,
  «Dinero», pistas «⑥ Jugar», «③ Menú de pausa».
- **Creación de personaje**: «Nombre», «Cabeza», «Ropa», «Espada», «Objetos», «Listo» y
  la pista «Terminar y empezar la partida.».
- **Récords** (título): pestañas, «Clasificación» (antes «Mejores puntuaciones»,
  demasiado pegado al valor), «Bajas de un golpe»…

Sin comprobar todavía (quedan como avisos de `check`): las páginas de espadas y
objetos, el armero y el baúl, el mapa de zona, los avisos del HUD, la pantalla de
resultados y los nombres de tiendas (380–410). Los mensajes largos caben en cuadros
anchos (los de objetos ya pasan de 320 px en inglés), pero conviene revisarlos al jugar.

No son texto de `menutext.txt` (siguen en inglés): el menú del título (Start, Records,
Settings, Easy/Normal…), los rótulos «Settings», «PAUSE», «Status Check», «Records»,
«Character Selection» (texturas), la página «Enhancements» del port (texto en el código)
y los textos de la historia (paso 4).
