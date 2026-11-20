""" Dit bestand bestaat als specifiek schema voor de AET filmfragment"""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, ValidationError

# these are the possible vlaues the Mais-flexis field 'gemeenten' allows
GEMEENTEN = [
    "De Bilt",
    "De Ronde Venen",
    "Stichtse Vecht",
    "De Bilt, De Ronde Venen",
    "De Bilt, De Ronde Venen, Stichtse Vecht",
    "De Bilt, Stichtse Vecht",
    "De Bilt, Stichtse Vecht, De Ronde Venen",
    "De Ronde Venen, Stichtse Vecht",
    "Overig",
    ]

# these are the possible vlaues the Mais-flexis field 'Plaatsnamen' allows
PLAATSEN = [
    "Abcoude", "Abcoude-Baambrugge", "Abcoude-Bossets", "Abcoude-Proostdij",
    "Abcoude-Proostdij en Aasdom", "Abcoude-Sint Pieters", "Achttienhoven",
    "Amstelhoek", "Baambrugge", "Baambrugge Bercks gerecht", "Bilthoven",
    "Blauwkapel", "Botshol", "Breukelen", "Breukelen-Nijenrode",
    "Breukelen-Orttsgerecht", "Breukelen-Statengerecht", "Breukelen-St. Pieters",
    "Breukelerwaard", "Breukeleveen", "Colenberg-De Bilt", "De Bilt",
    "De Bilt en Bilthoven", "De Geer", "De Hoef", "De Lage Haar",
    "De Ronde Venen", "Demmerik", "Gerverskop", "Gerverskop-Staten",
    "Gerverskop-Utenhams", "Gieltjesdorp", "Groenekan", "Heycops",
    "Hollandsche Rading", "Kockengen", "Kockengen-Lockhorst",
    "Kockengen en Spengen", "Kortrijk", "Laag Nieuwkoop", "Lettes",
    "Loefsgerecht van Ruwiel", "Loenen", "Loenen, Loenersloot en Slootdijk",
    "Loenen-Kronenburg", "Loenen-Nieuwersluis", "Loenersloot",
    "Loenersloot, Oukoop en Ter Aa", "Maarssen", "Maarssenbroek",
    "Maarsseveen", "Maartensdijk", "Maas", "Mijdrecht", "Mijdrecht en Wilnis",
    "Mijdrecht, Oudhuizen en Wilnis", "Mijnden", "Neerdijk",
    "Nieuw Maarsseveen", "Nieuwersluis", "Nieuwer Ter Aa", "Nigtevecht",
    "Oostbroek en De Bilt", "Oostveen", "Oud Maarsseveen", "Oud Zuilen",
    "Oudhuizen", "Over de Vecht-De Bilt", "Oukoop", "Piecks", "Portengen",
    "Portengen-Noordeinde", "Portengen-Zuideinde", "Ruige Wilnis", "Ruwiel",
    "Spengen", "Stichtse Vecht", "Ter Aa", "Tienhoven", "Utrecht (provincie)",
    "Vecht en Venen (werkgebied)", "Vijfhoeven in Kortrijk", "Vinkeveen",
    "Vinkeveen en Demmerik", "Vinkeveen en Waverveen", "Vreeland", "Waveren",
    "Waveren, Botshol en Ruige Wilnis", "Waverveen", "Waverveen en Waveren",
    "Weesp", "Weesperkarspel", "Westbroek", "Westveen", "Wilnis",
    "Wilnis en Westveen", "Zuilen", "Overig",
    ]

JaNee = Literal["Ja", "Nee"]
Gemeente = Literal[tuple(GEMEENTEN)] 
Plaats = Literal[tuple(PLAATSEN)]    


class FilmFragment(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    Titel: str = ""
    Beschrijving: str = ""
    Datering: str = ""
    Beginjaar: str = ""
    Eindjaar: str = ""
    Opmerkingen: str = ""
    Starttijd: str = ""
    Eindtijd: str = ""
    Gemeente: Gemeente
    Plaats: Plaats
    Adres: list[str] = []
    Oud_adres: list[str] = Field(default=[], alias="Oud adres")
    Copyright: str = ""
    Auteursrecht: JaNee
    Opm_auteursrecht: str = Field(default="", alias="Opm. auteursrecht")
    AVG: JaNee
    Vrij_downloaden: JaNee = Field(alias="Vrij downloaden")
    Uitsl_van_uitvoer: str = Field(default="", alias="Uitsl. van uitvoer")
    Automatische_Transcriptie : str
    Personen : str
    Trefwoorden : str

class Records(BaseModel):
    items: list[FilmFragment]