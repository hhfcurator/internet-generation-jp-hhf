"""
Internet Generation 日本語化パッチャ
==================================

使い方:
  1. このパッチを Internet Generation がインストールされている PC に展開
  2. install.bat を実行 (Steam ライブラリを自動検出)
  3. 起動して言語を English (Story 訳は EN スロットに格納)

引数:
  --game DIR     ゲームインストールフォルダを手動指定 (省略時は Steam を自動探索)
  --uninstall    .bak から復元 (アンインストール)
  --dry-run      実際の書込はせず、検証のみ行う
"""
import os, sys, json, argparse, shutil, struct, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # release/InternetGeneration_JP_v1.0.0/
DATA = ROOT / 'data'
TOOLS = ROOT / 'tools'

# UnityPy import (依存関係チェック)
try:
    import UnityPy
    from UnityPy.files.ObjectReader import ObjectReader
except ImportError:
    print('[ERROR] UnityPy が未インストールです。')
    print('  pip install UnityPy openpyxl Pillow')
    sys.exit(1)

# typetree サイズ不一致を吸収
_or = ObjectReader.read
def _safe_read(self, *a, **k):
    try: return _or(self, *a, **k)
    except ValueError as e:
        if 'Expected to read' in str(e):
            return self.read_typetree(wrap=True, check_read=False)
        raise
ObjectReader.read = _safe_read

# --- sf_rewriter.py を tools/ から import
sys.path.insert(0, str(TOOLS))
from sf_rewriter import rewrite, patch_object_blob_to


# ========== 改行ロジック v3 (jp_linebreak と同期) ==========
def _load_lines(path: Path):
    if not path.exists(): return []
    out = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            s = line.strip()
            if s and not s.startswith('#'): out.append(s)
    return out

_ADVERBS = set(_load_lines(DATA / 'jp_adverbs.txt'))
_KATAKANA_PARTS = sorted(set(_load_lines(DATA / 'katakana_parts.txt')), key=lambda s: -len(s))
NON_SYMBOL_OVERRIDE = set('#%*（）()「」『』<>＜＞[]【】')
LEADING_FORBIDDEN = set(
    'がをにでとへはもやの' 'っゃゅょゎァィゥェォッャュョヮぁぃぅぇぉ' 'ー'
    '。、，．！？!?…' '」』）)）】〕〉》〙〛'
)
_SPECIAL_PREFIXES = ['商品説明：', '商品介绍：', '商品介紹：', 'Item description: ']

def _is_hira(c): o=ord(c); return 0x3040<=o<=0x309F
def _is_kata(c):
    o=ord(c); return 0x30A0<=o<=0x30FF or 0x31F0<=o<=0x31FF or 0xFF66<=o<=0xFF9D
def _is_kanji(c):
    o=ord(c); return 0x3400<=o<=0x4DBF or 0x4E00<=o<=0x9FFF
def _is_ascii_word(c): return c.isascii() and (c.isalnum() or c=='_')

def _ccls(c):
    if c=='ー': return 'KATA'
    if _is_hira(c): return 'HIRA'
    if _is_kata(c): return 'KATA'
    if _is_kanji(c): return 'KANJI'
    if _is_ascii_word(c): return 'ASCII'
    if c in NON_SYMBOL_OVERRIDE or c.isspace(): return 'OTHER'
    return 'SYMBOL'

def _is_symbol(c): return _ccls(c)=='SYMBOL'

def _kata_runs(text):
    runs=[]; L=len(text); i=0
    while i<L:
        if _ccls(text[i])=='KATA':
            j=i+1
            while j<L and _ccls(text[j])=='KATA': j+=1
            if j-i>=2: runs.append((i,j))
            i=j
        else: i+=1
    return runs

def _split_compound_kata(run):
    L=len(run); pos=0; cuts=[]
    while pos<L:
        m=None
        for w in _KATAKANA_PARTS:
            if run.startswith(w,pos): m=w; break
        if m is None: pos+=1; continue
        pos+=len(m)
        if pos<L: cuts.append(pos)
    return cuts

def _chouon_split(run):
    return [i+1 for i,c in enumerate(run) if c=='ー' and i+1<len(run)]

def _adverb_forbid(text):
    forbid=set()
    for w in _ADVERBS:
        if len(w)<2: continue
        s=0
        while True:
            i=text.find(w,s)
            if i<0: break
            for k in range(i+1, i+len(w)): forbid.add(k)
            s=i+1
    return forbid

import re as _re
_TAG_RE = _re.compile(r'<[^>]*>')
def _richtext_forbid(text):
    forbid=set()
    for m in _TAG_RE.finditer(text):
        for k in range(m.start()+1, m.end()): forbid.add(k)
    return forbid

def _collect_cand(text, llm_breaks, n_max):
    cand=set(llm_breaks); L=len(text)
    for i in range(1,L):
        a=_ccls(text[i-1]); b=_ccls(text[i])
        if a=='SYMBOL' and b!='SYMBOL': cand.add(i)
        if a in ('HIRA','KATA','KANJI','ASCII') and b in ('HIRA','KATA','KANJI','ASCII'):
            if a!=b and not (a=='KANJI' and b=='HIRA'): cand.add(i)
    for rs,re_ in _kata_runs(text):
        run=text[rs:re_]
        for k in list(cand):
            if rs<k<re_: cand.discard(k)
        if len(run)>n_max+3:
            cuts=_split_compound_kata(run) or _chouon_split(run)
            for o in cuts: cand.add(rs+o)
    forbid=_adverb_forbid(text) | _richtext_forbid(text)
    for k in list(cand):
        if k in forbid: cand.discard(k)
    cand.discard(0); cand.discard(L)
    return sorted(cand)

def _greedy(text, cands, n_max):
    out=[]; start=0; L=len(text)
    while start<L:
        if L-start<=n_max+3: out.append(text[start:]); break
        chosen=-1
        for tol in (0,3,5):
            upper=start+n_max+tol; best=-1
            for c in cands:
                if c<=start: continue
                if c>upper: break
                lead=0
                while c+lead<L and text[c+lead] in LEADING_FORBIDDEN: lead+=1
                l1=(c-start)+lead
                if l1<=n_max+tol: best=c+lead
                elif all(_is_symbol(text[k]) for k in range(c,c+lead)): best=c+lead
            if best!=-1: chosen=best; break
        if chosen==-1:
            upper=start+n_max
            chouon=-1
            for k in range(start, min(upper,L)):
                if text[k]=='ー' and k+1<L and _ccls(text[k+1])=='KATA': chouon=k+1
            chosen=chouon if chouon!=-1 else upper
        out.append(text[start:chosen]); start=chosen
    return out

def _move_leading(lines):
    if not lines: return lines
    out=[lines[0]]
    for ln in lines[1:]:
        i=0
        while i<len(ln) and ln[i] in LEADING_FORBIDDEN: i+=1
        if i>0: out[-1]+=ln[:i]; ln=ln[i:]
        if ln: out.append(ln)
    return out

def apply_break_rules(text, n_max=15):
    if not text: return text
    for prefix in _SPECIAL_PREFIXES:
        if text.startswith(prefix) and len(text)>len(prefix):
            rest=text[len(prefix):].lstrip()
            return prefix + '\n' + apply_break_rules(rest, n_max)
    text=text.replace('\r\n','\n').replace('\r','\n')
    parts=text.split('\n')
    concat=''; llm=set(); pos=0
    for i,p in enumerate(parts):
        concat+=p; pos+=len(p)
        if i<len(parts)-1: llm.add(pos)
    if not concat: return text
    cands=_collect_cand(concat, llm, n_max)
    lines=_greedy(concat, cands, n_max)
    lines=_move_leading(lines)
    return '\n'.join(lines)


# ========== ゲーム検出 ==========
COMMON_STEAM_PATHS = [
    r'C:\Program Files (x86)\Steam\steamapps\common\InternetGeneration',
    r'C:\Program Files\Steam\steamapps\common\InternetGeneration',
    r'D:\Steam\steamapps\common\InternetGeneration',
    r'D:\SteamLibrary\steamapps\common\InternetGeneration',
    r'E:\SteamLibrary\steamapps\common\InternetGeneration',
    r'F:\SteamLibrary\steamapps\common\InternetGeneration',
    r'G:\SteamLibrary\steamapps\common\InternetGeneration',
]

# Steam libraryfolders.vdf 候補位置
COMMON_VDF_PATHS = [
    r'C:\Program Files (x86)\Steam\steamapps\libraryfolders.vdf',
    r'C:\Program Files\Steam\steamapps\libraryfolders.vdf',
    r'D:\Steam\steamapps\libraryfolders.vdf',
]


def _parse_vdf_paths(text):
    """libraryfolders.vdf から "path" "<dir>" を抽出。簡易パーサ。"""
    import re as _re
    return [m.group(1).replace('\\\\', '\\') for m in
            _re.finditer(r'"path"\s+"([^"]+)"', text)]


def find_game():
    """Steam ライブラリを順に探索。見つからなければ None。
    1. 既知の候補パスを総当たり
    2. libraryfolders.vdf があれば追加ライブラリも探索
    """
    for p in COMMON_STEAM_PATHS:
        if Path(p, 'InternetGeneration.exe').exists():
            return Path(p)
    # libraryfolders.vdf を読んで追加ライブラリを探索
    for vdf in COMMON_VDF_PATHS:
        if not Path(vdf).exists(): continue
        try:
            text = Path(vdf).read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        for lib_root in _parse_vdf_paths(text):
            cand = Path(lib_root) / 'steamapps' / 'common' / 'InternetGeneration'
            if (cand / 'InternetGeneration.exe').exists():
                return cand
    return None


# ========== バックアップ ==========
BAK_FILES = ['resources.assets', 'Managed/Assembly-CSharp.dll',
             'level0', 'level2', 'level7',
             'level10', 'level11', 'level12', 'level13', 'level14', 'level17',
             'level20', 'level21', 'level22', 'level23',
             'level26', 'level30', 'level31', 'level34', 'level37',
             'level39', 'level40', 'level42', 'level43', 'level44']

def ensure_backup(game_dir: Path):
    data_dir = game_dir / 'InternetGeneration_Data'
    missing = []
    for rel in BAK_FILES:
        src = data_dir / rel
        bak = data_dir / (rel + '.bak')
        if not src.exists():
            missing.append(rel); continue
        if not bak.exists():
            print(f'  バックアップ作成: {rel}')
            bak.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, bak)
    if missing:
        print(f'[ERROR] 以下のファイルが見当たりません: {missing}')
        return False
    return True


def restore_from_backup(game_dir: Path):
    data_dir = game_dir / 'InternetGeneration_Data'
    for rel in BAK_FILES:
        bak = data_dir / (rel + '.bak')
        tgt = data_dir / rel
        if bak.exists():
            shutil.copy(bak, tgt)
            print(f'  復元: {rel}')


# ========== Story 注入 (TextAsset 'TextEN' 書換) ==========
def inject_story(game_dir: Path, dry_run=False):
    """story_jp.json を読み、TextEN TextAsset の data フィールドを上書き"""
    with open(DATA / 'story_jp.json', encoding='utf-8') as f:
        story_data = json.load(f)
    # (block, stage, text) -> list of {line, speaker, sprite, jp}
    by_key = {}
    for it in story_data:
        by_key.setdefault((it['block'], it['stage'], it['text']), []).append(it)
    for k in by_key: by_key[k].sort(key=lambda x: x['line'])

    data_dir = game_dir / 'InternetGeneration_Data'
    bak = data_dir / 'resources.assets.bak'
    tgt = data_dir / 'resources.assets'

    # 既存 TextEN の JSON 構造を読み、JP で上書きしたものを書き戻す
    env = UnityPy.load(str(bak))
    text_en_obj = None
    for obj in env.objects:
        if obj.type.name != 'TextAsset': continue
        d = obj.read()
        if d.m_Name == 'TextEN':
            text_en_obj = (obj, d)
            break
    if text_en_obj is None:
        print('[ERROR] TextEN TextAsset が見つかりません'); return False
    obj, d = text_en_obj
    raw_json = bytes(d.m_Script).decode('utf-8') if not isinstance(d.m_Script, str) else d.m_Script
    json_obj = json.loads(raw_json)

    # 改行ロジック適用 (jp_linebreak v3 と同期)

    DIALOG_SEP = '\r\n'
    n_ov = n_fb = 0
    for entry in json_obj['data']:
        bi = entry.get('index')
        for si, stage in enumerate(entry.get('stage', [])):
            if not stage or not stage.get('valid'): continue
            for ti, t in enumerate(stage.get('text', [])):
                items = by_key.get((bi, si, ti), [])
                if not items: continue
                # 元の data を基準とし、line index 位置に JP を上書き。
                # 未翻訳の line index は EN のまま残す。これにより
                # 翻訳に欠番がある場合に JP→EN の重複表示が起きないようにする。
                orig_data = t.get('data', '')
                orig_lines = orig_data.split(DIALOG_SEP) if orig_data else []
                parts = list(orig_lines)
                overridden = set()
                for it in items:
                    li = it['line']
                    jp_norm = apply_break_rules(it['jp'])
                    dlg = jp_norm.replace('\n', ' ')
                    new_line = f"{it['speaker']};{it['sprite']};{dlg}"
                    while len(parts) <= li:
                        parts.append('')
                    parts[li] = new_line
                    overridden.add(li)
                    n_ov += 1
                # 上書きされなかったスロットで非空のものを EN fallback としてカウント
                for i, p in enumerate(parts):
                    if i not in overridden and p:
                        n_fb += 1
                t['data'] = DIALOG_SEP.join(parts)

    out_json = json.dumps(json_obj, ensure_ascii=False, indent=2)
    print(f'  Story: {n_ov} JP overrides, {n_fb} EN fallbacks ({len(out_json)} chars)')
    if dry_run: return True
    d.m_Script = out_json
    d.save()
    with open(tgt, 'wb') as f:
        f.write(env.file.save())
    return True


# ========== UI Asset 注入 (sf_rewriter 経由) ==========
def inject_ui_assets(game_dir: Path, dry_run=False):
    with open(DATA / 'asset_mappings.json', encoding='utf-8') as f:
        mappings = json.load(f)
    data_dir = game_dir / 'InternetGeneration_Data'

    # ファイル別グループ
    by_file = {}
    for m in mappings:
        for occ in m['occurrences']:
            by_file.setdefault(occ['file'], []).append({
                'path_id': occ['path_id'],
                'pos': occ['en_pos'],
                'en': m['en'], 'jp': m['jp'],
            })

    for file_key, items in by_file.items():
        # file_key may end in .bak (from extractor) - normalize
        actual_name = file_key.replace('.bak','')
        tgt = data_dir / actual_name
        if not tgt.exists():
            print(f'  Skip {actual_name}: not present'); continue

        env_cur = UnityPy.load(str(tgt))
        with open(tgt, 'rb') as f:
            cur_raw = f.read()
        obj_by_pid = {o.path_id: o for o in env_cur.objects}
        objects_meta = [(o.path_id, o.byte_start, o.byte_size) for o in env_cur.objects]

        per_obj = {}
        for it in items:
            per_obj.setdefault(it['path_id'], []).append(it)

        new_blobs = {}
        ok = miss = 0
        for pid, its in per_obj.items():
            obj = obj_by_pid.get(pid)
            if not obj:
                miss += len(its); continue
            blob = bytes(cur_raw[obj.byte_start:obj.byte_start + obj.byte_size])
            for it in sorted(its, key=lambda x: -x['pos']):
                new_blob, err = patch_object_blob_to(blob, it['en'], it['jp'], None)
                if new_blob is None:
                    miss += 1; continue
                blob = new_blob; ok += 1
            new_blobs[pid] = blob

        if dry_run:
            print(f'  [DRY] {actual_name}: ok={ok} miss={miss}')
            continue
        new_size, delta = rewrite(str(tgt), str(tgt), new_blobs, objects_meta)
        print(f'  Asset {actual_name}: ok={ok} miss={miss} delta={delta:+d}')
    return True


# ========== DLL 注入 ==========
DLL_PATCHER_EXE = TOOLS / 'dll_patcher' / 'Patcher.exe'
THRESHOLD = 15

def inject_dll(game_dir: Path, dry_run=False):
    """同梱の Patcher.exe を呼ぶ。なければ dotnet run を試す。"""
    with open(DATA / 'dll_mappings.json', encoding='utf-8') as f:
        mapping = json.load(f)
    # 改行ロジック適用: 長い説明文 (商品説明: prefix 等) には apply_break_rules を通し、
    # \n を半角スペースに変換。短いラベル類はそのまま (apply_break_rules は短文では no-op)。
    # Rich Text タグ (<color=...>...</color> 等) を含む文字列は、改行ロジックがタグ内に
    # スペースを挿入してタグを破壊するリスクがあるため、原文ママとする (タグは Unity
    # TextMeshPro が解釈、必要に応じて自動折返し)。
    import re as _re_tag
    _RICH_TAG = _re_tag.compile(r'<[^>]+>')
    formatted = {}
    n_fmt = 0
    n_skip_tag = 0
    for en, jp in mapping.items():
        if _RICH_TAG.search(jp):
            # タグを含む文字列は改行ロジック対象外
            formatted[en] = jp.replace('\n', ' ')
            n_skip_tag += 1
            continue
        jp_norm = apply_break_rules(jp)
        if jp_norm != jp:
            n_fmt += 1
        formatted[en] = jp_norm.replace('\n', ' ')
    print(f'  DLL: {n_fmt}/{len(mapping)} 文字列に改行ロジック適用 (Rich Text タグ含み {n_skip_tag} 件は対象外)')
    mapping_path = TOOLS / '_ui_dll_mapping.json'
    if not dry_run:
        # dry-run 時はファイルを書き出さず、メモリ内のみで検証
        with open(mapping_path, 'w', encoding='utf-8') as f:
            json.dump(formatted, f, ensure_ascii=False, indent=2)

    data_dir = game_dir / 'InternetGeneration_Data'
    dll_in = data_dir / 'Managed' / 'Assembly-CSharp.dll.bak'
    dll_tmp = data_dir / 'Managed' / 'Assembly-CSharp.dll.tmp'
    dll_out = data_dir / 'Managed' / 'Assembly-CSharp.dll'

    if not DLL_PATCHER_EXE.exists():
        print(f'[ERROR] {DLL_PATCHER_EXE} がありません。.NET 8 SDK でビルドしてください。')
        return False

    # Step 1: ldstr 置換 (ui mode)
    cmd1 = [str(DLL_PATCHER_EXE), 'ui', str(dll_in), str(dll_tmp), str(mapping_path)]
    if dry_run:
        print(f'  [DRY] {cmd1} (mapping ファイルは書き出さない)')
    else:
        r = subprocess.run(cmd1, capture_output=True, text=True)
        print(r.stdout[-500:] if len(r.stdout) > 500 else r.stdout)
        if r.returncode != 0:
            print(r.stderr); return False
    # Step 2: threshold (28→15)
    cmd2 = [str(DLL_PATCHER_EXE), 'threshold', str(dll_tmp), str(dll_out), str(THRESHOLD)]
    if dry_run:
        print(f'  [DRY] {cmd2}')
    else:
        r = subprocess.run(cmd2, capture_output=True, text=True)
        print(r.stdout[-300:] if len(r.stdout) > 300 else r.stdout)
        if r.returncode != 0:
            print(r.stderr); return False
        try: dll_tmp.unlink()
        except OSError: pass
    return True


# ========== 出力フック (GUI 連携用) ==========
# GUI 等から呼ぶ際に install()/uninstall() に output_fn= を渡すと、内部の
# print() 出力をすべて指定関数に流せる。デフォルトは標準 print。
_OUTPUT = print
def _set_output(fn):
    """patcher 内部の出力先を切り替える。GUI コールバック等を渡す。"""
    global _OUTPUT, print
    _OUTPUT = fn
    # 既存の inject_* / restore_* が直接 print を呼んでいるため上書きしてしまう。
    # モジュール内のローカル名 print を差し替えることで、関数群の print 呼び出しを
    # すべてキャプチャできる (Python の名前解決順序による)。
    import builtins
    if fn is print:  # restore default
        try: del globals()['print']
        except KeyError: pass
    else:
        globals()['print'] = fn


# ========== 公開 API (CLI / GUI 共通) ==========
def install(game_dir, dry_run=False, force=False, output_fn=None):
    """ゲームに日本語化パッチを適用する。

    Args:
        game_dir: str or Path - ゲームインストール先 (省略時は自動検出)
        dry_run: True なら検証のみ実施
        force: True ならゲーム起動中チェックを無視
        output_fn: 出力コールバック (str を 1 引数取る callable)。
                   None なら print。GUI ログ表示に使用。

    Returns:
        (success: bool, message: str)
    """
    if output_fn is not None:
        _set_output(output_fn)
    try:
        if is_game_running() and not force and not dry_run:
            _OUTPUT('[ERROR] InternetGeneration.exe が起動中です。')
            _OUTPUT('  ゲームを完全に終了してから再実行してください。')
            return False, 'game is running'

        game = Path(game_dir) if game_dir else find_game()
        if not game or not game.exists():
            _OUTPUT('[ERROR] ゲームインストール先が見つかりません。')
            return False, 'game directory not found'
        _OUTPUT(f'Game: {game}')

        _OUTPUT('--- バックアップ確認 ---')
        if not ensure_backup(game):
            return False, 'backup failed'

        _OUTPUT('\n--- DLL パッチ ---')
        if not inject_dll(game, dry_run): return False, 'DLL inject failed'

        _OUTPUT('\n--- Story 翻訳注入 ---')
        if not inject_story(game, dry_run): return False, 'Story inject failed'

        _OUTPUT('\n--- UI Asset 翻訳注入 ---')
        if not inject_ui_assets(game, dry_run): return False, 'Asset inject failed'

        _OUTPUT('\n=== 日本語化完了 ===')
        _OUTPUT('Steam から Internet Generation を起動して日本語表示を確認してください。')
        return True, 'ok'
    finally:
        if output_fn is not None:
            _set_output(print)


def uninstall(game_dir, output_fn=None):
    """`.bak` からゲームを元の状態に戻す。

    Returns: (success: bool, message: str)
    """
    if output_fn is not None:
        _set_output(output_fn)
    try:
        game = Path(game_dir) if game_dir else find_game()
        if not game or not game.exists():
            _OUTPUT('[ERROR] ゲームインストール先が見つかりません。')
            return False, 'game directory not found'
        _OUTPUT(f'Game: {game}')
        _OUTPUT('--- アンインストール ---')
        restore_from_backup(game)
        _OUTPUT('完了。')
        return True, 'ok'
    finally:
        if output_fn is not None:
            _set_output(print)


# ========== ゲームプロセス検出 ==========
def is_game_running():
    """InternetGeneration.exe が起動中なら True を返す。起動中パッチによる
    ファイル破損を防ぐためのガード。"""
    try:
        if os.name == 'nt':
            r = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq InternetGeneration.exe', '/NH'],
                               capture_output=True, text=True, timeout=10)
            return 'InternetGeneration.exe' in r.stdout
    except Exception:
        pass
    return False


# ========== メイン ==========
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--game', help='ゲームインストール先 (省略時は自動探索)')
    ap.add_argument('--uninstall', action='store_true', help='.bak から復元')
    ap.add_argument('--dry-run', action='store_true', help='検証のみ、ファイル書き換えない')
    ap.add_argument('--force', action='store_true', help='ゲーム起動中チェックを無視')
    args = ap.parse_args()

    if is_game_running() and not args.force and not args.dry_run:
        print('[ERROR] InternetGeneration.exe が起動中です。')
        print('  ゲームを完全に終了してから再実行してください。')
        print('  (Steam クライアントで Internet Generation を Stop してください)')
        print('  どうしても起動中に実行したい場合は --force を指定。')
        sys.exit(10)

    game = Path(args.game) if args.game else find_game()
    if not game or not game.exists():
        print('[ERROR] Internet Generation のインストール先が見つかりません。--game で指定してください。')
        sys.exit(1)
    print(f'Game: {game}')

    if args.uninstall:
        print('--- アンインストール ---')
        restore_from_backup(game)
        print('完了。')
        return

    print('--- バックアップ確認 ---')
    if not ensure_backup(game):
        sys.exit(2)

    print('\n--- DLL パッチ ---')
    if not inject_dll(game, args.dry_run): sys.exit(3)

    print('\n--- Story 翻訳注入 ---')
    if not inject_story(game, args.dry_run): sys.exit(4)

    print('\n--- UI Asset 翻訳注入 ---')
    if not inject_ui_assets(game, args.dry_run): sys.exit(5)

    print('\n=== 日本語化完了 ===')
    print('Steam から Internet Generation を起動して日本語表示を確認してください。')
    print('（言語設定はゲーム内で English のままで OK）')


if __name__ == '__main__':
    main()
