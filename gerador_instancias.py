#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador de Instâncias para Problema NP-Difícil de Alocação / Ensalamento (PISM)
-------------------------------------------------------------------------
Este script gera instâncias sintéticas personalizadas contendo informações de
escolas (capacidade total, salas e capacidades individuais), candidatos (CEP e tipo de prova)
e uma Matriz de Distâncias Euclidiana entre Candidatos e Escolas baseada em geolocalização por CEP.

Formatado estritamente de acordo com o modelo padronizado do projeto.
"""

import os
import math
import random
import json
import argparse
import time
import urllib.request
import urllib.parse
from typing import List, Dict, Any, Tuple

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

# CEPs de logradouros reais de outras cidades da região/estado para candidatos de fora de JF
CEPS_OUTRAS_CIDADES: List[str] = [
    "36200010",  # Barbacena - MG (Centro)
    "36500010",  # Ubá - MG (Centro)
    "36150000",  # Santos Dumont - MG
    "36120000",  # Matias Barbosa - MG
    "36140000",  # Lima Duarte - MG
    "36880002",  # Muriaé - MG (Centro)
    "36300004",  # São João del-Rei - MG (Centro)
    "36600000",  # Bicas - MG
    "20040002",  # Rio de Janeiro - RJ (Centro)
    "25620000",  # Petrópolis - RJ (Centro)
    "30110000"   # Belo Horizonte - MG (Centro)
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


def consultar_api_nominatim(query_str: str) -> Tuple[float, float]:
    """Consulta o geocodificador Nominatim (OpenStreetMap) por endereço/cidade."""
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(query_str)}&format=json"
        req = urllib.request.Request(url, headers={"User-Agent": "Antigravity-PISM-Geocoder/1.0"})
        time.sleep(0.5)  # Respeita o rate limit do Nominatim
        with urllib.request.urlopen(req, timeout=4) as response:
            res = json.loads(response.read().decode("utf-8"))
            if res:
                return float(res[0]["lat"]), float(res[0]["lon"])
    except Exception:
        pass
    return None, None


def obter_geolocalizacao_cep(cep: str, cache: Dict[str, Dict[str, float]], cache_file: str = CEP_CACHE_FILE) -> Dict[str, float]:
    """
    Obtém Latitude e Longitude para um CEP utilizando um pipeline híbrido:
    1. Cache Local (se já consultado)
    2. BrasilAPI v2 (retorna coordenadas exatas de CEPs urbanos)
    3. ViaCEP + OpenStreetMap/Nominatim (para obter coordenadas por rua/bairro/cidade)
    """
    cep_clean = str(cep).replace("-", "").strip()

    if cep_clean in cache:
        return cache[cep_clean]

    lat, lon = None, None

    # 1. Tentar BrasilAPI v2
    try:
        url = f"https://brasilapi.com.br/api/cep/v2/{cep_clean}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=4) as response:
            data = json.loads(response.read().decode("utf-8"))
            coords = data.get("location", {}).get("coordinates", {})
            if coords.get("latitude") and coords.get("longitude"):
                l_lat = float(coords["latitude"])
                l_lon = float(coords["longitude"])
                if not (abs(l_lat - (-21.76417)) < 0.0001 and abs(l_lon - (-43.35028)) < 0.0001):
                    lat, lon = l_lat, l_lon
    except Exception:
        pass

    # 2. Tentar ViaCEP + Nominatim (Rua/Bairro/Cidade) se a BrasilAPI não retornou coordenadas específicas
    if lat is None or lon is None:
        try:
            url_via = f"https://viacep.com.br/ws/{cep_clean}/json/"
            req_via = urllib.request.Request(url_via, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req_via, timeout=4) as response_via:
                d_via = json.loads(response_via.read().decode("utf-8"))
                street = d_via.get("logradouro", "")
                bairro = d_via.get("bairro", "")
                city = d_via.get("localidade", "")
                uf = d_via.get("uf", "")

                q = f"{street}, {bairro}, {city} - {uf}, Brasil" if street else f"{city} - {uf}, Brasil"
                lat, lon = consultar_api_nominatim(q)
        except Exception:
            pass

    # 3. Fallback genérico se nada retornar
    if lat is None or lon is None:
        lat, lon = -21.76417, -43.35028

    resultado = {"latitude": round(lat, 6), "longitude": round(lon, 6)}
    cache[cep_clean] = resultado
    salvar_cache_cep(cache, cache_file)
    return resultado


def calcular_distancia_euclidiana(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcula a distância euclidiana 2D em graus entre duas coordenadas (lat1, lon1) e (lat2, lon2)."""
    return math.sqrt((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2)


def calcular_matriz_distancias(
    candidatos: List[Dict[str, Any]],
    escolas: List[Dict[str, Any]]
) -> List[List[float]]:
    """
    Gera a Matriz de Distâncias Euclidiana em graus (Candidatos x Escolas).
    Cada linha i contém as distâncias do candidato i para todas as N escolas.
    """
    matriz = []
    for cand in candidatos:
        linha = []
        for esc in escolas:
            dist = calcular_distancia_euclidiana(
                cand["latitude"], cand["longitude"],
                esc["latitude"], esc["longitude"]
            )
            linha.append(round(dist, 6))
        matriz.append(linha)

    return matriz

# ==============================================================================
# FUNÇÕES GERADORAS
# ==============================================================================

def gerar_capacidades_salas(capacidade_total: int, num_salas: int, cap_minima_sala: int = 10) -> List[int]:
    """Divide a capacidade total da escola entre as salas de forma estocástica e justa."""
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
    ceps_disponiveis: List[str],
    cache: Dict[str, Dict[str, float]],
    cache_file: str = CEP_CACHE_FILE
) -> List[Dict[str, Any]]:
    """Gera a lista de escolas com características, coordenadas e salas."""
    escolas = []
    ceps_sorteados = random.choices(ceps_disponiveis, k=num_escolas)

    for id_escola in range(1, num_escolas + 1):
        cap_total = random.randint(min_cap, max_cap)
        num_salas = random.randint(min_salas, max_salas)
        capacidades_salas = gerar_capacidades_salas(cap_total, num_salas)
        cep = ceps_sorteados[id_escola - 1]
        coord = obter_geolocalizacao_cep(cep, cache, cache_file)

        escola = {
            "id": f"E{id_escola}",
            "cep": cep,
            "latitude": coord["latitude"],
            "longitude": coord["longitude"],
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
    tipos_prova: List[str],
    cache: Dict[str, Dict[str, float]],
    cache_file: str = CEP_CACHE_FILE
) -> List[Dict[str, Any]]:
    """Gera a lista de candidatos com CEP, Tipo de Prova e Coordenadas."""
    candidatos = []
    num_jf = int(round(num_candidatos * pct_jf))
    num_outras = num_candidatos - num_jf

    ceps_candidatos = random.choices(ceps_jf, k=num_jf) + random.choices(ceps_outras, k=num_outras)
    random.shuffle(ceps_candidatos)

    for id_cand in range(1, num_candidatos + 1):
        cep = ceps_candidatos[id_cand - 1]
        coord = obter_geolocalizacao_cep(cep, cache, cache_file)
        candidato = {
            "id": f"C{id_cand}",
            "cep": cep,
            "tipo_prova": random.choice(tipos_prova),
            "latitude": coord["latitude"],
            "longitude": coord["longitude"]
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
    """Cria uma instância completa contendo candidatos, escolas e a matriz de distâncias."""
    cache_cep = carregar_cache_cep(cache_file)

    num_escolas = random.randint(min_escolas, max_escolas)
    escolas = gerar_escolas(num_escolas, min_cap, max_cap, min_salas, max_salas, ceps_escolas, cache_cep, cache_file)

    capacidade_total_sistema = sum(e["capacidade_total"] for e in escolas)

    pct_candidatos = random.uniform(min_pct_cand, max_pct_cand)
    num_candidatos = int(round(capacidade_total_sistema * pct_candidatos))

    candidatos = gerar_candidatos(num_candidatos, pct_cand_jf, ceps_escolas, ceps_outras_cidades, tipos_prova, cache_cep, cache_file)

    # Calcular Matriz de Distâncias em graus
    matriz_distancias = calcular_matriz_distancias(candidatos, escolas)

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
    Exporta a instância seguindo estritamente a padronização oficial fornecida.

    Modelo:
    NUM_CANDIDATOS: M
    NUM_ESCOLAS: N

    # CANDIDATOS (id, CEP, tipo_prova, latitude, longitude)
    C1, 36037941, M3h, -21.779531, -43.376217
    ...

    # ESCOLAS (id, CEP, latitude, longitude, num_salas, capacidades_salas)
    E1, 36100538, -21.756893, -43.289668, 2, 8;8
    ...

    # MATRIZ_DISTANCIAS (linhas=candidatos, colunas=escolas, em graus)
    dist1, dist2, ..., distN
    ...
    """
    with open(filepath, "w", encoding="utf-8") as f:
        candidatos = instancia["candidatos"]
        escolas = instancia["escolas"]
        matriz = instancia["matriz_distancias"]

        # Cabeçalho de totais
        f.write(f"NUM_CANDIDATOS: {len(candidatos)}\n")
        f.write(f"NUM_ESCOLAS: {len(escolas)}\n\n")

        # Seção 1: CANDIDATOS
        f.write("# CANDIDATOS (id, CEP, tipo_prova, latitude, longitude)\n")
        for c in candidatos:
            f.write(f"{c['id']}, {c['cep']}, {c['tipo_prova']}, {c['latitude']:.6f}, {c['longitude']:.6f}\n")
        f.write("\n")

        # Seção 2: ESCOLAS
        f.write("# ESCOLAS (id, CEP, latitude, longitude, num_salas, capacidades_salas)\n")
        for e in escolas:
            salas_str = ";".join(map(str, e["capacidade_salas"]))
            f.write(f"{e['id']}, {e['cep']}, {e['latitude']:.6f}, {e['longitude']:.6f}, {e['numero_salas']}, {salas_str}\n")
        f.write("\n")

        # Seção 3: MATRIZ DE DISTÂNCIAS (em graus)
        f.write("# MATRIZ_DISTANCIAS (linhas=candidatos, colunas=escolas, em graus)\n")
        for linha_dist in matriz:
            linha_str = ", ".join(f"{d:.6f}" for d in linha_dist)
            f.write(f"{linha_str}\n")


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
