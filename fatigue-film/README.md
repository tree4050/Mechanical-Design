# Fatigue Failure: From Small Cracks to Sudden Fracture

A complete 180-second English teaching film with English captions, authentic specimen photographs, animated crack growth, S-N reading examples, and a bicycle-crank application.

## 這個資料夾是什麼？

這是影片的完整原始碼資料夾，可以上傳到你自己的 GitHub repository（程式碼儲存庫）。**本儲存庫包含影片製作原始碼、提示詞、字幕及參考來源**

- `render_video.py`：畫面、圖表、自行車、受力及裂紋動畫。
- `build_audio.py`：英文旁白、逐字時間戳與字幕製作。
- `storyboard.json`：逐段旁白與固定時間表。
- `captions.json`、`output/Fatigue_Failure_EN.srt`：同步英文字幕。
- `audio/narration_normalized.wav`：已完成旁白，可直接離線重製影片。
- `assets/`：真實照片、字型與字型授權。
- `PROMPTS.md`：作業提示詞及製作設定。
- `REFERENCES.md`、`output/Fatigue_Failure_References.pdf`：來源、圖片授權與示意數據說明。
- `.github/workflows/render.yml`：手動觸發的 GitHub Actions 製片流程。

## Timing

| Time | Content |
| --- | --- |
| 00:00-00:10 | Title, detailed outline and bicycle illustration |
| 00:10-00:23 | Repeated loading below yield strength |
| 00:23-00:33 | Authentic NIST specimen and stress concentration |
| 00:33-00:50 | Continuous initiation, growth and final fracture animation |
| 00:50-01:02 | S-N axes, amplitude and logarithmic scale |
| 01:02-01:16 | High/low stress read-off animation |
| 01:16-01:28 | Synthetic scatter, steel and aluminum trends |
| 01:28-01:41 | K_I versus K_Ic |
| 01:41-01:51 | Formula and variable definitions |
| 01:51-02:01 | Fixed crack/increasing stress; fixed stress/growing crack |
| 02:01-02:15 | Validity conditions and subcritical fatigue growth |
| 02:15-02:23 | Bicycle and crank location |
| 02:23-02:31 | Repeated pedal forces and stress concentrations |
| 02:31-02:40 | Authentic broken crank and animated crack development |
| 02:40-02:48 | Link fatigue life with crack-tip stress intensity |
| 02:48-03:00 | Care, inspection and source credits |

The science section occupies exactly 135 seconds (75%). The bicycle application, including its closing advice and credits, occupies exactly 45 seconds (25%).

## Rebuild the MP4

Install Python 3.12 and FFmpeg. Run the following commands **inside this folder**. FFmpeg and FFprobe must be on PATH.

```bash
python -m pip install -r requirements.txt
python render_video.py --preview
python render_video.py --render --workers 3
python verify_media.py
```

The finished file is `output/Fatigue_Failure_3min_75_25.mp4` (1920 x 1080, 24 fps, H.264/AAC, 180 seconds). The supplied normalized narration and caption timings are sufficient for offline rendering after dependency installation. Use `--workers 1` on a computer with limited memory.

To regenerate the reference PDF:

```bash
python make_references.py
```

To regenerate speech, internet access to the Edge speech service is required. The selected voice is `en-US-AriaNeural` and certificates are verified using the operating-system trust store.

```bash
python build_audio.py
```

Raw scene MP3s are cached. After changing a scene's speech, delete that scene's `.mp3` and `.words.json` from `audio/` before rerunning. Then render the video again. Captions use actual synthesized word timestamps; small tempo adjustments preserve pitch and fit the fixed scene slots. In captions, spoken "K one" and "K one C" are written `K_I` and `K_Ic`.

## Upload to GitHub

1. Create an empty repository in your GitHub account.
2. Upload the **contents** of this folder so that `README.md` is at the repository root.
3. Include the `audio/narration_normalized.wav` file and retain photo credits and licenses.
4. The optional workflow can be run manually from the repository's Actions page. It does not publish anything automatically.

The ZIP omits rendered intermediate clips and the final MP4 to keep source distribution small. Download the delivered MP4 separately, or recreate it with the command above.

## Scientific scope

S-N numerical points and scatter are **illustrative, not measured crank data**. The displayed curve is `S = 540 - 60*log10(N)` for `10^3 <= N <= 10^7`; it is not a material fit. The reading examples are 300 MPa at 10,000 cycles and 180 MPa at 1,000,000 cycles. No real crank life is predicted.

The formula is `K_I = Y * sigma * sqrt(pi*a)`. Relative demonstrations hold Y constant. The rapid-fracture comparison uses maximum K_I and K_Ic only under valid linear-elastic, plane-strain conditions. The case-study graphic explicitly notes this limitation. Cyclic growth may happen below K_Ic; a detailed growth-rate prediction is outside the three-minute scope.

The NIST image is a titanium test specimen. It is not presented as a bicycle crank. The second photograph is an actual broken crank credited to its photographer; no unverified alloy, load history or service life is assigned to it.

## Credits and license

See `REFERENCES.md` and `LICENSE.md`. The film and original educational visual content are offered under CC BY-SA 3.0, with third-party rights retained. Keep Oxensepp's photo credit and license, NIST credit, and the bundled font license when redistributing. Source links do not imply endorsement.

