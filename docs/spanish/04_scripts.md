# Mod en español, paso 4: el texto de los scripts (historia y tiendas)

Herramienta: `tools/spanish_script.py`. Traducciones: `translations/es/script/<script>.tsv`.
Glosario: `translations/es/GLOSSARY.md`.

## De dónde sale el texto

Los diálogos de la historia y de las tiendas están en los scripts Sol del disco
(`Us/script/**/*.sol`, UTF-16 con BOM, CR LF; ver `lib/sol/README.md`). Cada script trae
su fuente, y un `.sol` de un mod va antes que el `.sx` compilado del disco
(`mods/README.md`, «Scripts»). El mod escribe, por cada script traducido, el original con
sus literales de texto sustituidos, en UTF-8, en `mods/espanol/files/Us/script/<script>.sol`.
El juego lo compila al cargarlo (`[event] compiled script/CTX/TimeA/A01A1x.sol` en el log).

### Cómo se enumeran los scripts

`VOLUME.DAT` guarda el nombre de cada archivo justo después de sus datos (`name_len`
bytes en `stored_end`). La herramienta recorre las 4924 entradas y toma las que se
llaman `Us\script\…\*.sol`: son **181 scripts** (y 2 `.h`). No se buscan por el hash del
nombre porque hay **colisiones**: `CTX/TimeC/C01AFx` y `C01B3x` comparten hash, y también
`C01BFx` y `C01C3x` (flag 1 en la entrada; el juego original compara los nombres). Ojo:
`archive::read` del port toma la primera entrada con ese hash, así que hoy `C01B3x` y
`C01C3x` cargarían el código de `C01AFx`/`C01BFx`; los `.sol` del mod no se ven afectados
porque se leen por nombre de archivo.

Para saber cuáles usa el juego, `list` sigue los `StartScript(…)` y `Require(…)` desde
lo que arranca el propio juego: el ejecutable (`StartUp2`, `config`, `EndRoll`,
`shop/prison`) y los archivos de mapa (las 29 tiendas `Shop/…`). Así salen también los
que solo se cargan con `Require` (los de la fiesta `CTX/TimeC/C01*`, `CTX/TimeE/E0*E1*`…)
y los que nombra otro script (`CTX/Opening` → `CTX/TimeA/A01A1x`). Resultado:
**135 scripts en uso**, 121 de ellos con texto; los otros 46 (`Users/…`, `samples/…`,
`hanai`, `serifdat`…) son pruebas de los desarrolladores y no se traducen.

El juego pide `shop/prison` en minúsculas y el disco lo llama `Shop/prison`: `build` lo
escribe con el nombre pedido (Linux distingue mayúsculas). Tabla `REQUESTED`.

## Qué literal es texto

El lexer es el del compilador (`lib/sol/src/compiler.cpp`: `skip_string`,
`skip_comment`): se saltan `// …` y `/* … */`, los literales van entre `"` o `'`, y un
`\` antes de la comilla no la cierra. `\n` es un salto de línea, `\t` un tabulador y
`\x` cualquier otro carácter x.

Cada literal se clasifica por **la llamada de la que es argumento** (la más interior):

| llamada | argumento | tipo | cómo se ve |
|---|---|---|---|
| `Effect.Telop`, `Telop` (macro) | 0, 2, 4… | `subtitulo` | subtítulo abajo, a 1,2×; el juego lo parte solo (`WrapText`, 612 px a 1,2× = 510 px de fuente). Solo con «Subtítulos» activado |
| `UI.SetSerif`, `UI.SetSerif2`, `SetSerifEx` | 0 | `bocadillo` | bocadillo junto al personaje; **no** se parte: los `\n` mandan |
| `UI.SetTalkSelect` | 1 | `eleccion` | ventana de opciones; una opción por línea (`\n`); el script dice cuántas hay |
| `EventFlag.SetMessage` | 0 | `mensaje` | el objetivo/pensamiento de la pantalla de estado; se parte a 543 px y **se descarta si pasa de 127 caracteres** |
| `UI.AddMessage` | 0 | `aviso` | aviso del HUD («¡PV +400!», «Recibes 500 mon…») |
| `Battle.SetName` | 1 | `nombre` | nombre sobre la barra de un rival |
| `Effect.DrawText` | 0 | `texto` | texto suelto en pantalla |
| variable `st` en `Shop/numata/kajiya` | `st += "…"` | `aviso` | «Attack +3» del herrero, mostrado luego con `UI.AddMessage` (tabla `TEXT_VARS`) |

No son texto (`codigo`): `#include "…"`, los argumentos de `Require`, `StartScript`,
`print`, `Effect.EndRoll` (rutas), los datos de `TelopVoice([voz, segundos, texto, labios],
quién)` (el texto está vacío en esta versión; el cuarto elemento son los movimientos de
labios «o2c2o4…»), y cualquier literal fuera de esas llamadas que no parezca prosa.

Además, dentro de las llamadas de texto se apartan: `vacio` (`""`, `"\n"`), `signos` (sin
letras: «…………!»; no hace falta traducirlas) y `japones` (texto japonés: menús de
depuración con `ViewerMode` y un aviso de depuración en `A01D1x`; 60 en scripts en uso).

**Dudosos** (`dudoso`): un literal con aspecto de prosa fuera de las llamadas conocidas, o
asignado a una variable (`x = "…"`, `x += "…"`), o dentro de una lista en una llamada de
texto. No se traduce y se apunta en `translations/es/original/script/_dudosos.tsv`
(`extract all`) o con `doubtful`. Hoy hay **uno**, en `serifdat` (sin uso, japonés). La
asignación `st += "Attack "` del herrero era dudosa y se resolvió con `TEXT_VARS`. Si
aparece otro: mirar el script y, si es texto, añadir su llamada a `TEXT_CALLS` o la
variable a `TEXT_VARS`.

## Identificador de cada cadena

El **número de literal**: su posición (desde 0) entre *todos* los literales del script,
de texto o no, en el orden del archivo. La fuente del disco no cambia, y el número solo
depende del lexer, que es el del compilador, así que es estable; tampoco depende del
filtro, de modo que afinar las heurísticas no mueve ningún número. Se lee con `show`
(número, línea, tipo, quién, anchos, inglés, español) o en el archivo de trabajo, que
pone la línea del original. Como salvaguarda, `check` da error si un número de la
traducción no es un literal de texto. Se descartó usar la línea: varios literales
comparten línea (`"A\n" + "B"`) y no es más estable.

**Repetidas**: si un literal tiene el mismo inglés que otro anterior del mismo script,
basta traducir el primero; `build` copia la traducción (y `check` avisa si se tradujeron
distinto). En `A01A1x`, 86 literales de texto son 64 distintos.

**Espacios de los extremos**: `build` pone siempre los del inglés (los editores borran los
del final de línea, y hay subtítulos que siguen en el literal siguiente: «…my leg » +
«and we're gonna…»). En el `.tsv` no hace falta escribirlos.

## Formato de la traducción

`translations/es/script/<script>.tsv` (p. ej. `translations/es/script/CTX/TimeA/A01A1x.tsv`),
UTF-8:

```
# comentarios y líneas en blanco se ignoran
<número><TAB><español tal como va entre las comillas>
```

- Solo español, sin el inglés.
- `\n` para un salto de línea, `\"` para una comilla doble (la comilla del literal; en
  la práctica, mejor usar «»). Ninguna otra barra invertida. Nada de saltos de línea reales.
- `¿ » º` se escriben tal cual: `build` los cambia por los códigos de la fuente del paso 2
  (`to_game`, U+E000..U+E002).
- Un número que falta se queda en inglés.

## Flujo de trabajo

```
python3 -I tools/spanish_font.py                 # una vez: la fuente con ¿ » º (paso 2)
python3 -I tools/spanish_script.py list          # scripts en uso: literales, texto, distintos, traducidos
python3 -I tools/spanish_script.py extract all   # archivos de trabajo (ignorados por git)
#   translations/es/original/script/<script>.tsv  + _dudosos.tsv
# escribir translations/es/script/<script>.tsv
python3 -I tools/spanish_script.py build         # todos los que tienen .tsv
python3 -I tools/spanish_script.py check         # o: check CTX/TimeA/A01A1x
python3 -I tools/spanish_script.py show CTX/TimeA/A01A1x [números…]
```

`build` y `check` sin nombres trabajan con todos los scripts que tienen `.tsv`.

### Qué mira `check`

Errores (sale con 1): número que no es un literal de texto; vacío; comilla sin escapar o
barra invertida desconocida; salto de línea real; `%s`/`%d` distintos; iconos de botón
distintos (①–⑥, flechas, y los Latin-1 que la fuente dibuja como iconos); carácter que
no está en la fuente; en `eleccion`, distinto número de `\n` (cada línea es una opción);
en `mensaje`, 128 caracteres o más una vez partido (el juego lo descartaría). Y para el
script entero: el `.sol` generado debe compilar con `solc` (se compila `lib/sol` en
`build-sol/` si no está) y **dar el mismo código que el original salvo los valores de las
cadenas** (se comparan los dos desensamblados); y avisa si el generado está desfasado.

Avisos: en `subtitulo`, si al partirlo como el juego salen más de 2 líneas y más que en
inglés, o queda una línea vacía; en `mensaje`, más de 2 líneas; en `bocadillo`/`eleccion`/`aviso`, una línea más
ancha que la mayor de: su inglés y el máximo del tipo (bocadillo 300 px, elección 450,
aviso 300; los máximos del inglés en uso son 282, 443 y 269); distinto número de `\n`
en bocadillos y avisos; repetidas traducidas distinto.

## Reglas de estilo

- **Caja normal**, aunque el inglés vaya en MAYÚSCULAS. En la versión estadounidense
  todos los bocadillos (292 de 293) y todas las opciones (299) van en mayúsculas y los
  subtítulos (2097) y mensajes en caja normal. En español se escribe todo en caja normal:
  la fuente tiene minúsculas acentuadas bien dibujadas, las mayúsculas son más anchas (y
  el español ya es más largo que el inglés; los bocadillos no se parten), y en español
  las mayúsculas sostenidas se leen como gritos. Comprobado en el juego: las ventanas de
  opciones de `A01A1x` en caja normal se leen bien («Verificación», abajo).
- Español de España. Entre iguales y en la banda, **tú/vosotros**; comerciantes y
  posaderos al cliente, **usted**; el protagonista habla seco y digno («No puedo dejarte
  así.», «Esto no es asunto mío...»). Matones con habla vulgar («mocosa», «lárgate»).
- Tartamudeos como en inglés, sobre la primera sílaba: «¿Q-quién te c-crees…?».
  «Heh!» → «¡Je!», «Haha» → «¡Ja, ja!».
- `...` de tres puntos (como el inglés); un solo espacio tras el punto (el inglés pone dos).
- Signos de apertura siempre: `¿…?`, `¡…!`, y `¿¡…!?` para «What did you say?!».
- **Subtítulos sin `\n`**: el juego los parte solo; un `\n` heredado del inglés suele
  dejar una línea vacía o una palabra suelta en español (`check` avisa de la línea vacía).
  En bocadillos y opciones, en cambio, los `\n` son los que hay.
- Subtítulos partidos en dos literales (una frase que sigue en el siguiente `Telop`): se
  traduce cada mitad de modo que la frase siga leyéndose («…me ha roto la pierna» +
  «¡y nos las va a pagar!»).
- Nombres y términos: `translations/es/GLOSSARY.md` (PV/PR, samurái, ronin, banda Aoto…).
- Cifras, `mon` y nombres de objetos tal cual salgan en el menú (paso 3).

## Tarea para un traductor (un script por tarea)

Entrada: `translations/es/original/script/<script>.tsv` (de `extract`). Cada cadena son
dos líneas:

```
# L884 subtitulo habla: santa repetida en: 62
18	Watch where you're going, you little brat!
```

`L884` es la línea del `.sol` original; el tipo dice dónde se ve (tabla de arriba); `habla`
es el id interno de quien habla cuando el script lo dice (`santa`, `itikiti` = Ichikichi,
`chara_id_akindo` = el tendero; en `eleccion` habla el protagonista); `repetida en` son
los números que heredan esta traducción. Las repetidas no aparecen.

Salida: `translations/es/script/<script>.tsv`, una línea `número<TAB>español` por cada
número del archivo de trabajo, en el mismo orden, con una línea de comentario arriba
(`# <script>: …`). Luego `build` y `check <script>` hasta 0 errores y, si puede ser, 0
avisos (para un aviso de ancho: acortar, o mover el `\n` en bocadillos). No tocar otros
archivos.

Plantilla de prompt recomendada:

```
Traduce al español de España el script de Way of the Samurai 2 <SCRIPT>.
Lee: docs/spanish/04_scripts.md (secciones «Formato de la traducción», «Reglas de
estilo» y «Tarea para un traductor») y translations/es/GLOSSARY.md.
Entrada: translations/es/original/script/<SCRIPT>.tsv (si no existe:
python3 -I tools/spanish_script.py extract <SCRIPT>).
Contexto: lee también el .tsv ya traducido del script anterior en la historia
(<ANTERIOR>) para mantener el tono y los nombres.
Escribe translations/es/script/<SCRIPT>.tsv: «número<TAB>español» para cada número del
archivo de entrada, sin el inglés, conservando los \n de opciones y bocadillos.
Después ejecuta python3 -I tools/spanish_script.py build <SCRIPT> y
python3 -I tools/spanish_script.py check <SCRIPT>, y corrige hasta 0 errores; intenta
dejar 0 avisos. No modifiques ningún otro archivo ni hagas commits.
Informa: número de cadenas traducidas, avisos que queden y por qué, y términos nuevos
que convendría añadir al glosario (no los añadas tú).
```

## Cifras

Scripts en uso (`list`): 121 con texto. **2818 literales de texto, 2721 distintos** dentro
de cada script (contando por script; entre scripts hay más repeticiones):

| parte | scripts | texto | distintos |
|---|---|---|---|
| CTX/TimeA | 25 | 616 | 589 |
| CTX/TimeB | 17 | 543 | 511 |
| CTX/TimeC | 19 | 416 | 402 |
| CTX/TimeD | 12 | 373 | 367 |
| CTX/TimeE | 16 | 386 | 384 |
| CTX/TimeF | 3 | 53 | 53 |
| Shop | 29 | 431 | 415 |

Por tipo: 2097 subtítulos, 299 opciones, 293 bocadillos, 80 mensajes, 49 avisos.

**Traducido (primera muestra): `CTX/TimeA/A01A1x`, 86 de 2818 (64 de 2721 distintos).**
Es la primera escena jugable: tras la intro (`CTX/Opening`, que no tiene texto en el
script) el protagonista cae ante la puerta Otemon, Sayo le da una bola de arroz, y la
banda Aoto (Ichikichi, Nihei, Santa) la acosa.

## Siguientes tandas

Una tarea = un script; una tanda = varios scripts seguidos en el orden de la historia
(por nombre, que sigue a grandes rasgos el orden en que los arranca `StartUp2`), unas 200 cadenas
distintas. Cifra en negrita: cadenas distintas de la tanda; entre paréntesis, las de cada
script. La 1 es la muestra ya hecha (`CTX/TimeA/A01A1x`, 64).

2. **225** — `CTX/TimeA/A01A3a` (20), `CTX/TimeA/A01A4x` (42), `CTX/TimeA/A01A5x` (31), `CTX/TimeA/A01B1a` (19), `CTX/TimeA/A01B2a` (28), `CTX/TimeA/A01C2x` (39), `CTX/TimeA/A01D1x` (46)
3. **198** — `CTX/TimeA/A02A1x` (33), `CTX/TimeA/A02A2x` (32), `CTX/TimeA/A02A3a` (10), `CTX/TimeA/A02A3b` (16), `CTX/TimeA/A02A3c` (30), `CTX/TimeA/A02A4a` (9), `CTX/TimeA/A02A4b` (16), `CTX/TimeA/A02A4c` (30), `CTX/TimeA/A02C1a` (5), `CTX/TimeA/A02C1b` (5), `CTX/TimeA/A02C1c` (6), `CTX/TimeA/A02C1d` (6)
4. **228** — `CTX/TimeA/A02C1e` (40), `CTX/TimeA/A03C1a` (16), `CTX/TimeA/A03C1b` (5), `CTX/TimeA/A03C1c` (6), `CTX/TimeA/A03C1d` (35), `CTX/TimeB/B01A1x` (27), `CTX/TimeB/B01A2x` (40), `CTX/TimeB/B01B1a` (18), `CTX/TimeB/B01B1b` (23), `CTX/TimeB/B01B2a` (18)
5. **187** — `CTX/TimeB/B01B2b` (25), `CTX/TimeB/B01C1x` (23), `CTX/TimeB/B01D1x` (22), `CTX/TimeB/B02A1x` (23), `CTX/TimeB/B02C1x` (33), `CTX/TimeB/B02D1x` (43), `CTX/TimeB/B03A1x` (18)
6. **226** — `CTX/TimeB/B03B1a` (87), `CTX/TimeB/B03C1a` (37), `CTX/TimeB/B03D1x` (60), `CTX/TimeB/B04A1x` (9), `CTX/TimeB/B05A1x` (5), `CTX/TimeC/C01A1x` (28)
7. **222** — `CTX/TimeC/C01A2x` (9), `CTX/TimeC/C01A3a` (23), `CTX/TimeC/C01A3b` (9), `CTX/TimeC/C01B1x` (21), `CTX/TimeC/C01B2x` (19), `CTX/TimeC/C01B3x` (13), `CTX/TimeC/C01B4x` (28), `CTX/TimeC/C01C1x` (32), `CTX/TimeC/C01C2x` (16), `CTX/TimeC/C01C3x` (29), `CTX/TimeC/C01C4a` (23)
8. **184** — `CTX/TimeC/C01C4b` (12), `CTX/TimeC/C01CFx` (8), `CTX/TimeC/C01D1x` (30), `CTX/TimeC/C01Z1x` (13), `CTX/TimeC/C02D1x` (5), `CTX/TimeC/C02D2x` (32), `CTX/TimeC/C03D1x` (52), `CTX/TimeD/D01A1a` (1), `CTX/TimeD/D01A1b` (12), `CTX/TimeD/D01B1a` (19)
9. **207** — `CTX/TimeD/D01B1b` (93), `CTX/TimeD/D01C1x` (30), `CTX/TimeD/D01D1x` (6), `CTX/TimeD/D02A1x` (17), `CTX/TimeD/D02B1x` (34), `CTX/TimeD/D02C1x` (27)
10. **191** — `CTX/TimeD/D02D1x` (45), `CTX/TimeD/D03A1x` (26), `CTX/TimeD/D04A1x` (57), `CTX/TimeE/E01A1x` (23), `CTX/TimeE/E01B1a` (7), `CTX/TimeE/E01B1b` (33)
11. **216** — `CTX/TimeE/E01C1x` (55), `CTX/TimeE/E01C2x` (19), `CTX/TimeE/E01D1x` (47), `CTX/TimeE/E01E1a` (5), `CTX/TimeE/E01E1b` (19), `CTX/TimeE/E01E1c` (35), `CTX/TimeE/E02A1a` (36)
12. **158** — `CTX/TimeE/E02A1c` (17), `CTX/TimeE/E02D1x` (25), `CTX/TimeE/E02E1a` (5), `CTX/TimeE/E02E1b` (16), `CTX/TimeE/E02E1c` (28), `CTX/TimeE/E03D1x` (14), `CTX/TimeF/F01A1x` (16), `CTX/TimeF/F01B1x` (34), `CTX/TimeF/F01C1x` (3)
13. **236** — `Shop/amakaze/douguya` (2), `Shop/amakaze/gofukuya` (2), `Shop/amakaze/izakaya` (23), `Shop/amakaze/kanzasiya` (2), `Shop/amakaze/komamonoya` (2), `Shop/amakaze/yukaku` (21), `Shop/kakinuma/izakaya` (23), `Shop/kakinuma/syokuji` (25), `Shop/kakinuma/tyaya` (21), `Shop/kakinuma/yadoya` (17), `Shop/numata/kajiya` (78), `Shop/numata/sento_m` (17), `Shop/numata/sento_w` (3)
14. **179** — `Shop/numata/syokuji` (23), `Shop/numata/yaoya` (2), `Shop/ootemon/syokuji` (24), `Shop/ootemon/tyaya` (21), `Shop/ootemon/yadoya` (18), `Shop/ootuka/douguya` (2), `Shop/ootuka/izakaya` (2), `Shop/ootuka/komamonoya` (2), `Shop/ootuka/kusuriya` (2), `Shop/ootuka/yaoya` (2), `Shop/prison` (7), `Shop/shikano/syokuji` (23), `Shop/zinzya/douguya` (2), `Shop/zinzya/komamonoya` (2), `Shop/zinzya/syokuji` (24), `Shop/zinzya/tyaya` (23)

Las tiendas (13–14) se pueden hacer en cualquier momento; dentro de ellas, los
restaurantes (`syokuji`), casas de té (`tyaya`) y tabernas (`izakaya`) se parecen
mucho entre barrios: conviene traducir uno y usarlo de modelo para los demás.

## Verificación en el juego

Con `WOTS2_MODS` apuntando a un directorio con solo `espanol`, partida nueva por entrada
programada (`WOTS2_NEW_GAME=1`, `WOTS2_INPUT`) y capturas (`WOTS2_SHOTS`):

- El log dice `[event] compiled script/CTX/TimeA/A01A1x.sol` y el script corre.
- La ventana de opciones crece con el texto: «¡Jamás he probado una bola de arroz tan
  buena!» (la más ancha, 328 px) cabe con margen, y `¿` (U+E000) se dibuja bien.
- La escena entera, de la bola de arroz a la huida de los tres matones, con Cross cada 5 s
  (primera opción en cada elección): las tres ventanas de opciones («¿Cómo te llamas?»,
  «No puedo dejarte así.», «Tengo una deuda de gratitud con ella.»…) y los subtítulos
  («¡Ay! ¡Cómo duele! ¡Me muero!», «¡Je! Y bien, ¿cómo piensas pagar esto, niña?»,
  «¡E-eh, este samurái es duro! ¡Vámonos de aquí!»…) se ven completos, con tildes, `ñ`,
  `¡` y `¿`. Después arranca `CTX/TimeA/A01A3a`, aún en inglés.
- Subtítulos: a la izquierda, en la franja negra de abajo, partidos a ~570 px de pantalla
  como calcula la herramienta. Dos líneas caben de sobra y una tercera también cabría
  (la franja tiene ~85 px). «¿Sabes con quién demonios estás hablando? ¡Somos la banda
  Aoto!» dejaba «Aoto!» sola en la segunda línea y se acortó. Con los `\n` copiados del
  inglés, cuatro subtítulos quedaban con una línea vacía o cortados a destiempo (el
  `WrapText` del juego parte antes del `\n` si la línea ya no cabe); se quitaron, y de
  ahí la regla de no poner `\n` en los subtítulos.
- Cajas de opciones: crecen con la línea más ancha, sin recortes.

## Lo que no está en los scripts

- La narración de la intro: `end_roll/opening.er2` (`Effect.EndRoll` en `CTX/Opening`).
  Los créditos: `EndRoll` usa otros `end_roll/*.er*`.
- Nombres de objetos, espadas, trabajos (tareas), técnicas: otras tablas del disco
  (`task/*.bin`, datos de objetos…), aún sin estudiar.
- Rótulos dibujados en texturas (títulos de menú, «PAUSE»…).
