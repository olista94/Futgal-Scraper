import unittest
from unittest.mock import patch

import requests
from bs4 import BeautifulSoup

from scraper.futgal_scraper import scrape_all, source_identity, scrape_jornada


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.config = {"cod_competicion": "1", "cod_grupo": "2",
                       "cod_temporada": "3", "cod_primaria": "4",
                       "nombre_competicion": "Liga", "nombre_grupo": "Grupo",
                       "jornadas": [1, 2]}
        self.match = {"equipo_local": "Local", "equipo_visitante": "Visitante",
                      "arbitro": "APELLIDOS, NOMBRE", "url": "partido-1"}
        self.history = {"source": source_identity(self.config),
                        "jornadas": {"1": [self.match]}}

    def scrape(self, **kwargs):
        return scrape_all(self.config, delay=0, existing_data=self.history, **kwargs)

    @patch("scraper.futgal_scraper.scrape_jornada", return_value=[])
    def test_empty_response_keeps_history_and_future_rounds(self, _):
        result = self.scrape()
        self.assertEqual(result["jornadas"], {"1": [self.match], "2": []})

    @patch("scraper.futgal_scraper.scrape_jornada", side_effect=requests.Timeout())
    def test_network_failure_keeps_history(self, _):
        self.assertEqual(self.scrape()["jornadas"]["1"], [self.match])

    def test_partial_response_keeps_missing_matches_and_updates_existing(self):
        missing = dict(self.match, url="partido-2")
        self.history["jornadas"]["1"].append(missing)
        updated = dict(self.match, arbitro="OTROS, NOMBRE")
        with patch("scraper.futgal_scraper.scrape_jornada", side_effect=[[updated], []]):
            result = self.scrape()["jornadas"]["1"]
        self.assertEqual(result, [updated, missing])
        self.assertEqual(self.history["jornadas"]["1"][0], self.match)

    @patch("scraper.futgal_scraper.scrape_jornada", return_value=[])
    def test_season_change_does_not_mix_history(self, _):
        self.history["source"]["cod_temporada"] = "previous"
        self.assertEqual(self.scrape()["jornadas"]["1"], [])

    @patch("scraper.futgal_scraper.scrape_jornada", return_value=[])
    def test_legacy_history_is_migrated(self, _):
        self.history.pop("source")
        self.history.update(competicion="Liga", grupo="Grupo")
        self.assertEqual(self.scrape()["jornadas"]["1"], [self.match])

    @patch("scraper.futgal_scraper.scrape_jornada", side_effect=ValueError("Plantilla desconocida"))
    def test_invalid_match_page_keeps_history(self, _):
        self.assertEqual(self.scrape()["jornadas"]["1"], [self.match])

    def test_missing_teams_are_not_saved_as_valid_match(self):
        pages = [BeautifulSoup('<a href="NFG_CmpPrevio?id=1">Partido</a>', "lxml"),
                 BeautifulSoup('<html>Servicio no disponible</html>', "lxml")]
        with self.assertRaises(ValueError):
            scrape_jornada(None, self.config, 1, 0, fetch=lambda *_: pages.pop(0))


if __name__ == "__main__":
    unittest.main()
