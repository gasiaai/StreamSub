# StreamSub

**Language / ภาษา / 言語 / 语言 / 언어:**
[English](#english) | [ไทย](#ภาษาไทย) | [日本語](#日本語) | [中文](#中文) | [한국어](#한국어)

**[Download ZIP](https://github.com/gasiaai/StreamSub/archive/refs/heads/main.zip)** | `git clone https://github.com/gasiaai/StreamSub.git`

---

## English

Near real-time speech translation for everyone and streamers. The program captures audio from your system — whether it's your own microphone or PC audio — transcribes and translates it using a local LLM (Ollama), then displays subtitles as a transparent overlay. Enjoy foreign streamers in your language, or use it as a streamer to reach a wider audience.

No API keys, no cloud services — everything runs locally on your GPU.

### Features

- **Real-time ASR** — [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2) with Silero VAD
- **Local LLM Translation** — [Ollama](https://ollama.com/), no API keys needed
- **Multi-language output** — Translate to multiple languages at once (e.g. Japanese → Thai + English)
- **14 input languages** — Japanese, Chinese, Korean, English, Thai, Spanish, French, German, Russian, Portuguese, Italian, Vietnamese, Indonesian, Auto-detect
- **13 output languages** — English, Thai, Japanese, Chinese, Korean, Spanish, French, German, Russian, Portuguese, Italian, Vietnamese, Indonesian
- **Transparent overlay** — Frameless, always-on-top, draggable subtitle window
- **Adjustable response speed** — Fast (3s) / Balanced (5s) / Accurate (8s) buffer presets
- **Smart font sizing** — Text automatically shrinks to fit when sentences are long
- **WASAPI loopback** — Captures any system audio (game, browser, Discord, etc.)
- **One-click setup** — `run.bat` installs everything automatically

### Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **GPU** | NVIDIA 6 GB VRAM | NVIDIA 8-12 GB VRAM |
| **RAM** | 8 GB | 16 GB |
| **OS** | Windows 10 | Windows 10/11 |
| **Python** | 3.10+ | 3.11+ |

> **VRAM breakdown:**
> Whisper large-v3-turbo (~1.5 GB) + Ollama model (~2.5 GB) + overhead (~1-2 GB)
>
> If you don't have enough VRAM, Whisper will fall back to CPU automatically.

### Download

**[Download ZIP](https://github.com/gasiaai/StreamSub/archive/refs/heads/main.zip)** — Extract anywhere and run `run.bat`

Or use git: `git clone https://github.com/gasiaai/StreamSub.git`

### Quick Start (One-Click)

1. Install **Python 3.10+** from [python.org](https://www.python.org/downloads/)
   - Check **"Add Python to PATH"** during install
2. **Extract** the ZIP (or clone the repo)
3. Double-click **`run.bat`**

That's it. The script will automatically:
- Download and install **Ollama** (if not installed)
- Start the Ollama service
- Download the translation model (~2.5 GB, first time only)
- Create a Python virtual environment
- Install all Python dependencies
- Launch StreamSub

### Usage

1. **Select audio source** — Pick a WASAPI device (e.g. "What U Hear", "Stereo Mix")
2. **Choose input language** — The language being spoken
3. **Check target languages** — One or more languages to translate into
4. **Adjust buffer speed** — Fast (3s) for quick response, Accurate (8s) for longer sentences
5. **Click Start**

#### Overlay

- **Drag** to reposition
- **Double-click** to re-center on screen
- Stays on top of all windows — perfect for OBS

#### For Streamers

- Use **OBS Window Capture** to add the overlay to your stream
- The overlay has a semi-transparent dark background that works on most layouts
- For best results, capture system audio (not your microphone) via loopback device

### Configuration

Create a `.env` file to override defaults:

```env
OLLAMA_MODEL=qwen2.5
WHISPER_MODEL=large-v3-turbo
OLLAMA_BASE_URL=http://localhost:11434
```

#### Recommended Ollama Models

| Model | Size | Best For |
|-------|------|----------|
| `scb10x/typhoon-translate1.5-4b` | 2.5 GB | Thai translation (default) |
| `qwen2.5` | 4.7 GB | General multilingual |

### Architecture

```
System Audio → WASAPI Loopback → Audio Buffer
                                      ↓
                              Whisper ASR (GPU)
                                      ↓
                              Source Text (e.g. Japanese)
                                      ↓
                         ┌────────────┼────────────┐
                         ↓            ↓            ↓
                    Ollama LLM   Ollama LLM   Ollama LLM
                    (→ Thai)     (→ English)  (→ Chinese)
                         ↓            ↓            ↓
                         └────────────┼────────────┘
                                      ↓
                              Subtitle Overlay
```

### Project Structure

```
StreamSub/
├── main.py              # Entry point
├── config.py            # Configuration
├── run.bat              # One-click launcher (installs everything)
├── requirements.txt     # Python dependencies
├── core/
│   ├── audio.py         # WASAPI loopback capture
│   ├── asr.py           # Whisper ASR engine
│   ├── translator.py    # Ollama translation
│   └── pipeline.py      # Audio → ASR → Translate orchestrator
├── ui/
│   ├── control_panel.py # Settings window
│   └── overlay.py       # Transparent subtitle overlay
└── Model/               # Whisper models (auto-downloaded)
```

### Troubleshooting

**No audio device found** — Enable WASAPI loopback ("Stereo Mix", "What U Hear") in Windows Sound Settings → Recording → right-click → Show Disabled Devices. Click **Refresh** in the app.

**Ollama connection error** — Make sure Ollama is running (`ollama serve`). Check models: `ollama list`. Pull manually: `ollama pull scb10x/typhoon-translate1.5-4b`

**Out of VRAM** — Use a smaller Whisper model (`medium` or `small`). Whisper auto falls back to CPU if CUDA fails.

**Slow response** — Set Buffer to **Fast (3s)**. Use a smaller Whisper model. Close other GPU-heavy apps.

---

## ภาษาไทย

โปรแกรมแปลเสียงพูดแบบ(เกือบ)เรียลไทม์สำหรับผู้คนทั่วไปและสตรีมเมอร์ โดยโปรแกรมจะจับเสียงจากระบบ เช่น ไมค์ของคุณเองหรือเสียงจากเครื่อง PC → ถอดเสียงและแปลด้วย LLM (Ollama) → แสดงซับไตเติ้ล เพื่อให้ทุกคนสามารถสนุกกับสตรีมเมอร์ต่างชาติได้ และสตรีมเมอร์ยังใช้เพื่อเพิ่มฐานผู้ชมได้อีกด้วย

ไม่ต้องใช้ API key, ไม่ต้องพึ่งคลาวด์ — ทุกอย่างรันบน GPU ของคุณ

### คุณสมบัติ

- **ถอดเสียงเรียลไทม์** — [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2) พร้อม Silero VAD
- **แปลด้วย LLM ในเครื่อง** — [Ollama](https://ollama.com/) ไม่ต้องใช้ API key
- **แปลหลายภาษาพร้อมกัน** — เช่น ญี่ปุ่น → ไทย + อังกฤษ ในเวลาเดียวกัน
- **รองรับ 14 ภาษาอินพุต** — ญี่ปุ่น, จีน, เกาหลี, อังกฤษ, ไทย, สเปน, ฝรั่งเศส, เยอรมัน, รัสเซีย, โปรตุเกส, อิตาลี, เวียดนาม, อินโดนีเซีย, ตรวจจับอัตโนมัติ
- **รองรับ 13 ภาษาเอาต์พุต** — อังกฤษ, ไทย, ญี่ปุ่น, จีน, เกาหลี, สเปน, ฝรั่งเศส, เยอรมัน, รัสเซีย, โปรตุเกส, อิตาลี, เวียดนาม, อินโดนีเซีย
- **Overlay โปร่งใส** — ไม่มีขอบ, อยู่ด้านบนสุด, ลากย้ายได้
- **ปรับความเร็วได้** — เร็ว (3 วินาที) / สมดุล (5 วินาที) / แม่นยำ (8 วินาที)
- **ตัวอักษรย่อขยายอัตโนมัติ** — ข้อความยาวจะย่อฟอนต์ให้พอดี
- **WASAPI loopback** — จับเสียงจากทุกแหล่ง (เกม, เบราว์เซอร์, Discord ฯลฯ)
- **ติดตั้งคลิกเดียว** — `run.bat` จัดการทุกอย่างให้อัตโนมัติ

### ความต้องการของระบบ

| ส่วนประกอบ | ขั้นต่ำ | แนะนำ |
|-----------|---------|-------|
| **GPU** | NVIDIA 6 GB VRAM | NVIDIA 8-12 GB VRAM |
| **RAM** | 8 GB | 16 GB |
| **OS** | Windows 10 | Windows 10/11 |
| **Python** | 3.10+ | 3.11+ |

> **การใช้ VRAM:**
> Whisper large-v3-turbo (~1.5 GB) + Ollama model (~2.5 GB) + overhead (~1-2 GB)
>
> ถ้า VRAM ไม่พอ Whisper จะสลับไปใช้ CPU อัตโนมัติ

### ดาวน์โหลด

**[ดาวน์โหลด ZIP](https://github.com/gasiaai/StreamSub/archive/refs/heads/main.zip)** — แตกไฟล์แล้วรัน `run.bat` ได้เลย

หรือใช้ git: `git clone https://github.com/gasiaai/StreamSub.git`

### เริ่มต้นใช้งาน (คลิกเดียว)

1. ติดตั้ง **Python 3.10+** จาก [python.org](https://www.python.org/downloads/)
   - ติ๊ก **"Add Python to PATH"** ตอนติดตั้ง
2. **แตกไฟล์ ZIP** (หรือ clone repo)
3. ดับเบิ้ลคลิก **`run.bat`**

แค่นี้เลย! สคริปต์จะจัดการทุกอย่างให้อัตโนมัติ:
- ดาวน์โหลดและติดตั้ง **Ollama** (ถ้ายังไม่มี)
- เริ่ม Ollama service
- ดาวน์โหลดโมเดลแปลภาษา (~2.5 GB, ครั้งแรกเท่านั้น)
- สร้าง Python virtual environment
- ติดตั้ง dependencies ทั้งหมด
- เปิด StreamSub

### วิธีใช้

1. **เลือกแหล่งเสียง** — เลือก WASAPI device (เช่น "What U Hear", "Stereo Mix")
2. **เลือกภาษาอินพุต** — ภาษาที่กำลังพูด
3. **เลือกภาษาเป้าหมาย** — เลือกได้หลายภาษาพร้อมกัน
4. **ปรับความเร็ว Buffer** — เร็ว (3 วินาที) หรือ แม่นยำ (8 วินาที)
5. **กด Start**

### แก้ปัญหา

**ไม่พบอุปกรณ์เสียง** — เปิดใช้ WASAPI loopback ("Stereo Mix", "What U Hear") ใน Windows Sound Settings → Recording → คลิกขวา → Show Disabled Devices กด **Refresh** ในแอป

**เชื่อมต่อ Ollama ไม่ได้** — ตรวจสอบว่า Ollama ทำงานอยู่: `ollama serve` เช็คโมเดล: `ollama list` ดาวน์โหลด: `ollama pull scb10x/typhoon-translate1.5-4b`

**VRAM ไม่พอ** — เลือกโมเดล Whisper ที่เล็กกว่า (`medium` หรือ `small`) Whisper จะสลับไปใช้ CPU อัตโนมัติ

**ตอบช้า** — ตั้ง Buffer เป็น **เร็ว (3 วินาที)** ใช้โมเดล Whisper ที่เล็กกว่า ปิดแอปที่ใช้ GPU อื่นๆ

> **หมายเหตุ:** ตัวถอดเสียงเป็นข้อความ (Whisper) ยังไม่ดีนักสำหรับภาษาไทย อาจทำให้ข้อความที่ถอดออกมาเพี้ยนหรือผิดเพี้ยนจากต้นฉบับ ส่งผลให้คำแปลที่ได้อาจไม่ตรงตามที่พูดจริง

---

## 日本語

すべての人と配信者のための、ほぼリアルタイムの音声翻訳プログラム。マイクやPC音声などのシステムオーディオをキャプチャし、ローカルLLM（Ollama）で文字起こし・翻訳して字幕を表示します。海外の配信者を自分の言語で楽しんだり、配信者として視聴者層を広げたりできます。

APIキー不要、クラウドサービス不要 — すべてローカルGPUで動作します。

### 特徴

- **リアルタイム音声認識** — [faster-whisper](https://github.com/SYSTRAN/faster-whisper)（CTranslate2）+ Silero VAD
- **ローカルLLM翻訳** — [Ollama](https://ollama.com/)、APIキー不要
- **複数言語同時翻訳** — 例：日本語 → タイ語 + 英語を同時に
- **14の入力言語** — 日本語、中国語、韓国語、英語、タイ語、スペイン語、フランス語、ドイツ語、ロシア語、ポルトガル語、イタリア語、ベトナム語、インドネシア語、自動検出
- **13の出力言語** — 英語、タイ語、日本語、中国語、韓国語、スペイン語、フランス語、ドイツ語、ロシア語、ポルトガル語、イタリア語、ベトナム語、インドネシア語
- **透明オーバーレイ** — フレームレス、常に最前面、ドラッグ移動可能
- **応答速度調整** — 高速（3秒）/ バランス（5秒）/ 高精度（8秒）
- **フォント自動調整** — 長い文章は自動的にフォントが縮小
- **WASAPIループバック** — あらゆるシステム音声をキャプチャ（ゲーム、ブラウザ、Discordなど）
- **ワンクリックセットアップ** — `run.bat`がすべて自動でインストール

### システム要件

| コンポーネント | 最低 | 推奨 |
|------------|------|------|
| **GPU** | NVIDIA 6 GB VRAM | NVIDIA 8-12 GB VRAM |
| **RAM** | 8 GB | 16 GB |
| **OS** | Windows 10 | Windows 10/11 |
| **Python** | 3.10+ | 3.11+ |

> **VRAM内訳：**
> Whisper large-v3-turbo（約1.5 GB）+ Ollamaモデル（約2.5 GB）+ オーバーヘッド（約1-2 GB）
>
> VRAMが不足している場合、Whisperは自動的にCPUにフォールバックします。

### ダウンロード

**[ZIPをダウンロード](https://github.com/gasiaai/StreamSub/archive/refs/heads/main.zip)** — 解凍して `run.bat` を実行するだけ

またはgit: `git clone https://github.com/gasiaai/StreamSub.git`

### クイックスタート（ワンクリック）

1. **Python 3.10+** を [python.org](https://www.python.org/downloads/) からインストール
   - インストール時に **「Add Python to PATH」** にチェック
2. **ZIPを解凍**（またはリポジトリをクローン）
3. **`run.bat`** をダブルクリック

以上です！スクリプトが自動的に以下を実行します：
- **Ollama** のダウンロードとインストール（未インストールの場合）
- Ollamaサービスの起動
- 翻訳モデルのダウンロード（約2.5 GB、初回のみ）
- Python仮想環境の作成
- すべてのPython依存関係のインストール
- StreamSubの起動

### 使い方

1. **音声ソースを選択** — WASAPIデバイスを選択（例：「What U Hear」「Stereo Mix」）
2. **入力言語を選択** — 話されている言語
3. **翻訳先言語を選択** — 複数言語を同時に選択可能
4. **バッファ速度を調整** — 高速（3秒）で素早い応答、高精度（8秒）で長い文章向け
5. **Startをクリック**

### トラブルシューティング

**音声デバイスが見つからない** — WASAPIループバックデバイス（「Stereo Mix」「What U Hear」など）をWindows サウンド設定 → 録音 → 右クリック → 無効なデバイスの表示で有効化。アプリで**Refresh**をクリック。

**Ollama接続エラー** — Ollamaが動作中か確認：`ollama serve` モデル確認：`ollama list` 手動ダウンロード：`ollama pull scb10x/typhoon-translate1.5-4b`

**VRAMが不足** — より小さいWhisperモデルを選択（`medium`または`small`）。CUDAが失敗した場合、Whisperは自動的にCPUにフォールバック。

**応答が遅い** — Bufferを**高速（3秒）**に設定。より小さいWhisperモデルを使用。他のGPU負荷の高いアプリを閉じる。

---

## 中文

面向所有人和主播的近实时语音翻译程序。捕获系统音频（麦克风或PC音频），通过本地 LLM（Ollama）进行语音识别和翻译，并以透明叠加层显示字幕。让每个人都能用自己的语言享受海外主播的内容，主播也可以用它来扩大观众群。

无需 API 密钥，无需云服务 — 一切都在本地 GPU 上运行。

### 功能特点

- **实时语音识别** — [faster-whisper](https://github.com/SYSTRAN/faster-whisper)（CTranslate2）+ Silero VAD
- **本地 LLM 翻译** — [Ollama](https://ollama.com/)，无需 API 密钥
- **多语言同步翻译** — 例如：日语 → 泰语 + 英语同时翻译
- **14 种输入语言** — 日语、中文、韩语、英语、泰语、西班牙语、法语、德语、俄语、葡萄牙语、意大利语、越南语、印尼语、自动检测
- **13 种输出语言** — 英语、泰语、日语、中文、韩语、西班牙语、法语、德语、俄语、葡萄牙语、意大利语、越南语、印尼语
- **透明叠加层** — 无边框、始终置顶、可拖拽移动
- **可调响应速度** — 快速（3秒）/ 均衡（5秒）/ 精准（8秒）
- **字体自动调整** — 长文本自动缩小字体以适应显示
- **WASAPI 回环** — 捕获任何系统音频（游戏、浏览器、Discord 等）
- **一键安装** — `run.bat` 自动处理所有安装

### 系统要求

| 组件 | 最低 | 推荐 |
|------|------|------|
| **GPU** | NVIDIA 6 GB VRAM | NVIDIA 8-12 GB VRAM |
| **RAM** | 8 GB | 16 GB |
| **OS** | Windows 10 | Windows 10/11 |
| **Python** | 3.10+ | 3.11+ |

> **显存用量：**
> Whisper large-v3-turbo（约1.5 GB）+ Ollama 模型（约2.5 GB）+ 额外开销（约1-2 GB）
>
> 如果显存不足，Whisper 会自动切换到 CPU 运行。

### 下载

**[下载 ZIP](https://github.com/gasiaai/StreamSub/archive/refs/heads/main.zip)** — 解压后运行 `run.bat` 即可

或使用 git: `git clone https://github.com/gasiaai/StreamSub.git`

### 快速开始（一键安装）

1. 从 [python.org](https://www.python.org/downloads/) 安装 **Python 3.10+**
   - 安装时勾选 **"Add Python to PATH"**
2. **解压 ZIP**（或克隆仓库）
3. 双击 **`run.bat`**

就这么简单！脚本会自动：
- 下载并安装 **Ollama**（如果未安装）
- 启动 Ollama 服务
- 下载翻译模型（约2.5 GB，仅首次）
- 创建 Python 虚拟环境
- 安装所有 Python 依赖
- 启动 StreamSub

### 使用方法

1. **选择音频源** — 选择 WASAPI 设备（如 "What U Hear"、"Stereo Mix"）
2. **选择输入语言** — 正在说的语言
3. **选择目标语言** — 可同时选择多种语言
4. **调整缓冲速度** — 快速（3秒）用于快速响应，精准（8秒）用于长句
5. **点击 Start**

### 故障排除

**找不到音频设备** — 在 Windows 声音设置 → 录制 → 右键 → 显示禁用设备中启用 WASAPI 回环设备（"Stereo Mix"、"What U Hear"等）。点击应用中的**Refresh**重新扫描。

**Ollama 连接错误** — 确认 Ollama 正在运行：`ollama serve` 检查模型：`ollama list` 手动下载：`ollama pull scb10x/typhoon-translate1.5-4b`

**显存不足** — 选择更小的 Whisper 模型（`medium`或`small`）。CUDA 失败时 Whisper 会自动切换到 CPU。

**响应慢** — 将 Buffer 设为**快速（3秒）**。使用更小的 Whisper 模型。关闭其他占用 GPU 的应用。

---

## 한국어

모든 사람과 스트리머를 위한 거의 실시간 음성 번역 프로그램. 마이크나 PC 오디오 등 시스템 오디오를 캡처하고, 로컬 LLM(Ollama)으로 음성 인식 및 번역하여 자막을 표시합니다. 외국 스트리머의 방송을 자국어로 즐기거나, 스트리머로서 시청자층을 넓힐 수 있습니다.

API 키 불필요, 클라우드 서비스 불필요 — 모든 것이 로컬 GPU에서 실행됩니다.

### 기능

- **실시간 음성 인식** — [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2) + Silero VAD
- **로컬 LLM 번역** — [Ollama](https://ollama.com/), API 키 불필요
- **다국어 동시 번역** — 예: 일본어 → 태국어 + 영어 동시 번역
- **14개 입력 언어** — 일본어, 중국어, 한국어, 영어, 태국어, 스페인어, 프랑스어, 독일어, 러시아어, 포르투갈어, 이탈리아어, 베트남어, 인도네시아어, 자동 감지
- **13개 출력 언어** — 영어, 태국어, 일본어, 중국어, 한국어, 스페인어, 프랑스어, 독일어, 러시아어, 포르투갈어, 이탈리아어, 베트남어, 인도네시아어
- **투명 오버레이** — 프레임 없음, 항상 위에 표시, 드래그 이동 가능
- **응답 속도 조절** — 빠름 (3초) / 균형 (5초) / 정확 (8초)
- **스마트 폰트 크기** — 긴 텍스트는 자동으로 폰트가 축소되어 맞춤
- **WASAPI 루프백** — 모든 시스템 오디오 캡처 (게임, 브라우저, Discord 등)
- **원클릭 설치** — `run.bat`이 모든 것을 자동으로 설치

### 시스템 요구 사항

| 구성 요소 | 최소 | 권장 |
|----------|------|------|
| **GPU** | NVIDIA 6 GB VRAM | NVIDIA 8-12 GB VRAM |
| **RAM** | 8 GB | 16 GB |
| **OS** | Windows 10 | Windows 10/11 |
| **Python** | 3.10+ | 3.11+ |

> **VRAM 사용량:**
> Whisper large-v3-turbo (~1.5 GB) + Ollama 모델 (~2.5 GB) + 오버헤드 (~1-2 GB)
>
> VRAM이 부족하면 Whisper가 자동으로 CPU로 전환됩니다.

### 다운로드

**[ZIP 다운로드](https://github.com/gasiaai/StreamSub/archive/refs/heads/main.zip)** — 압축 해제 후 `run.bat` 실행

또는 git: `git clone https://github.com/gasiaai/StreamSub.git`

### 빠른 시작 (원클릭)

1. [python.org](https://www.python.org/downloads/)에서 **Python 3.10+** 설치
   - 설치 시 **"Add Python to PATH"** 체크
2. **ZIP 압축 해제** (또는 저장소 클론)
3. **`run.bat`** 더블클릭

그게 끝입니다! 스크립트가 자동으로:
- **Ollama** 다운로드 및 설치 (미설치 시)
- Ollama 서비스 시작
- 번역 모델 다운로드 (~2.5 GB, 첫 실행만)
- Python 가상 환경 생성
- 모든 Python 의존성 설치
- StreamSub 실행

### 사용 방법

1. **오디오 소스 선택** — WASAPI 장치 선택 (예: "What U Hear", "Stereo Mix")
2. **입력 언어 선택** — 말하고 있는 언어
3. **대상 언어 선택** — 여러 언어를 동시에 선택 가능
4. **버퍼 속도 조절** — 빠름 (3초)으로 빠른 응답, 정확 (8초)으로 긴 문장 대응
5. **Start 클릭**

### 문제 해결

**오디오 장치를 찾을 수 없음** — Windows 사운드 설정 → 녹음 → 우클릭 → 사용할 수 없는 장치 표시에서 WASAPI 루프백 장치("Stereo Mix", "What U Hear" 등)를 활성화. 앱에서 **Refresh** 클릭.

**Ollama 연결 오류** — Ollama가 실행 중인지 확인: `ollama serve` 모델 확인: `ollama list` 수동 다운로드: `ollama pull scb10x/typhoon-translate1.5-4b`

**VRAM 부족** — 더 작은 Whisper 모델 선택 (`medium` 또는 `small`). CUDA 실패 시 Whisper가 자동으로 CPU로 전환.

**응답이 느림** — Buffer를 **빠름 (3초)**으로 설정. 더 작은 Whisper 모델 사용. 다른 GPU 사용 앱 종료.

---

## Author / ผู้พัฒนา / 開発者 / 开发者 / 개발자

**Gasia** — [Facebook](https://www.facebook.com/gasiaai123)

### Support

<a href="https://www.buymeacoffee.com/gasia" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" alt="Buy Me A Coffee" style="height: 41px !important;width: 174px !important;box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;-webkit-box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;" ></a>

[TipMe](https://tipme.in.th/gasia)

## License

MIT
