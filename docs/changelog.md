# Changelog

## v1.0.0 (2026-05-25)

### Initial Public Release

#### Translation Coverage

##### Story
- **Story dialogue**: 1143 lines across 86 chapters (block 0–85)
- 用語統一: `沙雕图（おバカ画像）` 等の括弧注釈表記、`VTuber信者` 等
- キャラ別一人称: 浮昔/浮昔盔甲 → アタシ、海豹/海豹群主 → 我輩、树系 → ウチ、舔狗系 → 私
- `line` index にギャップがある対話ブロックでも、JP→EN の重複表示が起きないよう注入ロジック修正

##### DLL UI strings (121 mappings)
- Title screen prompts (4 variants)
- Save UI (Auto Save / Enter the savefile name / Save / Quit / Unnamed Save 等)
- Settings labels (Difficulty / Language / Display / Resolution)
- Difficulty options (Easy / Normal / Hard / Story / Default)
- Fullscreen / Window switching
- Confirmation dialogs (delete / overwrite / load)
- Battle hints (4種: sweep mines / Chinese Cheese / Rebounce bullets / Stun Fuxi)
- Battle dialogs (4種: What's up / Who is that guy / EXPLANATION / WITHERED)
- Plot dialogs (10種: mods/Overthrow/Who cares/lackeys 等)
- Battle hint buttons (D-Pad / Key 1-4 / Start / I key)
- Cheater menu instructions (Green button / "Option" 等)
- Cheat menu current-state values (戦闘前/戦闘中/戦闘後)
- "Unreads" counter label / Compendium notifications

##### Asset UI strings (234 mappings, 約 340 occurrences across 18 level files)
- Buff names and descriptions (resources.assets, 162 entries)
- Skill names and descriptions
- Enemy names and descriptions
- Gamepad Map Options
- **Environmental dialogs** in 18 level scenes (level2/7/14/17/20×2/21/22/23/26/30/31/34/37/39/40×5/42/43/44)
  - 例: 「もう何年もテレビなんて観てないなぁ」(level26)、「床が溶けてる」(level44)
- **Cheat menu panel labels** (sharedassets0 pid 1201, 19 entries)
  - 最大HP / HP固定 / 死亡回数 / モンスター / モンスター追加 / Buff追加 / スキル解放 / 全体ダメージ / 全体即殺 / STEAM実績リセット 他
- **Cheat menu enemy dropdown character names** (sharedassets0 pids 1158-1195, 30 entries)

#### Technical
- Mono.Cecil ベース DLL パッチャ (threshold 28→15, ldstr 置換) — `dump` モードで全 ldstr 抽出に対応
- 自作 SerializedFile rewriter (Unity 2021.3 v22 対応、任意長文字列)
- 改行ロジック (jp_linebreak): Rule 1 / Rule 2 + 行頭禁則 + 記号巻込 + 副詞分割禁止 + Rich Text タグ保護
- DLL UI で Rich Text タグ (`<color>...</color>`) を含む文字列は改行ロジック対象外 — タグ破損 (`<color=#ff 0000>` 等) を防止
- 自動バックアップ (`.bak` 同梱配置) — 25 ファイル対象
- アンインストール対応 (`uninstall.bat` で全ファイル原状復帰)
- `--dry-run` の副作用を排除（mapping ファイルを書き出さない）
- `patcher.py` にゲームプロセス起動中チェックを実装 — 起動中の誤適用によるファイル破損を防止 (`--force` で上書き可)

### Known Issues
- 内部ディレクティブ (#动画切换 等) は意図的に未訳
- ゲーム言語設定は "English" 固定 (Story 訳が EN スロット格納のため)
- DLL UI 長文の一部に改行候補由来の半角スペースが残る（実機表示確認後に調整予定）
- **チートメニュー (cheater mode) の Buff / Monster プルダウン項目は中国語のまま**
  - これらの内部識別文字列はゲームコードから直接参照されており、日本語化するとゲームが起動しなくなることを確認したため、安定動作優先で中国語表記を維持
  - パネル本体のラベル（最大HP / HP固定 / モンスター / Buff 等）と「現在の状態」値（戦闘前/中/後）は日本語化済み
