#!/usr/bin/env python3
"""
Nanoxus — Gerador de imagens sintéticas de NANOFIOS (nanowires) MEV.

Gera micrografias procedurais realistas de nanofios vistos em microscopia
eletrônica de varredura (MEV/SEM), controladas por receitas YAML.

Nanofios são estruturas rígidas, retas ou quase retas, com:
  - Bordas definidas com efeito de carga (edge brightness)
  - Substrato texturizado visível entre os fios
  - Possíveis clusters/aglomerados
  - Partículas catalíticas nas pontas
  - Sombras projetadas sobre o substrato

Para alterar os tipos de imagem, edite scripts/prompts.yaml.

Uso:
    python scripts/gerar_sinteticas.py                        # usa prompts.yaml
    python scripts/gerar_sinteticas.py -p meu_prompt.yaml     # prompt custom
    python scripts/gerar_sinteticas.py -n 500 --seed 99       # flags opcionais
"""

from __future__ import annotations

import argparse
import hashlib
import math
import random
import sys
from pathlib import Path

import cv2
import numpy as np
import yaml

RAIZ = Path(__file__).resolve().parent.parent
DIR_SINTETICAS = RAIZ / "dados" / "sinteticas"
PROMPTS_PADRAO = Path(__file__).resolve().parent / "prompts.yaml"
W_PADRAO, H_PADRAO = 1024, 768


def _r(lo, hi):
    if isinstance(lo, float) or isinstance(hi, float):
        return random.uniform(float(lo), float(hi))
    return random.randint(int(lo), int(hi))


def _rng(val, dlo, dhi):
    if val is None:
        return (dlo, dhi)
    if isinstance(val, list):
        return (val[0], val[1])
    return (val, val)


def gerar_substrato(h: int, w: int, cfg: dict) -> np.ndarray:
    brilho = _rng(cfg.get("brilho"), 30, 100)
    base = _r(*brilho)
    sub = np.full((h, w), base, dtype=np.float64)

    grad = cfg.get("gradiente", 12)
    sub += np.linspace(_r(-grad, 0), _r(0, grad), h)[:, None]
    sub += np.linspace(_r(-grad * 0.5, 0), _r(0, grad * 0.5), w)[None, :]

    tipo = cfg.get("textura", "granular")
    if tipo == "granular":
        escala_grao = cfg.get("escala_grao", 32)
        graos = np.random.normal(0, _r(10, 25), (max(1, h // escala_grao),
                                                   max(1, w // escala_grao)))
        graos = cv2.resize(graos, (w, h), interpolation=cv2.INTER_NEAREST)
        graos = cv2.GaussianBlur(graos.astype(np.float64), (5, 5), 0)
        sub += graos
    elif tipo == "liso":
        sub += np.random.normal(0, _r(3, 8), (h, w))
    elif tipo == "poroso":
        sub += np.random.normal(0, _r(5, 12), (h, w))
        n_poros = _r(10, 50)
        for _ in range(n_poros):
            cx, cy = _r(0, w - 1), _r(0, h - 1)
            raio = _r(3, 15)
            prof = _r(20, 60)
            cv2.circle(sub.astype(np.uint8), (cx, cy), raio, max(0, base - prof), -1)
        sub_u8 = np.clip(sub, 0, 255).astype(np.uint8)
        sub = sub_u8.astype(np.float64)

    sigma_ruido = _rng(cfg.get("ruido"), 4, 12)
    sub += np.random.normal(0, _r(*sigma_ruido), (h, w))

    sp = cfg.get("salt_pepper", 0.002)
    if sp > 0:
        mask = np.random.random((h, w))
        sub[mask < sp] = _r(200, 255)
        sub[mask > 1 - sp * 0.3] = _r(0, 15)

    return np.clip(sub, 0, 255).astype(np.uint8)


def desenhar_nanofio(canvas: np.ndarray, sombra: np.ndarray,
                     h: int, w: int, cfg: dict):
    # Geometria: nanofios são RETAS ou com curvatura muito leve
    angulo = random.uniform(0, 2 * math.pi)

    # Permitir orientação preferencial
    orient = cfg.get("orientacao", None)
    if orient == "vertical":
        angulo = random.gauss(math.pi / 2, 0.3)
    elif orient == "horizontal":
        angulo = random.gauss(0, 0.3)
    elif orient == "diagonal":
        angulo = random.gauss(math.pi / 4, 0.3)

    comp_range = _rng(cfg.get("comprimento"), 80, 400)
    comp = _r(*comp_range)

    esp_range = _rng(cfg.get("diametro"), 2, 8)
    esp = _r(*esp_range)

    cx = _r(int(w * 0.05), int(w * 0.95))
    cy = _r(int(h * 0.05), int(h * 0.95))

    dx = math.cos(angulo) * comp / 2
    dy = math.sin(angulo) * comp / 2
    x1, y1 = int(cx - dx), int(cy - dy)
    x2, y2 = int(cx + dx), int(cy + dy)

    ondulacao = cfg.get("ondulacao", 0.02)
    n_pts = max(20, comp // 3)
    ts = np.linspace(0, 1, n_pts)
    pts_x = x1 + (x2 - x1) * ts
    pts_y = y1 + (y2 - y1) * ts

    if ondulacao > 0:
        freq = _r(1, 4)
        amp = comp * ondulacao
        perp_x = -math.sin(angulo)
        perp_y = math.cos(angulo)
        wave = amp * np.sin(2 * math.pi * freq * ts + random.uniform(0, 2 * math.pi))
        pts_x += perp_x * wave
        pts_y += perp_y * wave

    pontos = np.column_stack([pts_x, pts_y]).astype(np.int32)

    brilho_range = _rng(cfg.get("brilho"), 150, 240)
    brilho = int(_r(*brilho_range))

    # 1) Sombra
    if cfg.get("sombra", True):
        offset = max(2, int(esp * 0.6))
        pts_sombra = pontos.copy()
        pts_sombra[:, 0] += offset
        pts_sombra[:, 1] += offset
        cv2.polylines(sombra, [pts_sombra], False, 40, int(esp * 1.5),
                      cv2.LINE_AA)

    # 2) Corpo
    esp_px = max(1, int(esp))
    cv2.polylines(canvas, [pontos], False, brilho, esp_px, cv2.LINE_AA)

    # 3) Bordas brilhantes (efeito de carga)
    if cfg.get("efeito_borda", True) and esp_px >= 2:
        borda_brilho = min(255, brilho + _r(25, 60))
        cv2.polylines(canvas, [pontos], False, borda_brilho, esp_px + 2,
                      cv2.LINE_AA)
        interior_brilho = max(80, brilho - _r(10, 30))
        esp_interior = max(1, esp_px - 1)
        cv2.polylines(canvas, [pontos], False, interior_brilho, esp_interior,
                      cv2.LINE_AA)

    # 4) Partícula catalítica na ponta
    if cfg.get("catalise_ponta", True) and random.random() < 0.4:
        ponta = pontos[-1] if random.random() > 0.5 else pontos[0]
        raio_cat = max(2, int(esp * _r(0.8, 1.8)))
        brilho_cat = min(255, brilho + _r(10, 40))
        cv2.circle(canvas, tuple(ponta), raio_cat, brilho_cat, -1, cv2.LINE_AA)


def desenhar_cluster(canvas: np.ndarray, sombra: np.ndarray,
                     h: int, w: int, cfg: dict):
    cx = _r(int(w * 0.1), int(w * 0.9))
    cy = _r(int(h * 0.1), int(h * 0.9))

    n_fios = _r(3, 12)
    angulo_base = random.uniform(0, 2 * math.pi)
    abertura = cfg.get("abertura_cluster", 0.8)

    for _ in range(n_fios):
        ang = angulo_base + random.gauss(0, abertura)
        comp = _r(*_rng(cfg.get("comprimento"), 60, 300))

        dx = math.cos(ang) * comp
        dy = math.sin(ang) * comp

        pontos = []
        n_pts = max(10, comp // 5)
        for t in np.linspace(0, 1, n_pts):
            px = int(cx + dx * t + random.gauss(0, comp * 0.01))
            py = int(cy + dy * t + random.gauss(0, comp * 0.01))
            pontos.append([px, py])
        pontos = np.array(pontos, dtype=np.int32)

        esp = _r(*_rng(cfg.get("diametro"), 2, 6))
        brilho = int(_r(*_rng(cfg.get("brilho"), 150, 230)))

        cv2.polylines(canvas, [pontos], False, brilho, max(1, int(esp)),
                      cv2.LINE_AA)

        if cfg.get("efeito_borda", True) and esp >= 2:
            cv2.polylines(canvas, [pontos], False,
                          min(255, brilho + _r(20, 45)),
                          max(1, int(esp)) + 2, cv2.LINE_AA)
            cv2.polylines(canvas, [pontos], False,
                          max(80, brilho - _r(10, 25)),
                          max(1, int(esp) - 1), cv2.LINE_AA)


def camada_nanofios(h: int, w: int, cfg: dict) -> tuple[np.ndarray, np.ndarray]:
    canvas = np.zeros((h, w), dtype=np.float64)
    sombra = np.zeros((h, w), dtype=np.float64)

    qtd = _rng(cfg.get("quantidade"), 10, 50)
    n = _r(*qtd)
    for _ in range(n):
        desenhar_nanofio(canvas, sombra, h, w, cfg)

    n_clusters = cfg.get("clusters", 0)
    if isinstance(n_clusters, list):
        n_clusters = _r(n_clusters[0], n_clusters[1])
    for _ in range(int(n_clusters)):
        desenhar_cluster(canvas, sombra, h, w, cfg)

    return canvas, sombra


def camada_particulas(h: int, w: int, cfg: dict) -> np.ndarray:
    canvas = np.zeros((h, w), dtype=np.float64)
    if not cfg.get("ativo", True):
        return canvas

    qtd = _rng(cfg.get("quantidade"), 5, 30)
    raio = _rng(cfg.get("raio"), 1, 4)
    brilho = _rng(cfg.get("brilho"), 120, 230)

    for _ in range(_r(*qtd)):
        cx, cy = _r(0, w - 1), _r(0, h - 1)
        r = _r(*raio)
        b = _r(*brilho)
        if random.random() > 0.7:
            pts = []
            n_vert = _r(4, 8)
            for k in range(n_vert):
                ang = 2 * math.pi * k / n_vert + random.gauss(0, 0.3)
                rr = r * _r(0.5, 1.5)
                pts.append([int(cx + rr * math.cos(ang)),
                            int(cy + rr * math.sin(ang))])
            cv2.fillPoly(canvas, [np.array(pts, dtype=np.int32)], b)
        else:
            cv2.circle(canvas, (cx, cy), r, b, -1, cv2.LINE_AA)

    return canvas


def barra_info(canvas: np.ndarray, h: int, w: int, cfg: dict) -> np.ndarray:
    if not cfg.get("ativo", True):
        return canvas
    if random.random() > cfg.get("probabilidade", 0.5):
        return canvas

    bh = _r(45, 65)
    barra = np.zeros((bh, w), dtype=np.uint8)
    cv2.line(barra, (0, 1), (w, 1), 180, 1)

    mags = cfg.get("magnificacoes", ["10kX", "25kX", "50kX", "100kX", "5kX"])
    dets = cfg.get("detectores", ["SE2", "InLens", "BSE", "ETD"])
    kvs = cfg.get("tensoes", ["5.00 kV", "10.00 kV", "15.00 kV", "20.00 kV"])
    escalas = cfg.get("escalas", ["500 nm", "1 µm", "2 µm", "5 µm", "200 nm"])

    font = cv2.FONT_HERSHEY_SIMPLEX
    s = _r(0.35, 0.5)
    c = _r(160, 210)

    cv2.putText(barra, f"Mag = {random.choice(mags)}", (10, bh - 12),
                font, s, c, 1, cv2.LINE_AA)
    cv2.putText(barra, f"EHT = {random.choice(kvs)}", (w // 3, bh - 12),
                font, s, c, 1, cv2.LINE_AA)
    cv2.putText(barra, random.choice(dets), (int(w * 0.62), bh - 12),
                font, s, c, 1, cv2.LINE_AA)

    bw = _r(60, 140)
    bx = w - bw - 20
    by = bh - 22
    cv2.line(barra, (bx, by), (bx + bw, by), c, 2)
    cv2.line(barra, (bx, by - 5), (bx, by + 5), c, 1)
    cv2.line(barra, (bx + bw, by - 5), (bx + bw, by + 5), c, 1)
    cv2.putText(barra, random.choice(escalas), (bx + bw // 4, by - 7),
                font, s * 0.8, c, 1, cv2.LINE_AA)

    return np.vstack([canvas[:h - bh, :], barra])


def pos_proc(img: np.ndarray, cfg: dict) -> np.ndarray:
    out = img.astype(np.float64)

    # Blur (resolução finita)
    blur = cfg.get("blur", {})
    if blur and random.random() < blur.get("probabilidade", 0.3):
        ks = random.choice(blur.get("kernels", [3, 5]))
        out = cv2.GaussianBlur(out.astype(np.uint8), (ks, ks), 0).astype(np.float64)

    r_det = _rng(cfg.get("ruido_detector"), 2, 5)
    out += np.random.normal(0, _r(*r_det), out.shape)

    contraste = _rng(cfg.get("contraste"), 0.85, 1.2)
    brilho = _rng(cfg.get("brilho_ajuste"), -8, 8)
    out = _r(*contraste) * out + _r(*brilho)

    return np.clip(out, 0, 255).astype(np.uint8)


def gerar_imagem(prompt: dict) -> np.ndarray:
    w = prompt.get("largura", W_PADRAO)
    h = prompt.get("altura", H_PADRAO)

    # 1) Substrato
    substrato = gerar_substrato(h, w, prompt.get("substrato", {}))

    # 2) Nanofios + sombras
    fios, sombras = camada_nanofios(h, w, prompt.get("nanofios", {}))

    resultado = substrato.astype(np.float64)

    sombra_mask = (sombras > 0).astype(np.float64)
    resultado = resultado * (1 - sombra_mask * 0.3)

    fio_mask = (fios > 0).astype(np.float64)
    resultado = resultado * (1 - fio_mask) + fios * fio_mask

    part = camada_particulas(h, w, prompt.get("particulas", {}))
    p_mask = (part > 0).astype(np.float64)
    resultado = resultado * (1 - p_mask) + part * p_mask

    resultado = np.clip(resultado, 0, 255).astype(np.uint8)
    resultado = pos_proc(resultado, prompt.get("pos_processamento", {}))
    resultado = barra_info(resultado, h, w, prompt.get("barra_info", {}))

    if len(resultado.shape) == 2:
        resultado = cv2.cvtColor(resultado, cv2.COLOR_GRAY2BGR)

    return resultado


def carregar_prompts(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f).get("prompts", [])


def nome_arquivo(idx: int, img: np.ndarray) -> str:
    h = hashlib.md5(img.tobytes()[:4096] + idx.to_bytes(4, "big"),
                    usedforsecurity=False).hexdigest()[:12]
    return f"SYN_{idx:04d}_{h}.jpg"


def main():
    ap = argparse.ArgumentParser(
        description="Gera imagens sintéticas de nanofios MEV via receitas YAML"
    )
    ap.add_argument("-p", "--prompts", type=Path, default=PROMPTS_PADRAO)
    ap.add_argument("-n", "--quantidade", type=int, default=None)
    ap.add_argument("-s", "--seed", type=int, default=42)
    ap.add_argument("-q", "--qualidade", type=int, default=92)
    ap.add_argument("-o", "--saida", type=Path, default=DIR_SINTETICAS)
    args = ap.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)

    if not args.prompts.exists():
        print(f"ERRO: {args.prompts} não encontrado")
        sys.exit(1)

    prompts = carregar_prompts(args.prompts)
    if not prompts:
        print("ERRO: nenhum prompt no YAML")
        sys.exit(1)

    total_yaml = sum(p.get("quantidade", 100) for p in prompts)
    total = args.quantidade or total_yaml

    print(f"{'=' * 62}")
    print(f"  Nanoxus — Gerador de Nanofios Sintéticos (MEV)")
    print(f"{'=' * 62}")
    print(f"  Prompts:  {args.prompts.name} ({len(prompts)} receitas)")
    print(f"  Total:    {total} imagens")
    print(f"  Saída:    {args.saida}")
    print(f"{'=' * 62}")
    for i, p in enumerate(prompts):
        print(f"  [{i+1}] {p.get('nome','?')}: {p.get('quantidade',100)} — "
              f"{p.get('descricao','')}")
    print(f"{'=' * 62}\n")

    args.saida.mkdir(parents=True, exist_ok=True)

    qtds = [max(1, round(total * p.get("quantidade", 100) / total_yaml))
            for p in prompts]
    qtds[0] += total - sum(qtds)

    idx = 0
    erros = 0
    for pi, (prompt, qtd) in enumerate(zip(prompts, qtds)):
        nome = prompt.get("nome", f"prompt_{pi}")
        print(f"▸ [{pi+1}/{len(prompts)}] {nome} — {qtd} imagens...")
        for j in range(qtd):
            try:
                img = gerar_imagem(prompt)
                cv2.imwrite(str(args.saida / nome_arquivo(idx, img)), img,
                            [cv2.IMWRITE_JPEG_QUALITY, args.qualidade])
                idx += 1
                if (j + 1) % 100 == 0 or j == 0:
                    print(f"    [{j+1}/{qtd}]")
            except Exception as e:
                erros += 1
                idx += 1
                print(f"    ERRO #{idx}: {e}")

    print(f"\n{'=' * 62}")
    print(f"  {idx - erros} geradas, {erros} erros → {args.saida}")
    print(f"{'=' * 62}")


if __name__ == "__main__":
    main()
