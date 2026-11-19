# Glosario de la traducción al español

Términos fijados en `menutext.tsv` (paso 3) y en los scripts (paso 4,
`translations/es/script/`). Toda traducción nueva debe usar los mismos. Español de España, neutro; se tutea al jugador («Elige», «No puedes»).
Los nombres propios japoneses se dejan como en la versión inglesa (sin tildes ni
macrones añadidos: `Amakaze-cho`, `Mumei-tou`).

## Interfaz y botones

| inglés | español | notas |
|---|---|---|
| Select | Elegir | en pistas de botón: «④ Elegir» |
| Back | Atrás | |
| Cancel | Cancelar | |
| Done | Listo | |
| Enter | Aceptar | |
| Delete | Borrar | |
| Yes / No | Sí / No | |
| On / Off | Sí / No | en Opciones |
| Settings | Opciones | (el título «Settings» es un gráfico, no texto) |
| Reset | Reiniciar | |
| End | Fin | |
| Quit | Salir | |
| Exit | Salir | |
| Return to Game | Volver al juego | |
| Pause Screen | Menú de pausa | (el rótulo «PAUSE» es un gráfico) |
| Status Check | Ver estado | |
| Loading | Cargando | |
| Page N | Pág. N | |
| Skip this event? | ¿Saltar esta escena? | event = escena |
| Records | Récords | |
| Start a new game | Empezar partida nueva | |
| Points / pts | Puntos / ptos | |

## Personaje y combate

| inglés | español | notas |
|---|---|---|
| HP | PV | Puntos de Vida |
| EP | PR | Puntos de Resistencia (el código lo llama *vigour*: 10–15 cuentas, se recupera durmiendo). Decidido por el usuario; también en los scripts: «¡PV +600!», «¡PR +4!» |
| Endurance | Resistencia | |
| Dur / Durability | Dur / Durabilidad | de la espada |
| Att / Attack | Atq / Ataque | |
| Def / Defense | Def / Defensa | |
| Qual / Quality | Cal / Calidad | |
| Kills | Bajas | |
| Total Kills | Bajas totales | |
| Instant Kills | Bajas de un golpe | |
| Stance | Postura | |
| Top / Center / Bottom / Side | Alta / Media / Baja / Lateral | posturas |
| One / 2 hand | 1 mano / 2 manos | posturas |
| Ninja / Fencing | Ninja / Esgrima | posturas |
| technique, move | técnica | «Ver técnicas», «Has aprendido %s» |
| scroll | pergamino | |
| Float / Break / Crush / Throw | Alza / Rompe / Aplasta / Lanza | etiqueta del tipo de golpe |
| Charge | Cargar | en la notación de botones |
| J (jump) | Ｓ (salto) | en la notación de botones, ancho completo |
| or | ｏ | ídem |
| Finishing Blow | Golpe de gracia | también el nivel de dificultad |
| Easy / Normal / Hard | Fácil / Normal / Difícil | |
| link (techniques) | enlazar | |
| upgrade | mejorar | |

## Objetos y espadas

| inglés | español |
|---|---|
| Sword | Espada |
| Items | Objetos |
| Equip / Remove | Equipar / Quitar |
| Ready (a sword) | Empuñar |
| Drop | Tirar |
| Use | Usar |
| Take out | Sacar |
| Change order | Cambiar orden |
| Sword Safe | Armero |
| Item Box | Baúl |
| Safe Selection | Elegir almacén |
| Money / mon | Dinero / mon (moneda, se deja) |
| Job | Trabajo |
| Head / Clothes / Decoration | Cabeza / Ropa / Adorno |
| accessory | accesorio |
| mask | máscara |

## Tiempo

| inglés | español |
|---|---|
| Early Morning / Morning / Afternoon / Evening / Late Night | Amanecer / Mañana / Tarde / Anochecer / Noche |
| August 21st | 21 de agosto |
| Day | Día |
| Amahara Festival Day | Fiesta de Amahara |

## Lugares

| inglés | español |
|---|---|
| Amahara | Amahara |
| Otemon Gate | Puerta Otemon |
| Amakaze-cho, Otsuka-cho, Numata-cho, Kakinuma-cho, Shikano-cho | igual |
| Magistrate's Office | Magistratura |
| Aoto Gang Headquarters | Cuartel de los Aoto |
| Amahara Shrine | Santuario de Amahara |
| Edge of Town | Afueras |
| Outside Amahara | Fuera de Amahara |
| Home / Leave house | Casa / Salir de casa |
| Tea House | Casa de té |
| Restaurant | Restaurante |
| Inn / Amakaze Inn | Posada / Posada Amakaze |
| Pub | Taberna |
| Textiles | Telas |
| Jewelry Store | Joyería |
| Fancy Goods Store | Bazar |
| General Store | Tienda |
| Liquor Store | Bodega |
| Green-grocer | Verdulería |
| Clinic | Médico |
| Pharmacy | Botica |
| Bath House | Baños |
| Blacksmith | Herrería |
| Jail | Cárcel |
| Dojo | Dojo |

## Dormir (menú de casa)

Take a Nap / Lie down / Sleep a bit / Sleep / Deep Sleep → Echar la siesta / Tumbarse /
Dormir un poco / Dormir / Dormir a fondo.

## Historia (scripts, paso 4)

Estilo: ver «Reglas de estilo» en `docs/spanish/04_scripts.md` (caja normal aunque el
inglés vaya en MAYÚSCULAS, tú/vosotros entre iguales, usted de comerciantes a clientes,
tartamudeos «Q-quién», «...» de tres puntos, un solo espacio tras el punto).

| inglés | español | notas |
|---|---|---|
| samurai | samurái (pl. samuráis) | nombre común, con tilde (RAE) |
| ronin | ronin (pl. ronin) | |
| Aoto Gang | la banda Aoto / los Aoto | el cuartel: «Cuartel de los Aoto» (menús) |
| Yakuza Boss | el jefe yakuza | |
| Magistrate's Office | la Magistratura | |
| Chief Magistrate | el magistrado jefe | |
| Magistrate | el magistrado | |
| Shogun / Shogunate | el shogun / el shogunato | |
| rice ball | bola de arroz | (onigiri) |
| mon | mon | moneda, no se traduce |
| brat (Sayo) | mocosa, cría | |
| Dr. Genan | el doctor Genan | |
| HP +400! | ¡PV +400! | avisos del HUD (`UI.AddMessage`) |
| EP +2! | ¡PR +2! | |

**Nombres propios**: como en la versión inglesa, sin tildes ni cambios: Sayo, Kyojiro,
Hanzaemon, Kasumi, Goshiro, Soma, Yasuno, Maikaze, Danpachi, Kuroha, Nakamura, Genan,
Takanuma, Muto, Nami, Otomi, Chiyo, Sosuke, Kagenuma; los tres matones de los Aoto:
Ichikichi (`itikiti` en los scripts), Nihei (`nihei`, tartamudea) y Santa (`santa`).
Lugares: Amahara, Amakaze, Shikano-cho… (ver «Lugares»).

## Decisiones fijadas (tandas de scripts)

- **El protagonista es masculino** (decisión del usuario): «quieto», «te detendremos», «chaval». Sin formas femeninas ni «la protagonista».
- stray samurai → «samurái callejero» (juego de palabras con «gato callejero»).
- No-Name from Amakaze → «la sin nombre de Amakaze» (apodo de la niña muda, Sayo).
- O-kyo (apodo de Kyojiro que usa Ichikichi) → se deja «O-kyo».
- bodyguard → «guardaespaldas».
- Tratamiento: Sosuke Nakamura (magistrado) y Danpachi hablan de «usted» al protagonista; Danpachi tutea a Maikaze y a la niña; Chiyo tutea.
- Clínica (tanda 3): Genan tutea al protagonista y a Chiyo, usted a los pacientes; la enfermera Oboro usa usted con Genan y con el protagonista. Nombre propio: Oboro.
- «la pequeña sin nombre» (little No-Name); «mochi de pasta de alubia» (bean-jam rice cakes); «sede de la gran banda Aoto» en diálogo (menús: «Cuartel de los Aoto»); en diálogo «la clínica» / «el doctor Genan».
- Interjecciones de Genan: «Ja», «Hum». Nihei tartamudea («T-tú de v-verdad…»).
- Tiendas: el protagonista trata de «usted» a los tenderos («Déjelo», «Hágalo, por favor»). Gritos con tartamudeo: «¡T-tú!», «¡S-alguien!».
- Comida: sopa de miso, almuerzo de sashimi, ñame rallado con natto, fideos de gelatina, dango, mochi, cuenco.
- Herrería (Dojima): «Tasar» = appraise («Tasar el título», «Tasar historial»); atributos «Ataque », «Defensa », «Calidad », «Durabilidad », «Técnica » con espacio final.
- Yukaku → «posada de Amakaze» en menús; en diálogo «nuestras chicas». Guardia de la cárcel: dōshin / «el guardia».
- Tratamientos (tanda 4): Hanzaemon y Goshiro tutean al protagonista; Sosuke usa usted con el protagonista y tú con Goshiro; Kusaburo (vendedor ambulante de medicinas) usa usted con el protagonista, que le tutea. Sayo: «la niña».
- Expresiones: «bajo la bota» (magistrados), «huele a chamusquina». Maikaze: «mensajera» (usa a la niña de mensajera).
- Kyojiro es **femenina** (el inglés dice «She loves this kind of thing»): usar género femenino al hablar de ella.
- rub out → «liquidar»; protection money → «dinero de protección»; «calaña» (his kind); Maikaze trata de usted al protagonista.
- ryo y mon: monedas, sin traducir. Soma: droga (nombre propio). Yasuno: magistrado corrupto (el hablante `kureemon` se trata como Yasuno); Nishino: ronin; Otomi y Kasumi: femeninas. Yasuno tutea al protagonista.
- Juego de palabras Sayo/Sayonara: «¿Sayo? ¿Sayonara? ¿Adiós?».
- `yositaka` = el magistrado jefe Kuroha («el magistrado jefe»; «el magistrado» en corto): usted al protagonista, tú a Goshiro. Yasuno usa usted con el magistrado jefe y tú con Hanzaemon.
- «samurái de tres al cuarto» (bum), «timar» (rip off), «la altanera» (uppity wench), «puesto de guardia» (guardhouse), Jirocho (nombre propio).
- Kasumi y el protagonista se tutean. wolfsbane → «acónito». «el Chief» sin más: según contexto, Hanzaemon («el jefe») o el magistrado jefe Kuroha; Goshiro lo trata de usted.
- Nami (camarera): femenina. Soma sin artículo en diálogo. Interjecciones: «¡Iiih!» (grito femenino), «¡Aaaah!», «¡Ja, ja!», «¡Je, je!». «escoria de los Aoto», «samurái molesto». Beniya: nombre propio.
