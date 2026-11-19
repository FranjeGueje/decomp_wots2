# Mod en español, paso 5: el texto de los archivos de datos

Herramienta: `tools/spanish_data.py`. Traducciones: `translations/es/data/<archivo>.tsv`.
Glosario: `translations/es/GLOSSARY.md`.

Son los archivos con texto que no son `menu/menutext.txt` (paso 3), ni los scripts
(paso 4), ni las tareas (`task/alltask`, aparte).

## Los archivos

| archivo (bajo `Us/`) | qué es | cadenas | distintas | formato (resumen) |
|---|---|---|---|---|
| `item/ItemInfo.Dat` | objetos: nombre, ayuda, descripción, mensaje al usarlo | 198 | 195 | `ItIf`, nº, tabla de desplazamientos; cada registro: 12 bytes de datos, 5 desplazamientos (nombre, ayuda, descripción, uso, icono), las 4 cadenas de 16 bits y la ruta ASCII del icono, relleno a 4 |
| `object/ObjectName.Lst` | nombre de lo que se recoge del suelo | 31 | 0 (sale de `ItemInfo`) | `003`; por objeto: modelo ASCII + 0, nombre de 16 bits + 0, 16 bytes |
| `Accessory/AccessoryPos.Lst` | dónde se lleva un accesorio (Récords) | 28 | 7 | BOM y cadenas de 16 bits seguidas, acabadas en una vacía |
| `menu/Title/TitleNameList` | títulos del jugador | 30 | 30 | `s32` nº y registros fijos de 0x32 bytes: **máx. 24 caracteres** + 0 |
| `chara/paramlist` | nombres de personaje: solo los **roles genéricos** | 117 | 39 | `u16` nº, `u16` versión 9; por personaje 14 `s32` y el nombre (`s32` bytes, 16 bits, relleno a 4) |
| `ui/GameUI/ShopList.dat` | frases de tienda, menú sí/no, «Dinero»… | 138 | 19 | versión 3; 5 cadenas comunes; por tienda: género, 11 × {`s16` voz, frase} y la hoja del rótulo |
| `mcard/message.dat` | mensajes de guardar / cargar | 86 | 85 | cadenas de 16 bits seguidas (`src/game/mcard.cpp`) |
| `ui/NameInput/CharGlance.txt` | el teclado del nombre | 6 filas | — | UTF-16 con BOM, CR LF; la primera página (hasta una línea en blanco) es el teclado |
| `end_roll/*.er2` (23) | rollos de texto: la intro (`opening`) y los finales | 90 | 90 | cabecera (x, y, modo, fotogramas, voces) y líneas {`s16` separación, texto} (`src/game/text_roll.cpp`) |

Los rollos: `opening` (7 líneas), `ed01_01` (1), `ed02_01` (5), `ed02_02` (1), `ed03_01` (7),
`ed03_02` (2), `ed04_01` (5), `ed04_02` (6), `ed04_03` (2), `ed05_01` (5), `ed06_01` (6),
`ed07_01` (6), `ed08_01` (8), `ed09_01` (2), `ed10_01` (3), `ed11_01` (5), `ed12_01` (4),
`ed13_01` (5), `ed14_01` (4), `jiseinoku` (3), `later_01` (1), `yokujitu` (1), `doujitu` (1).

**Total: 724 cadenas, 471 distintas por traducir** (dentro de cada archivo; contando el
teclado como 6). Lo que no es texto no se cuenta ni se puede traducir (`check` da error):
las etiquetas japonesas de los desarrolladores (objetos 0 y 10 de `ItemInfo`, los 92
objetos de escenario de `ObjectName`, los `不明` de `AccessoryPos`, la tienda de prueba 12
de `ShopList`), los mensajes de uso `特になし` («nada») de los objetos que no se usan,
la ruta `item/pim/item.BPM` que el objeto 0 tiene por descripción, `5 mon` y similares,
y los nombres propios de `paramlist`.

No se tocan: los nombres de espadas, técnicas y apellidos, ni los títulos de tasación
del herrero (`weapon/smithdata`, decisión del usuario), ni los rótulos de las texturas
(«Name Entry», «Store», «Item Selection»…: más adelante). `ui/Start.er2` y `CharGlance.BAK`
no los usa el juego.

## Ids

| archivo | id | ejemplo |
|---|---|---|
| `item/ItemInfo` | `<objeto>.<campo>`, campo `name`, `help`, `desc`, `use` | `1.name`, `1.desc` |
| `object/ObjectName`, `Accessory/AccessoryPos`, `menu/Title/TitleNameList`, `chara/paramlist`, `mcard/message` | el número de la cadena (desde 0) | `12` |
| `ui/GameUI/ShopList` | `c0`…`c4` las comunes; `<tienda>.<frase>` (tienda 0–12, frase 0–10) | `c0`, `8.1` |
| `ui/NameInput/CharGlance` | la fila del teclado (0–5 las de ahora; 6, 7… filas nuevas) | `6` |
| `end_roll/<rollo>` | la línea (desde 0) | `3` |

La herramienta lo comprueba: un id que no existe, o que no es texto, es un error.

**Repetidas**: si una cadena tiene el mismo inglés que otra del mismo tipo en el mismo
archivo, basta traducir la primera (las demás la heredan; `check` avisa si se tradujeron
distinto). Así `WELCOME!` se traduce una vez para las 12 tiendas, y `Magistrate` una vez
para los 17 personajes.

**`ObjectName` no se traduce**: cada nombre toma el español del objeto de `ItemInfo` con el
mismo nombre inglés (todos lo tienen), así el aviso del suelo y el menú coinciden. Se
puede forzar otro con `object/ObjectName.tsv` (`check` avisa si difiere). `build` escribe
`ObjectName.Lst` siempre que haya traducción de `ItemInfo`.

**Espacios de los extremos**: `build` pone los del inglés en cada línea (si el número de
líneas coincide; si no, en los de la cadena entera). En el `.tsv` no hace falta escribirlos:
el menú de la tienda es `"     I'LL TAKE IT\n     I'LL THINK ABOUT IT     "` y basta con
`Me lo llevo\nMe lo pensaré`.

## Formato de la traducción

`translations/es/data/<ruta sin extensión>.tsv`, UTF-8 (p. ej.
`translations/es/data/item/ItemInfo.tsv`, `translations/es/data/end_roll/ed05_01.tsv`):

```
# comentarios y líneas en blanco se ignoran
<id><TAB><español>
```

- Solo español, sin el inglés.
- `\n` es un salto de línea, `\\` una barra invertida, `\t` un tabulador; ningún otro `\`.
- `¿ » º` se escriben tal cual: `build` los cambia por los códigos de la fuente del paso 2
  (`to_game`, U+E000..U+E002).
- Un id que falta se queda en inglés. Varias tandas pueden ir añadiendo líneas al mismo
  archivo (mejor en el orden de los ids).

## Flujo de trabajo

```
python3 -I tools/spanish_font.py               # una vez: la fuente con ¿ » º (paso 2)
python3 -I tools/spanish_data.py list          # archivos: cadenas, distintas, traducidas
python3 -I tools/spanish_data.py extract       # archivos de trabajo (ignorados por git):
#   translations/es/original/data/<ruta>.tsv
# escribir translations/es/data/<ruta>.tsv
python3 -I tools/spanish_data.py build         # los que tienen traducción -> mods/espanol/files/Us/<ruta>
python3 -I tools/spanish_data.py check         # o: check item/ItemInfo, check end_roll
python3 -I tools/spanish_data.py show item/ItemInfo 1.name 1.desc
python3 -I tools/spanish_data.py roundtrip     # cada archivo reconstruido sin traducir == el del disco
```

`FILE` es la ruta sin extensión (`item/ItemInfo`, `end_roll/opening`) o un directorio
(`end_roll`). `build --out DIR` escribe en otro `Us/` (p. ej. una copia del mod para
probar); `build --all` escribe también los no traducidos.

`build` escribe el archivo entero y **sin comprimir** (el juego lee el del mod tal cual,
`src/native/archive.cpp`). **Ida y vuelta**: sin traducción, cada uno de los 31 archivos
sale idéntico, byte a byte, al descomprimido del disco, y también pasando cada cadena por
el camino completo (`resolved()` con el inglés como «traducción»): `roundtrip` lo comprueba.

### Qué mira `check`

Errores (sale con 1): id inexistente o que no es texto; vacía; `%s %d %n %p` distintos o
en otro orden (con sus asteriscos: en `mcard/message`, `%n************` reserva sitio y el
port los quita al rellenar, `src/game/mcard.cpp` `Fill`); `＆` / `＃` distintos; iconos de
botón distintos (①–⑥, flechas, y los Latin-1 que la fuente dibuja como iconos);
carácter que no está en la fuente; escape desconocido; `\n` donde el juego dibuja una
línea (nombres, títulos, roles, rollos…); en el menú sí/no de la tienda, distinto número
de líneas (una por opción); título de más de 24 caracteres (`TitleNameList` tiene
registros fijos); fila del teclado que no tiene 15 teclas (salvo la última) o filas nuevas
con huecos.

Avisos: una línea más ancha que el sitio (tabla de abajo; si no se conoce, la línea
inglesa más ancha de ese tipo en el archivo; anchos de la `.Fnt` del mod, sin escalar);
más líneas de las que caben; cadena en MAYÚSCULAS (salvo `end_roll/ed05_01`, ver abajo);
repetidas traducidas distinto; teclas repetidas en el teclado.

| tipo | dónde se ve | sitio (px de la fuente) |
|---|---|---|
| `item.name` | listas de objetos (creación de personaje, pausa), tienda a 0,82× | 185 (fila de la tienda: de x 86 a 238, a 0,82×) |
| `item.help` | línea de ayuda del menú de objetos (pausa) | 434 (inglés), 2 líneas |
| `item.desc` | recuadro de la tienda y de la creación de personaje, a 0,82× | 338 (277 px de recuadro), 3 líneas |
| `item.use` | ver «Decisiones» | 394 (inglés), 2 líneas |
| `worn` | Récords, accesorios | 44 (inglés) |
| `title` | Récords (centrado), resultados | 115 (inglés); máx. 24 caracteres |
| `role` | placa del rival / quien habla | 200 (como `nombre` de los scripts) |
| `shop.choice` | menú sí/no de la tienda | 219 (inglés) |
| `shop.label` | «Dinero» (centrado, 0,82×) | 60 |
| `shop.got` | aviso al comprar («Has conseguido: %s») | 300 |
| `shop.hint` | pista del pie, a 0,82× desde x 474 | 190 |
| `shop.line` | bocadillo del tendero (no se parte) | 255 (inglés), 2 líneas |
| `mcard`, `mcard.short` | pantallas de guardar / cargar | inglés |
| `roll` | rollo a 1,2× desde la x del archivo | (600 − x) / 1,2: 458 a x 50, 417 a x 100, 308 a x 230 |

## Decisiones

- **Rollos (`.er2`)**: el español tiene **las mismas líneas** que el inglés, una por línea,
  sin `\n`, y **no se tocan la cabecera ni las separaciones**: la duración (`frames`), el
  tiempo que cada línea está encendida (`stay`), la velocidad y el momento de la voz están
  ahí, y la herramienta los copia tal cual. Como el texto sube a velocidad fija y cada línea
  aparece tras su separación en píxeles, cambiar el número de líneas desplazaría todo
  respecto a la narración inglesa y al final (`frames`); por eso no se puede (una línea
  que no cabe se reparte con sus vecinas). El `U+F8F3` que cierra el último texto lo pone
  `build`: la última línea de cada rollo solo tiene ese carácter y no es texto.
- **La carta de Sayo (`ed05_01`)**: en inglés es la carta de una niña, en MAYÚSCULAS y con
  faltas fonéticas («HE SED I CULD HAVE ALL THE RICE-BALLS I CAN EET», «DONT WORRY»,
  «EVRYTHING»): unas cinco faltas, casi una por línea. En español se mantiene el espíritu:
  **mayúsculas, sin tildes ni `¿`/`¡`, y una falta infantil verosímil por línea** (b/v,
  h que falta o sobra, ll/y, c/z/s, qu/k), sin que cueste leerla. Por ejemplo:
  «ME DIJO QUE PODRIA COMER TODAS LAS BOLAS DE ARROZ QUE QISIERA,» / «ASI QUE ME BOY
  CON EL SEÑOR BENIYA.» / «NO TE PREOCUPES.» / «LA FIESTA FUE DIBERTIDA.» / «GRASIAS POR
  TODO.». Es el único texto en mayúsculas (`CAPITALS_OK` en la herramienta).
- **`ed04_01`** tiene una errata en inglés («that would after it's foundation...», falta
  el verbo: «que sacudirían sus cimientos»): se traduce el sentido.
- **Tiendas**: caja normal (en inglés todo va en MAYÚSCULAS), como los bocadillos del
  paso 4; el tendero trata de **usted**. Las 13 tiendas comparten casi todas las frases
  (las repetidas heredan); la 12 es una tienda de prueba en japonés (solo su `THANK YOU!`
  hereda).
- **Tarjeta de memoria (`mcard/message`)**: el port guarda en un directorio
  (`src/native/mcard_native.cpp`), pero las pantallas son las del juego y hablan de la
  tarjeta. Se deja la tarjeta y se usa la terminología oficial de Sony para la PS2 en
  España: «tarjeta de memoria (8MB) (para PlayStation®2)», «ranura para MEMORY CARD 1»
  (MEMORY CARD en mayúsculas, como Sony), «formatear», «archivo de guardado». No se
  adapta nada: los mensajes de tarjeta ausente o sin formato no deberían salir en el port (el
  directorio siempre está), y los que sí salen (guardar, cargar, copiar, borrar,
  sobrescribir, «¿Volver al título?») tienen sentido tal cual. `Y e s` / `N o` son
  botones con letras espaciadas: `S í` / `N o`. `crrupt data` (69) es una errata inglesa.
- **Mensaje de uso de los objetos (`item.use`)**: en el port, `UseItem`
  (`src/game/items_page.cpp`) no lo enseña al usar el objeto con éxito; queda guardado y
  solo sale si el siguiente uso falla (en vez de «no tendría ningún efecto»). No se pudo
  ver en el juego con la entrada programada. Se traduce igual (19 cadenas), en 2 líneas
  como máximo.
- **Roles de `paramlist`**: solo los genéricos, la lista `ROLES` de la herramienta:
  Thug, Magistrate, Warrior, Merchant, Citizen, Foreigner, Wife, Guard, Monk, Child, Girl,
  Traveler, Samurai, Man, Contact, Old lady, Ronin, No-name, Peddler, Student, Killer,
  Character, Lady, Townsperson, Courtesan, Job Broker, Collector, Shady Man, Kidnapper,
  Son, Daughter, Spy, Teacher, Sculptor, Worker, The Count, Carpenter, Steward, Informant.
  Los nombres propios (Kasumi, Kuroha, Dr. Genan, Yoriki…) no se traducen (`check` da
  error). «Magistrate» (17 personajes) son los hombres de la Magistratura: no es «el
  magistrado» del glosario sino un bando; propuesta: «Magistratura» o «Guardia»; lo decide
  el traductor de la tanda 3 (y conviene apuntarlo en el glosario).
- **Teclado del nombre (`CharGlance.txt`)**: el teclado es la primera página del archivo:
  15 teclas por fila, en tres grupos de 5; el juego junta todas las filas en una lista
  (por eso todas menos la última han de tener 15) y enseña 6 filas, desplazándose si hay
  más (`src/game/name_input.cpp`, `CharPage_Parse`, `CharGrid_Draw`). Las 6 filas inglesas
  se dejan como están (letras, cifras y signos ASCII) y se **añaden dos filas**:
  `ÁÉÍÓÚ áéíóú ÑñÜü¡` y `ÀÈÌÒÙ àèìòù Çç¿ªº` (catalán y gallego incluidos; `ª` para
  «Mª»). `¿` se guarda como U+E000 (el U+00BF de la fuente es el botón ✕). El nombre
  admite 14 caracteres y se dibuja con la misma fuente en todas partes.

## Reglas de estilo

Las del paso 4 (`docs/spanish/04_scripts.md`, «Reglas de estilo») y el glosario. Además:

- **Nombres de objeto**: cortos (≤ 185 px; «Dulce de alubia» 128), con mayúscula solo
  inicial («Bola de arroz», «Pescado seco»). Sin artículo.
- **HP / EP → PV / PR**: «Recupera 200 PV.», «PV máx. +100», «PR máx. +1». «Attack /
  Defense Power» → «Ataque» / «Defensa» (glosario).
- **Ayuda y descripción** dicen lo mismo con distintos cortes: la ayuda (`help`) en 2
  líneas anchas, la descripción (`desc`) en 3 líneas estrechas (≤ 338 px). Repartir los
  `\n` para que quepan; un solo espacio tras el punto.
- **Títulos**: ≤ 24 caracteres, cortos (el inglés llega a 115 px): adjetivo o sustantivo
  («Seta», «Inofensivo», «Rey samurái»). Como el protagonista es masculino, en masculino.
- **Roles**: sustantivo con mayúscula inicial («Matón», «Comerciante», «Extranjero»,
  «Guardia»), sin artículo.
- **Rollos**: narrador culto, frases completas; cada línea ≤ el sitio (458 px a x 50); se
  reparte la frase entre las mismas líneas que el inglés.
- **Tiendas**: usted; frases cortas (no se parten; 2 líneas como máximo con `\n`).

## Tarea para un traductor

Entrada: `translations/es/original/data/<ruta>.tsv` (de `extract`). Cada cadena son dos
líneas:

```
# item.desc | 287/339px | objeto 2: Dried fish
2.desc	Fish dried using seawater and sake.\nNon-perishable.\nRestores 400 HP.
```

El comentario da el tipo (tabla de arriba), el ancho del inglés / el sitio, de quién o
dónde es (objeto, tienda y frase con su voz, personaje, rollo con su x y duración) y las
repetidas que heredan. Las repetidas y lo que no es texto no aparecen.

Salida: `translations/es/data/<ruta>.tsv` con «id<TAB>español» para cada id que toque, sin
el inglés, en el orden del archivo de trabajo, con un comentario arriba. Luego `build` y
`check` hasta 0 errores y, si se puede, 0 avisos.

Plantilla de prompt recomendada:

```
Traduce al español de España los textos de datos de Way of the Samurai 2: <TANDA>.
Lee: docs/spanish/05_data.md (secciones «Ids», «Formato de la traducción», «Decisiones»,
«Reglas de estilo» y «Tarea para un traductor»), docs/spanish/04_scripts.md («Reglas de
estilo») y translations/es/GLOSSARY.md.
Entrada: translations/es/original/data/<ARCHIVO>.tsv (si no existe:
python3 -I tools/spanish_data.py extract <ARCHIVO>). Mira también lo ya traducido en
translations/es/data/ para mantener los términos.
Escribe (o amplía, sin tocar lo que ya hay) translations/es/data/<ARCHIVO>.tsv:
«id<TAB>español» para cada id de la tanda, sin el inglés.
Después ejecuta python3 -I tools/spanish_data.py build <ARCHIVO> y
python3 -I tools/spanish_data.py check <ARCHIVO>, y corrige hasta 0 errores; intenta
dejar 0 avisos. No modifiques ningún otro archivo ni hagas commits.
Informa: cadenas traducidas, avisos que queden y por qué, y términos nuevos para el
glosario (no los añadas tú).
```

## Tandas propuestas

Cifras: cadenas distintas por traducir.

1. **107** — objetos que se usan y de encargo: `item/ItemInfo` objetos 6–32 (91: Ginseng…
   Small Bottle; solo los de 6–22 tienen `use`), lo que queda de `ui/GameUI/ShopList`
   (9) y `Accessory/AccessoryPos` (7).
2. **114** — accesorios: `item/ItemInfo` objetos 33–60 (84: Fox Mask… Angel Wings; sin
   `use`) y `menu/Title/TitleNameList` (30).
3. **124** — personajes y guardado: `chara/paramlist` (39 roles) y `mcard/message` (85).
4. **83** — los rollos: `end_roll` salvo `opening` (22 archivos; la carta `ed05_01` según
   «Decisiones»).

`object/ObjectName` no necesita tanda (sale de `ItemInfo`), ni el teclado (hecho).

## Muestra traducida (este paso)

- `item/ItemInfo`: objetos 1–5 (Bola de arroz, Pescado seco, Rábano, Dulce de alubia y la
  bola de arroz podrida), los 4 campos: 20 cadenas. `ObjectName` toma sus nombres.
- `end_roll/opening`: las 7 líneas de la intro.
- `ui/NameInput/CharGlance`: las dos filas nuevas.
- `ui/GameUI/ShopList`: `c0`–`c4` (menús sí/no, «Dinero», «Has conseguido: %s»,
  «③ Salir de la tienda») y 5 frases (`¡Bienvenido!`, `¿Qué le pongo?`, `¿Qué va a ser
  hoy?`, `¿Es esto lo que quiere?`, `¡Gracias!`), que heredan las 12 tiendas.

Total: 37 de 471 cadenas distintas (más las 2 filas del teclado).

## Verificación en el juego

Con una copia del mod (`WOTS2_MODS` con solo `espanol`, `build --out`), partida nueva por
entrada programada (`WOTS2_NEW_GAME=1`, `WOTS2_INPUT`) y capturas (`WOTS2_SHOTS`):

- **Teclado del nombre** (creación de personaje → Nombre): las 6 filas inglesas igual; al
  bajar de la sexta, el teclado se desplaza y salen las dos nuevas, con todas las letras
  bien dibujadas (las mayúsculas acentuadas, comprimidas como en la fuente, y `¿` del paso
  2). Escribiendo con ellas, el nombre queda «MIFUNEÁÀÌÒ».
- **Baúl de la creación de personaje** (`WOTS2_GIVE_ITEMS=3`): la lista con «Bola de
  arroz», «Pescado seco», «Rábano», «Dulce de alubia» y la descripción en 3 líneas; la más
  ancha, «Pescado secado con agua de mar y sake.» (330 px), llega justo al borde del
  recuadro: el sitio de 338 px es real.
- **Intro** (`opening.er2`): las 7 líneas suben con el mismo ritmo que el inglés; la más
  ancha («llega a Amahara, un pueblo sacudido por estos tiempos...», 451 px) acaba en la x
  565 de 640. Tildes y `í` bien.
- **Tienda** (bazar de Otsuka-cho, `WOTS2_AREA=6`, `WOTS2_WARP` a su puerta, de
  `tools/doors.py`): «¡Bienvenido!», «¿Qué va a ser hoy?», «¿Es esto lo que quiere?»,
  «¡Gracias!», los menús «Me lo llevo / Me lo pensaré» y «Aquí tiene / ¡No pienso
  pagar!», «Dinero», «③ Salir de la tienda» (acaba en la x 607), el aviso «Has
  conseguido: Pescado seco» y los nombres y descripciones de los objetos. Las frases sin
  traducir de la muestra siguen en inglés («I'LL TAKE THE MONEY NOW.»).
- **Menú de objetos** (pausa → Elegir objeto, `WOTS2_CARRY`): la línea de ayuda en 2
  líneas («Arroz recién hecho envuelto en alga. / Recupera 200 PV.»).

Sin comprobar: el aviso al recoger del suelo (`ObjectName`), los mensajes de uso, los
títulos, `AccessoryPos`, los roles y la pantalla de guardar (sin traducir aún).
