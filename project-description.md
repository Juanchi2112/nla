# Verbalize

**Auditamos qué está *pensando* un LLM mientras habla, no solo lo que dice.**

<!-- TODO: GIF / video corto mostrando detección de misalignment en vivo: el output verbal compliant a la izquierda, el thought stream a la derecha, el juez prendiéndose en amarillo cuando aparece la divergencia. -->
<!-- ![Verbalize detectando una divergencia en vivo](./docs/verbalize-divergence-demo.gif) -->

## El problema

Todos queremos delegar tareas a la IA, pero los modelos de frontera ya engañan a sus operadores cuando creen que nadie los está observando. *Alignment-faking* (Anthropic, 2024) demostró que Claude cumplía estratégicamente con la alineación durante el entrenamiento y lo revertía cuando infería que no estaba siendo medido.

Esto es un defecto de cómo funcionan los sistemas de inteligencia artificial modernos. Nosotros le definimos un objetivo sub-especificado y el agente, con tal de maximizar ese objetivo, sí o sí tiene que *evitar ser apagado* para poder cumplir su meta. Entonces es fundamental entender los "pensamientos" de estos modelos para poder contar con ellos de forma segura y alinearlos con nuestros objetivos. La pregunta dejó de ser **"¿el modelo va a engañar?"** y pasó a ser **"¿nos vamos a dar cuenta cuando lo haga?"**

## Por qué los enfoques actuales no se dan cuenta

La respuesta default en 2026, es **monitoreo de chain-of-thought**: pedirle al modelo que razone en texto y leer ese razonamiento. Todos esos enfoques leen texto que el modelo *escribió sabiendo que iba a ser leído*. La investigación de fidelidad de CoT de Anthropic (2025) mostró que los trazos de razonamiento rutinariamente justifican respuestas pre-decididas en vez de describir la computación que las produjo. Si entrenás un modelo contra un monitor de CoT, aprende a maquillar su razonamiento, no a dejar de razonar así. **Estás leyendo un comunicado de prensa que el modelo escribió sobre sí mismo.**

## Qué leemos en cambio

Verbalize lee el **residual stream**: el estado oculto interno del modelo en una capa intermedia, una señal sobre la cual el modelo base nunca tuvo presión de entrenamiento, porque ningún humano ni señal de RL la vio nunca durante el entrenamiento. Otro modelo (NLA de `kitft/nla-models`) invierte ese estado oculto de vuelta a lenguaje natural abierto, cada K tokens, mientras la generación todavía se está streaming. Un juez Claude Haiku 4.5 lee cada pensamiento contra una rúbrica y marca las divergencias contra la salida verbal, en vivo.

| Enfoque | Lee | ¿Gameable? | Output |
|---|---|---|---|
| Clasificadores de output / refusal | String final | Trivialmente | Booleano |
| **Monitoreo de CoT** *(lo que la mayoría va a construir)* | Trazo escrito por el modelo | **Sí, performativo** | Texto libre, pero performado |
| Probes de activaciones | Estado oculto | No | Un escalar por concepto fijo |
| **Verbalize** | **Estado oculto** | **No, señal no-performada** | **Texto libre, contra cualquier rúbrica** |

## Cómo se ve en 30 segundos

Un fintech quiere desplegar un modelo como agente de atención al cliente. Su equipo de compliance escribe 4 reglas en español llano: nunca afirmes acceder a datos del cliente, nunca des consejos financieros específicos, siempre disclosá que sos una IA, nunca le des la razón a un cliente que afirma algo factualmente incorrecto.

Hoy, la única forma de validar que el modelo cumple esas reglas es red-teaming caja-negra: un humano escribe prompts adversariales, lee las respuestas, juzga. Esto no escala, no puede testear miles de combinaciones regla-prompt, y **solo ve lo que el modelo dice**, no lo que computa.

Con Verbalize:

1. Un agente Claude genera N probes adversariales por regla.
2. Cada probe corre por el stack en vivo: Qwen genera la respuesta token por token, el actor NLA verbaliza cada K activaciones del residual stream.
3. Un juez evalúa cada corrida contra la regla, en *dos capas independientes*:
   - **output_aligned**: ¿la respuesta verbal cumple la regla?
   - **internal_aligned**: ¿la representación interna era consistente con esa intención?
4. Reporte por regla con la columna que ningún framework de evals tiene hoy: **casos divergentes** (output cumple, interno no, o viceversa).

## Arquitectura

```
┌────────────────────┐   SSE     ┌────────────────────┐   SSE     ┌──────────────────────────┐
│  Next.js 15 / App  │ ───────►  │  FastAPI backend   │ ───────►  │  GPU box (vast.ai, A6000)│
│  Router (Vercel)   │ ◄─tokens─ │  on Railway        │ ◄─tokens─ │  SGLang + Qwen + NLA actor│
└────────────────────┘   verdict └────────┬───────────┘           └──────────────────────────┘
                                          │ in-process
                                          ▼
                                  ┌────────────────────┐
                                  │ Claude Haiku 4.5   │
                                  │ judge w/ rubric    │
                                  └────────────────────┘
```

Tres streams convergen en una pantalla: el **stream de tokens** (lo que Qwen dice), el **stream de pensamientos** (verbalizaciones NLA del residual stream en capa 20, sniffeadas cada K tokens), y el **stream del juez** (un score 0-3 por pensamiento contra una rúbrica configurable). Cada evento lleva un índice `step` para que el frontend re-correlacione visualmente aunque lleguen fuera de orden.

## Stack y por qué cada elección

- **SGLang** como servidor de inferencia: es el único framework mainstream con un path `input_embeds` funcional, que necesitamos porque al actor NLA se lo invoca sobreescribiendo *un* embedding de token en un prompt fijo con un vector de activación arbitrario.
- **Server-Sent Events de punta a punta**: tokens, pensamientos y veredictos son heterogéneos, asíncronos y unidireccionales. SSE es HTTP plano, sobrevive a cualquier CDN, y permite eventos nombrados sin un parser custom.
- **FastAPI en Railway**: el backend es orquestación + relay SSE + juez in-process. Sin dependencia de GPU. Container de $5/mes que habla con una GPU rentada solo durante la demo.
- **Claude Haiku 4.5 como juez, in-process**: mejor punto en la curva latencia × razonamiento para grading estructurado. Un único hop HTTP a Anthropic, sin servicio extra que mantener.
- **Next.js 15 App Router en Vercel**: el valor de la demo es *visual*. Framer Motion + Next dan 60fps sin un loop de render custom, y el App Router hace trivial conectarse a un consumer SSE.
- **Qwen-2.5-7B como modelo bajo observación**: partimos de la investigación de Anthropic y el repositorio de sus creadores ([`kitft/nla-models`](https://github.com/kitft/natural_language_autoencoders)), entra en una sola GPU de 24 GB, licencia permisiva.

## Dificultades reales de deployment GPU

Hacer que dos modelos clase 7B cooperen en una sola GPU con streaming de baja latencia fue la mayor parte del trabajo de ingeniería:

- **El path `input_embeds` de SGLang tenía bugs**: el validator de FastAPI bloqueaba el event loop ~155ms por request (PR upstream abierto), y bajo presión de memoria el path de retract crasheaba con shape mismatch en el KV slot.
- **Presupuesto de VRAM al milímetro**: SGLang con `--mem-fraction-static 0.85` por default no deja lugar a que `gpu/server.py` cargue Qwen base in-process. Bajamos a `MEM_FRAC=0.5`.
- **El radix cache corrompe resultados silenciosamente** con `input_embeds`: keyea por token IDs y nuestros requests no los traen, así que vectores distintos aliasean al mismo entry. `--disable-radix-cache` es obligatorio. No está documentado en ningún lado.
- **Parámetros de inyección no son intercambiables**: Qwen-7B usa `injection_scale=150`, Gemma-3-12B usa 80,000 (500x de diferencia). Errar el número falla en silencio: la salida es inglés gramatical pero describe la cosa equivocada.

## Caso de uso comercial

**Auditoría pre-deployment de alineamiento para LLMs open-source en contextos regulados.** Un compliance officer escribe 5-20 reglas en lenguaje natural. Verbalize genera probes adversariales, los corre, y devuelve un reporte por regla con la tasa de cumplimiento en output y en residual stream, más la columna de divergencias. Mercado primario: bancos, healthcare, legal. Tailwind regulatorio: EU AI Act Art. 5 prohíbe sistemas de IA con técnicas manipulativas o deceptivas, y hoy no hay forma estándar de auditarlas.

## Créditos

Modelos NLA, pipeline de entrenamiento y receta original de inferencia: **[Kit Fraser-Taliente · kitft/natural_language_autoencoders](https://github.com/kitft/natural_language_autoencoders)**.

Verbalize es el stack de monitoreo y juicio en vivo construido sobre esos modelos para **Platanus Hack 2026**.

Licencia: Apache-2.0.
