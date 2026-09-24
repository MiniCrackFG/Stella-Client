# Auditoría de Stella Client

Informe de bugs priorizado. Estado: `pendiente` / `en curso` / `hecho`.

## 🔴 Críticos (1–6)

### 1. Inyección HTML con contenido remoto → fuga de tokens de Microsoft — `hecho`
- **Dónde:** `ui/app.js` inserta datos remotos con `innerHTML` sin escapar (descripciones de mods, `motd.clean` de servidores, nombre/icono de instancia); `ui/index.html` no define CSP.
- **Causa:** cualquiera puede publicar un proyecto en Modrinth o controlar un servidor; un `<img onerror=...>` en esos datos ejecuta JS en el webview, que expone `pywebview.api`, incluida `get_auth()` con `mc_access_token` y `refresh_token`.
- **Arreglo:** helpers `escapeHtml()`/`jsArg()` para todo dato remoto y `get_auth()` devolviendo solo `{username, uuid}`. La CSP que se añadió al principio se descartó (ver incidente del 23-sep): rompía el puente de pywebview.

### 2. El botón PLAY puede quedarse bloqueado para siempre — `hecho`
- **Dónde:** `api.py` `launch()` → `run()` sin `try/finally`; `_launch_status` solo llega a `"stopped"` si `launch_minecraft()` retorna sin excepción.
- **Causa:** cualquier fallo (versión inexistente, java inválido, red caída) mata el hilo; `launch()` ya devolvió `ok` y la UI queda en "⏳ Launching..." con el botón deshabilitado.
- **Arreglo:** `try/except/finally` con estado `"error"` + mensaje; la UI lo muestra y rehabilita el botón.

### 3. Se instalan mods incompatibles con la versión elegida, sin avisar — `hecho`
- **Dónde:** `mods.get_mod_versions()` devuelve `versions[0]` si no hay versión para `mc_version`; `search_modrinth()` no filtra por versión de juego; `get_trending_mods()` ignora `version`; el `<select id="mod-sort">` nunca se envía.
- **Causa:** el filtro de versión es decorativo; se descarga un jar para otra MC y Fabric lo rechaza al arrancar.
- **Arreglo:** facet `versions:<mc_version>` en search/trending, sin fallback ciego en `get_mod_versions` (devolver error visible) y conectar `mod-sort` a `index`.

### 4. Resource Packs y Shaders van a la carpeta equivocada y desaparecen — `hecho`
- **Dónde:** `mods.get_mods_dir()` devuelve siempre `mods/` y `get_installed_mods()` hace `glob("*.jar")`.
- **Causa:** los `.zip` de resourcepack/shader se guardan en `mods/`, Minecraft no los lee y la pestaña Installed los ignora.
- **Arreglo:** carpeta por tipo (`resourcepacks/`, `shaderpacks/`, `modpacks/`), listar extensiones según tipo.

### 5. Forge está roto y falla en silencio — `hecho`
- **Dónde:** `mods.search_forge()` devuelve entradas sin `mod_id`; `download_forge()` es un stub que solo loguea; `api.download_mod()` no devuelve error.
- **Causa:** la UI ofrece "Forge" pero pulsar Download no hace nada ni avisa.
- **Arreglo:** retirar la opción de la UI y devolver error explícito desde la API.

### 6. Detección de "jugando" con falsos positivos y sin reset — `hecho`
- **Dónde:** `api._detect_java()` busca cualquier proceso llamado "java" durante ~120 s.
- **Causa:** un IDE, servidor u otro launcher provoca "Playing" falso; si la instalación tarda más de ~2 min el detector muere y el estado queda en "launching" toda la partida.
- **Arreglo:** lanzar con `subprocess.Popen`, guardar el PID y seguir ese proceso (`poll()`), sin ventana de tiempo.

## 🟠 Medios (7–14)

### 7. Registro de mods global en vez de por instancia (migración muerta) — `hecho`
- **Dónde:** `mods.py` usaba `~/.stellaclient/instances/installed_mods.json` aunque cada instancia tenga su `mods_dir`; `delete_mod` no borraba la entrada; `ensure_default_instance()` migraba a una ruta que mods.py no leía.
- **Arreglo:** `get_registry_file()` guarda el registro junto a las carpetas de la instancia activa; `remove_installed_mod_info()` limpia al borrar; el registro antiguo se adopta solo la primera vez que una instancia no tiene el suyo (sin pérdida de datos) y se retiró el `shutil.move` inútil de `ensure_default_instance`.

### 8. Descargas no atómicas ni verificadas — `hecho (adelantado con #3/#4)`
- **Dónde:** `download_mod_with_deps` y `_ensure_fabric_api_in` escriben directo al `.jar` final.
- **Causa:** un corte deja un jar truncado que `_is_mod_installed` da por bueno.
- **Arreglo:** `.part` + `os.replace()`, validar `Content-Length`/checksum y borrar el temporal al fallar.

### 9. `delete_mod` sin sanear el nombre — `hecho (adelantado con #4)`
- **Dónde:** `mods.delete_mod(filename)` hace `mods_dir / filename` + `unlink()`.
- **Arreglo:** `Path(filename).name` y comprobar que el destino siga dentro de la carpeta.

### 10. Borrar la instancia activa deja la config rota — `hecho`
- **Dónde:** `instances.delete_instance()` no reasignaba `current_instance`; `launch()` guardaba el `minecraft_dir` de la instancia en config.
- **Arreglo:** al borrar la activa se reasigna otra, o se crea la `default` si no queda ninguna; se limpia `STELLA_MODS_DIR` si apuntaba a la carpeta borrada, y la UI refresca home/versiones/mods al borrar.

### 11. `instances.json`/`config.json`: lectura sin validar y escritura no atómica — `hecho`
- **Dónde:** `instances._load()` sin `try`; escrituras en sitio.
- **Arreglo:** nuevo `launcher/storage.py` con `load_json()` (tolerante: corrupto → valores por defecto) y `save_json()` (temporal + `os.replace` + `fsync`). Lo usan `minecraft` (config y auth), `instances.json` y el registro de mods. `load_settings()` además mezcla los valores por defecto y descarta entradas de instancia incompletas.

### 12. Paginación inconsistente y rota con búsquedas — `hecho`
- **Dónde:** `PAGE_SIZE = 15` frente a `limit=20` en `search_modrinth`; `refreshBrowse()` forzaba `off = 0` cuando había query (Next/Previous no hacían nada al buscar).
- **Arreglo:** `limit` unificado a 15 y el offset pasa explícito por parámetro; `runBrowseSearch()` centraliza búsqueda/offset y `installMod` conserva consulta y página.
- **Verificado en navegador:** con 30 resultados simulados, página 2 de una búsqueda muestra los resultados 16-30 (antes se quedaba en la 1).

### 13. Ajustes y endpoints muertos que engañan — `hecho`
- **Dónde:** `smooth_rendering` no se leía, `mod-sort` no se usaba, y `API.move_window`, `API.install_stella_mod`, `minecraft.clear_offline_account` y `mods.set_stella_mod_dir` no tenían llamadores.
- **Arreglo:** `Smooth Rendering` ahora funciona de verdad. Con el ajuste **desactivado** (`body.no-smooth`) se quitan animaciones y transiciones CSS, el fondo de estrellas se pinta **una sola vez** (fotograma estático, sin bucle `requestAnimationFrame`) y la luna se queda quieta; con el ajuste activo vuelve todo a animarse. La casilla viene marcada por defecto (comportamiento de siempre). Se eliminó también el código muerto: `API.move_window`, `API.install_stella_mod`, `clear_offline_account` y `set_stella_mod_dir`.
- **Ojo (corregido en el momento):** la primera versión ocultaba el canvas con CSS, así que con el ajuste en `false` el fondo quedaba vacío y la app parecía "plana". Ahora se mantiene el aspecto y solo se para la animación.
- **Verificado en navegador:** desactivado → canvas visible y pintado, idéntico tras 1,2 s (sin bucle), luna quieta, transiciones y animaciones en `none`; activado → el canvas cambia y la luna se mueve.

### 14. Rutas sin expandir: se puede crear un directorio llamado `~` — `hecho`
- **Dónde:** `launch_minecraft()` usaba `settings["minecraft_dir"]` sin `expanduser`.
- **Arreglo:** `minecraft.expand_path()` (expanduser + expandvars + abspath) se aplica al leer y al guardar ajustes, en `java_path` si empieza por `~`, y al lanzar. Al cambiar `minecraft_dir` desde la UI se actualiza también el `mods_dir` de la instancia activa, para que la carpeta de mods siga colgando del directorio del juego.

## 🟡 Menores (15–25)

### 15. El botón □ no restaura — `hecho`
- **Dónde:** `api.maximize()` solo maximizaba; pywebview no alterna por su cuenta.
- **Arreglo:** nuevo `API.toggle_maximize()` con estado `_maximized = True` (la ventana se crea maximizada en `main.py`). Si el backend nativo expone `is_maximized()` se consulta de verdad; si no, se alternan `restore()`/`maximize()`. `maximizeWin()` en `app.js` llama a `toggle_maximize()`.
- **Verificado:** con dos llamadas seguidas sobre una ventana falsa se invocan `maximize()`/`restore()` según el estado.

### 16. La luna flota sobre los modales — `hecho`
- **Dónde:** `app.js` crea la luna con `z-index:9998` y `.overlay` usaba `1000`.
- **Arreglo:** `.overlay { z-index: 11000 }`, por encima de la luna (9998) y por debajo del splash (99999).

### 17. UUID offline fijo (`00000000-...`) — `hecho`
- **Dónde:** todos los usuarios offline compartían el mismo UUID.
- **Arreglo:** `minecraft.offline_uuid()` calcula `md5('OfflinePlayer:<nombre>')` con bits de versión 3 y variante RFC 4122, y `launch_minecraft()` lo usa en modo offline.
- **Verificado:** `Player` → `a01e3843-e521-3998-958a-f459800e4d11`, idéntico al cálculo manual (mismo UUID que un servidor en modo offline).

### 18. El mod Stella Client bloqueaba el arranque — `hecho`
- **Dónde:** `STELLA_MOD_DIR` apunta al repo hermano `../stella-client-mod` (no existe en el binario empaquetado) y `install_stella_mod()` recompilaba con Gradle en cada lanzamiento, hasta 120 s.
- **Arreglo:** si las fuentes no existen no se compila nada; si el jar instalado (`stella-client.jar`) es más reciente que la fuente más nueva (`_newest_mtime()`) tampoco; el timeout baja a 90 s y un fallo marca `_stella_build_failed`, así que no se reintenta en la misma ejecución. Si el build falla pero ya había un jar, se conserva.
- **Verificado:** con el jar presente y al día, `install_stella_mod()` responde en 0,0 s sin invocar Gradle.

### 19. Lógica de auth Microsoft duplicada — `hecho`
- **Dónde:** la cadena XBL → XSTS → Minecraft estaba copiada en `api._finish_microsoft_auth` y en `minecraft`.
- **Arreglo:** la única versión vive en `minecraft.finish_microsoft_auth(tokens)` (devuelve `{"username","uuid"}` o `{"error"}`) y guarda la sesión; `api._finish_microsoft_auth` solo adapta la respuesta a `{"status":"success", ...}`.

### 20. `poll_microsoft_login(interval=5)` no usaba el parámetro — `hecho`
- **Arreglo:** firma reducida a `poll_microsoft_login(self, device_code)`; el intervalo lo decide la UI (y `slow_down` se sigue devolviendo).

### 21. Empaquetado — `hecho`
- **Dónde:** `main.spec` con la ruta del icono hardcodeada; `build-deb.sh` declaraba `libgirepository1.0-dev`/`gobject-introspection` y no declaraba los GIR de WebKitGTK.
- **Arreglo:** `icon=os.path.join(SPECPATH, 'assets', 'icon-256.png')` (el bloque `import os` volvió al spec) y `Depends: libgtk-3-0, libwebkit2gtk-4.1-0, libjavascriptcoregtk-4.1-0, gir1.2-gtk-3.0, gir1.2-webkit2-4.1`. Ojo: `main.spec` está en `.gitignore`, así que se reescribió con herramienta de escritura.
- **Superado por el punto 35:** las dos rutas relativas se conservan, pero la receta se mudó a `packaging/stella-client.spec` y las dependencias ya no se escriben a mano.

### 22. Doble binding de pestañas — `hecho`
- **Dónde:** `initTabs()` enganchaba `.tab-btn` y las pestañas de Mods/Settings tenían además su propio listener: cada clic se procesaba dos veces.
- **Arreglo:** `initTabs()` ignora los botones dentro de `.mods-tabs` y `.settings-tabs`.

### 23. CSS del splash duplicado — `hecho`
- **Arreglo:** eliminados los bloques muertos `.splash-star`, `@keyframes starSpin` y `.shooting-star::after` (el elemento real es `.splash-logo`).

### 24. `installMod`/`deleteMod` no informaban de fallos — `hecho`
- **Dónde:** `delete_mod()` devolvía `None` aunque el borrado del jar fallase.
- **Arreglo:** `API.delete_mod()` devuelve `{"ok": bool}` y `deleteMod()` muestra un `toast` de error y reactiva el botón si falla (igual que `installMod`).
- **Verificado:** con un archivo inexistente la API responde `{'ok': False}`.

### 25. Letras con el degradado parado — `hecho`
- **Dónde:** los títulos llevaban el degradado animado en el padre, pero parte del texto iba envuelto en `<span class="sc-ste|sc-lla|sc-cli|sc-ent">`, y esos spans eran `display:inline-block`.
- **Causa:** `background-clip: text` **no se hereda**, mientras que `-webkit-text-fill-color: transparent` **sí**. Un hijo que crea su propia capa de pintura (inline-block, transform, opacity, filter…) se dibuja sin el fondo del padre, así que sus letras se quedan transparentes y sin animación mientras el resto del título sí se mueve. Medido en navegador: los spans tenían `bgImage:none`, `clip:border-box` y `animationName:none`.
- **Arreglo:** fuera los spans envoltorio (`#drag-region`, `.hero h1` y `.splash-title` vuelven a ser texto plano) y fuera la regla `.sc-*` del CSS. Además se añadió una red de seguridad: los hijos directos (que no sean `svg`) de todo texto con degradado reciben otra vez el degradado animado, para que envolver texto en el futuro no vuelva a romperlo.
- **Verificado en navegador:** `#drag-region`, `.hero h1`, `.splash-title`, `#version-current`, `.badge-grad` y un `<span>` `inline-block` inyectado a propósito tienen `clip:text`, `background-size:300% 100%` y `slideRight` corriendo con `background-position` cambiando entre muestras.

### 26. La pestaña Browse mostraba versiones falsas de cada mod — `hecho`
- **Dónde:** `mods.get_trending_mods()` seguía calculando la etiqueta de versión como `hit["versions"][0]`, que es la **más antigua** del proyecto.
- **Síntoma:** la lista de mods de la pestaña Browse (la que se ve al entrar, sin buscar nada) mostraba `Fabric API · v18w49a`, `Sodium · v1.16.3`, `Entity Culling · vb1.7.3`... aunque la instancia es 1.21.11 y esos proyectos sí tienen 1.21.11. Con las etiquetas así, cualquier mod parece ser de otra versión.
- **Arreglo:** `_hit_to_result()` normaliza los hits y es el único sitio que decide la versión (la pedida si el proyecto la soporta, si no la más antigua del hit), y `search_modrinth()` y `get_trending_mods()` lo comparten.
- **Verificado:** antes/después medido por consola: `Fabric API 18w49a → 1.21.11`, `Sodium 1.16.3 → 1.21.11`, `Iris Shaders 1.16.5 → 1.21.11`.

### 27. Los fallos de red quedaban cacheados y la lista no se reintentaba — `hecho`
- **Dónde:** `_cached()` guardaba cualquier resultado, incluidos los vacíos que `search_modrinth` devuelve cuando Modrinth falla, así que un error puntual se veía como "No results found" durante 60 s seguidos. Además la lista de Browse solo se pedía **una vez**, al arrancar (`initModsPage`): si esa primera llamada fallaba (sin red al abrir, error de Modrinth...), entrar en la pestaña Mods no la volvía a pedir y el apartado se quedaba vacío para siempre.
- **Arreglo:** `_cached()` no cachea respuestas con `error`; `search_modrinth`/`get_trending_mods` devuelven el motivo real (`HTTP 500`, `No se pudo conectar...`) y la API lo propaga; la UI muestra ese texto en vez de un genérico, añade un botón **↻ Reintentar** en los estados de error y de "sin resultados", y `navigate('mods')` vuelve a pedir la lista (y la de instalados) cada vez que se abre la pestaña.
- **Verificado en navegador** contra el backend real: con `get_trending_mods` forzado a fallar se ve `Error: No se pudo conectar con Modrinth: ...` + botón; al pulsar Reintentar vuelven los 15 resultados. Con la pestaña abierta se disparan `get_trending_mods` y `get_installed_mods`.

### 28. La pestaña Browse podía pedirse sin filtro de versión — `hecho`
- **Dónde:** `refreshBrowse()` tomaba la versión de `<select id="mod-version">`, que rellena `loadVersions()` de forma asíncrona y sin `await` en `initApp()`. En el primer arranque el select aún está vacío y la petición salía sin el facet `versions:` (lista sin filtrar).
- **Arreglo:** si el select está vacío se consulta `get_settings()` y se usa la versión instalada. Verificado: con el select vacío la petición sale igualmente con la versión correcta.

### 29. `get_mod_detail` devolvía la licencia como objeto — `hecho`
- **Dónde:** `"license": d.get("license", "")`; Modrinth devuelve `{id, name, url}`, así que la ficha del mod mostraba `License: [object Object]`.
- **Arreglo:** se normaliza a texto usando `name` y, si viene vacío (Sodium trae `name: ""`), el `id`.
- **Verificado:** `Sodium → LicenseRef-Polyform-Shield-1.0.0`, `Fabric API → Apache License 2.0`.

### 30. Las letras se veían borrosas: el canvas de estrellas tapaba la interfaz — `hecho`
- **Dónde:** `#stars` tenía `z-index: 2` y `#app` `z-index: 1`, así que el fondo de estrellas se pintaba **por encima de todo** el launcher.
- **Causa:** además de dibujar puntitos sobre las letras, un canvas animado a pantalla completa encima del texto obliga al motor a componer *todo* el texto contra una capa no opaca: WebKit deja de usar antialiasing de subpíxel y las letras se ven blandas (medido en la captura del usuario: los bordes de las letras son gris puro, sin el fringe de color del subpíxel, y el render es 1:1, sin reescalado del compositor).
- **Arreglo:** `#stars { z-index: 0 }` (detrás de todo) y los paneles pasan a translúcidos (`--panel`: `rgba(10,7,32,.82)` en oscuro, equivalente en claro y OLED) para que el fondo animado siga viéndose por debajo, con `#app-body` transparente. Se retiraron los rellenos `#app-body::before/::after`, que solo existían para tapar la costura en el diseño opaco.
- **Verificado:** con el canvas detrás el campo de estrellas sigue viéndose en contenido y barra lateral, ningún punto queda sobre el texto, y el tema claro y el OLED se ven correctos.

### 31. Calidad tipográfica: contraste, pesos y fuentes — `hecho`
- **Dónde:** el texto pequeño usaba `--text2: #7a72b0` (contraste ~4:1 sobre las tarjetas), había textos a 12px y los títulos iban en `font-weight: 800` sin cara 800 declarada.
- **Arreglo:** `--text2` sube a `#9e97d2` en oscuro (y `#6d6d74` en claro, `--text` también un punto más luminoso); el texto meta de las tarjetas de mods pasa de 12 a 13px; se añade la cara `font-weight: 800 900` apuntando a `ComicNeue-Bold.ttf`; y se retira el `<link>` a Google Fonts, así que las tres caras salen siempre de `assets/fonts` (sin depender de la red ni cambiar de tipografía al arrancar).
- **Verificado:** `document.fonts` resuelve la familia desde los TTF locales y las medidas de texto coinciden con las del launcher real (mismo ancho de cadenas en px), confirmando que no había ninguna fuente de reserva estropeando el render.

### 32. No se podía copiar el código de inicio de sesión de Microsoft — `hecho`
- **Dónde:** el código (`user_code`) se mostraba como texto y había que copiarlo a mano.
- **Arreglo:** `API.copy_to_clipboard(text)` usa el portapapeles de GTK (con `GLib.MainContext.default().is_owner()` para copiar en el hilo principal y devolver un resultado real, o encolarlo con `idle_add` si la llamada viene de otro hilo). En la UI aparece el código en monoespaciado dentro de un recuadro y un botón **📋 Copy code**; `copyText()` intenta en orden GTK → `navigator.clipboard` → textarea + `execCommand`, y `copyMsCode()` avisa con un toast y cambia el texto del botón a `✓ Copied`.
- **Verificado:** GTK copia y devuelve el texto leído de vuelta en la sesión real del usuario (clipboard restaurado después); en el navegador los tres caminos devuelven `true` y el botón muestra `✓ Copied` con el toast correspondiente.

### 33. Al pulsar PLAY no se veía nada mientras se descargaba el juego — `hecho`
- **Dónde:** si la versión elegida (o Fabric) no estaba instalada, el botón se quedaba en `⏳ Launching...` durante minutos sin ninguna señal de avance: parecía colgado.
- **Por qué pasaba:** `launch_minecraft()` llamaba a `install_fabric()` / `install_minecraft_version()` **sin callback**, así que el progreso que ya emite `minecraft_launcher_lib` no llegaba a ninguna parte; y el frontend solo volvía a preguntar el estado cada 2 s.
- **Arreglo backend:** `minecraft.launch_plan()` decide **sin tocar la red** si hace falta descargar (`versions/<v>/<v>.json` + `.jar` para la versión, y algún `versions/fabric-loader-*` si el mod Stella está instalado). `launch_minecraft(callback=None)` pasa el callback a la instalación y reporta `Descargando Fabric para <v>`, `Descargando Minecraft <v>` e `Iniciando Minecraft`. En `api.py`, `_progress_callback()` traduce el `CallbackDict` (`setStatus`/`setProgress`/`setMax`) a `_launch_status` bajo `_progress_lock` y con `_publish(**fields)` (reemplaza el dict entero, nunca muta en sitio: los callbacks llegan desde los hilos del pool de descargas). `_PHASE_LABELS` traduce las fases a español (`Download Libraries` → `Descargando librerías`, etc.).
- **Detalle que hubo que corregir:** `download_file()` llama `setStatus("Download <archivo>")` muchas veces por segundo, y esos avisos pisaban la fase buena (`Descargando librerías` → `Descargando archivos`). El callback recuerda con `flags["named_phase"]` si la última fase fue una nombrada y **ignora** los `Download <archivo>` mientras lo sea.
- **Arreglo frontend:** barra `#launch-progress` al pie de la ventana (mismo lenguaje visual: panel translúcido, degradado de marca en relleno y porcentaje, `lpPulse` en el punto, `lpSweep` cuando aún no hay máximo → se muestra `···` en vez de un porcentaje inventado). Solo se abre con `state === 'launching' && needs_download`, así que **con el juego ya instalado no aparece** (no hay nada que enseñar). El toast se sube 92px con `body.launch-bar-visible` para no quedar debajo, y el sondeo pasa de 2 s a 400 ms con una consulta inmediata al pulsar PLAY.
- **Verificado:** `py_compile` de `api.py`/`main.py`/`launcher/*.py` y `gjs ui/app.js` sin `SyntaxError`; test offline del callback con 8 hilos × 500 iteraciones de `Download fileN.jar` (la fase se mantiene, sin excepciones, y con `state="playing"` ya no publica); instalación real de `26.3` con las fases saliendo en orden (`Descargando librerías` 32/113 → `Descargando recursos` 33/5146 → `Instalando Java` 434/433 → `playing`); flujo completo de `launch()` con 14 transiciones; guard de doble lanzamiento (`Minecraft ya se está ejecutando`); y en el navegador, con una versión sin instalar simulada, la barra aparece con fase y porcentaje correctos (28 %), pasa a `···`/barrido cuando aún no hay máximo, marca 100 % al terminar y vuelve a cerrarse en `playing` (alto 60px → 1px, opacidad 1 → 0, sin clase en `body`).

### 34. Al crear una instancia y seleccionarla, los mods se instalaban en la carpeta de `default` — `hecho`
- **Síntoma:** se crea una instancia nueva, se selecciona, y al descargar mods acaban en `instances/default/mods`. No es que la descarga eligiera mal la carpeta: **`instances.json` guardaba la instancia nueva con `minecraft_dir` y `mods_dir` de `default`** (comprobado en los datos reales: `prueba` → `.../instances/default/mods`).
- **Por qué pasaba:** todos los campos de Ajustes son de la instancia activa, pero `initSettings()` se ejecutaba **una sola vez** al arrancar, cuando la activa era `default`. Al seleccionar otra instancia, `#mc-dir` seguía mostrando la carpeta de `default`; al pulsar «Save» (o cualquier guardado que incluya `minecraft_dir`), `api.save_settings()` copiaba ese valor a la instancia **nueva** vía `instances.update_instance()`, que aceptaba sin más cualquier ruta.
- **Arreglo frontend:** se separa `refreshSettingsForm()` (solo vuelca los valores de la instancia activa: RAM, Java, carpeta del juego) del alta de listeners, que sigue ocurriendo una sola vez en `initSettings()`. Se refresca al **seleccionar instancia**, al **crear** (que además deja activa la nueva de inmediato), al **borrar** y al **entrar en la página de Ajustes**.
- **Arreglo backend:** `instances.update_instance()` rechaza un `minecraft_dir` que ya pertenece a **otra** instancia (avisa por log y descarta la clave, junto con su `mods_dir`); una instancia no puede apropiarse de la carpeta de otra porque `delete_instance()` haría `rmtree` de los archivos de la otra. Además, `_load()` repara al vuelo la inconsistencia: si dos instancias comparten carpeta de juego, la que no es dueña (su id no coincide con el nombre de la carpeta) vuelve a `instances/<su-id>` y se guarda la corrección. Esto arregla sola la instancia dañada (`prueba`) en el siguiente arranque.
- **Verificado:** `py_compile` y `gjs` sin `SyntaxError`. Test con `HOME` aislado: guardar los ajustes con la carpeta de `default` mientras la activa es `prueba` **ya no contamina** `prueba`; con datos ya corruptos, `list_instances()` los repara (`prueba` → `instances/prueba`, `default` conserva la suya); y un `download_mod()` con `prueba` activa deja el `.jar` en `instances/prueba/mods`. Reproducido también sobre una **copia de los datos reales**. Nota: los mods descargados mientras la instancia estaba mal apuntada siguen físicamente en `default/mods` (no se pueden distinguir unos de otros), así que si alguno era de `prueba` hay que moverlo a mano.

### 35. Los paquetes sólo arrancaban en Arch — `hecho`
- **Dónde:** el empaquetado construía un binario que dependía del entorno donde se compilaba. Medido con `objdump -T`: `math.cpython-314….so` del Python de Arch exigía **`GLIBC_2.44`**, `libncursesw`/`termios` pedían 2.42 y el payload arrastraba la glibc del host. Ubuntu 24.04 (2.39) y Debian 13 (2.41) no podían ejecutarlo, así que "funciona en todas las distros" era falso: solo servía en Arch y derivados.
- **Causa de fondo:** el suelo de una distribución no lo fija lo que empaquetas, sino **con qué se compila**. Y había un segundo problema: PyInstaller, al ver `gi.repository.Gtk`, intentaba empaquetar la pila gráfica entera — 39 783 enlaces simbólicos al tema de iconos del sistema, módulos de GIO, loaders de gdk-pixbuf — que en otra máquina serían enlaces rotos.
- **Arreglo:** el payload se compila con un **Python portátil de `python-build-standalone`** (glibc 2.17) en `build/buildenv`, no con el del sistema; el spec descarta la pila gráfica (la pone la distro) y **poda los huérfanos** siguiendo los `DT_NEEDED`, además de descartar los datos ajenos por su destino. El ejecutable se `strip`ea en el spec y las librerías internas en `payload.sh` (el Python portátil viene sin strip: 230 MB de `libpython` → 29 MB). **Resultado: glibc 2.27** en lugar de 2.44, y de 398 MB/30 677 ficheros a 38 MB/57.
- **Arreglo del empaquetado:** `packaging/` con el payload compartido (`payload.sh`, `files.sh`), los tres formatos (`deb.sh`, `rpm.sh` + `stella-client.spec.in`, `appimage.sh`) y `build.sh` como punto de entrada único; `VERSION` como fuente única de la versión (antes hardcodeada en `build-deb.sh`). El `.rpm` lleva `AutoReqProv: no` — sin eso rpmbuild pide los `.so` que el paquete lleva dentro y el RPM queda ininstalable — y declara por soname y por `typelib(...)`, que son provided reales en Fedora, RHEL y openSUSE. El `.deb` usa alternativas (`libgtk-3-0t64 | libgtk-3-0`) para el renombrado de Ubuntu 24.04.
- **Hallazgo del que no se veía nada con `ldd`:** GTK y WebKitGTK se cargan en caliente por los typelibs de GObject Introspection, así que **no aparecen como dependencia enlazada**. Declarar solo lo que sale en `ldd` produce un paquete que se instala sin un error y luego no arranca. La auditoría los añade explícitamente.
- **Verificado:** auditoría del payload en cada build (31 externas identificadas, nada gráfico dentro, glibc mínima medida y escrita en `build/glibc-min.txt`); `main.py --check` arranca el payload en frío y, con pantalla, **llega a crear y cerrar la ventana**; el `.deb` extraído con `dpkg-deb -x` y el `.rpm` extraído con `rpm2cpio | bsdtar` se ejecutan desde su enlace `/usr/bin/stella-client`; el AppImage funciona montado, extraído con `--appimage-extract` y **con `APPDIR` heredado del entorno apuntando a otro sitio** (venía de esta propia aplicación, que también es un AppImage). Artefactos: 13 MB (.deb), 14 MB (.rpm), 16 MB (AppImage).
- **Límite conocido:** glib ≥ 2.80, porque PyGObject enlaza `libgirepository-2.0`. Eso deja fuera Ubuntu 22.04 y anteriores, y está declarado en los paquetes para que falle al instalar y no al arrancar.

### 36. El launcher sólo existía para Linux: no había forma de tener un `.exe` — `hecho`
- **Dónde:** no había nada para Windows, y tampoco se podía improvisar: **PyInstaller no cross-compila**, sólo genera un ejecutable del sistema en el que se ejecuta. Además el código no habría funcionado allí aunque se empaquetara, y esa es la parte que importa.
- **Por qué no bastaba con empaquetar:** en Linux la ventana la dibujan GTK y WebKitGTK, que se cargan por los typelibs; en Windows pywebview usa el **motor de Edge (WebView2)** a través de `pythonnet` —lo declara el propio paquete: `Requires-Dist: pythonnet; sys_platform == "win32"`—. Con la receta de Linux, el `.exe` se habría creado y no habría abierto ninguna ventana.
- **Arreglo, rutas:** `launcher/paths.py` es ahora el único sitio donde se decide dónde viven los datos: `%LOCALAPPDATA%\StellaClient` en Windows y `~/.stellaclient` en Linux, **idéntico a antes** (los seis sitios que tenían la ruta copiada a mano —`minecraft.py`, `mods.py` ×3, `instances.py` ×2, `main.py`, `api.py`— pasan a importarla). `%LOCALAPPDATA%` y no `%APPDATA%`: el segundo es el perfil itinerante, que se sincroniza entre máquinas y no es sitio para varios GB de juego. `migrate_once()` mueve los datos de la ruta antigua si existen y **reapunta las rutas absolutas guardadas** en `config.json` e `instances.json` (mover la carpeta sin tocar el JSON dejaría al launcher buscando el juego donde ya no está).
- **Arreglo, plataforma:** `main.py` aplica las variables de la pila gráfica y los iconos sólo en Linux (en Windows el icono va como recurso del propio `.exe`), `api.py` usa `clip.exe` en UTF-16LE para el portapapeles —sin `CREATE_NO_WINDOW` asomaría una consola un instante— y `_open_url` usa `os.startfile`, `_ensure_glib()` sale antes de tocar `sys.path` y `begin_window_move` tiene su rama de Win32 (`ReleaseCapture` + `WM_NCLBUTTONDOWN`, el equivalente de `begin_move_drag`: cede el arrastre al gestor de ventanas en vez de mover la ventana desde Python, que sería un viaje de ida y vuelta por cada movimiento del ratón). Como el ejecutable va sin consola, `sys.stderr` es `None`, así que `main.py` escribe el registro en `%LOCALAPPDATA%\StellaClient\logs\stella.log` con rotación: **sin ese fichero, cualquier fallo allí no dejaría rastro que poder leer**. `--check` se divide en dos (GTK en Linux, WebView2 y `pythonnet` en Windows, leyendo la versión del runtime del registro) y `launch_minecraft()` prefiere `javaw.exe` para que no quede una ventana negra de consola detrás del juego. `detect_java()` busca en `%JAVA_HOME%` y en las carpetas habituales (`Java`, `Adoptium`, `Microsoft`, `Zulu`, `BellSoft`, `Corretto`) además de en `/usr/lib/jvm`.
- **Arreglo, empaquetado:** `packaging/stella-client-win.spec` en modo **onedir** (con `onefile` el arranque descomprime en `%TEMP%` y es lo que más hace saltar a los antivirus) y con **dos ejecutables del mismo programa**: `stella-client.exe` sin consola para el jugador y `stella-client-check.exe` con consola para poder leer la comprobación (se distingue por el nombre del ejecutable, así no hay que pasarle argumentos). El spec genera el **recurso de versión** desde `VERSION` y `packaging/windows/make-ico.py` el `.ico` desde el PNG (PyInstaller con un PNG no falla, pero deja el ejecutable **sin icono**; Inno Setup directamente no lo acepta). El instalador es `packaging/windows/stella-client.iss` (Inno Setup 6.3+, por `x64compatible`), por usuario en `%LOCALAPPDATA%\Programs` para no pedir administrador, y **el desinstalador no toca la carpeta de datos**, que es donde están las cuentas y los GB de juego. `build.ps1` es el `build.sh` de Windows, con los mismos nombres y la misma idea: el payload se construye una vez y el instalador y el ZIP envuelven ese mismo directorio.
- **Arreglo, dependencias:** `requirements.txt` pedía `PyGObject>=3.48` sin condiciones, y en Windows eso no instala —no hay rueda en PyPI y necesita las cabeceras de GTK—; ahora lleva `; sys_platform == "linux"`. `packaging/requirements-win.txt` reutiliza la lista común y añade `pythonnet>=3.0.5` (las anteriores no soportan Python 3.13, que es el que se compila aquí).
- **Por qué el build vive en GitHub:** al no poder cross-compilar y no tener Windows en esta máquina, `.github/workflows/windows.yml` compila en `windows-latest` al publicar una etiqueta `v*` o a mano desde *Actions*, ejecuta la comprobación como puerta del build e instala Inno Setup con `choco` en vez de darlo por hecho (hay peticiones abiertas para añadirlo a la imagen `windows-2025`).
- **Verificado:** `py_compile` de todo el Python y `gjs ui/app.js` sin `SyntaxError`. `main.py --check` sigue imprimiendo `datos : /home/ivan/.stellaclient`, **exactamente la misma ruta que antes del refactor**, y sale con código 0. Prueba de rutas y migración (`build/tests/stella_paths_test.py`) en los dos modos: con `sys.platform` real y falseado a `win32`, comprobando las constantes ya resueltas de `minecraft`/`mods`/`instances`, la reescritura de rutas (prefijo, ruta exacta, listas y diccionarios, y que no toca lo ajeno), que la migración mueve `config.json`, `instances` y `mods`, reapunta `minecraft_dir` y `mods_dir` en el JSON, vacía la carpeta antigua, no se repite en una segunda pasada y **no pisa** datos de la instalación nueva. El `.ico` se genera y se relee con 7 tamaños (16 a 256). El YAML del workflow se parsea y su estructura es la esperada.
- **Límites:** el `.exe` no está firmado, así que Windows mostrará el aviso de SmartScreen hasta que haya un certificado; en un servidor de integración continua no hay sesión interactiva, así que allí la comprobación valida WebView2 y `pythonnet` pero no abre la ventana (por eso `build.ps1 launch` existe aparte, para comprobarlo donde sí hay escritorio); y el arrastre de la barra de título, el portapapeles y el arranque real de Minecraft sólo se pueden probar en un Windows de verdad. **Sin probar en Windows todavía.**

## Incidente del 23-sep (regresión del arreglo #1)

**Síntoma:** al abrir el launcher todo se veía borroso y no se podía usar.

**Causa doble:**
1. `#splash` llevaba `background: rgba(10,10,10,.75)` y `backdrop-filter: blur(8px)` en su estado base, así que oscurecía y difuminaba toda la app **aunque el splash nunca se mostrara**. Si el JS no llegaba a `hideSplash`, la interfaz quedaba tapada para siempre (y con el contenido del splash invisible, porque `.show` ni siquiera se aplicaba).
2. La meta `Content-Security-Policy` añadida con el arreglo #1 puede impedir la inyección de `window.pywebview` por parte de pywebview (su puente inyecta scripts y usa evaluación dinámica), con lo que `initApp()` no se ejecutaba nunca.

**Arreglo:**
- `#splash` es invisible por defecto (`opacity: 0; visibility: hidden`, sin fondo ni blur); el fondo oscuro y el desenfoque solo se aplican con `.show`. Si el JS muere, la UI se sigue viendo.
- Retirada la meta CSP de `index.html`. Para volver a añadirla hay que quitar antes los `onclick` inline y comprobar que el puente de pywebview sigue funcionando.
- `initApp()` envuelve cada paso en `try/catch` y hay watchdog que oculta el splash a los 1,5 s y a los 5 s.
- El arranque ya no depende solo de `pywebviewready`: `whenBridgeReady()` sondea el puente cada 100 ms hasta 15 s y, si no aparece, avisa con un `toast`.
- Errores JS no capturados y promesas rechazadas ahora se muestran con `toast` en vez de perderse en el webview.

**Verificado:** sin backend la UI se ve nítida y avisa del problema; con un `pywebview` simulado la app arranca sin errores, actualiza las insignias y elimina el splash. `app.js` parsea sin errores con gjs (SpiderMonkey).

## Notas

- Verificado que **no** es bug: `jvmArguments` se *añade* a los argumentos por defecto de `minecraft-launcher-lib` (`command.py:213`), así que `[ram, "-XX:+UseG1GC"]` es seguro.
- Plan de trabajo: críticos 1–6 → medios 7–14 → menores 15–25 → repaso del descargador de mods (26–29) → tipografía y código de login (30–32) → barra de progreso de descarga (33) → carpeta de mods de las instancias nuevas (34) → empaquetado para distros modernas (35). **Los 35 puntos están cerrados**; lo que quede por verificar es solo en la app real (pywebview + GTK), no en el navegador.
- Para reproducir el frontend sin abrir la ventana GTK se usó un puente HTTP temporal (`_debug_bridge.py`, ya borrado) que sirve `ui/` y expone los métodos de `api.API`, con `window.pywebview` simulado desde la consola del navegador. Sirvió para comprobar Browse, búsqueda, paginación, categorías, ficha del mod, descarga e instalados contra el backend real.
