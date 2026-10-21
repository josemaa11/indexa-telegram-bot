# 📈 Bot de Indexa Capital para Telegram

Un bot gratuito que vigila tu cartera de **Indexa Capital** y te escribe por **Telegram**:

- ⚠️ **Si tu cartera cae con fuerza** (más de un 10 %, 15 %, 20 %…) desde su máximo, te avisa.
  Un solo aviso por cada nivel, sin repetirse cada día.
- 📊 **Una vez al mes** te manda un resumen: cuánto vale, cuánto has aportado, cuánto has ganado
  y la rentabilidad del mes.

No tienes que instalar nada ni dejar ningún ordenador encendido: funciona solo, gratis,
en los servidores de GitHub.

> 🔒 **Es de solo lectura.** El bot puede *ver* tu cartera, pero **no puede mover dinero,
> comprar ni vender**. Tus claves se quedan en tu propia cuenta y nadie más las ve,
> tampoco el autor de este bot.

---

## ✅ Qué necesitas

- Tu cuenta de **Indexa Capital**.
- **Telegram** en el móvil.
- Un **ordenador** con navegador (solo para la configuración).
- Unos **15 minutos**.

Vas a hacer 6 pasos. Ve con calma y sigue el orden.

---

## Paso 1 · Crea una cuenta en GitHub (gratis)

GitHub es la web donde vivirá tu bot. Si ya tienes cuenta, salta al paso 2.

1. Entra en **https://github.com/signup**.
2. Pon tu correo, una contraseña y un nombre de usuario.
3. Confirma el código que te llega por correo.

Si te ofrece planes de pago, elige **Free**.

---

## Paso 2 · Copia el bot a tu cuenta

1. Con tu sesión de GitHub iniciada, vuelve a **esta página**.
2. Arriba a la derecha, pulsa el botón verde **`Use this template`** → **`Create a new repository`**.
3. Rellena:
   - **Repository name:** por ejemplo `mi-bot-indexa`.
   - Marca **`Private`**. ⚠️ **Muy importante:** así solo tú puedes ver tu bot.
4. Pulsa **`Create repository`**.

Ya tienes tu propia copia. A partir de ahora trabaja siempre en **tu** copia, no en esta página.

---

## Paso 3 · Crea tu bot de Telegram

1. En Telegram, busca **`@BotFather`**. Es el que tiene la ✔️ azul de verificado.
2. Pulsa **Iniciar** y escribe `/newbot`.
3. Te pedirá un **nombre**: escribe el que quieras, por ejemplo `Mi Indexa`.
4. Te pedirá un **usuario**: tiene que acabar en `bot`, por ejemplo `mi_indexa_bot`.
   Si está cogido, prueba con otro.
5. BotFather te responderá con un mensaje que contiene una línea larga como esta:

   `123456789:AAH4k9xZ...`

   Eso es el **token del bot**. **Cópialo** y guárdalo un momento (por ejemplo en una nota).
6. En ese mismo mensaje hay un enlace `t.me/...`. **Púlsalo y dale a `Iniciar`** en tu bot nuevo.
   ⚠️ Sin este paso, el bot no podrá escribirte.

> 🔒 No compartas ese token con nadie: quien lo tenga puede hablar en nombre de tu bot.

---

## Paso 4 · Consigue tu clave de Indexa

1. Entra en **indexacapital.com** con tu usuario.
2. Ve a **Configuración de usuario → Aplicaciones**.
3. Pulsa **Generar token** y **cópialo**. Es un texto muy largo: asegúrate de copiarlo entero.

> 🔒 Este token solo permite **consultar** tu cuenta. Si algún día quieres anularlo,
> vuelve a pulsar *Generar token* y el anterior dejará de funcionar.

---

## Paso 5 · Guarda las dos claves en GitHub

Las claves se guardan como **"secrets"**: GitHub las cifra y nadie puede volver a verlas,
ni siquiera tú.

1. En **tu** repositorio de GitHub, pulsa **`Settings`** ⚙️, la última pestaña de arriba.
2. En el menú de la izquierda: **`Secrets and variables`** → **`Actions`**.
3. Pulsa el botón verde **`New repository secret`**.
4. Crea el primero:
   - **Name:** `TELEGRAM_BOT_TOKEN`
   - **Secret:** pega el token de Telegram (paso 3).
   - Pulsa **`Add secret`**.
5. Vuelve a pulsar **`New repository secret`** y crea el segundo:
   - **Name:** `INDEXA_TOKEN`
   - **Secret:** pega el token de Indexa (paso 4).
   - Pulsa **`Add secret`**.

Al terminar deberías ver los dos en la lista:

| Name | Qué es |
|---|---|
| `INDEXA_TOKEN` | La clave de Indexa |
| `TELEGRAM_BOT_TOKEN` | La clave de tu bot de Telegram |

⚠️ Los nombres tienen que estar escritos **exactamente así**, en mayúsculas y con guiones bajos.

---

## Paso 6 · Pruébalo

1. En tu repositorio, pulsa la pestaña **`Actions`** ▶️.
2. Si aparece un botón verde que dice *"I understand my workflows, go ahead and enable them"*,
   **púlsalo**.
3. En la columna de la izquierda, pulsa **`Bot de Indexa`**.
4. A la derecha verás **`Run workflow`** ▾. Púlsalo, deja la opción **"Probar el bot"** y pulsa
   el botón verde **`Run workflow`**.
5. Espera un minuto. En la lista aparecerá una ejecución que se pondrá en ✅ verde.

📱 **Te tiene que llegar un mensaje a Telegram:** *"Bot de Indexa conectado correctamente"*.

🎉 **¡Ya está!** Desde ahora el bot se ejecuta solo cada tarde de lunes a viernes.
La mayoría de los días no te escribirá nada: eso significa que todo va bien.

> ℹ️ Si todavía no has hecho tu primera aportación en Indexa, te dirá que tu cuenta aún no
> está activa. Es normal: empezará a vigilarla solo en cuanto Indexa invierta tu dinero.

---

## ❌ Si algo sale mal

Si la ejecución sale con una ❌ roja:

1. **Pulsa sobre ella.**
2. Baja hasta **"Bot de Indexa summary"**: ahí verás **qué ha pasado y cómo arreglarlo**.

Los problemas más habituales:

| Mensaje | Qué hacer |
|---|---|
| *Todavía no encuentro tu chat de Telegram* | Abre tu bot en Telegram, pulsa **Iniciar** (o escríbele «hola») y vuelve a probar (paso 6) en menos de 24 horas. |
| *El token del bot de Telegram no es válido* | Repite el paso 5 con `TELEGRAM_BOT_TOKEN`, copiando el token completo de BotFather. Para cambiar un secret: pulsa el ✏️ que hay a su lado. |
| *Indexa no acepta tu token* | Genera un token nuevo en Indexa (paso 4) y actualiza `INDEXA_TOKEN`. |
| *Falta configurar…* | Te falta alguno de los dos secrets o tiene el nombre mal escrito. |
| No aparece **Run workflow** | Comprueba que estás en **tu** copia, no en la plantilla original. |

Si una vez configurado deja de funcionar (por ejemplo, porque cambias el token de Indexa),
**el bot te avisará por Telegram** de qué tienes que arreglar.

---

## ⚙️ Personalizar (opcional)

Si no tocas nada, se usan estos valores:

| Variable | Por defecto | Qué hace |
|---|---|---|
| `UMBRALES_CAIDA` | `10,15,20,25,30` | Caídas (en %) a partir de las que te avisa. |
| `RECUPERACION` | `5` | Cuando la caída vuelve a ser menor que esto, te avisa de que se ha recuperado. |
| `DIA_RESUMEN` | `3` | Día del mes a partir del cual te manda el resumen. |

Para cambiarlas: **Settings → Secrets and variables → Actions →** pestaña **`Variables`** →
**`New repository variable`**, con el nombre de la tabla y el valor que quieras.

Si quieres recibir el resumen en otro momento: **Actions → Bot de Indexa → Run workflow →
"Mandar el resumen ahora"**.

---

## ❓ Preguntas frecuentes

**¿Cuesta dinero?**
No. Usa el plan gratuito de GitHub y este bot gasta unos minutos al mes, muy por debajo del límite.

**¿Puede mover mi dinero?**
No. La API de Indexa que usa solo permite consultar.

**¿Quién puede ver mis datos?**
Solo tú, siempre que tu repositorio sea **privado** (paso 2). El autor de esta plantilla no recibe nada.

**¿Por qué aparecen cambios automáticos llamados "bot: actualizar memoria"?**
El bot guarda en un archivo (`state.json`) qué avisos te ha enviado ya, para no repetirlos.

**¿Funciona con el plan de pensiones de Indexa?**
Sí. Vigila todas tus cuentas activas, cada una con sus propios avisos.

**¿Cómo lo paro?**
**Actions → Bot de Indexa →** botón **`···`** arriba a la derecha → **`Disable workflow`**.
Si además quieres anular el acceso, genera un token nuevo en Indexa: el antiguo deja de funcionar.

**¿Qué significa "caída desde el máximo"?**
Cuánto ha bajado tu cartera desde el punto más alto que ha alcanzado. Se calcula con la
rentabilidad de tus fondos, así que tus aportaciones o retiradas no la alteran.

---

## ⚖️ Aviso

Proyecto independiente, **sin relación con Indexa Capital**. Se ofrece tal cual, sin garantías.
La información que envía es solo informativa y **no es asesoramiento financiero**.

<details>
<summary>Para curiosos: cómo funciona por dentro</summary>

- `bot.py` consulta la API de Indexa (`/users/me` y `/accounts/{cuenta}/performance`) y usa
  la serie `return.index` (rentabilidad *time-weighted*) para calcular la caída desde máximos.
- `.github/workflows/indexa-bot.yml` lo ejecuta de lunes a viernes a las 16:17 UTC y guarda
  `state.json` en el repositorio.
- El chat de Telegram se detecta automáticamente la primera vez (`getUpdates`) y se guarda en
  `state.json`. También puedes fijarlo con un secret `TELEGRAM_CHAT_ID`.
- En local: `pip install -r requirements.txt` y `python bot.py --test --dry-run`
  (con `INDEXA_TOKEN` en el entorno), o `python bot.py --debug` para ver la estructura de la API.

</details>
