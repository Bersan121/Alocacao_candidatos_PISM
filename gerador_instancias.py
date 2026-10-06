#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador de Instâncias para Problema NP-Difícil de Alocação / Ensalamento
-------------------------------------------------------------------------
Este script gera instâncias sintéticas personalizadas contendo informações de
escolas (capacidade total, salas e capacidades individuais), candidatos (CEP e tipo de prova)
e uma Matriz de Distâncias Euclidiana entre Candidatos e Escolas baseada em geolocalização por CEP.

Todos os parâmetros principais podem ser alterados nas VARIÁVEIS GLOBAIS abaixo
ou via linha de comando (CLI).
"""

import os
import math
import random
import json
import argparse
import urllib.request
import urllib.parse
from typing import List, Dict, Any

# ==============================================================================
# VARIÁVEIS GLOBAIS DE CONFIGURAÇÃO (Altere aqui se desejar)
# ==============================================================================

# Faixa do número de escolas por instância
MIN_ESCOLAS: int = 10
MAX_ESCOLAS: int = 20

# Faixa da capacidade total por escola (número de alunos)
MIN_CAPACIDADE_ESCOLA: int = 200
MAX_CAPACIDADE_ESCOLA: int = 500

# Faixa da quantidade de salas por escola
MIN_SALAS_POR_ESCOLA: int = 5
MAX_SALAS_POR_ESCOLA: int = 15

# Porcentagem de candidatos em relação à capacidade total acumulada de todas as escolas
MIN_PCT_CANDIDATOS: float = 0.80  # 80%
MAX_PCT_CANDIDATOS: float = 0.95  # 95%

# Porcentagem de candidatos com CEP de Juiz de Fora (o restante será de outras cidades)
PCT_CANDIDATOS_JF: float = 0.80  # 80% Juiz de Fora, 20% Outras cidades

# Arquivo de Cache de Geolocalização de CEPs (evita requisições repetidas na API)
CEP_CACHE_FILE: str = "cep_cache.json"

# Lista oficial de CEPs das Escolas em Juiz de Fora (apenas dígitos)
CEPS_ESCOLAS_JF: List[str] = [
    "36036900", "36026420", "36025001", "36048001", "36088260",
    "36032580", "36020540", "36031130", "36033170", "36032750",
    "36085420", "36047080", "36050280", "36051520", "36015000",
    "36087070", "36090380", "36036180", "36033480", "36083770"
]

# Tipos de prova dos candidatos
TIPOS_PROVA: List[str] = ["M1", "M2", "M3e", "M3s", "M3h", "M3d"]

# CEPs de outras cidades da região/estado para candidatos de fora de JF (apenas dígitos)
CEPS_OUTRAS_CIDADES: List[str] = [
    "36200010",  # Barbacena - MG
    "36500010",  # Ubá - MG
    "36150000",  # Santos Dumont - MG
    "36120000",  # Matias Barbosa - MG
    "36140000",  # Lima Duarte - MG
    "36880000",  # Muriaé - MG
    "36300000",  # São João del-Rei - MG
    "36600000",  # Bicas - MG
    "20000000",  # Rio de Janeiro - RJ
    "25600000",  # Petrópolis - RJ
    "30100000"   # Belo Horizonte - MG
]

# ==============================================================================
# GEOLOCALIZAÇÃO E CACHE DE CEPS
# ==============================================================================

def carregar_cache_cep(filepath: str = CEP_CACHE_FILE) -> Dict[str, Dict[str, float]]:
    """Carrega o arquivo de cache de CEPs do disco se existir."""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Aviso ao carregar cache de CEPs: {e}")
    return {}


def salvar_cache_cep(cache: Dict[str, Dict[str, float]], filepath: str = CEP_CACHE_FILE) -> None:
    """Salva o dicionário de cache de CEPs no arquivo JSON local."""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Erro ao salvar cache de CEPs: {e}")


def obter_geolocalizacao_cep(cep: str, cache: Dict[str, Dict[str, float]], cache_file: str = CEP_CACHE_FILE) -> Dict[str, float]:
    """
    Obtém Latitude e Longitude para um CEP via BrasilAPI v2.
    Caso o CEP já tenha sido consultado antes, retorna diretamente do cache local.
    """
    cep_clean = str(cep).replace("-", "").strip()

    if cep_clean in cache:
        return cache[cep_clean]

    # Consulta a API BrasilAPI v2
    url = f"https://brasilapi.com.br/api/cep/v2/{cep_clean}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Antigravity/1.0)"})
    lat, lon = None, None

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            coords = data.get("location", {}).get("coordinates", {})
            if coords.get("latitude") and coords.get("longitude"):
                lat = float(coords["latitude"])
                lon = float(coords["longitude"])
    except Exception:
        pass

    # Fallback se a API não retornar coordenadas
    if lat is None or lon is None:
        lat, lon = -21.76417, -43.35028

    resultado = {"latitude": lat, "longitude": lon}
    cache[cep_clean] = resultado
    salvar_cache_cep(cache, cache_file)
    return resultado


def calcular_distancia_euclidiana(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcula a distância euclidiana 2D entre duas coordenadas (lat1, lon1) e (lat2, lon2).
    """
    return math.sqrt((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2)


def calcular_matriz_distancias(
    candidatos: List[Dict[str, Any]],
    escolas: List[Dict[str, Any]],
    cache: Dict[str, Dict[str, float]],
    cache_file: str = CEP_CACHE_FILE
) -> List[List[float]]:
    """
    Gera a Matriz de Distâncias Euclidiana (Candidatos x Escolas).
    Cada linha i contém as distâncias do candidato i para todas as N escolas.
    """
    coords_escolas = [obter_geolocalizacao_cep(e["cep"], cache, cache_file) for e in escolas]
    
    matriz = []
    for cand in candidatos:
        coord_cand = obter_geolocalizacao_cep(cand["cep"], cache, cache_file)
        linha = []
        for coord_esc in coords_escolas:
            dist = calcular_distancia_euclidiana(
                coord_cand["latitude"], coord_cand["longitude"],
                coord_esc["latitude"], coord_esc["longitude"]
            )
            linha.append(round(dist, 6))
        matriz.append(linha)

    return matriz

# ==============================================================================
# FUNÇÕES GERADORAS
# ==============================================================================

def gerar_capacidades_salas(capacidade_total: int, num_salas: int, cap_minima_sala: int = 10) -> List[int]:
    """
    Divide a capacidade total da escola entre as salas de forma estocástica e justa,
    garantindo que o somatório das capacidades seja EXATAMENTE igual à capacidade total.
    """
    if capacidade_total < num_salas * cap_minima_sala:
        cap_minima_sala = max(1, capacidade_total // num_salas)

    capacidade_restante = capacidade_total - (num_salas * cap_minima_sala)

    cortes = sorted([random.randint(0, capacidade_restante) for _ in range(num_salas - 1)])
    cortes = [0] + cortes + [capacidade_restante]

    capacidades = [cap_minima_sala + (cortes[i + 1] - cortes[i]) for i in range(num_salas)]
    random.shuffle(capacidades)
    return capacidades


def gerar_escolas(
    num_escolas: int,
    min_cap: int,
    max_cap: int,
    min_salas: int,
    max_salas: int,
    ceps_disponiveis: List[str]
) -> List[Dict[str, Any]]:
    """Gera a lista de escolas com suas características e salas."""
    escolas = []
    ceps_sorteados = random.choices(ceps_disponiveis, k=num_escolas)

    for id_escola in range(1, num_escolas + 1):
        cap_total = random.randint(min_cap, max_cap)
        num_salas = random.randint(min_salas, max_salas)
        capacidades_salas = gerar_capacidades_salas(cap_total, num_salas)

        escola = {
            "id": id_escola,
            "cep": ceps_sorteados[id_escola - 1],
            "capacidade_total": cap_total,
            "numero_salas": num_salas,
            "capacidade_salas": capacidades_salas
        }
        escolas.append(escola)

    return escolas


def gerar_candidatos(
    num_candidatos: int,
    pct_jf: float,
    ceps_jf: List[str],
    ceps_outras: List[str],
    tipos_prova: List[str]
) -> List[Dict[str, Any]]:
    """Gera a lista de candidatos com CEP e Tipo de Prova."""
    candidatos = []
    num_jf = int(round(num_candidatos * pct_jf))
    num_outras = num_candidatos - num_jf

    ceps_candidatos = random.choices(ceps_jf, k=num_jf) + random.choices(ceps_outras, k=num_outras)
    random.shuffle(ceps_candidatos)

    for id_cand in range(1, num_candidatos + 1):
        candidato = {
            "id": id_cand,
            "cep": ceps_candidatos[id_cand - 1],
            "tipo_prova": random.choice(tipos_prova)
        }
        candidatos.append(candidato)

    return candidatos


def gerar_instancia(
    min_escolas: int = MIN_ESCOLAS,
    max_escolas: int = MAX_ESCOLAS,
    min_cap: int = MIN_CAPACIDADE_ESCOLA,
    max_cap: int = MAX_CAPACIDADE_ESCOLA,
    min_salas: int = MIN_SALAS_POR_ESCOLA,
    max_salas: int = MAX_SALAS_POR_ESCOLA,
    min_pct_cand: float = MIN_PCT_CANDIDATOS,
    max_pct_cand: float = MAX_PCT_CANDIDATOS,
    pct_cand_jf: float = PCT_CANDIDATOS_JF,
    ceps_escolas: List[str] = CEPS_ESCOLAS_JF,
    ceps_outras_cidades: List[str] = CEPS_OUTRAS_CIDADES,
    tipos_prova: List[str] = TIPOS_PROVA,
    cache_file: str = CEP_CACHE_FILE
) -> Dict[str, Any]:
    """Cria uma instância completa contendo escolas, candidatos e a matriz de distâncias."""
    cache_cep = carregar_cache_cep(cache_file)

    num_escolas = random.randint(min_escolas, max_escolas)
    escolas = gerar_escolas(num_escolas, min_cap, max_cap, min_salas, max_salas, ceps_escolas)

    capacidade_total_sistema = sum(e["capacidade_total"] for e in escolas)

    pct_candidatos = random.uniform(min_pct_cand, max_pct_cand)
    num_candidatos = int(round(capacidade_total_sistema * pct_candidatos))

    candidatos = gerar_candidatos(num_candidatos, pct_cand_jf, ceps_escolas, ceps_outras_cidades, tipos_prova)

    # Calcular Matriz de Distâncias
    matriz_distancias = calcular_matriz_distancias(candidatos, escolas, cache_cep, cache_file)

    instancia = {
        "resumo": {
            "num_escolas": num_escolas,
            "capacidade_total_sistema": capacidade_total_sistema,
            "num_candidatos": num_candidatos,
            "taxa_ocupacao": round(pct_candidatos * 100, 2),
            "pct_candidatos_jf": round(pct_cand_jf * 100, 2)
        },
        "escolas": escolas,
        "candidatos": candidatos,
        "matriz_distancias": matriz_distancias
    }

    return instancia


# ==============================================================================
# EXPORTAÇÃO DE ARQUIVOS (.TXT e .JSON)
# ==============================================================================

def salvar_txt(instancia: Dict[str, Any], filepath: str) -> None:
    """
    Exporta a instância em formato TXT totalmente limpo (sem comentários #).

    Estrutura:
    <NUM_ESCOLAS>
    <ID_ESCOLA> <CEP> <CAPACIDADE_TOTAL> <NUM_SALAS> <CAP_S1> <CAP_S2> ... <CAP_Sn>
    ... (N linhas)
    <NUM_CANDIDATOS>
    <ID_CANDIDATO> <CEP> <TIPO_PROVA>
    ... (M linhas)
    <DISTANCIA_CAND_1_ESC_1> <DISTANCIA_CAND_1_ESC_2> ... <DISTANCIA_CAND_1_ESC_N>
    ... (M linhas de distâncias)
    """
    with open(filepath, "w", encoding="utf-8") as f:
        # 1. Número de escolas e linhas de escolas
        f.write(f"{len(instancia['escolas'])}\n")
        for e in instancia["escolas"]:
            salas_str = " ".join(map(str, e["capacidade_salas"]))
            f.write(f"{e['id']} {e['cep']} {e['capacidade_total']} {e['numero_salas']} {salas_str}\n")

        # 2. Número de candidatos e linhas de candidatos
        f.write(f"{len(instancia['candidatos'])}\n")
        for c in instancia["candidatos"]:
            f.write(f"{c['id']} {c['cep']} {c['tipo_prova']}\n")

        # 3. Matriz de distâncias (M linhas por N colunas)
        for linha_dist in instancia["matriz_distancias"]:
            f.write(" ".join(map(str, linha_dist)) + "\n")


def salvar_json(instancia: Dict[str, Any], filepath: str) -> None:
    """Exporta a instância em formato JSON legível."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(instancia, f, indent=4, ensure_ascii=False)


# ==============================================================================
# MAIN / CLI INTERFACE
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="Gerador de Instâncias para Alocação de Candidatos em Escolas")
    parser.add_argument("--qtd", type=int, default=1, help="Quantidade de instâncias a serem geradas")
    parser.add_argument("--outdir", type=str, default="instancias", help="Diretório onde salvar as instâncias")
    parser.add_argument("--prefixo", type=str, default="instancia", help="Prefixo dos arquivos gerados")
    parser.add_argument("--formato", type=str, choices=["txt", "json", "ambos"], default="txt", help="Formato de saída (txt, json ou ambos)")
    parser.add_argument("--seed", type=int, default=None, help="Semente do gerador aleatório para reprodutibilidade")
    parser.add_argument("--cache", type=str, default=CEP_CACHE_FILE, help="Arquivo de cache para geolocalização de CEPs")

    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    os.makedirs(args.outdir, exist_ok=True)

    print(f"Generating {args.qtd} instance(s) in folder '{args.outdir}' (Format: {args.formato})...")

    for i in range(1, args.qtd + 1):
        instancia = gerar_instancia(cache_file=args.cache)

        base_filename = f"{args.prefixo}_{i}"
        
        if args.formato in ["txt", "ambos"]:
            txt_path = os.path.join(args.outdir, f"{base_filename}.txt")
            salvar_txt(instancia, txt_path)
            print(f" -> Saved TXT: {txt_path}")

        if args.formato in ["json", "ambos"]:
            json_path = os.path.join(args.outdir, f"{base_filename}.json")
            salvar_json(instancia, json_path)
            print(f" -> Saved JSON: {json_path}")

    print("\nGeneration finished successfully!")


if __name__ == "__main__":
    main()
