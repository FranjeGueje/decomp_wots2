# Mod en español, paso 6: lo que dicen los NPC (tareas, `task/alltask`)

Herramienta: `tools/spanish_task.py`. Traducciones: `translations/es/task/<tanda>.tsv`.
Glosario: `translations/es/GLOSSARY.md`. Estilo general: `docs/spanish/04_scripts.md`.

## De dónde sale el texto

Lo que dicen los vecinos, matones, guardias y los que ofrecen trabajos por la calle no
está en los scripts sino en su **tarea** (el programa de cada NPC: `src/game/task.cpp`,
`task_mgr.cpp`, `task_actions.cpp`; `tools/task.py dump <tarea>.bin` la desensambla).
Las 182 tareas van en un solo archivo, `Us/task/alltask` (asset 0x8A), que el juego lee
entero al arrancar (`App_CreateDevices`, `src/native/hle.cpp`) y del que desempaqueta
una tarea cuando un NPC la necesita (`LoadTask`, `src/game/spawner.cpp`).

**El contenedor** (formato propio del juego, no del volumen):

```
u32 número de tareas (182), u32 alineación (64), u32 inicio de los datos (0x300), u32 0
u32 tabla[182]                 = tamaño empaquetado de cada una, redondeado a 16
cada tarea, desde el inicio y alineada a 64:
  u32 empaquetado (bytes de la entrada, estos 8 incluidos), u32 desempaquetado, flujo LZSS
  ceros hasta tabla[i] y hasta la alineación
```

En el orden de la tabla de nombres del ejecutable (0x2D7D10; `tools/task.py`
`names()`). El LZSS es el de `Unpack` (ventana de 4 KB desde 0xFEE; lee un byte más allá
de «empaquetado» y puede escribir dos de más: el juego reserva 4).

**El archivo del mod** es el contenedor tal como lo da el volumen (el `VOLUME.DAT` lo
guarda además comprimido, pero un archivo de `files/` se lee sin más:
`archive::read`, `read_overlays`): `mods/espanol/files/Us/task/alltask`. `build` deja los
bytes del disco de cada tarea sin español y vuelve a empaquetar (LZSS de verdad, voraz,
1,10 MB todo frente a 1,02 MB el disco) solo las que cambian; recalcula tamaños, tabla y
relleno, y mantiene el orden.

**Una tarea**: `u32`, y 11 programas; cada programa, un número de comandos y los
comandos `{índice, op, float segundos, quién1, quién2, longitud del texto, texto, 5 ×
{tipo, valor}}`. El texto es UTF-16; su longitud en bytes va redondeada a 4 (el juego
avanza `longitud & ~3`) y lleva un 0 solo si cabe (con un número par de caracteres no
lo lleva: el juego añade dos bytes a 0 al copiarlo). `build` hace lo mismo.

## Qué comando es texto

| op | comando | tipo | dónde se ve | límites |
|---|---|---|---|---|
| 0x10 | `DrawSerif` | `bocadillo` | bocadillo junto al NPC; **no** se parte: mandan los `\n` | ancho por línea ≤ máx(inglés, 330 px); el inglés llega a 300 y 3 líneas; `%s`/`%S` = nombre del jugador (como mucho uno: con dos el juego deja basura) |
| 0x24 | `DrawTalkSelect` | `eleccion` | ventana de opciones del protagonista, una por línea | mismo nº de líneas; ≤ máx(inglés, 450 px); aquí `%s` no se sustituye |
| 0x2D | `DrawInfoPlate` | `aviso` | placa del HUD, abajo a la derecha | ≤ máx(inglés, 300 px) |
| 0x46 | `SetWorkName` | `encargo` | nombre del trabajo: placa del HUD al aceptarlo, «Trabajo : …» en Ver estado, «… (fracaso)», «Te quedas sin paga: …» | **< 24 caracteres** (si no, el juego no lo guarda); ~200 px; sin `\n` |
| 0x3F | `SetWorkMessage` | `objetivo` | la línea de ayuda de Ver estado mientras dura el trabajo | **≤ 118 caracteres** (el juego lo descarta si su longitud en bytes llega a 0xF0); 3 líneas como mucho |
| 0x58 | `SetOtherMessage` | `estado` | la misma línea de ayuda (los 3 avisos de carterista de `evil_pick_a`: «Te faltan 200 mon…») | < 128 caracteres (búfer de 0x100 bytes); aviso si pasa del inglés |
| 0x05 | `PlayVoice` | `voz` | **no se ve**: 3 comandos de `work_deliver_obj_a` con texto que el juego ignora | no se traduce |

La línea de ayuda de Ver estado (`objetivo`, `estado`) es una caja de 490 px de pantalla a
0,88 (≈ 556 px de la fuente) que corta **por caracteres**, no por palabras, y solo
muestra 3 líneas: poner los `\n` a mano (el inglés usa 2 líneas). `check` simula la caja
y da error si una palabra queda partida o no cabe.

En los bocadillos habla `quién1` a `quién2`: casi siempre el propio NPC al jugador; si
`quién2 = quién1` es un comentario para sí (no espera botón). El protagonista nunca
tiene bocadillos en las tareas: lo que dice son las opciones.

No están en `alltask`: el rótulo con el nombre del NPC encima de la cabeza («Job Broker»,
datos de personajes), los menús y los scripts (pasos 3 y 4).

### Lo que no se traduce

`list` y `extract all` los apartan:

- **Japonés** (`japones`): **221** cadenas, todas en tareas **sin uso**
  (`translations/es/original/task/_japones.tsv`). Las 6 que el filtro antiguo contaba
  de más eran signos de ancho completo («！», «？», un espacio U+3000).
- **Tareas sin uso**: 9 que ninguna entrada de `task/DataList` (asset 0x40, las clases
  de NPC que crea el spawner) nombra: `main_ichikichi1`, `main_kyojiro1`,
  `main_yasuno1`, `normal_boy_a`, `normal_cowardice_b`, `normal_message_ask_a`,
  `normal_message_obj_a`, `normal_walk_madam_c`, `work_fightyakuza_a`. Su inglés casi
  siempre está también en tareas en uso; las 14 cadenas que no, en la tanda
  `38_sin_uso` (opcional). (`DataList` nombra además `task/test.bin` y
  `task/kanatest.bin`, que no existen.)
- **Signos** (`signos`): 353 sin letras («........», «?», «! !»): se quedan.
- **`voz`**: los 3 `PlayVoice` con texto.

## Identificador y repeticiones

Cada cadena se conoce por **`<tarea>:<programa>.<índice>`**, p. ej.
`work_chonin_a:0.256`: el nombre de la tarea (sin `task/` ni `.bin`), el programa
(0–10) y el índice del comando, que es como el propio juego distingue los comandos
(`Task_Goto` salta a un índice) y no cambia porque el disco no cambia. Se lee
directamente en `tools/task.py dump` y en `show`. Se descartó numerar las cadenas
(dependería del filtro) y usar un hash del inglés (ilegible, y no permitiría traducir
distinto la misma frase en dos sitios).

**Deduplicación global**: 11 829 comandos con texto, 7 888 textos distintos; con los
espacios de alrededor de los `\n` y dobles normalizados y sin japonés, signos ni `voz`,
**7 610 cadenas distintas** (7 596 en tareas en uso). Cada una se traduce **una vez**,
con el id de su primera aparición en el orden de las tandas (trabajos, principales,
rumores, Magistratura, Aoto, vecinos; las tareas sin uso al final), y todas las demás
apariciones heredan esa traducción. Si en algún sitio no vale (sobre todo por el
**género**: «Estoy cansado» en boca de una mujer), se añade una línea con el id de esa
otra aparición, que manda sobre la heredada. El archivo de trabajo avisa («OJO: la dicen
hombres y mujeres») cuando la frase sale en tareas de los dos.

## Formato de la traducción

`translations/es/task/<tanda>.tsv` (todas las `.tsv` de la carpeta se leen; los ids son
globales, así que el archivo solo sirve para organizarse), UTF-8:

```
# comentarios y líneas en blanco se ignoran
work_chonin_a:0.256	Frenar a los matones
work_chonin_a:0.255	Los vecinos me han pedido que pare\na unos matones en el Santuario.
```

- Solo español, sin el inglés. `\n` = salto de línea; ninguna otra barra invertida, ni
  tabuladores, ni saltos reales.
- `¿ » º` tal cual (`build` los cambia por los códigos de la fuente, `to_game`).
- Un id que falta se queda en inglés; un id repetido en dos archivos es error.

## Flujo de trabajo

```
python3 -I tools/spanish_font.py                 # una vez: la fuente con ¿ » º (paso 2)
python3 -I tools/spanish_task.py list            # tandas, cadenas, traducidas (--tasks: por tarea)
python3 -I tools/spanish_task.py extract all     # archivos de trabajo (ignorados por git):
#   translations/es/original/task/<tanda>.tsv  + _japones.tsv
# escribir translations/es/task/<tanda>.tsv
python3 -I tools/spanish_task.py check [TANDA…]  # errores y avisos (sale con 1 si hay errores)
python3 -I tools/spanish_task.py build           # mods/espanol/files/Us/task/alltask (--out otro)
python3 -I tools/spanish_task.py show work_chonin_a | work_chonin_a:0.256 …
python3 -I tools/spanish_task.py verify [--pack-all]
```

`verify` comprueba: el contenedor se reescribe byte a byte; cada una de las 182 tareas se
lee y se reescribe byte a byte; `build` **sin traducción da el `alltask` del disco byte
a byte**; con `--pack-all`, las 182 empaquetadas con el LZSS de la herramienta y
desempaquetadas como el juego (con sus límites) dan lo mismo; y el `build` con la
traducción se relee: mismas tareas, programas, comandos y argumentos, y el texto cambia
justo donde dice la traducción.

### Qué mira `check`

Errores: id que no es un comando de texto (o es japonés/signos/voz); vacío; barra
invertida que no es `\n`; `%s`/`%S` distintos del inglés; un `%` en lo que no es un
bocadillo; iconos de botón distintos (②, ③…); carácter que no está en la fuente; en
`eleccion`, otro número de líneas; en `encargo`, 24 caracteres o más o un `\n`; en
`objetivo`, más de 118 caracteres; en `estado`, 128 o más; en `objetivo`/`estado`, más
de 3 líneas en la caja o una palabra partida por la caja.

Avisos: línea más ancha que lo permitido (tabla de arriba); bocadillo de más de 3 líneas
(y más que el inglés); `objetivo`/`estado` con más líneas que el inglés; `estado` más
largo que el inglés; una traducción propia de una repetición cuyo original
(canónico) aún no está traducido. Cada traducción se comprueba también contra el tipo
de las repeticiones que la heredan, si es otro.

## Reglas de estilo (tareas)

Las de `04_scripts.md` («Reglas de estilo») y el glosario, más:

- **Caja normal** (el inglés de las tareas ya la usa). `...` de tres puntos, un espacio
  tras el punto, `¿…?` y `¡…!` siempre, comillas «».
- **Los `\n` de los bocadillos se reparten de nuevo** para que las líneas queden
  parejas y no pasen de ~300 px (el archivo de trabajo da el ancho del inglés); 1–3
  líneas. En opciones, una opción por línea, el mismo número.
- **Trato**: los vecinos, tenderos, mujeres, ancianos, monjes y el intermediario de
  trabajos hablan de **usted** al protagonista (un samurái forastero: «¿Es nuevo en
  Amahara, samurái?», «Pruebe a…»). Los matones de los Aoto, los ronin, los niños y
  los guardias de la Magistratura cuando amenazan **tutean** («¡Lárgate!», «¿Buscas
  pelea?»). Los personajes principales, como en el glosario (Chiyo tutea; Sosuke
  Nakamura, Danpachi, Kakube, Maikaze: usted; Hanzaemon, Goshiro, Genan, Kasumi, Nami:
  tú…).
- **El protagonista es masculino** (opciones en primera persona, secas y dignas:
  «Salvaré al bebé.», «No soy una niñera.»; trata de usted a tenderos y al
  intermediario).
- **Femeninas**: Kyojiro, Kasumi, Otomi, Nami, Chiyo, Oboro, Sayo; y las tareas `lady`,
  `girl`, `madam`, `woman`, `yujo` (el archivo de trabajo pone «probablemente mujer»).
  Cuidado con los adjetivos en primera persona.
- **Registro de Edo** sin anacronismos: matones vulgares («mocosa», «lárgate», «¡Je!»),
  comerciantes zalameros («¡Pasen y vean!», «¡Bienvenido!»), guardias secos y
  autoritarios, aldeanos sencillos. Nada de «vale», «guay», «OK».
- **Nombres de trabajo** (`encargo`): infinitivo corto, < 24 caracteres y ~200 px
  («Buscar al bebé», «Frenar a los matones», «Matar al magistrado»); se leen también
  como «Buscar al bebé (fracaso)» y «Te quedas sin paga: Buscar al bebé».
- **Objetivos** (`objetivo`): primera persona del protagonista, 2 líneas, `\n` a mano
  («Debo encontrar a un bebé. Mi única pista\nes la frase «…».»).
- Nombres propios romanizados como en inglés (Amahara, Amakaze-cho, Kuroha, Hanzaemon…);
  espadas y técnicas tal cual. Lugares y términos: glosario («la Magistratura», «la
  banda Aoto», «el magistrado jefe», «Ver estado»…). Cifras y `mon` como en inglés.
- Adivinanzas y juegos de palabras (las pistas de los trabajos): traducir el sentido
  para que siga apuntando al mismo sitio (comprobar con el resto de la tarea).

## Tarea para un traductor (una tanda por tarea)

Entrada: `translations/es/original/task/<tanda>.tsv` (de `extract`). Cada cadena son dos
líneas:

```
# bocadillo · habla el NPC al jugador · 202 px · repetida 1x (también en work_yakuza_a) · antes: «Just remember that.»
work_chonin_a:0.180	So, shall we review the \nguidelines I just taught \nyou?
```

El comentario da el tipo (tabla de arriba), quién habla y a quién, si `%s` es el nombre
del jugador, el ancho del inglés, cuántas veces se repite (y en qué tareas: la
traducción vale para todas) y, si la línea anterior de la conversación no es la de
encima, cuál es («antes:»). Las cadenas van por tarea (`===== tarea … =====`, con
«probablemente mujer» o «SIN USO») y en el orden de la conversación. Las ya traducidas
salen como `# hecha: id<TAB>español`.

Salida: `translations/es/task/<tanda>.tsv`; si ya existe (la muestra del paso 6 está en
`01_work`–`04_work`, `26_normal` y `34_normal`), **conservar sus líneas** y añadir las
nuevas. Una línea `id<TAB>español` por cada id del archivo de trabajo. Luego `check
<tanda>` hasta 0 errores y, si puede ser, 0 avisos.

Plantilla de prompt:

```
Traduce al español de España la tanda <TANDA> del texto de los NPC de Way of the
Samurai 2.
Lee: docs/spanish/06_tasks.md (secciones «Qué comando es texto», «Formato de la
traducción», «Reglas de estilo (tareas)» y «Tarea para un traductor»), las «Reglas de
estilo» de docs/spanish/04_scripts.md y translations/es/GLOSSARY.md.
Entrada: translations/es/original/task/<TANDA>.tsv (si no existe:
python3 -I tools/spanish_task.py extract <TANDA>).
Escribe translations/es/task/<TANDA>.tsv: una línea «id<TAB>español» por cada id de la
entrada, sin el inglés, con \n para los saltos de línea. Si el archivo ya existe,
conserva sus líneas y añade las que faltan.
- Bocadillos: reparte los \n para que ninguna línea pase de ~300 px (como mucho
  3 líneas); opciones: una por línea, las mismas que en inglés.
- Conserva %s (nombre del jugador) e iconos; nombres de trabajo < 24 caracteres;
  objetivos en 2 líneas con \n.
- Usted de vecinos/tenderos al protagonista; tú de matones, ronin y niños; el
  protagonista es masculino; mira el género de quien habla («probablemente mujer»,
  «OJO: la dicen hombres y mujeres»): si una frase repetida no vale para todos, usa
  una forma neutra o añade una línea propia con el id de la otra aparición.
Después ejecuta python3 -I tools/spanish_task.py check <TANDA> y corrige hasta 0
errores; intenta dejar 0 avisos (acorta o mueve los \n). No modifiques ningún otro
archivo ni hagas commits.
Informa: cadenas traducidas, avisos que queden y por qué, ids con línea propia por
género, y términos nuevos que convendría añadir al glosario (no los añadas tú).
```

## Tandas

Orden: trabajos (`work_*`), personajes principales (`main_*`), rumores (`news_*`),
Magistratura (`magistrate_*`, `magistoka_*`), Aoto y maleantes (`evil_*`), vecinos
(`normal_*`); dentro de cada grupo, en el orden del archivo. Una tanda reúne tareas
enteras hasta ~200 cadenas (máx. 250) sin mezclar grupos; las tareas enormes de los que
dan trabajos (`work_bugyo_a` en la Magistratura, `work_chonin_a` el intermediario de
Amakaze-cho, `work_yakuza_a` en los Aoto; 300–500 cadenas) se parten, por donde empieza
un programa si hay uno cerca. Las tandas salen solo del disco (no de las traducciones):
`list` las da siempre igual. Entre paréntesis, cadenas nuevas de cada tarea.

| tanda | cadenas | tareas |
|---|---|---|
| 01_work | 200 | `work_assassin_obj_a` (21), `work_broker_obj_a` (38), `work_bugyo_a` (141) |
| 02_work | 200 | `work_bugyo_a` (170), `work_chonin_a` (30) |
| 03_work | 200 | `work_chonin_a` (200) |
| 04_work | 124 | `work_chonin_a` (124) |
| 05_work | 234 | `work_collector_obj_a` (144), `work_deliver_asis_a` (11), `work_deliver_obj_a` (34), `work_dispose_obj_a` (45) |
| 06_work | 227 | `work_dispose_obj_b` (36), `work_fight_bugyo_a` (5), `work_hunting_obj_a` (42), `work_informant_a` (71), `work_judgment_obj_a` (19), `work_kidnapping_obj_a` (54) |
| 07_work | 205 | `work_lostarticle_obj_a` (23), `work_message_ask_a` (28), `work_message_obj_a` (13), `work_mob_bugyo_a` (16), `work_mob_yakuza_a` (7), `work_pick_obj_a` (118) |
| 08_work | 200 | `work_rescue_obj_a` (15), `work_revenge_obj_a` (22), `work_robber_obj_a` (16), `work_search_obj_a` (77), `work_stingy_a` (11), `work_training_bouncer_a` (9), `work_yakuza_a` (50) |
| 09_work | 234 | `work_yakuza_a` (234) |
| 10_main | 196 | `main_chiyo1` (95), `main_danpachi1` (57), `main_dojima1` (36), `main_follower1` (8) |
| 11_main | 224 | `main_genan1` (83), `main_goshiro1` (60), `main_kasumi1` (30), `main_kasumi_runaway` (4), `main_kurikichi1` (47) |
| 12_main | 212 | `main_kusaburo1` (42), `main_master1` (103), `main_mitsugo1` (67) |
| 13_main | 201 | `main_nakamura1` (57), `main_nakamura_around1` (16), `main_oboro1` (4), `main_sayo1` (24), `main_sayo1sub` (17), `main_shinobikusa1` (3), `main_tsubohachi1` (80) |
| 14_news | 230 | `news_amabou_1` (47), `news_boy1` (3), `news_bushido1` (6), `news_carpenter_1` (85), `news_carpenter_assi_1` (19), `news_doshin1` (24), `news_madam1` (46) |
| 15_news | 194 | `news_man1` (28), `news_man_b1` (24), `news_man_ge_before` (29), `news_mister1` (22), `news_pupil1` (22), `news_pupil2` (34), `news_pupil3` (35) |
| 16_news | 211 | `news_pupil4` (70), `news_pupil5` (83), `news_ronin1` (18), `news_woman1` (21), `news_yakuza_a1` (19) |
| 17_news | 129 | `news_yakuza_b1` (17), `news_yakuza_c1` (3), `news_yakuza_cashcase1` (5), `news_yakuza_ev` (43), `news_yakuza_line3a` (5), `news_yakuza_line4a` (4), `news_yakuza_line4b` (4), `news_yakuza_posse_a` (7), `news_yakuza_posse_b` (9), `news_yujo1` (32) |
| 18_magistrate | 211 | `magistoka_control_a` (78), `magistoka_control_b` (45), `magistoka_control_c` (15), `magistoka_control_d` (46), `magistoka_enter_a` (27) |
| 19_magistrate | 199 | `magistoka_enter_b` (18), `magistrate_arrest_a` (8), `magistrate_beginner_a` (31), `magistrate_control_a` (68), `magistrate_control_b` (74) |
| 20_magistrate | 221 | `magistrate_control_night_a` (120), `magistrate_invite_a` (49), `magistrate_observer_a` (52) |
| 21_magistrate | 118 | `magistrate_observer_b` (47), `magistrate_prisoner_a` (21), `magistrate_room_a` (50) |
| 22_evil | 182 | `evil_beginner_a` (30), `evil_executioner` (12), `evil_friendly_a` (44), `evil_friendly_b` (54), `evil_hottemper_a` (42) |
| 23_evil | 224 | `evil_hottemper_night_a` (116), `evil_invite_a` (41), `evil_invite_b` (67) |
| 24_evil | 196 | `evil_mug_a` (47), `evil_pick_a` (61), `evil_room_a` (29), `evil_room_b` (59) |
| 25_evil | 179 | `evil_swagger_a` (63), `evil_swagger_b` (68), `evil_swagger_big_a` (48) |
| 26_normal | 248 | `normal_area_a` (29), `normal_barker_a` (13), `normal_barker_b` (13), `normal_barker_c` (12), `normal_beginner_a` (9), `normal_beginner_area_a` (42), `normal_beginner_b` (6), `normal_beginner_c` (18), `normal_beginner_d` (9), `normal_beginner_e` (17), `normal_bushido_a` (80) |
| 27_normal | 217 | `normal_bushido_b` (50), `normal_bushido_smith_a` (63), `normal_collision_a` (58), `normal_collision_b` (46) |
| 28_normal | 218 | `normal_cowardice_a` (61), `normal_cowardice_night_a` (72), `normal_damage_a` (28), `normal_dutiful_a` (57) |
| 29_normal | 246 | `normal_dutiful_assi_a` (10), `normal_gambler_a` (104), `normal_gossip_a` (59), `normal_gossip_assi_a` (12), `normal_gyosho_a` (61) |
| 30_normal | 235 | `normal_lady_a` (31), `normal_lady_b` (39), `normal_lady_c` (30), `normal_lady_d` (33), `normal_mister_a` (54), `normal_mister_b` (48) |
| 31_normal | 188 | `normal_mysteryman_a` (29), `normal_phantom_a` (21), `normal_priest_a` (32), `normal_priest_b` (79), `normal_priest_battle_a` (27) |
| 32_normal | 210 | `normal_priest_c` (75), `normal_pupil_a` (87), `normal_pupil_yard_a` (48) |
| 33_normal | 240 | `normal_ronin_a` (58), `normal_ronin_b` (68), `normal_room_a` (24), `normal_shonin_a` (90) |
| 34_normal | 214 | `normal_shopper_a` (38), `normal_stall_a` (23), `normal_walk_a` (36), `normal_walk_b` (76), `normal_walk_boy_a` (41) |
| 35_normal | 191 | `normal_walk_boy_b` (81), `normal_walk_girl_a` (85), `normal_walk_girl_b` (25) |
| 36_normal | 221 | `normal_walk_girl_c` (65), `normal_walk_madam_a` (49), `normal_walk_madam_b` (49), `normal_walk_nonjap_a` (26), `normal_walk_nonjap_b` (32) |
| 37_normal | 217 | `normal_walk_woman_a` (28), `normal_walk_woman_b` (37), `normal_walk_woman_c` (47), `normal_walk_woman_d` (48), `normal_yujo_a` (33), `normal_yujo_b` (24) |
| 38_sin_uso | 14 | `main_kyojiro1` (7), `main_yasuno1` (7) — **sin uso**, opcional |

No son tandas: `_japones.tsv` (221, sin uso) y los signos.

Por tipo (en uso): 6925 bocadillos, 334 opciones, 182 avisos, 125 objetivos, 27 nombres
de trabajo, 3 `estado`.

## Muestra traducida (paso 6)

189 cadenas distintas (335 comandos con la herencia): `normal_beginner_area_a` entera
(el guía de cada barrio), `normal_stall_a` entera (el puesto de soba de Otemon) y, de
`work_chonin_a` (el intermediario de trabajos de Amakaze-cho), la presentación, el
tutorial, el trabajo «Frenar a los matones» y el trabajo «Buscar al bebé» con sus 24
pistas. En `01_work`–`04_work`, `26_normal` y `34_normal`.

## Verificación en el juego

Con una copia del mod en el directorio temporal (`WOTS2_MODS`), partida nueva sin intro
(`WOTS2_NEW_GAME=1 WOTS2_SKIP_INTRO=1 WOTS2_AREA=n`), el jugador llevado junto al NPC
(`WOTS2_WARP="1000:x,z>tx,tz"`), entrada programada (Círculo para hablar, Cruz para
pasar y elegir la primera opción), capturas (`WOTS2_SHOTS`) y `WOTS2_DUMP_ACTORS=1`
(el log pone cada `[say]` y dónde está cada NPC; los NPC se reconocen por el tamaño de
su tarea):

- **Amakaze-cho** (`WOTS2_AREA=1`; el intermediario, `work_chonin_a`, en -6.3, 28.5):
  primera charla: «¿Qué voy a hacer...?», «Ah, hola, samurái.», «Disculpe, pero ¿es la
  primera vez que trabaja aquí?» (3 líneas) y la ventana de opciones «Ya tengo
  experiencia. / Sí, es la primera vez.»; segunda charla: el trabajo del bebé, la
  opción «Salvaré al bebé. / No soy una niñera.», la pista «Al secuestrador le oyeron
  decir la frase: «El sonido de las campanillas de viento».» (324 px, la línea más
  ancha de la muestra: el bocadillo la muestra entera), la placa del HUD **«Buscar al
  bebé»**, y en Ver estado **«Trabajo : Buscar al bebé»** y la línea de ayuda «Debo
  encontrar a un bebé. Mi única pista / es la frase «El sonido de las campanillas de
  viento».» en sus dos líneas. Tildes, `ñ`, `¡`, `¿` (U+E000) y «» bien.
- **Otemon** (`WOTS2_AREA=0`; el guía, `normal_beginner_area_a`, en 2.4, -50.4):
  «¿Es nuevo en Amahara, samurái?», «Esta es la Puerta Otemon, / la entrada a Amahara.
  Aquí / hay mercaderes como yo.»… El guía es un anciano.

Qué trabajo y qué pista ofrece el intermediario depende del azar del juego (en estas
pruebas, siempre el mismo con la misma entrada).
