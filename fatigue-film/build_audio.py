"""Generate neural English narration, word-timed captions, and a 180 s mix.

Requires edge-tts and FFmpeg. Pre-generated audio and captions are included,
so rebuilding the video does not require a network connection.
"""
import asyncio
import json
import re
import ssl
import subprocess
import wave
from pathlib import Path

import edge_tts
import edge_tts.communicate

ROOT = Path(__file__).resolve().parent
DATA = json.loads((ROOT / 'storyboard.json').read_text())
AUD = ROOT / 'audio'
AUD.mkdir(exist_ok=True)
# Use the operating system's trusted certificates, including managed roots.
# Certificate verification remains enabled.
edge_tts.communicate._SSL_CTX = ssl.create_default_context()


def run(args):
    return subprocess.run(args, check=True, capture_output=True, text=True)


def display(s):
    return (s.replace('K one C', 'K_Ic').replace('K one', 'K_I')
            .replace('K One C', 'K_Ic').replace('K One', 'K_I'))


def stamp(sec):
    ms = round(sec * 1000)
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f'{h:02}:{m:02}:{s:02},{ms:03}'


async def synth(scene):
    raw = AUD / (scene['id'] + '.mp3')
    timings = AUD / (scene['id'] + '.words.json')
    if not raw.exists() or not timings.exists() or raw.stat().st_size < 1000:
        words = []
        comm = edge_tts.Communicate(scene['speech'], DATA['voice'],
                                   rate='+0%', boundary='WordBoundary')
        with raw.open('wb') as out:
            async for part in comm.stream():
                if part['type'] == 'audio':
                    out.write(part['data'])
                elif part['type'] == 'WordBoundary':
                    words.append({k: part[k] for k in ('offset','duration','text')})
        timings.write_text(json.dumps(words, indent=2))
    words = json.loads(timings.read_text())
    probe = run(['ffprobe','-v','error','-show_entries','format=duration',
                 '-of','default=nw=1:nk=1',str(raw)])
    duration = float(probe.stdout.strip())
    slot = scene['end'] - scene['start']
    # Center speech in its slot with a short, deliberate lead-in. Small atempo
    # adjustments preserve pitch; raw recordings remain included.
    lead = .22
    target = slot - .50
    speed = max(1.0, duration / target)
    if speed > 1.22:
        raise ValueError(f"Narration too dense in {scene['id']}: {speed:.3f}")
    final = AUD / (scene['id'] + '.wav')
    run(['ffmpeg','-v','error','-y','-i',str(raw),'-af',
         f'atempo={speed:.9f},adelay={round(lead*1000)}:all=1,apad',
         '-t',str(slot),'-ac','1','-ar','48000','-c:a','pcm_s16le',str(final)])
    # Reattach original punctuation to the engine's word tokens. This keeps
    # captions verbatim while using real synthesis word timestamps.
    text = scene['speech']
    cursor = 0
    tokens = []
    for w in words:
        needle = w['text']
        pos = text.lower().find(needle.lower(),cursor)
        token = needle
        if pos >= 0:
            end = pos + len(needle)
            while end < len(text) and text[end] in '.,;:!?': end += 1
            token = text[pos:end]
            cursor = end
        tokens.append({'text':token,
            'start':scene['start']+lead+w['offset']/1e7/speed,
            'end':scene['start']+lead+(w['offset']+w['duration'])/1e7/speed})
    # Do not break inside "K one C"; display the standard engineering symbol.
    merged=[]; i=0
    while i < len(tokens):
        n=1
        if tokens[i]['text'].lower()=='k' and i+1<len(tokens) and tokens[i+1]['text'].lower().strip('.,;:!?')=='one':
            n=2
            if i+2<len(tokens) and tokens[i+2]['text'].lower().strip('.,;:!?')=='c': n=3
        merged.append({'text':display(' '.join(x['text'] for x in tokens[i:i+n])),
                       'start':tokens[i]['start'],'end':tokens[i+n-1]['end']})
        i+=n
    cues=[]; group=[]
    for i,w in enumerate(merged):
        proposal=' '.join(x['text'] for x in group+[w])
        if group and (len(proposal)>120 or w['end']-group[0]['start']>7.5):
            cues.append({'start':group[0]['start'],'end':group[-1]['end']+.08,
                         'text':' '.join(x['text'] for x in group),'scene':scene['id']})
            group=[]
        group.append(w)
        if re.search(r'[.!?]$',w['text']):
            cues.append({'start':group[0]['start'],'end':group[-1]['end']+.12,
                         'text':' '.join(x['text'] for x in group),'scene':scene['id']})
            group=[]
    if group:
        cues.append({'start':group[0]['start'],'end':group[-1]['end']+.12,
                     'text':' '.join(x['text'] for x in group),'scene':scene['id']})
    print(f"{scene['id']}: raw={duration:.2f}s slot={slot}s speed={speed:.3f} cues={len(cues)}",flush=True)
    return cues


async def main():
    cues=[]
    # Sequential service requests are reproducible and avoid rate bursts.
    for scene in DATA['scenes']:
        cues.extend(await synth(scene))
    for i,cue in enumerate(cues):
        if i+1<len(cues): cue['end']=min(cue['end'],cues[i+1]['start']-.01)
        cue['end']=min(cue['end'],180.)
    (ROOT/'captions.json').write_text(json.dumps(cues,indent=2))
    srt='\n\n'.join(f"{i+1}\n{stamp(c['start'])} --> {stamp(c['end'])}\n{c['text']}" for i,c in enumerate(cues))+'\n'
    (ROOT/'output'/'Fatigue_Failure_EN.srt').write_text(srt)
    with wave.open(str(AUD/'narration.wav'),'wb') as dst:
        dst.setparams((1,2,48000,0,'NONE','not compressed'))
        for scene in DATA['scenes']:
            with wave.open(str(AUD/(scene['id']+'.wav')),'rb') as src:
                dst.writeframes(src.readframes(src.getnframes()))
    run(['ffmpeg','-v','error','-y','-i',str(AUD/'narration.wav'),
         '-af','loudnorm=I=-16:TP=-1.5:LRA=7','-ar','48000',
         '-c:a','pcm_s16le',str(AUD/'narration_normalized.wav')])
    print('Audio and synchronized captions complete.',flush=True)


if __name__=='__main__':
    asyncio.run(main())
