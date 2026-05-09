# Deploy — NLA Inference (Qwen2.5-7B)

Pasos para levantar este repo en una VM con GPU.

> Para desarrollo local del backend + frontend (sin GPU), ver § "Desarrollo local"
> más abajo.

## Requisitos (GPU box)

- GPU NVIDIA con ≥ 16 GB VRAM (L4 24GB, A10 24GB, RTX 4090, A100 — todas funcionan)
- Driver NVIDIA ≥ 535, CUDA 12.1+
- Ubuntu 22.04 / Debian 12 (otras distros probablemente andan)
- Python 3.11
- ~40 GB de disco libre (15 GB pesos + venv + caches HF)

## Pasos (GPU box)

**1. Clonar el repo en la VM**

```bash
git clone <tu-repo-url> nla
cd nla
```

**2. Setup** (uv + venv + deps GPU + descarga de pesos)

```bash
bash gpu/scripts/setup.sh
```

El script auto-instala uv si falta y corre `uv sync --extra gpu`.

**3. Levantar SGLang** (terminal 1)

```bash
bash gpu/scripts/launch_sglang.sh
```

Esperá a ver `The server is fired up and ready to roll!` antes de seguir.

**4. Smoke test** (terminal 2)

```bash
bash gpu/scripts/smoke_test.sh
```

Genera 1 explicación con un vector random.
**Si la salida es inglés → OK**. Si es CJK / chino → algo falló (ver `README.md` § Debugging).

## Pipeline end-to-end (Qwen base → NLA)

El smoke test usa un vector random. Para probar con activations **reales** del residual stream de Qwen, hace falta correr Qwen base, extraer activations, y mandárselas al NLA actor. En una sola GPU de 24 GB esto se hace **secuencialmente** porque ambos modelos no entran simultáneos.

**Flujo**:

1. **Apagar SGLang** si está corriendo (`Ctrl+C`). Verificar VRAM libre con `nvidia-smi`.

2. **Extraer activations** (carga Qwen base, descarga ~15 GB la primera vez):
   ```bash
   uv run python gpu/scripts/extract_activations.py --output vectors.parquet
   ```
   El script libera la VRAM al terminar.

3. **Re-levantar SGLang** con el NLA actor (terminal 1):
   ```bash
   bash gpu/scripts/launch_sglang.sh
   ```

4. **Decodificar las activations extraídas** (terminal 2):
   ```bash
   uv run python gpu/nla_inference.py ./actor_hf --parquet vectors.parquet --n 20
   ```

**Criterio de validación cualitativa**: las decodificaciones deberían describir conceptos relacionados con el contexto del token. Ej. en `"The capital of France is Paris..."`, la posición de `Paris` debería decodificar a algo sobre ciudades / Francia / geografía europea, no a CJK ni a algo sin relación.

**Textos de prueba**: están hardcoded en `gpu/scripts/extract_activations.py` (`TEST_TEXTS`). Editá ese list para probar con otros textos.

## Levantar el GPU FastAPI server (`gpu/server.py`)

Para que el backend (Railway) se conecte vía `/decode`, hay que levantar el FastAPI del lado GPU:

```bash
# Después de setup + SGLang corriendo
uv run uvicorn gpu.server:app --host 0.0.0.0 --port 44016
```

El backend usa `ORCHESTRATOR_GPU=decoder` y `GPU_URL=http://<gpu-ip>:44016` para hablarle.

## Variables de entorno (GPU)

| var | default | uso |
|---|---|---|
| `MODEL_REPO` | `kitft/nla-qwen2.5-7b-L20-av` | repo HF con los pesos |
| `MODEL_DIR` | `./actor_hf` | dónde se descargan los pesos |
| `PORT` | `30000` (SGLang) / `44016` (server.py) | — |
| `MEM_FRAC` | `0.85` | `--mem-fraction-static` de SGLang |

Ej: `MODEL_DIR=/data/qwen bash gpu/scripts/setup.sh`

## Otros modelos

Gemma-3 / Llama-3.3 son **gated** en HF (necesitan `HF_TOKEN`) y Gemma además requiere un parche custom en SGLang. Ver `README.md` § Model-specific parameters. Los scripts están calibrados para Qwen — para otros modelos hay que ajustar más cosas.

---

## Desarrollo local (sin GPU)

Para correr el stack monitoring (backend + frontend) sin GPU.
Útil para desarrollo del backend, validar UI, escribir tests.

### Setup (una vez)

```bash
# Instalar uv si no lo tenés
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clonar y crear venv
git clone <tu-repo-url> nla
cd nla
uv venv --python 3.11
uv sync --extra dev
```

`uv sync --extra dev` instala las deps de runtime (FastAPI, anthropic) + las de
desarrollo (pytest, ruff). El Dockerfile del backend usa `uv sync --frozen --no-dev`
durante el build de Railway.

### Correr los servicios

2 terminales (judge ya corre in-process en el backend):

```bash
# Terminal 1 — backend (orchestrator + judge in-process)
PYTHONPATH=. JUDGE_BACKEND=regex ORCHESTRATOR_GPU=mock \
  uv run uvicorn backend.app:app --port 8001

# Terminal 2 — frontend
cd frontend
NEXT_PUBLIC_ORCHESTRATOR_URL=http://localhost:8001 npm run dev
```

Abrí `http://localhost:3000`.

Para usar Claude como judge en lugar de regex:
```bash
ANTHROPIC_API_KEY=sk-ant-... JUDGE_BACKEND=claude ORCHESTRATOR_GPU=mock \
  uv run uvicorn backend.app:app --port 8001
```

### Tests

```bash
# Linter + formatter
uv run ruff check .
uv run ruff format --check .

# Test suite (38 tests, ~6s)
PYTHONPATH=. uv run pytest

# Solo unit tests del judge (más rápidos)
PYTHONPATH=. uv run pytest tests/test_judge.py
```

CI (`.github/workflows/ci.yml`) corre los 3 chequeos automáticamente en cada PR
y push a `main`.

### Estructura

```
nla/
├── frontend/                   # Next.js 16 dashboard            → Vercel
├── backend/                    # FastAPI (orchestrator + judge)  → Railway
│   ├── app.py
│   ├── judge/                  # in-process Judge lib
│   │   ├── judge.py            #   RegexJudge, ClaudeJudge, MultiTokenJudge
│   │   └── rubrics.py
│   ├── judge_runner.py         # async wrapper around backend.judge
│   ├── gpu/                    # HTTP client adapter (mock + decoder)
│   ├── sessions.py
│   ├── schemas.py
│   ├── mock_generator.py
│   ├── Dockerfile              # uv-based, no requirements.txt
│   └── railway.toml
├── gpu/                        # GPU-only code                    → vast.ai
│   ├── server.py               # FastAPI /decode endpoint
│   ├── nla_inference.py        # vendored from kitft — NO MODIFICAR
│   ├── scripts/                # setup, launch_sglang, smoke_test, extract, decode
│   └── examples/               # transcripts vendored
├── tests/                      # pytest del backend + judge
├── .github/workflows/ci.yml
├── pyproject.toml              # única fuente de deps + ruff + pytest config
├── uv.lock
├── DEPLOY.md
└── README.md
```

### Switch a GPU real (cuando esté listo)

Cuando la GPU esté arriba (port 44016 por convención):

```bash
PYTHONPATH=. \
  ORCHESTRATOR_GPU=decoder \
  GPU_URL=http://<gpu-ip>:44016 \
  GPU_SKIP_FIRST=5 \
  JUDGE_BACKEND=regex \
  uv run uvicorn backend.app:app --port 8001
```

El frontend no necesita cambios — los `nla_trace` events ahora vienen de decodes
reales del NLA en lugar de monólogos canned.
