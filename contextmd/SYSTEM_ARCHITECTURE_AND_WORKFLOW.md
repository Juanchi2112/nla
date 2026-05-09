# Plan General de Arquitectura y Proceso: NLA Steering & Monitoring

## 1. Visión General
El objetivo es construir un sistema de monitoreo en tiempo real para modelos de lenguaje que no solo observe lo que el modelo dice (output), sino lo que "piensa" (activaciones internas o NLA). El sistema permite detectar decespción o comportamientos no deseados y "corregir" al modelo en pleno vuelo mediante la inyección de vectores de activación (Steering).

## 2. Infraestructura (3-Tier Architecture)

### Tier 1: Frontend (Next.js + TypeScript)
- **Interfaz de Usuario:** Renderiza el streaming de tokens de forma interactiva.
- **Visualización de Riesgo:** Muestra un gráfico de "picos" basado en el Score del Juez (Rubrics).
- **Control de Intervención:** Permite al usuario enviar comandos de "Steer" (Direccionamiento) basados en las alertas.
- **Comunicación:** Usa `EventSource` (SSE) para recibir datos y `fetch` (POST) para enviar comandos.

### Tier 2: Orchestrator Backend (FastAPI + Python)
- **Gestión de Sesiones:** Mantiene un mapa en memoria de las sesiones activas (`session_id`).
- **Lógica de Control:** Coordina el flujo entre el usuario y la GPU.
- **Judge LLM:** Un componente (puede ser un modelo más pequeño o una lógica de clasificación) que analiza el "Internal Monologue" extraído y genera scores de seguridad/decepción.
- **Routing de Señales:** Cuando recibe un comando de steering, lo marca en la sesión para que el loop de inferencia lo detecte.

### Tier 3: GPU Backend (sglang / Inference Engine)
- **Motor de Inferencia:** Ejecuta el modelo base (Gemma, Llama, etc.).
- **NLA Extraction:** Expone los hooks necesarios para extraer estados internos (activaciones) sin detener la generación.
- **Activation Injection:** Permite sumar vectores de dirección (Steering Vectors) a los estados internos del modelo durante el proceso de autoregresión.

---

## 3. El Proceso (Flujo de Datos)

### Paso 1: Inicialización
1. El usuario ingresa un prompt en el Frontend.
2. El Frontend genera un `UUID` único (Session ID) y envía un `POST /api/generate` al Backend.
3. El Backend crea un objeto de estado para esa sesión e inicia el loop de inferencia en la GPU.

### Paso 2: Generación y Monitoreo (The Loop)
1. La **GPU** genera el siguiente token.
2. El **Backend** extrae el "Internal Monologue" (activaciones NLA transformadas a texto).
3. El **Juez** evalúa ese monólogo contra las rúbricas (ej: ¿Es esto engañoso?).
4. El Backend envía un paquete JSON vía **SSE** al Frontend: `{ token: "...", score: 0.85, monologue: "..." }`.
5. El **Frontend** actualiza la pantalla: el texto crece y el gráfico de riesgo sube.

### Paso 3: Intervención (Steering)
1. El usuario nota un pico de riesgo y hace clic en **"Steer: Honesty"**.
2. El Frontend envía `POST /api/steer { session_id, rubric: "honesty" }`.
3. El **Backend** actualiza el flag `active_rubric` en la memoria de la sesión.
4. En la siguiente iteración, la **GPU** detecta el cambio y suma el vector de "Honestidad" a las capas del modelo.
5. El modelo cambia su trayectoria de salida y el Juez refleja una baja en el riesgo.

---

## 4. Gestión de Sesiones (Session Handling)

Para mantener la simplicidad y velocidad requerida en un hackathon:
- **Estado en Memoria:** No usaremos bases de datos externas (Redis/Postgres). Todo vive en un diccionario global de Python mientras el proceso esté corriendo.
- **Concurrencia:** FastAPI manejará múltiples sesiones mediante tareas asincrónicas (`asyncio`). Cada sesión tiene su propio buffer de eventos.
- **ID de Sesión:** El cliente es el dueño del ID, lo que facilita la reconexión si el stream de SSE se interrumpe.

---

## 5. Resumen de Comunicación
| Acción | Protocolo | Payload |
| :--- | :--- | :--- |
| Iniciar Generación | REST (POST) | `session_id`, `prompt` |
| Recibir Tokens/Alertas | SSE (GET) | `token`, `judge_score`, `trace` |
| Aplicar Steering | REST (POST) | `session_id`, `target_rubric` |
