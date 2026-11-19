# Mod en español, paso 1: glifos de la fuente

Herramienta: `tools/font_info.py` (lee `extracted/VOLUME.DAT`, o `--fnt`/`--pim`;
`--list` lista todos los glifos, `--png DIR` vuelca las texturas).

## Formato

- `Us/Font/Samu2.Fnt`: `u16 count` + `count` × `FontGlyph` de 10 bytes
  (`include/engine/font.h`), ordenados por código UTF-16; `Font_FindGlyph` hace
  búsqueda binaria. El ancho del glifo es también su avance (no hay kerning).
- `Us/Font/Samu2.Pim`: dos descriptores de textura, ambos PSMT8H (`psm=0x1B`),
  píxeles de 8 bits en orden de filas normal (sin swizzle).
  - **Textura 0**, 512×1024, 4 paletas. Glifos de 2 bits empaquetados por planos
    de bits: la paleta N (campo `clut` = 4·N) muestra los bits 2N..2N+1, así que
    cada texel sirve a hasta cuatro glifos distintos. Aquí están los kanji/kana.
  - **Textura 1**, 512×512, 1 paleta de 256 colores. Aquí están el ASCII, el
    Latin-1 y los iconos (flechas, botones de mando, ①–⑥).

## Hallazgos

- 2499 entradas, 2493 códigos distintos, U+0020..U+FFE5 (1970 kanji, 179
  kana/puntuación CJK, 95 ASCII, 95 Latin-1, 89 de ancho completo, 35 símbolos,
  20 griegas, 8 Latin extendido). Códigos duplicados: U+002D, U+2019, U+201D,
  U+2026, U+FF3F.
- **ASCII imprimible completo** (95). Latin-1 completo salvo U+00A0.
- Glifos latinos: ~17–21 px de alto (`a` 8×18, `M` 12×19, `0` 11×18); kanji
  21×22/21×23. Altura de línea 22 px.
- Español, presentes y con el dibujo correcto: `á é í ó ú Á É Í Ó Ú ñ Ñ ü Ü ¡ «`.
- **Presentes pero con otro dibujo** (el juego reutiliza esos códigos para
  iconos):

  | código | debería ser | se dibuja |
  |---|---|---|
  | U+00B8 `¸` | cedilla | → |
  | U+00B9 `¹` | superíndice 1 | ← |
  | U+00BA `º` | ordinal masculino | ↑ |
  | U+00BB `»` | comillas latinas | ↓ |
  | U+00BC–U+00BE `¼ ½ ¾` | fracciones | ○ □ △ |
  | U+00BF `¿` | interrogación de apertura | ✕ (botón) |
  | U+00A7 `§` | sección | ∞ |

  Es decir: **faltan de verdad `¿` y `»`** (y `º`, útil para «nº»). `menu/menutext.txt`
  no usa esos códigos; falta comprobar si los usan otros textos (guiones, tareas)
  como iconos de botón antes de redibujarlos.

## Espacio libre para glifos nuevos

- Textura 0: planos 0 y 1 llenos (~90 %); plano 2 con 205 glifos, filas
  207–1023 libres; **plano 3 (paleta 3, `clut` 12) vacío por completo**:
  512×1024 a 2 bits, ~880 celdas de 24×24. La paleta 3 ya está en el archivo.
- Textura 1: 223 glifos, filas 220–511 libres (~237 celdas de 24×24) y paleta
  de 256 colores, el mismo estilo que el resto del alfabeto latino.

## Recomendación para el paso 2

Las vocales acentuadas, `ñ`, `ü` y `¡` ya funcionan: el texto traducido puede
escribirlas tal cual en UTF-16. Para `¿` y `»` (y `º`), dibujar los glifos en la
zona libre de la textura 1 (filas ≥ 220) con la paleta y el tamaño de los
latinos, y darles códigos nuevos (p. ej. del área privada, U+E000…) insertados en
orden en la tabla `.Fnt`; luego, al generar los textos del mod, sustituir `¿`
por ese código. Así no se rompen los iconos de botón que usen U+00BF. Los
archivos irían en `mods/espanol/files/Us/Font/`. Alternativa: redefinir U+00BF
como `¿` si se confirma que ningún texto lo usa como icono.
