# AVAB: AudioVisueel Automatisch Beschrijven

Pipeline die archiefvideo's automatisch beschrijft: scènedetectie → frame-extractie →
Whisper-transcriptie → per-scène LLM-beschrijving (JSON) → **EBUCore XML-sidecar**.

## Gebruik

```bash
python annotate_video.py [video.mp4]        # beschrijf een video (output/<stem>/scene_N.json)
python export_xml.py                        # exporteer alle outputs naar EBUCore XML
python export_xml.py NL-BklVV_0752_0001 --validate   # één video, met XSD-validatie
```

De EBUCore-sidecars (`output/<stem>/<stem>.ebucore.xml`, v1.10) zijn zelfstandig
doorzoekbare metadata-bestanden per video: één `<part>` per filmfragment met
timecode-interval, beschrijving, transcriptie, trefwoorden, locatie, datering en
rechten. Veldmapping en standaardkeuze: [EBUCORE_MAPPING.md](EBUCORE_MAPPING.md).
XSD en afhankelijkheden staan in `schemas/` (validate met `--validate`;
lxml vereist: `pip install lxml`).
