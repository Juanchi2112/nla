# Deploy — NLA Inference (Qwen2.5-7B)

Pasos para levantar este repo en una VM con GPU.

## Requisitos

- GPU NVIDIA con ≥ 16 GB VRAM (L4 24GB, A10 24GB, RTX 4090, A100 — todas funcionan)
- Driver NVIDIA ≥ 535, CUDA 12.1+
- Ubuntu 22.04 / Debian 12 (otras distros probablemente andan)
- Python 3.11
- ~40 GB de disco libre (15 GB pesos + venv + caches HF)

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

**4. Smoke test** (terminal 2)

```bash
bash scripts/smoke_test.sh
```

Genera 1 explicación con un vector random.
**Si la salida es inglés → OK**. Si es CJK / chino → algo falló (ver `README.md` § Debugging).

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

## Variables de entorno

| var | default | uso |
|---|---|---|
| `PYTHON_BIN` | `python3.11` | binario de python para el venv |
| `MODEL_REPO` | `kitft/nla-qwen2.5-7b-L20-av` | repo HF con los pesos |
| `MODEL_DIR` | `./actor_hf` | dónde se descargan los pesos |
| `VENV_DIR` | `.venv` | venv path |
| `PORT` | `30000` | puerto SGLang |
| `MEM_FRAC` | `0.85` | `--mem-fraction-static` |

Ej: `MODEL_DIR=/data/qwen bash scripts/setup.sh`

## Otros modelos

Gemma-3 / Llama-3.3 son **gated** en HF (necesitan `HF_TOKEN`) y Gemma además requiere un parche custom en SGLang. Ver `README.md` § Model-specific parameters. Los scripts acá están calibrados para Qwen — para otros modelos hay que ajustar más cosas.
