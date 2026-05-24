# Internet Generation 日本語化パッチ

中国産インディーゲーム **Internet Generation** ([Steam](https://store.steampowered.com/app/1556980/Internet_Generation/)) の非公式日本語化パッチです。

* バージョン: **1.0.0**
* 対応ゲームビルド: Unity 2021.3.3f1c1 / 2026 年 05 月 時点の Steam 版
* 翻訳セリフ数: **1143 行**（全 1241 行中、内部ディレクティブ 98 行を除く）
* 翻訳 UI 文字列: DLL **121** / Asset **234** ペア（出現箇所累計 **約 340** 箇所）
* 翻訳済み level シーン: **18 ファイル**（環境ダイアログ・チートメニュー含む）
* 作者: **hhfcurator**（非公式）

---

## ⚠️ 免責事項（必ずお読みください）

本パッチは **岛叶游戏 および Internet Generation 公式とは一切関係のない、第三者による非公式翻訳パッチ** です。

* 本パッチの利用によって生じた **いかなる損害（ゲームデータの破損・セーブデータ消失・Steam アカウントへの影響・PC への影響・その他直接的/間接的損害を含むがこれらに限られないあらゆる損害）について、作者は一切の責任を負いません**
* 本パッチはゲームファイル（DLL / Asset）を **書き換えます**。`.bak` の自動バックアップを取りますが、Steam クラウドや別の競合パッチとの併用、ゲーム本体のアップデートと組み合わさることでの不具合まで保証するものではありません
* 本パッチの利用は **完全に自己責任** でお願いします。心配な場合は使用しないでください
* 本パッチに関する問題・不具合について、ゲーム開発元 岛叶游戏 に問い合わせることは **絶対におやめください**（公式に迷惑がかかります）

利用を続けるという行為をもって、上記すべてに同意したものとみなします。

---

## 翻訳の品質ポリシー

本翻訳は **「厳密に正確な日本語」を目的としていません**。あくまでインディーゲームの範疇で、ストレスなく遊んでもらえれば嬉しい、というスタンスです。

* 各キャラクターの名前は、意図的に原文（中国語）を残した表記となっています。
* 機械翻訳ベース＋人手調整で短期間に全 86 章を仕上げているため、誤訳・口調揺れ・微妙な意訳が含まれます。
* キャラクターの口調は雰囲気優先で作っており、原文ニュアンスとずれることがあります。
* 「ここはこう訳した方が良い」という改善提案は歓迎しますが、完璧な訳を約束するものではありません。

「ゲームを問題なく理解しながらプレイできる」レベルを目指しています。

---

## 動作環境

* **Windows 10 バージョン 1903 (2019年5月) 以降 / Windows 11 推奨**
  * 旧バージョンでは `install.bat` 内の日本語メッセージが文字化けする可能性があります（パッチの動作自体は問題ありません）
* Python 3.10 以降（自動インストール手順あり）: GUI版.exeを使わない場合
* Steam 版 Internet Generation がインストール済み
* インストール先のディスクに 200MB 以上の空き

---

## インストール手順

### 推奨: GUI インストーラ (.exe 単体・Python 不要)

[Releases ページ](https://github.com/hhfcurator/internet-generation-jp-hhf/releases/latest) から **`InternetGeneration-JP-Installer.exe`** をダウンロード → ダブルクリックで起動。

1. ゲームを Steam クライアントから終了
2. .exe を起動
3. 「ゲームインストール先」を確認（自動検出、必要なら「参照」で手動指定）
4. **「日本語化を適用」** ボタンを押す
5. 完了したら Steam から Internet Generation を起動

> .exe は内部に Python + 必要ライブラリ + 翻訳データ全部を同梱しているため、追加インストール不要です。

### 上級者向け: バッチ版（要 Python 3.10+）

ソースコードを clone または ZIP DL し、`install.bat` をダブルクリック:

1. パッチを展開（任意の場所）
2. Steam クライアントで Internet Generation を終了
3. `install.bat` 実行
   * 初回実行時、Python パッケージ（`UnityPy` 等）を自動 `pip install`
   * `.bak` バックアップを自動生成
   * DLL / resources.assets / level シーン群を順次パッチ
4. Steam から起動

> ゲーム内の言語設定は **English のまま**で OK です（Story 訳は EN スロットに格納されています）。

### 動作確認

* タイトル画面下部に「赤い [ENTER] キーで新しいゲームを開始」などとナビゲーションが日本語で表示されれば成功
* 新規ゲーム開始 → 冒頭の凌倾／宣铃の会話が日本語表示

---

## アンインストール

* **GUI 版**: `.exe` を起動して「元に戻す」ボタン
* **バッチ版**: `uninstall.bat` をダブルクリック

いずれも `.bak` から復元してオリジナル版に戻ります。

---

## トラブルシューティング

### 「Internet Generation のインストール先が見つかりません」と表示される

`install.bat` を以下のように手動でパスを指定して起動:

```cmd
install.bat --game "X:\YourSteamLibrary\steamapps\common\InternetGeneration"
```

### Python が見つからない

[Python 公式サイト](https://www.python.org/downloads/) から Python 3.10 以降をインストールしてください。インストール時に **"Add Python to PATH"** を必ずチェック。

### pip install に失敗する

ネットワーク環境を確認の上、手動で:

```cmd
pip install UnityPy openpyxl Pillow
```

---

## 既知の問題

* 内部ディレクティブ（`#动画切换` 等）は意図的に未訳（ゲームロジックで参照されるため）
* `Fullscreen` / `Window` の切替時、内部状態が中国語表現と一部混在する箇所がある可能性
* DLL UI の一部長文（説明文系）は改行候補位置に半角スペースが入る場合があります（実機表示の整え方は今後調整予定）
* **チートメニュー（cheater mode）の Buff / Monster プルダウン項目は中国語のまま**です。これらの内部識別文字列はゲームコードから直接参照されており、日本語化するとゲームが起動しなくなることを確認したため、安定動作優先で中国語表記を維持しています。パネル本体のラベル（最大HP / HP固定 / モンスター / Buff 等）と「現在の状態」値（戦闘前/中/後）は日本語化済み

問題を見つけた場合は GitHub Issue にてご報告ください。

---

## 翻訳方針

* キャラクターごとに口調を作り分け
  * **凌倾**（主人公）: ボーイッシュなギャル口調
  * **宣铃**（チュートリアル）: ドジっ子の龍娘
  * **机器人**（チャットボット）: メイド敬語ベース
  * **豚可**（商人）: サバサバ姐御
  * 他多数
* セリフは 1 行 12 文字目安（n=12, 許容 ±3）で改行
* 助詞の直前で改行しない（文節境界で改行）
* UI 文字列の長文には改行ロジックを適用、短文ラベルはそのまま

---

## 技術詳細（開発者向け）

### 改変箇所

| ファイル | 改変内容 |
|---|---|
| `Managed/Assembly-CSharp.dll` | `FormatText.ENFormatText` 内 IL リテラル 28→15、`ldstr` 93 件の英語文字列を日本語に置換 |
| `resources.assets` | `TextAsset 'TextEN'` の JSON 全置換、敵/スキル/バフ系 MonoBehaviour の文字列を生バイト書換（162 ペア） |
| `level0/10/11/12/13` | UI ラベル（Gamepad Map Options 等）の生バイト書換 |

### 使用ツール

* **Python 3.10+** (`UnityPy 1.25`, `openpyxl`, `Pillow`)
* **.NET SDK** + **Mono.Cecil 0.11.6**（DLL IL 書換 / ビルド済 exe 同梱）
* 自作 **SerializedFile rewriter** — 任意長文字列の置換に対応

### ソース・データ

* `data/story_jp.json` — 1143 行のセリフ翻訳
* `data/dll_mappings.json` — DLL ldstr 置換マップ（93 件）
* `data/asset_mappings.json` — Asset 置換マップ（162 ペア・出現箇所 occurrences 込み）

---

## ライセンス

* 本パッチに含まれる **翻訳テキスト** は CC BY-NC 4.0 (非商用利用・要表示)
* 本パッチに含まれる **スクリプト類** は MIT
* **Internet Generation 本体の著作権は開発元に帰属します**。本パッチはゲーム本体を含みません。ゲーム本体は正規 Steam 経由でご購入ください。

詳細は `LICENSE.txt` を参照してください。

---

## 連絡・報告

問題報告・翻訳改善提案は以下まで:

* **GitHub**: https://github.com/hhfcurator

---

## 謝辞

* Internet Generation 開発元 (岛叶游戏)
* UnityPy / Mono.Cecil コミュニティ

---

# English Summary

This is an **unofficial Japanese translation patch** for *Internet Generation* (Steam, Unity 2021.3).

## Disclaimer

This patch is created by a third party and is **not affiliated with InsularLobeGame**. Use at your own risk. The author assumes **no responsibility** for any damage to your game data, save files, Steam account, or PC. Do **not** contact the official developer about issues with this patch.

## Quick Install

1. Extract the ZIP
2. Close the game in Steam
3. Run `install.bat` (Python 3.10+ required; dependencies installed automatically)
4. Launch the game from Steam (keep in-game language as English)

## Uninstall

Run `uninstall.bat` to restore from `.bak` backups.

## What's translated

* 1143 dialogue lines across all 86 chapters
* 93 DLL UI mappings: title screen prompts, save UI, settings menu, difficulty options, confirmation dialogs
* 162 Asset UI mappings: enemy / skill / buff names and descriptions in the in-game compendium, "Gamepad Map Options"

## Translation quality

This patch aims for "playable enjoyment" rather than perfect accuracy. Some lines are summarized or rephrased loosely for screen-fit. Improvement suggestions welcome.

## Limitations

* Some long descriptions are summarized due to byte constraints
* Internal directives (`#动画切换` etc.) intentionally untranslated
* Game language must remain "English" (the patch overrides EN-slot strings)

Issues / Improvements: https://github.com/hhfcurator
