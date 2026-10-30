# Assignment prompt and production brief

## Original user request

參考我附的作業圖片，幫我做一部3分鐘的疲勞破壞教學影片，要有英文旁白和英文字幕，用簡單英文把觀念講清楚。

第一頁寫影片標題和內容大綱，內容大綱寫先講觀念越詳細越好，再講自行車案例，搭配自行車插圖。觀念占影片四分之三，自行車案例占影片四分之一。

內容先說明金屬在反覆載重下，即使應力低於降伏強度，也可能因疲勞而破壞。搭配真實試件照片，介紹應力集中處的裂紋起始、逐漸成長，以及剩餘完整截面縮小後的最終快速斷裂。用連續動畫呈現這三個階段，讓人看得出疲勞是逐漸累積損傷的過程。

S–N曲線要說明縱軸是應力振幅、橫軸是破壞前的循環次數，橫軸用對數刻度。用動畫示範如何從應力讀出疲勞壽命，並比較同樣試驗條件下，高、低應力的壽命差異。也簡單提到某些鋼材有疲勞限，但鋁合金一般沒有明確的疲勞限。

斷裂韌性要講出材料抵抗既有裂紋造成斷裂的能力，並區分應力強度因子K_I和材料的斷裂韌性K_Ic。說明應力越大、裂紋越長，K_I通常越大；在線彈性、平面應變條件下，最大K_I達到K_Ic時可能發生快速斷裂。也要提醒，疲勞裂紋在未達這個臨界值前就可能逐漸成長。

S-N曲線用示意數據和動畫比較高低應力的疲勞壽命，標明數據差異及非曲柄實測結果，再用簡單公式和動畫說明應力增加、裂紋變長會提高應力強度因子，並介紹平面應變斷裂韌性及裂紋在未達臨界值前仍可能成長。

影片最後，也就是整體時間的四分之一，再用「自行車曲柄為什麼會在反覆踩踏後突然斷裂？」作為實際應用，把前面介紹的疲勞破壞、S–N曲線和斷裂韌性串起來。先展示自行車與曲柄的位置，用動態箭頭表示踩踏時的反覆受力，再放大到曲柄連接處等容易產生應力集中的位置。搭配有可靠來源的真實疲勞斷面照片，以及裂紋從起始、逐漸成長到最後快速斷裂的動畫，說明零件可能在多次使用後累積損傷。接著用示意S–N曲線說明踩踏造成的應力振幅與疲勞壽命的關係，再回扣裂紋變長會提高應力強度因子，達到適用的臨界條件後可能快速斷裂。不要捏造特定曲柄的實測數據或使用壽命。最後以避免表面損傷、注意異常與檢查裂紋作結束。

美編希望有科技感、統一配色和有層次的排版。

最後給我MP4、參考來源和GitHub的原始碼。

## Structured production brief derived from the request

Create a 180-second, 1920 x 1080 educational animation. Reserve 0-135 seconds for concepts and 135-180 seconds for the bicycle application and credits. Use accessible English, synthetic English narration and matching timed English captions. Make the opening outline detailed and include a bicycle illustration.

Use a consistent navy, cyan and warm-yellow visual system with large type and a reserved caption band. Draw accurate diagrams in code, including moving force arrows, a continuously growing edge crack, shrinking intact ligament and a rapid final separation. Use real sourced photographs rather than generated "specimen" images.

For the S-N example, use explicitly synthetic data: 300 MPa at 10,000 cycles and 180 MPa at 1,000,000 cycles. Keep the horizontal axis logarithmic. Animate horizontal movement from the chosen amplitude to the curve, followed by vertical movement to the cycle axis. Show synthetic scatter and distinguish typical steel/aluminum trends. State that these are not crank test results.

Render K_I = Y * sigma * sqrt(pi*a), define each factor and distinguish loading from resistance. Animate increasing stress at fixed crack length and growing crack length at fixed stress, with Y held constant for the relative comparisons. Explain linear-elastic plane-strain applicability, maximum K_I reaching K_Ic, and the possibility of cyclic growth below this value.

In the bicycle section, show the full bicycle, identify the crank, then enlarge the load-transfer region. Use the authentic broken-crank photo with attribution. Connect cumulative damage, the stress-life trend and the existing-crack criterion, without claiming a measured crank lifetime. Finish with surface care, attention to changes, crack inspection and stopping use of a suspect part.

## Actual production tools

- ChatGPT/Codex: source research, instructional script, storyboard, original Python code and review.
- Python/Pillow: bicycle drawing, diagrams and animation frames.
- Matplotlib mathtext: accurately typeset formulas.
- Microsoft Edge en-US-AriaNeural via edge-tts: English synthetic speech and word timestamps.
- FFmpeg: scene encoding, audio timing/normalization and final MP4 assembly.
- ReportLab: linked reference PDF.

No image-generation model was used for the real photographs. No GitHub account was accessed and no repository was created. This package is prepared for uploading to a repository chosen by the user.

The final scene-by-scene English narration is stored in `storyboard.json`, and the readable transcript is in `TRANSCRIPT.md`.
