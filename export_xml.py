""" Dit script is gemaakt door deepseek-v4.1-flash in Claude Code.

Exporteer AVAB scene-JSON naar EBUCore XML sidecar.

Leest de per-scene JSON-bestanden van één video (output/<stem>/scene_*.json,
schema: output_schema.Records) en schrijft één EBUCore v1.10 XML-sidecar
(output/<stem>/<stem>.ebucore.xml):

- één record per video (titel, identifier, technische metadata, provenance)
- één <part> per scène/fragment met timecode-interval (Starttijd/Eindtijd),
  beschrijving, trefwoorden, personen, locatie, datering en rechten
- de tijdgebonden transcriptie (Tech 3293 §3.27) als <ebucore:textLine>-elementen:
  één keer op videoniveau (coreMetadata, alle whisper-segmenten) en één keer per
  scène (de segmenten die binnen het scène-interval beginnen). De timestamps zijn
  steeds absoluut t.o.v. het begin van het bestand. Bron is transcript.json
  (geschreven door annotate_video.py); als dat ontbreekt, worden de segmenten
  uit de scene-JSON's samengevoegd. Elk textLine verwijst via textLink naar het
  sidecar-bestand <stem>.srt.

Gebruik:
    python export_xml.py                     # exporteert alle subdirs van output/
    python export_xml.py NL-BklVV_0752_0001  # exporteert één specifieke video
    python export_xml.py --validate          # valideert na het schrijven tegen schemas/ebucore.xsd
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from lxml import etree

from output_schema import Records

OUTPUT_DIR = Path(__file__).parent / "output"
DATA_DIR = Path(__file__).parent / "data"
SCHEMA_PATH = Path(__file__).parent / "schemas" / "ebucore.xsd"

NS_EBU = "urn:ebu:metadata-schema:ebucore"
NS_DC = "http://purl.org/dc/elements/1.1/"
NS_XML = "http://www.w3.org/XML/1998/namespace"

LLM_MODEL = "gemma4:31b"
ASR_MODEL = "Whisper large-v3 (faster-whisper)"

EBU = f"{{{NS_EBU}}}"
DC = f"{{{NS_DC}}}"


def _el(parent, tag, text=None, type_label=None, **attrs):
    """Subelement helper; text en typeLabel worden netjes weggeschreven."""
    el = etree.SubElement(parent, tag)
    if text:
        el.text = text
    if type_label:
        el.set("typeLabel", type_label)
    for k, v in attrs.items():
        if v is not None:
            el.set(k, str(v))
    return el


def _dc(parent, tag, text):
    """Zet een Dublin Core-kind-element (bijv. dc:title) met tekst."""
    el = etree.SubElement(parent, DC + tag)
    el.text = text
    return el


def _split_veld(waarde: str):
    """Splits door-komma's gescheiden velden ('Trefwoorden', 'Personen')."""
    return [p.strip() for p in waarde.split(",") if p.strip()]


def _to_seconds(t: str) -> float:
    """'00:00:11.520' of '11.52' -> seconden."""
    if ":" in t:
        h, m, s = t.split(":")
        return int(h) * 3600 + int(m) * 60 + float(s)
    return float(t)


def _fmt_time(seconds: float) -> str:
    """seconden -> 'HH:MM:SS.mmm' (gebruikt als ebucore:normalPlayTime-tijdstip)."""
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


# ---------------------------------------------------------------- technische metadata

def ffprobe_metadata(video_path: Path) -> dict:
    """Technische metadata van de video via ffprobe (duur, resolutie, codecs)."""
    if not video_path.exists():
        return {}
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", str(video_path),
    ]
    try:
        data = json.loads(subprocess.run(cmd, check=True, capture_output=True).stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        print(f"  ⚠ ffprobe mislukt voor {video_path.name}: {e}", file=sys.stderr)
        return {}

    out = {"duration": data.get("format", {}).get("duration"),
           "fileSize": data.get("format", {}).get("size"),
           "fileName": video_path.name}
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video" and "video" not in out:
            fps_num, _, fps_den = (stream.get("avg_frame_rate") or "0/0").partition("/")
            fps = None
            try:
                fps = round(float(fps_num) / float(fps_den), 2) if fps_den else None
            except (ZeroDivisionError, ValueError):
                pass
            out["video"] = {"codec": stream.get("codec_name"), "width": stream.get("width"),
                            "height": stream.get("height"), "frameRate": fps}
        elif stream.get("codec_type") == "audio" and "audio" not in out:
            out["audio"] = {"codec": stream.get("codec_name")}
    return out


def _xsd_duration(seconds: str | None) -> str | None:
    """'101.72' -> 'PT1M41.72S' (xs:duration)."""
    if not seconds:
        return None
    total = float(seconds)
    hours, rem = divmod(int(total), 3600)
    minutes, secs = divmod(rem, 60)
    frac = total - int(total)
    part = ""
    if frac:
        part = f"{secs + frac:.2f}S"
    elif secs:
        part = f"{secs}S"
    out = "PT"
    if hours:
        out += f"{hours}H"
    if minutes:
        out += f"{minutes}M"
    if part:
        out += part
    return out if out != "PT" else "PT0S"


# ---------------------------------------------------------------- XML-bouw

def _add_video_metadata(core, stem: str, tech: dict):
    """Vul het videoniveau: identificatie, titel, techniek, provenance."""
    _el(_el(core, EBU + "title", type_label="Bestandsnaam"), DC + "title", stem)
    _el(_el(core, EBU + "identifier", type_label="Werkenummer (toegang/inventarisnummer)"),
        DC + "identifier", stem)

    # Provenance: automatisch gegenereerd, model, datum, waarschuwing
    nu = datetime.now().astimezone().isoformat(timespec="seconds")
    provenance = (
        f"Beschrijvingen en transcripties automatisch gegenereerd door de AVAB-pipeline "
        f"(AudioVisueel Automatisch Beschrijven) op {nu}. "
        f"Beeldbeschrijving: LLM {LLM_MODEL} (ollama), gebaseerd op scene-frames en "
        f"automatische transcriptie. Spraakherkenning: {ASR_MODEL}. "
        f"Terminologie: Netwerk of Terms / Termennetwerk (Netwerk Digitaal Erfgoed). "
        f"Deze metadata is machinaal gegenereerd en vereist menselijke controle voor "
        f"definitieve registratie in de catalogus."
    )
    _el(_el(core, EBU + "description", type_label="Provenance (AVAB, machinaal)"),
        DC + "description", provenance)

    if tech:
        fmt = etree.SubElement(core, EBU + "format")
        vid = tech.get("video")
        if vid:
            vf = etree.SubElement(fmt, EBU + "videoFormat")
            if vid.get("codec"):
                vf.set("videoFormatName", vid["codec"])
            for key in ("width", "height"):
                if vid.get(key):
                    _el(vf, EBU + key, str(vid[key]))
            if vid.get("frameRate"):
                _el(vf, EBU + "frameRate", str(int(vid["frameRate"])))
        aud = tech.get("audio")
        if aud:
            af = etree.SubElement(fmt, EBU + "audioFormat")
            if aud.get("codec"):
                af.set("audioFormatName", aud["codec"])
        cont = _el(fmt, EBU + "containerFormat")
        if tech["fileName"]:
            cont.set("containerFormatName", Path(tech["fileName"]).suffix.lstrip(".") or "mp4")
        if tech.get("duration"):
            start = etree.SubElement(fmt, EBU + "start")
            _el(start, EBU + "normalPlayTime", "00:00:00.000")
            dur = etree.SubElement(fmt, EBU + "duration")
            _el(dur, EBU + "normalPlayTime", _xsd_duration(tech["duration"]))
        if tech.get("fileName"):
            _el(fmt, EBU + "fileName", tech["fileName"])
        if tech.get("fileSize"):
            _el(fmt, EBU + "fileSize", str(tech["fileSize"]))
        _el(fmt, EBU + "locator", f"data/{tech['fileName']}")


def _add_textlines(parent, segments: list[dict], srt_name: str, id_prefix: str):
    """Voeg <ebucore:textLine>-elementen toe (Tech 3293 §3.27: 'TextLine is a new
    element that allows to link text to parts/segments/scenes or a timestamp;
    Text can be referenced from various sources such as ... speech to text ...').

    Per segment: textLink naar het .srt-sidecar, de tekst zelf, de ASR-bron
    (relatedAgent) en het absolute starttijdstip (timestamp). Eindtijd is in
    EBUCore 1.10 niet uitdrukbaar per regel (alleen een start-timestamp); de
    volledige start/end-timing staat in het .srt-sidecar.
    """
    for i, seg in enumerate(segments, start=1):
        tl = etree.SubElement(parent, EBU + "textLine")
        tl.set("textLineId", f"{id_prefix}-{i:04d}")
        tl.set("order", str(i))
        tl.set(f"{{{NS_XML}}}lang", "nl")
        tl.set("typeLabel", "speech-to-text")
        _el(tl, EBU + "textLink", srt_name)
        _el(tl, EBU + "text", seg["text"])
        ra = etree.SubElement(tl, EBU + "relatedAgent")
        org = etree.SubElement(ra, EBU + "organisationDetails")
        _el(org, EBU + "organisationName", ASR_MODEL)
        etree.SubElement(ra, EBU + "role", typeLabel="speech-to-text")
        ts = etree.SubElement(tl, EBU + "timestamp")
        _el(ts, EBU + "normalPlayTime", _fmt_time(seg["start"]))


def load_transcript(dir_path: Path) -> list[dict]:
    """Laad de tijdgebonden transcriptie ({start, end, text} in absolute seconden).

    Bron: transcript.json (door annotate_video.py). Fallback: de per-scene
    segmenten (Automatische_Transcriptie_Segmenten, in HH:MM:SS.mmm) uit de
    scene-JSON's, ontdubbeld op starttijdstip (een segment dat een scènegrens
    overschrijdt staat dan mogelijk in meerdere scene-JSON's).
    """
    tpath = dir_path / "transcript.json"
    if tpath.exists():
        return [{"start": float(s["start"]), "end": float(s["end"]),
                 "text": s["text"].strip()}
                for s in json.loads(tpath.read_text(encoding="utf-8"))]

    out: list[dict] = []
    seen: set[float] = set()
    for path in sorted(dir_path.glob("scene_*.json"), key=_scene_num):
        for record in json.loads(path.read_text(encoding="utf-8")).get("items", []):
            for seg in record.get("Automatische_Transcriptie_Segmenten", []):
                t = round(_to_seconds(seg["Starttijd"]), 3)
                if t in seen:
                    continue
                seen.add(t)
                out.append({"start": _to_seconds(seg["Starttijd"]),
                            "end": _to_seconds(seg["Eindtijd"]),
                            "text": seg["Tekst"]})
    return sorted(out, key=lambda s: s["start"])


def _scene_num(p: Path) -> int:
    n = p.stem.split("_")[1]
    return int(n) if n.isdigit() else 0


def _add_rights(part, frag) -> None:
    """Rechtenblok: Auteursrecht, AVG, Vrij downloaden, Copyright, opmerkingen."""
    rights = etree.SubElement(part, EBU + "rights")
    for label, waarde in (
        ("Auteursrecht", frag.Auteursrecht),
        ("AVG", frag.AVG),
        ("Vrij downloaden", frag.Vrij_downloaden),
        ("Copyright", frag.Copyright),
    ):
        if waarde:
            _dc(rights, "rights", f"{label}: {waarde}")
    if frag.Uitsl_van_uitvoer:
        _el(rights, EBU + "exploitationIssues",
            f"Uitsl. van uitvoer: {frag.Uitsl_van_uitvoer}")
    if frag.Opm_auteursrecht:
        _el(rights, EBU + "copyrightStatement", frag.Opm_auteursrecht)
    if frag.Auteursrecht == "Ja":
        _el(rights, EBU + "rightsClearanceFlag", "true")


def _add_part(core, nr: int, frag, total: int, transcript: list[dict], srt_name: str):
    """Eén scène/fragment als <part> met eigen coreMetadata-inhoud."""
    titel = frag.Titel or f"Fragment {nr}"
    part = _el(core, EBU + "part", partId=f"scene-{nr}", partName=titel,
               partNumber=nr, partTotalNumber=total, partDefinition="Filmfragment (scene-detectie)")

    # volgorde volgens schema: eerst de inhoud (coreMetadata), daarna de times
    _el(_el(part, EBU + "title"), DC + "title", titel)
    if frag.Beschrijving:
        _el(_el(part, EBU + "description", type_label="Beschrijving"),
            DC + "description", frag.Beschrijving)
    if frag.Opmerkingen:
        _el(_el(part, EBU + "description", type_label="Opmerkingen"),
            DC + "description", frag.Opmerkingen)
    if frag.Automatische_Transcriptie:
        _el(_el(part, EBU + "description",
                type_label="Automatische transcriptie (machinaal, Whisper)"),
            DC + "description", frag.Automatische_Transcriptie)

    # datering
    if frag.Datering:
        _el(_el(part, EBU + "date", type_label="Datering"), DC + "date", frag.Datering)
    if frag.Beginjaar or frag.Eindjaar:
        periode = f"{frag.Beginjaar}–{frag.Eindjaar}" if frag.Beginjaar and frag.Eindjaar \
            else (frag.Beginjaar or "") + (frag.Eindjaar or "")
        _el(_el(part, EBU + "date", type_label="Datering (jaarperiode)"),
            DC + "date", periode)

    # geografische ontsluiting (EBUCore: coverage/spatial/location/name)
    cov = etree.SubElement(part, EBU + "coverage")
    spatial = etree.SubElement(cov, EBU + "spatial")
    location = etree.SubElement(spatial, EBU + "location")
    if frag.Gemeente:
        _el(location, EBU + "name", frag.Gemeente, type_label="Gemeente")
    if frag.Plaats:
        _el(location, EBU + "name", frag.Plaats, type_label="Plaats")
    for adres in frag.Adres:
        _el(location, EBU + "name", adres, type_label="Adres")
    for adres in frag.Oud_adres:
        _el(location, EBU + "name", adres, type_label="Oud adres")

    # personen en trefwoorden als subjects
    for persoon in _split_veld(frag.Personen):
        _el(_el(part, EBU + "subject", type_label="Persoon"), DC + "subject", persoon)
    for trefwoord in _split_veld(frag.Trefwoorden):
        _el(_el(part, EBU + "subject", type_label="Trefwoord"), DC + "subject", trefwoord)

    _add_rights(part, frag)

    # tijdgebonden transcriptieregels die binnen dit fragment beginnen:
    # per schema vóór partStartTime (partType is een extensie van
    # coreMetadataType: de timecode-blokken moeten als laatste)
    t0, t1 = _to_seconds(frag.Starttijd), _to_seconds(frag.Eindtijd)
    in_part = [s for s in transcript if t0 <= s["start"] < t1]
    if in_part:
        _add_textlines(part, in_part, srt_name,
                       id_prefix=f"{Path(srt_name).stem}-scene-{nr}")

    # tijdinterval van het fragment (volgens schema ná de inhoudselementen)
    start = etree.SubElement(part, EBU + "partStartTime")
    _el(start, EBU + "normalPlayTime", frag.Starttijd)
    end = etree.SubElement(part, EBU + "partEndTime")
    _el(end, EBU + "normalPlayTime", frag.Eindtijd)


def build_ebucore(stem: str, fragments: list, tech: dict,
                  transcript: list[dict]) -> etree._Element:
    """Bouw de volledige EBUCore-boom voor één video."""
    root = etree.Element(EBU + "ebuCoreMain", nsmap={"ebucore": NS_EBU, "dc": NS_DC})
    root.set("schema", "ebucore.xsd")
    root.set("version", "1.10")
    root.set("dateLastModified", datetime.now().strftime("%Y-%m-%d"))
    root.set("documentId", stem)
    root.set("writingLibraryName", "avab/export_xml.py")
    root.set("writingLibraryVersion", "0.1")
    root.set(f"{{{NS_XML}}}lang", "nl")

    core = etree.SubElement(root, EBU + "coreMetadata")
    _add_video_metadata(core, stem, tech)

    # tijdgebonden transcriptie van de hele video op resourceniveau
    # (Tech 3293 §3.27); timestamps absoluut t.o.v. bestandsbegin
    srt_name = f"{stem}.srt"
    if transcript:
        _add_textlines(core, transcript, srt_name, id_prefix=stem)

    for nr, frag in enumerate(fragments, start=1):
        _add_part(core, nr, frag, len(fragments), transcript, srt_name)

    provider = etree.SubElement(root, EBU + "metadataProvider")
    org = etree.SubElement(provider, EBU + "organisationDetails")
    _el(org, EBU + "organisationName", "AVAB pipeline (machinaal gegenereerd)")
    return root


# ---------------------------------------------------------------- in-/uitvoer

def load_fragments(dir_path: Path) -> list:
    """Lees alle scene_*.json in en geef terug als list[FilmFragment]."""
    fragments = []
    for path in sorted(dir_path.glob("scene_*.json"),
                       key=lambda p: int(p.stem.split("_")[1]) if p.stem.split("_")[1].isdigit() else 0):
        data = json.loads(path.read_text(encoding="utf-8"))
        records = Records.model_validate(data)
        fragments.extend(records.items)
    return fragments


def export_video(dir_path: Path, validate: bool = False) -> Path:
    """Exporteer één video-map naar een EBUCore sidecar."""
    stem = dir_path.name
    fragments = load_fragments(dir_path)
    if not fragments:
        raise SystemExit(f"Geen scene_*.json gevonden in {dir_path}")

    num = len(list(dir_path.glob("scene_*.json")))
    tech = ffprobe_metadata(DATA_DIR / f"{stem}.mp4")
    transcript = load_transcript(dir_path)
    print(f"{stem}: {len(fragments)} fragmenten uit {num} bestanden"
          + (f", techniek: {tech.get('duration')}s" if tech else ", geen technische metadata")
          + f", {len(transcript)} transcriptiesegmenten")

    root = build_ebucore(stem, fragments, tech, transcript)
    xml_bytes = etree.tostring(root, pretty_print=True, xml_declaration=True,
                               encoding="UTF-8")
    out_path = dir_path / f"{stem}.ebucore.xml"
    out_path.write_bytes(xml_bytes)
    print(f"  ✓ geschreven: {out_path.relative_to(Path(__file__).parent)}")

    if validate:
        validate_xml(out_path)
    return out_path


def validate_xml(xml_path: Path):
    """Valideer het sidecar-bestand tegen de officiële EBUCore XSD."""
    schema_doc = etree.parse(str(SCHEMA_PATH))
    schema = etree.XMLSchema(schema_doc)
    doc = etree.parse(str(xml_path))
    if schema.validate(doc):
        print(f"  ✓ {xml_path.name} valideert tegen EBUCore v1.10 XSD")
    else:
        print(f"  ✗ {xml_path.name} VALIDEERT NIET:", file=sys.stderr)
        for error in schema.error_log:
            print(f"    - {error}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stems", nargs="*", help="video-stem of output-submap; leeg = alles")
    parser.add_argument("--validate", action="store_true",
                        help="valideer de XML na het schrijven tegen schemas/ebucore.xsd")
    args = parser.parse_args()

    if args.stems:
        dirs = []
        for s in args.stems:
            p = Path(s)
            if p.is_dir():
                dirs.append(p)
            else:
                dirs.append(OUTPUT_DIR / s)
    else:
        dirs = sorted(d for d in OUTPUT_DIR.iterdir() if d.is_dir())

    # validatie-schema opnieuw per aanroep: niet herladen tussen batches
    for d in dirs:
        export_video(d, validate=args.validate)


if __name__ == "__main__":
    main()
