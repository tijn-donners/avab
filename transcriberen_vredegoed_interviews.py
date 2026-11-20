from annotate_video import transcribe_audio, segments_to_srt
from pathlib import Path

videos_path = Path("vredegoed_interviews/data")
output_dir = Path("vredegoed_interviews/output")

for video_path in videos_path.iterdir():
    segments, full_transcription = transcribe_audio(video_path)
    srt = segments_to_srt(segments)

    with open(f"vredegoed_interviews/output/{video_path.stem}.srt", "w", encoding="utf-8") as f:
            f.write(srt)
                 
    Path(output_dir / video_path.stem).with_suffix(".txt").write_text("[Let op: deze transcriptie is automatisch gemaakt met Whisper V3 Large (https://huggingface.co/openai/whisper-large-v3). Er kunnen fouten in zitten.]\n" + full_transcription, encoding="utf-8")