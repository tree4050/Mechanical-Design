"""Check the delivered media, timeline, and caption bounds using FFprobe."""
import json
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
path=ROOT/'output/Fatigue_Failure_3min_75_25.mp4'
r=subprocess.run(['ffprobe','-v','error','-count_frames','-show_format','-show_streams','-of','json',str(path)],capture_output=True,text=True,check=True)
info=json.loads(r.stdout)
video=next(s for s in info['streams'] if s['codec_type']=='video')
audio=next(s for s in info['streams'] if s['codec_type']=='audio')
assert abs(float(info['format']['duration'])-180)<.05
assert (video['width'],video['height'])==(1920,1080)
assert video['avg_frame_rate']=='24/1'
assert int(video['nb_read_frames'])==4320
assert video['codec_name']=='h264' and video['pix_fmt']=='yuv420p'
assert audio['codec_name']=='aac' and int(audio['sample_rate'])==48000
story=json.loads((ROOT/'storyboard.json').read_text())['scenes']
assert story[0]['start']==0 and story[-1]['end']==180
assert next(s for s in story if s['id']=='bike')['start']==135
for prev,nxt in zip(story,story[1:]): assert prev['end']==nxt['start']
caps=json.loads((ROOT/'captions.json').read_text())
for c in caps: assert 0<=c['start']<c['end']<=180 and c['text'].strip()
for a,b in zip(caps,caps[1:]): assert a['end']<=b['start']
report={
 'duration_seconds':float(info['format']['duration']),
 'resolution':[video['width'],video['height']],
 'frames':int(video['nb_read_frames']),
 'fps':24,
 'video_codec':video['codec_name'],
 'audio_codec':audio['codec_name'],
 'audio_sample_rate':int(audio['sample_rate']),
 'concept_seconds':135,'bicycle_seconds':45,
 'caption_cues':len(caps),
 'size_bytes':path.stat().st_size,
 'checks':'passed'
}
(ROOT/'output/quality_report.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
