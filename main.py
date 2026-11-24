import json
from collections import defaultdict
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from starlette.websockets import WebSocketDisconnect


# ===== Estilos comunes a todas las páginas =====
estilos = """
  <style>
    /* ===== Colores: se cambian aquí y afectan a toda la página ===== */
    :root {
      --fondo: #eef1f7;
      --tarjeta: #ffffff;
      --texto: #1c2333;
      --texto-suave: #6b7488;
      --borde: #e1e5ee;
      --acento: #5b5bd6;          /* burbujas propias y botones */
      --acento-texto: #ffffff;
      --burbuja-otro: #f1f3f9;
      --ok: #1f9d55;
      --espera: #d69e2e;
      --error: #d64545;
    }
    /* Modo oscuro automático si el sistema operativo lo usa */
    @media (prefers-color-scheme: dark) {
      :root {
        --fondo: #0f1320;
        --tarjeta: #181d2c;
        --texto: #e8ebf3;
        --texto-suave: #98a1b6;
        --borde: #2a3145;
        --acento: #7c7cf0;
        --burbuja-otro: #232a3d;
      }
    }

    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background: var(--fondo);
      color: var(--texto);
      font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    }

    /* ===== Tarjeta ===== */
    .chat {
      width: min(680px, 100%);
      height: min(760px, 100vh);
      display: flex;
      flex-direction: column;
      background: var(--tarjeta);
      border: 1px solid var(--borde);
      border-radius: 20px;
      box-shadow: 0 20px 50px rgba(20, 30, 60, .12);
      overflow: hidden;
    }
    /* En el móvil ocupa toda la pantalla, sin bordes redondeados */
    @media (max-width: 700px) {
      .chat { height: 100vh; border-radius: 0; border: 0; }
    }

    /* ===== Cabecera ===== */
    header {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 16px 20px;
      border-bottom: 1px solid var(--borde);
    }
    header h1 { margin: 0; font-size: 1.2rem; flex: 1; overflow-wrap: anywhere; }
    header a { color: var(--acento); text-decoration: none; font-size: 1.4rem; }
    .estado {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-size: .85rem;
      color: var(--texto-suave);
    }
    .estado::before {             /* el puntito de color */
      content: "";
      width: 10px; height: 10px;
      border-radius: 50%;
      background: var(--color-estado, var(--espera));
    }
    .estado.conectado    { --color-estado: var(--ok); }
    .estado.desconectado { --color-estado: var(--error); }

    /* ===== Lista de mensajes / salas ===== */
    .lista {
      flex: 1;
      margin: 0;
      padding: 20px;
      list-style: none;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .vacio { margin: auto; color: var(--texto-suave); text-align: center; }
    .aviso { align-self: center; font-size: .8rem; color: var(--texto-suave); }
    .burbuja {
      max-width: 75%;
      padding: 10px 14px;
      border-radius: 16px;
      background: var(--burbuja-otro);
      align-self: flex-start;      /* mensajes recibidos: a la izquierda */
      border-bottom-left-radius: 4px;
      overflow-wrap: anywhere;     /* que una palabra larguísima no rompa el diseño */
      animation: aparecer .2s ease-out;
    }
    .burbuja.mio {
      align-self: flex-end;        /* mensajes propios: a la derecha */
      background: var(--acento);
      color: var(--acento-texto);
      border-bottom-left-radius: 16px;
      border-bottom-right-radius: 4px;
    }
    .burbuja strong { display: block; font-size: .8rem; color: var(--acento); margin-bottom: 2px; }
    .burbuja time { display: block; margin-top: 4px; font-size: .7rem; opacity: .7; text-align: right; }
    @keyframes aparecer { from { opacity: 0; transform: translateY(6px); } }

    /* Salas en el vestíbulo */
    .sala {
      display: flex; justify-content: space-between; align-items: center;
      padding: 12px 16px; border: 1px solid var(--borde); border-radius: 12px;
    }
    .sala span { color: var(--texto-suave); font-size: .85rem; }

    /* ===== Barra para escribir ===== */
    form {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      padding: 14px 16px;
      border-top: 1px solid var(--borde);
    }
    input {
      flex: 1;
      min-width: 0;
      padding: 12px 16px;
      font: inherit;
      color: inherit;
      background: var(--fondo);
      border: 1px solid var(--borde);
      border-radius: 999px;
    }
    button {
      padding: 10px 18px;
      font: inherit;
      font-weight: 600;
      color: var(--acento-texto);
      background: var(--acento);
      border: 0;
      border-radius: 999px;
      cursor: pointer;
      transition: filter .15s;
    }
    button:hover { filter: brightness(1.1); }
    button.secundario { background: transparent; color: var(--acento); border: 1px solid var(--borde); padding: 6px 14px; }
    button:disabled, input:disabled { opacity: .5; cursor: not-allowed; }
    input:focus-visible, button:focus-visible { outline: 3px solid var(--acento); outline-offset: 2px; }
  </style>
"""

# ===== Vestíbulo: elegir nombre y sala =====
html_inicio = """
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Salas de chat</title>
""" + estilos + """
</head>
<body>
  <main class="chat">
    <header><h1>Salas de chat</h1></header>

    <ul id="salas" class="lista" aria-live="polite">
      <li class="vacio">No hay salas activas. ¡Crea la primera!</li>
    </ul>

    <form id="formulario">
      <input id="nombre" maxlength="30" placeholder="Tu nombre" aria-label="Tu nombre" required>
      <input id="sala" maxlength="40" placeholder="Nombre de la sala" aria-label="Sala" required>
      <button>Entrar</button>
    </form>
  </main>

  <script>
    const nombre = document.getElementById("nombre");
    const sala   = document.getElementById("sala");
    const lista  = document.getElementById("salas");

    // Recuerda el nombre en este navegador (si el navegador lo permite)
    try { nombre.value = localStorage.getItem("nombre") || ""; } catch {}

    function entrar(nombreSala) {
      if (!nombre.reportValidity()) return;
      try { localStorage.setItem("nombre", nombre.value.trim()); } catch {}
      location.href = "/sala/" + encodeURIComponent(nombreSala.trim()) + "?nombre=" + encodeURIComponent(nombre.value.trim());
    }

    document.getElementById("formulario").addEventListener("submit", (e) => {
      e.preventDefault();
      entrar(sala.value);
    });

    // Pide al servidor las salas activas y cuánta gente hay en cada una
    async function cargarSalas() {
      try {
        const salas = await (await fetch("/salas")).json();
        const nombres = Object.keys(salas);
        if (!nombres.length) {
          lista.innerHTML = '<li class="vacio">No hay salas activas. ¡Crea la primera!</li>';
          return;
        }
        lista.replaceChildren(...nombres.map((s) => {
          const li = document.createElement("li");
          li.className = "sala";
          const titulo = document.createElement("div");
          titulo.textContent = s + " ";
          const gente = document.createElement("span");
          gente.textContent = salas[s] + (salas[s] === 1 ? " persona" : " personas");
          titulo.appendChild(gente);
          const boton = document.createElement("button");
          boton.className = "secundario";
          boton.textContent = "Unirse";
          boton.onclick = () => entrar(s);
          li.append(titulo, boton);
          return li;
        }));
      } catch {}
    }
    cargarSalas();
    setInterval(cargarSalas, 5000);
  </script>
</body>
</html>
"""

# ===== Chat de una sala (y panel del servidor) =====
html_chat = """
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Chat</title>
""" + estilos + """
</head>
<body>
  <main class="chat">
    <header>
      <a href="/" aria-label="Volver a las salas">&larr;</a>
      <h1 id="titulo">Chat</h1>
      <span id="estado" class="estado" role="status">Conectando...</span>
      <button id="reconectar" class="secundario" type="button" hidden>Reconectar</button>
    </header>

    <ul id="mensajes" class="lista" aria-live="polite">
      <li class="vacio" id="vacio">Aún no hay mensajes</li>
    </ul>

    <form id="formulario">
      <input id="texto" autocomplete="off" maxlength="500" placeholder="Escribe un mensaje..." aria-label="Mensaje" disabled>
      <button id="enviar" disabled>Enviar</button>
    </form>
  </main>

  <script>
    const PANEL = __PANEL__; // true en /servidor: escribe a todas las salas

    // Elementos de la página
    const estado     = document.getElementById("estado");
    const reconectar = document.getElementById("reconectar");
    const mensajes   = document.getElementById("mensajes");
    const vacio      = document.getElementById("vacio");
    const formulario = document.getElementById("formulario");
    const texto      = document.getElementById("texto");
    const enviar     = document.getElementById("enviar");

    // Sala y nombre salen de la dirección: /sala/<sala>?nombre=<nombre>
    const sala = decodeURIComponent(location.pathname.split("/")[2] || "");
    let nombre = new URLSearchParams(location.search).get("nombre");
    if (!PANEL && !nombre) nombre = prompt("¿Cómo te llamas?") || "Anónimo";
    const titulo = PANEL ? "Panel del servidor" : "Sala: " + sala;
    document.getElementById("titulo").textContent = titulo;
    document.title = titulo;

    let ws = null; // la conexión WebSocket actual

    // Cambia la insignia de estado y activa/desactiva la barra de escribir
    function ponerEstado(clase, etiqueta) {
      estado.className = "estado " + clase;
      estado.textContent = etiqueta;
      const abierto = clase === "conectado";
      texto.disabled = !abierto;
      enviar.disabled = !abierto;
      reconectar.hidden = clase !== "desconectado";
      if (abierto) texto.focus();
    }

    // Añade una burbuja. autor = null si lo escribí yo
    function agregarMensaje(contenido, autor) {
      vacio.remove(); // quita el aviso de "Aún no hay mensajes"
      const li = document.createElement("li");
      li.className = autor === null ? "burbuja mio" : "burbuja";
      if (autor !== null) {
        const quien = document.createElement("strong");
        quien.textContent = autor;
        li.appendChild(quien);
      }
      li.appendChild(document.createTextNode(contenido)); // texto tal cual, nunca como HTML
      const hora = document.createElement("time");
      hora.textContent = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      li.appendChild(hora);
      mensajes.appendChild(li);
      mensajes.scrollTop = mensajes.scrollHeight; // baja hasta el último mensaje
    }

    // Avisos grises: "X entró en la sala"
    function agregarAviso(contenido) {
      vacio.remove();
      const li = document.createElement("li");
      li.className = "aviso";
      li.textContent = contenido;
      mensajes.appendChild(li);
      mensajes.scrollTop = mensajes.scrollHeight;
    }

    function conectar() {
      ponerEstado("", "Conectando...");
      const protocolo = location.protocol === "https:" ? "wss" : "ws";
      const ruta = PANEL ? "/ws/servidor"
                         : "/ws/" + encodeURIComponent(sala) + "?nombre=" + encodeURIComponent(nombre);
      ws = new WebSocket(protocolo + "://" + location.host + ruta);

      ws.onopen    = () => ponerEstado("conectado", "Conectado");
      ws.onclose   = () => ponerEstado("desconectado", "Desconectado");
      ws.onmessage = (evento) => {
        const datos = JSON.parse(evento.data);
        if (datos.aviso) agregarAviso(datos.aviso);
        else agregarMensaje(datos.texto, datos.de);
      };
    }

    // Al enviar el formulario (botón o tecla Enter)
    formulario.addEventListener("submit", (e) => {
      e.preventDefault(); // evita que la página se recargue
      const mensaje = texto.value.trim();
      if (!mensaje || !ws || ws.readyState !== WebSocket.OPEN) return;
      ws.send(mensaje);
      agregarMensaje(mensaje, null);
      texto.value = "";
    });

    reconectar.addEventListener("click", conectar);
    conectar();
  </script>
</body>
</html>
"""

salas: dict[str, set[WebSocket]] = defaultdict(set)  # nombre de sala -> conexiones
paneles: set[WebSocket] = set()                       # conexiones de /servidor


async def enviar(destinos, datos, excepto=None):
    """Manda un JSON a cada conexión; una conexión rota no detiene a las demás."""
    texto = json.dumps(datos)
    for ws in list(destinos):
        if ws is not excepto:
            try:
                await ws.send_text(texto)
            except Exception:
                destinos.discard(ws)


app = FastAPI()


@app.get("/")
async def inicio():
    return HTMLResponse(html_inicio)


@app.get("/salas")
async def listar_salas():
    return {nombre: len(conexiones) for nombre, conexiones in salas.items()}


@app.get("/sala/{sala}")
async def pagina_sala(sala: str):
    return HTMLResponse(html_chat.replace("__PANEL__", "false"))


@app.get("/servidor")
async def servidor():
    return HTMLResponse(html_chat.replace("__PANEL__", "true"))


# Debe ir antes de /ws/{sala} para que "servidor" no se tome como nombre de sala
@app.websocket("/ws/servidor")
async def ws_servidor(websocket: WebSocket):
    await websocket.accept()
    paneles.add(websocket)
    try:
        while True:
            mensaje = (await websocket.receive_text())[:500]
            for conexiones in list(salas.values()):
                await enviar(conexiones, {"de": "Servidor", "texto": mensaje})
    except WebSocketDisconnect:
        pass
    finally:
        paneles.discard(websocket)


@app.websocket("/ws/{sala}")
async def ws_sala(websocket: WebSocket, sala: str, nombre: str = "Anónimo"):
    sala = sala.strip()[:40] or "general"
    nombre = nombre.strip()[:30] or "Anónimo"
    await websocket.accept()
    miembros = salas[sala]
    miembros.add(websocket)
    await enviar(miembros, {"aviso": f"{nombre} entró en la sala"}, excepto=websocket)
    try:
        while True:
            mensaje = (await websocket.receive_text())[:500]
            await enviar(miembros, {"de": nombre, "texto": mensaje}, excepto=websocket)
            await enviar(paneles, {"de": f"{nombre} @ {sala}", "texto": mensaje})
    except WebSocketDisconnect:
        pass
    finally:
        miembros.discard(websocket)
        if miembros:
            await enviar(miembros, {"aviso": f"{nombre} salió de la sala"})
        else:
            salas.pop(sala, None)  # sala vacía: desaparece de la lista
