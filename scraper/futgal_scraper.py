#!/usr/bin/env python3
"""
Scraper para futgal.es (sistema PNFG) — versión "web".

Lee `config.json` (competición, grupo, temporada, delegación y qué
jornadas scrapear) y genera un único JSON con, para cada jornada, la
lista de partidos con: equipo local, equipo visitante, árbitro, primer
asistente y segundo asistente.

Pensado para ejecutarse periódicamente desde GitHub Actions y volcar
el resultado en docs/data/partidos.json, que luego lee la web estática.

Uso manual:
    python3 scraper/futgal_scraper.py --config config.json --output docs/data/partidos.json
"""

import argparse
import datetime
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE = "https://www.futgal.es/pnfg/NPcd/NFG_CmpJornada"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}


def get_soup(session: requests.Session, url: str) -> BeautifulSoup:
    resp = session.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding
    return BeautifulSoup(resp.text, "lxml")


def build_jornada_url(config: dict, jornada: int) -> str:
    params = {
        "cod_primaria": config["cod_primaria"],
        "CodCompeticion": config["cod_competicion"],
        "CodGrupo": config["cod_grupo"],
        "CodTemporada": config["cod_temporada"],
        "cod_agrupacion": config.get("cod_agrupacion", ""),
        "CodJornada": jornada,
        "Sch_Codigo_Delegacion": config.get("cod_delegacion", ""),
        "Sch_Tipo_Juego": config.get("tipo_juego", ""),
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{BASE}?{query}"


def find_match_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    """Cualquier enlace cuyo href contenga NFG_CmpPrevio.

    No filtramos por clase CSS del botón (p.ej. "btn green-meadow btn-sm"
    o, tras el rediseño de la web en 2026, "btn btn-success btn-sm")
    porque futgal.es ya ha cambiado esa clase una vez. Los botones
    "Anterior/Siguiente" usan href="javascript:IrA(...)" y no contienen
    NFG_CmpPrevio, así que no hay riesgo de cogerlos por error.
    """
    links = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "NFG_CmpPrevio" in href:
            full = urljoin(base_url, href)
            if full not in seen:
                seen.add(full)
                links.append(full)
    return links


def extract_teams(soup: BeautifulSoup) -> tuple[str, str]:
    divs = soup.select('div.col-sm-4[style*="text-align:center"]')
    if len(divs) >= 3:
        local_h4 = divs[0].find("h4")
        visit_h4 = divs[2].find("h4")
        local = local_h4.get_text(strip=True) if local_h4 else ""
        visitante = visit_h4.get_text(strip=True) if visit_h4 else ""
        return local, visitante
    return "", ""


def extract_officials(soup: BeautifulSoup) -> dict:
    """Extrae árbitro/asistentes de la tabla 'ÁRBITROS'.

    Soporta dos formatos, porque futgal.es ya ha cambiado de plantilla
    una vez (2026) y puede volver a hacerlo:

    - Formato nuevo (desde el rediseño de 2026): sin etiquetas, 3 celdas
      con clase 'txtficha' en orden fijo (árbitro, asistente1,
      asistente2), cada nombre con prefijo 'D. '/'Dª. ' y sufijo tipo
      '(Comité )' que hay que limpiar.
    - Formato antiguo: filas <strong>Árbitro</strong> /
      <strong>Asistente</strong> seguidas de una fila con el nombre.
    """
    data = {"arbitro": "", "asistente1": "", "asistente2": ""}

    title_td = soup.find(
        "td", class_="title", string=lambda s: bool(s) and "RBITRO" in s.upper()
    )
    if not title_td:
        return data

    table = title_td.find_parent("table")
    if not table:
        return data

    # --- Formato nuevo: celdas con clase txtficha, en orden fijo ---
    txtficha_cells = table.find_all("td", class_="txtficha")
    if txtficha_cells:
        names = []
        for td in txtficha_cells:
            text = td.get_text(" ", strip=True)
            text = re.sub(r"^(D|Dª|Dna)\.\s*", "", text)  # quita "D. " / "Dª. "
            text = re.sub(r"\s*\([^)]*\)\s*$", "", text).strip()  # quita "(Comité )"
            if text:
                names.append(text)
        if len(names) >= 1:
            data["arbitro"] = names[0]
        if len(names) >= 2:
            data["asistente1"] = names[1]
        if len(names) >= 3:
            data["asistente2"] = names[2]
        return data

    # --- Formato antiguo: <strong>Árbitro</strong>/<strong>Asistente</strong> ---
    current_label = None
    assistant_count = 0

    for tr in table.find_all("tr"):
        strong = tr.find("strong")
        if strong:
            current_label = strong.get_text(strip=True)
            continue

        tds = tr.find_all("td")
        if not tds or current_label is None:
            continue

        value = tds[0].get_text(" ", strip=True)
        if not value:
            continue

        label_lower = current_label.lower()
        if "rbitro" in label_lower:
            data["arbitro"] = value
        elif "sistente" in label_lower:
            assistant_count += 1
            if assistant_count == 1:
                data["asistente1"] = value
            elif assistant_count == 2:
                data["asistente2"] = value

        current_label = None

    return data


def parse_match_page(soup: BeautifulSoup, url: str) -> dict:
    local, visitante = extract_teams(soup)
    officials = extract_officials(soup)
    return {
        "equipo_local": local,
        "equipo_visitante": visitante,
        "arbitro": officials["arbitro"],
        "asistente1": officials["asistente1"],
        "asistente2": officials["asistente2"],
        "url": url,
    }


def scrape_jornada(session: requests.Session, config: dict, jornada: int, delay: float, fetch=get_soup) -> list[dict]:
    """`fetch` es inyectable para poder testear sin red."""
    jornada_url = build_jornada_url(config, jornada)
    soup = fetch(session, jornada_url)
    match_links = find_match_links(soup, jornada_url)

    results = []
    for link in match_links:
        match_soup = fetch(session, link)
        results.append(parse_match_page(match_soup, link))
        time.sleep(delay)
    return results


def scrape_all(config: dict, delay: float = 1.0, fetch=get_soup) -> dict:
    session = requests.Session()
    jornadas_out = {}
    for jornada in config["jornadas"]:
        print(f"Jornada {jornada}...")
        try:
            jornadas_out[str(jornada)] = scrape_jornada(session, config, jornada, delay, fetch=fetch)
        except requests.RequestException as e:
            print(f"  ✗ Error en jornada {jornada}: {e}")
            jornadas_out[str(jornada)] = []
        time.sleep(delay)

    return {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "competicion": config.get("nombre_competicion", ""),
        "grupo": config.get("nombre_grupo", ""),
        "jornadas": jornadas_out,
    }


def main():
    parser = argparse.ArgumentParser(description="Scraper de futgal.es para la web")
    parser.add_argument("--config", default="config.json", help="Fichero de configuración")
    parser.add_argument("--output", default="docs/data/partidos.json", help="JSON de salida")
    parser.add_argument("--delay", type=float, default=1.0, help="Segundos entre peticiones")
    args = parser.parse_args()

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    data = scrape_all(config, delay=args.delay)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✔ Guardado en {out_path}")


if __name__ == "__main__":
    sys.exit(main())
