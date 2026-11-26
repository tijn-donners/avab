# Metadataschema-keuze en veldmapping AVAB → EBUCore v1.10

## Waarom EBUCore?

De AVAB-metadata moet drie doelen dienen: **doorzoekbaar archief**, **langdurig
bewaren met provenance** en **bewaren van fragment-timestamps**. Geëvalueerde
standaarden:

| Standaard | Beoordeeld | Oordeel |
|---|---|---|
| **EBUCore (EBU Tech 3295, v1.10)** | | **Gekozen.** De facto XML-standaard voor AV-erfgoed (EBU/Beeld en Geluid-veld). Rijk: tijdfragmenten (`part` met timecode), rechtenblok, techniek, provenance-attributen (`writingLibraryName`, `dateLastModified`) en een rechten/provenance-vocabulaire. |
| PBCore (WGBH) | Lichter archiefformaat | Geen eersteklas time-based segmentatie binnen één asset — fragmenten zouden losse documenten moeten worden. |
| METS (+MODS) | Preservatie-verpakking | Container zonder eigen woordenschat; te zwaar voor een sidecar, geschikt als latere delivery-laag. |
| MPEG-7 | ISO AV-descriptie | Verouderd, nauwelijks actieve tooling; EBUCore dekt zelfde gebied moderner. |
| Dublin Core (alleen) | Harvest | Te simpel (geen timing/provenance); kan later als OAI-PMH-laag juist *afgeleid* worden uit de sidecar. |
| XMP | Inbedding in bestanden | Geen fragmentstructuur. |
| EBU-TT/TTML | Timed text | Aanvullend (later): XML-transcripties behouden woordniveau-timestamps die SRT verliest. |

XSD's staan in `schemas/` (officieel `ebucore.xsd` v1.10 + lokaal
`xml.xsd` en `simpledc20021212.xsd` als imports). Validatie: `python export_xml.py <stem> --validate`.

## Outputlocatie en -structuur

`python export_xml.py` schrijft per video `output/<stem>/<stem>.ebucore.xml`:

- **Videoniveau**: `title` (bestandsnaam), `identifier` (werkenummer),
  `description[typeLabel="Provenance (AVAB, machinaal)"]` (modellen, datum,
  controle-versplichting), `format` (codec, resolutie, fps, duur, grootte via ffprobe),
- **Fragmentniveau**: één `<part partId="scene-N">` per scène met eigen
  titel/beschrijving/datering/locatie/subjects/rechten **en**
  `partStartTime`/`partEndTime` (normaal speeltijd) uit de scène-grenzen.
- root-attributen: `version="1.10"`, `documentId`, `xml:lang="nl"`,
  `writingLibraryName="avab/export_xml.py"`, `dateLastModified`.

## Veldmapping (`FilmFragment` in `output_schema.py` → EBUCore in `part`)

| AVAB/MAIS-veld | EBUCore-element | Toelichting |
|---|---|---|
| Titel | `part@partName` + `part/title/dc:title` | |
| Beschrijving | `description[typeLabel="Beschrijving"]/dc:description` | |
| Opmerkingen | `description[typeLabel="Opmerkingen"]` | alleen indien gevuld |
| Datering | `date[typeLabel="Datering"]/dc:date` | |
| Beginjaar/Eindjaar | `date[typeLabel="Datering (jaarperiode)"]/dc:date` | `1995–1995` |
| Starttijd | `partStartTime/normalPlayTime` (`00:00:11.520`, xs:time) | |
| Eindtijd | `partEndTime/normalPlayTime` | |
| Gemeente | `coverage/spatial/location/name[typeLabel="Gemeente"]` | EBUCore kent geen losse `location` onder `coreMetadata` |
| Plaats | `coverage/spatial/location/name[typeLabel="Plaats"]` | |
| Adres / Oud adres | `location/name[typeLabel="Adres"|"Oud adres"]` | idem, herhaald |
| Personen | `subject[typeLabel="Persoon"]/dc:subject` | gesplitst op komma |
| Trefwoorden | `subject[typeLabel="Trefwoord"]/dc:subject` | gesplitst op komma |
| Copyright | `rights/dc:rights` ("Copyright: Ja") | |
| Auteursrecht | `rights/dc:rights` ("Auteursrecht: Ja") + `rights/rightsClearanceFlag` (=true bij "Ja") | flag = rechtenhouder bekend |
| Opm. auteursrecht | `rights/copyrightStatement` | |
| AVG | `rights/dc:rights` ("AVG: Ja") | |
| Vrij downloaden | `rights/dc:rights` ("Vrij downloaden: Nee") | |
| Uitsl. van uitvoer | `rights/exploitationIssues` ("Uitsl. van uitvoer: ...") | |
| Automatische_Transcriptie | `description[typeLabel="Automatische transcriptie (machinaal, Whisper)"]` | provenance zit in het typeLabel |
| Automatische_Transcriptie_Segmenten | `textLine` per whisper-segment (Tech 3293 §3.27) | zie hieronder |

Videoprovenance staat op videoniveau onder `description[typeLabel="Provenance
(AVAB, machinaal)"]` (LLM-model `gemma4:31b`, Whisper, datum, controle-versplichting);
signature van de writer staat in root-attributen. De provider is
`metadataProvider/organisationDetails/organisationName = "AVAB pipeline (machinaal
gegenereerd)"`.

## Timed transcriptie (`ebucore:textLine`, Tech 3293 §3.27)

De tijdgebonden (segmentniveau) transcriptie van Whisper wordt op **twee niveaus**
uitgeleerd, conform Tech 3293 §3.27 ("TextLine is a new element that allows to
link text to parts/segments/scenes or a timestamp. Text can be referenced from
various sources such as subtitling, **speech to text**, text extraction, etc."):

- **Videoniveau**: één `textLine` per whisper-segment onder `coreMetadata`,
  met als timestamps de absolute segment-start.
- **Scèneniveau**: binnen elke `part` de segmenten die beginnen binnen het
  scène-interval (`partStartTime ≤ timestamp < partEndTime`). De timestamps zijn
  ook hier absoluut — een segment dat een scènegrens overschrijdt staat dus
  alleen in de scène waar het begint, maar wel op videoniveau.

Elke `textLine`-regel bevat (de elementen `textLink`, `text`, `relatedAgent` en
`timestamp` zijn verplicht in EBUCore 1.10):

| Element | Inhoud |
|---|---|
| `@textLineId` | `<stem>[-scene-N]-<volgnummer>` |
| `@order` | volgnummer binnen het (scène-)transcript |
| `@xml:lang` | `nl` |
| `@typeLabel` | `speech-to-text` (bron van de tekst) |
| `textLink` | relatieve URI naar `<stem>.srt` (sidecar met volledige start/end-timing) |
| `text` | de tekst van het segment |
| `relatedAgent/organisationDetails/organisationName` | `Whisper large-v3 (faster-whisper)` |
| `relatedAgent/role@typeLabel` | `speech-to-text` |
| `timestamp/normalPlayTime` | `HH:MM:SS.mmm` (xs:time, absoluut) |

**Beperking**: `textLineType` kent in 1.10 alleen een start-`timestamp`; een
eindtijd per regel is niet uitdrukbaar. De volledige start/end-timing staat in
het `textLink`-verwezen `.srt`-bestand (en in `transcript.json` in de
output-map).

**Brongegevens**: annotate_video.py schrijft per video `transcript.json`
(absolute seconden) en `<stem>.srt` en zet de velden `Automatische_Transcriptie`
en `Automatische_Transcriptie_Segmenten` in de scene-JSON's **code-side** op
basis van de whisper-mapping (de LLM vult geen transcriptie meer in).

## Niet in deze export (todo/latere uitbreiding)

- Woordniveau-timestamps van Whisper: nu weggegooid; behouden als EBU-TT/TTML-sidecar.
- Termlinking (`termennetwerk_zoekfunctie.py`): URI's kunnen later als
  `subject@subjectCode`-URI's (of `dc:identifier` bij subject) toegevoegd worden.
- Dublin Core/OAI-PMH-harvestlaag afleiden uit de sidecar.
