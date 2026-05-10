export type DecodeRow = {
  pos: number;
  context: string;
  context_highlighted: string;
  norm: number;
  decode: string;
  mse: number | null;
  cos: number | null;
};

export type DecodeResponse = {
  text: string;
  activation_layer: number;
  n_total_tokens: number;
  rows: DecodeRow[];
};

export type DecodeOptions = {
  skip_first?: number;
  score?: boolean;
  temperature?: number;
  max_new_tokens?: number;
};

export async function decode(
  text: string,
  opts: DecodeOptions = {}
): Promise<DecodeResponse> {
  const res = await fetch("/api/decode", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ text, ...opts }),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`decode failed: ${res.status} ${detail}`);
  }
  const data = (await res.json()) as DecodeResponse;
  if (!data || !Array.isArray(data.rows)) {
    throw new Error("decode: malformed response");
  }
  return data;
}
