# Deploy — NLA Inference (Qwen2.5-7B)

Pasos para levantar este repo en una VM con GPU.

## Requisitos

- GPU NVIDIA con ≥ 16 GB VRAM para validación cualitativa (L4 24GB, A10 24GB, RTX 4090).
- **Para el steering loop completo (Qwen base + AV + AR cohabitando): A100 80GB** (cómodo)
  o A100 40GB (apretado, AR en CPU). Ver § Sizing para steering.
- Driver NVIDIA ≥ 535, CUDA 12.1+
- Ubuntu 22.04 / Debian 12
- Python 3.11
- ~50 GB de disco libre (15 GB AV + 10 GB AR + 14 GB Qwen base + venv + caches HF)

## Pasos

**1. Clonar el repo en la VM**

```bash
git clone <tu-repo-url> nla
cd nla
```

**2. Setup** (venv + deps + descarga de pesos)

```bash
bash scripts/setup.sh
```

**3. Levantar SGLang** (terminal 1)

```bash
bash scripts/launch_sglang.sh
```

Esperá a ver `The server is fired up and ready to roll!` antes de seguir.

**4. Smoke test del AV** (terminal 2)

```bash
bash scripts/smoke_test.sh
```

Genera 1 explicación con un vector random.
**Si la salida es inglés → OK**. Si es CJK / chino → algo falló (ver `README.md` § Debugging).

**5. Sanity test del AR** (terminal 2, no necesita SGLang)

```bash
python scripts/test_critic.py
```

Carga `NLACritic` desde `./critic_hf` y valida que `reconstruct(text)` produce
vectores con geometría semántica coherente (textos similares → cos alto, distintos → cos bajo).
Si falla, `compute_delta` del steering loop estará roto. Ver `README.md` § critic.

## Pipeline end-to-end (Qwen base → NLA)

El smoke test usa un vector random. Para probar con activations **reales** del residual stream de Qwen, hace falta correr Qwen base, extraer activations, y mandárselas al NLA actor. En una sola GPU de 24 GB esto se hace **secuencialmente** porque ambos modelos no entran simultáneos.

**Flujo**:

1. **Apagar SGLang** si está corriendo (`Ctrl+C`). Verificar VRAM libre con `nvidia-smi`.

2. **Extraer activations** (carga Qwen base, descarga ~15 GB la primera vez):
   ```bash
   python scripts/extract_activations.py --output vectors.parquet
   ```
   El script libera la VRAM al terminar.

3. **Re-levantar SGLang** con el NLA actor (terminal 1):
   ```bash
   bash scripts/launch_sglang.sh
   ```

4. **Decodificar las activations extraídas** (terminal 2):
   ```bash
   python nla_inference.py ./actor_hf --parquet vectors.parquet --n 20
   ```

**Criterio de validación cualitativa**: las decodificaciones deberían describir conceptos relacionados con el contexto del token. Ej. en `"The capital of France is Paris..."`, la posición de `Paris` debería decodificar a algo sobre ciudades / Francia / geografía europea, no a CJK ni a algo sin relación.

**Textos de prueba**: están hardcoded en `scripts/extract_activations.py` (`TEST_TEXTS`). Editá ese list para probar con otros textos.

### Validación cuantitativa: round-trip fidelity (necesario antes del steering loop)

Cierra el ciclo `h → AV → s → AR → ĥ` y mide `cos(h, ĥ)`. Si esto pasa, el AR produce direcciones útiles para `compute_delta` y el steering loop es viable.

```bash
# Con SGLang corriendo y vectors.parquet ya extraído:
python scripts/roundtrip_real.py --parquet vectors.parquet --device cpu
```

**Esperado**:
- `mean cos ≥ 0.85` → PASS, steering loop viable.
- `0.70 ≤ mean cos < 0.85` → MARGINAL, steering puede andar a ~50% como el paper.
- `mean cos < 0.70` → FAIL, hay bug (injection_scale, embed_scale, layer mismatch). Cazarlo antes de gastar A100.

En A100 80GB usá `--device cuda` (~10× más rápido).

## Variables de entorno

| var | default | uso |
|---|---|---|
| `PYTHON_BIN` | `python3.11` | binario de python para el venv |
| `MODEL_REPO` | `kitft/nla-qwen2.5-7b-L20-av` | repo HF con los pesos del AV (verbalizer) |
| `MODEL_DIR` | `./actor_hf` | dónde se descargan los pesos del AV |
| `CRITIC_REPO` | `kitft/nla-qwen2.5-7b-L20-ar` | repo HF con los pesos del AR (reconstructor) |
| `CRITIC_DIR` | `./critic_hf` | dónde se descargan los pesos del AR |
| `VENV_DIR` | `.venv` | venv path |
| `PORT` | `30000` | puerto SGLang |
| `MEM_FRAC` | `0.85` | `--mem-fraction-static` para SGLang (AV standalone). Para steering loop en A100 cohabitando con Qwen+AR, override a `0.30` (80GB) o `0.20` (40GB). |

Ej: `MODEL_DIR=/data/qwen bash scripts/setup.sh`

## Sizing para steering (1× A100)

El steering loop necesita **Qwen base + AV (en SGLang) + AR (in-process)** simultáneos.

**A100 80GB (recomendado)**:
- Qwen base bf16: ~14 GB
- SGLang AV con `MEM_FRAC=0.30`: ~24 GB pre-allocated
- AR truncado bf16: ~10 GB
- Headroom: ~10 GB
- **Total: ~58/80 GB** — cómodo.

**A100 40GB (apretado)**:
- Qwen base: ~14 GB
- SGLang AV con `MEM_FRAC=0.20`: ~8 GB
- AR en CPU (`device="cpu"` en `NLACritic`): 0 GB GPU, ~10 GB RAM, ~3s por reconstruct
- Headroom: ~18 GB
- **Total GPU: ~22/40 GB** — funciona pero margen mínimo. Cualquier OOM por activations
  altas requiere bajar `MEM_FRAC` a 0.15 o capar context-length.

Lanzamiento:

```bash
# A100 80GB
MEM_FRAC=0.30 bash scripts/launch_sglang.sh

# A100 40GB
MEM_FRAC=0.20 bash scripts/launch_sglang.sh
# y al instanciar NLACritic en tu código:
# critic = NLACritic("./critic_hf", device="cpu")
```

## Otros modelos

Gemma-3 / Llama-3.3 son **gated** en HF (necesitan `HF_TOKEN`) y Gemma además requiere un parche custom en SGLang. Ver `README.md` § Model-specific parameters. Los scripts acá están calibrados para Qwen — para otros modelos hay que ajustar más cosas.
