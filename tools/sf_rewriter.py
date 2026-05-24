"""
SerializedFile (Unity v22 / 2021.3) を手動で書き換えるユーティリティ。

機能:
  - 指定 path_id の MonoBehaviour のデータバイト列を任意長で差し替え可能
  - オブジェクトテーブルのエントリ (byte_start_relative_LE, byte_size_LE) を再計算
  - 後続オブジェクトの byte_start を delta だけシフト
  - ファイルヘッダの file_size を更新

レイアウト前提:
  - ヘッダ先頭 20 バイト:
    bytes  0..3  = 0 placeholder (旧 metadata_size 32bit)
    bytes  4..7  = 0 placeholder (旧 file_size 32bit)
    bytes  8..11 = version (BE u32)
    bytes 12..15 = 0 placeholder (旧 data_offset 32bit)
    byte  16     = endianness flag (data section の)
    bytes 17..19 = reserved
  - 拡張ヘッダ:
    bytes 20..23 = metadata_size (BE u32)
    bytes 24..31 = file_size (BE u64)
    bytes 32..39 = data_offset (BE u64)
    bytes 40..47 = unknown / reserved
  - メタデータ内のオブジェクトテーブルエントリ (各ヘッダオフセットは
    UnityPy が把握しているので、UnityPy 経由で位置を特定する):
    u64 path_id (LE) | u64 byte_start_relative (LE) | u32 byte_size (LE) | u32 type_id (LE)

スコープ:
  - 同 SerializedFile 内の複数 MonoBehaviour のリサイズに対応
  - サイズが減ることも増えることも可能
  - data_offset 自体は変更しない (メタデータサイズが変わる場合のみ必要だが、
    今回はメタデータは触らない=オブジェクト table のエントリ値だけ更新)
"""
import struct
from typing import Dict


def _find_object_entry_offsets(data: bytes, data_offset: int, objects: list) -> Dict[int, int]:
    """各 path_id -> オブジェクトテーブルエントリ先頭のファイルオフセットを返す。
    objects は [(path_id, byte_start_abs, byte_size), ...]"""
    entries = {}
    for pid, bs_abs, sz in objects:
        bs_rel = bs_abs - data_offset
        bs_bytes = struct.pack('<Q', bs_rel)
        sz_bytes = struct.pack('<I', sz)
        idx = -1
        while True:
            idx = data.find(bs_bytes, idx+1, data_offset)
            if idx < 0:
                break
            if data[idx+8:idx+12] == sz_bytes:
                # 前 8 バイトが path_id か確認
                pid_bytes = struct.pack('<q', pid)
                if data[idx-8:idx] == pid_bytes:
                    entries[pid] = idx - 8  # エントリ先頭 = path_id 位置
                    break
        if pid not in entries:
            raise KeyError(f'Object entry not found for path_id={pid}')
    return entries


def rewrite(src_path: str, dst_path: str, new_blobs: Dict[int, bytes], objects: list):
    """src_path を読み込み、new_blobs[pid] が指定されている path_id のデータを
    そのバイト列に差し替えて dst_path に書き出す。
    objects は UnityPy から取得した [(path_id, byte_start_abs, byte_size), ...] のリスト。
    """
    with open(src_path, 'rb') as f:
        d = bytearray(f.read())

    # ヘッダ読み取り
    data_offset = struct.unpack_from('>Q', d, 32)[0]
    file_size = struct.unpack_from('>Q', d, 24)[0]

    # path_id -> エントリオフセット
    entry_offsets = _find_object_entry_offsets(bytes(d), data_offset, objects)

    # オブジェクト byte_start 順にソート
    objects_sorted = sorted(objects, key=lambda x: x[1])

    # 各オブジェクトの新サイズと累積デルタを計算
    cumulative_delta = 0
    out_data_parts = []  # 順次データ部分を構築
    prev_end_abs = data_offset  # 直前の data 部終端
    # 元のデータ部分から、各オブジェクト境界で切って差し替え
    for pid, bs_abs, old_sz in objects_sorted:
        # 前のオブジェクト終端 〜 このオブジェクト開始までのギャップ (alignment 等) をコピー
        gap_start = prev_end_abs
        gap_end = bs_abs
        if gap_start < gap_end:
            out_data_parts.append(bytes(d[gap_start:gap_end]))

        # 新しい blob
        if pid in new_blobs:
            new_blob = new_blobs[pid]
            # 4-byte align: 末尾に \x00 を追加
            pad = (4 - (len(new_blob) % 4)) % 4
            new_blob_padded = new_blob + b'\x00' * pad
            new_sz = len(new_blob_padded)
        else:
            new_blob_padded = bytes(d[bs_abs:bs_abs+old_sz])
            new_sz = old_sz
        out_data_parts.append(new_blob_padded)

        # オブジェクトテーブルエントリを更新
        entry_off = entry_offsets[pid]
        # 新 byte_start_relative = 元 byte_start_relative + 累積 delta
        new_bs_rel = (bs_abs - data_offset) + cumulative_delta
        struct.pack_into('<Q', d, entry_off + 8, new_bs_rel)
        struct.pack_into('<I', d, entry_off + 16, new_sz)

        delta = new_sz - old_sz
        cumulative_delta += delta
        prev_end_abs = bs_abs + old_sz

    # 末尾の余白 (data section 終端まで)
    if prev_end_abs < file_size:
        out_data_parts.append(bytes(d[prev_end_abs:file_size]))

    # ヘッダ部分 (data_offset まで)
    header = bytes(d[:data_offset])
    new_data = b''.join(out_data_parts)
    new_file_size = data_offset + len(new_data)

    # ヘッダの file_size を更新
    header_mut = bytearray(header)
    struct.pack_into('>Q', header_mut, 24, new_file_size)

    with open(dst_path, 'wb') as f:
        f.write(bytes(header_mut))
        f.write(new_data)
    return new_file_size, cumulative_delta


def patch_object_blob_to(blob: bytes, en: str, jp: str, hint_pos: int = None):
    """blob 内の [int32 LE length][en_utf8] を [int32 LE new_len][jp_utf8] に置換し、
    新しい blob を返す。サイズは変わってよい。pad to 4-byte alignment 込みで返す。"""
    import struct as _s
    en_b = en.encode('utf-8')
    jp_b = jp.encode('utf-8')
    pat = _s.pack('<i', len(en_b)) + en_b
    if hint_pos is not None and blob[hint_pos:hint_pos+len(pat)] == pat:
        start = hint_pos
    else:
        start = blob.find(pat)
    if start < 0:
        return None, 'EN not found'
    old_payload = 4 + len(en_b)
    old_padded = (old_payload + 3) & ~3
    new_payload = 4 + len(jp_b)
    new_padded = (new_payload + 3) & ~3
    new_fragment = _s.pack('<i', len(jp_b)) + jp_b + b'\x00' * (new_padded - new_payload)
    return blob[:start] + new_fragment + blob[start + old_padded:], None
