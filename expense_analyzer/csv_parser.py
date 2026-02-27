"""
CSV / Excel / PDF の明細を (摘要, 金額, 月) の標準形式に変換する。

対応ファイル形式:
  .csv / .tsv / .txt  : テキスト（UTF-8, Shift-JIS 自動判定）
  .xlsx / .xls        : Excel（ヘッダー行を自動検出）
  .pdf                : PDF テーブル抽出（pdfplumber 使用）

対応金融機関フォーマット:
  moneyforward  : マネーフォワード ME（最も汎用的）
  rakuten       : 楽天カード
  smbc          : 三井住友カード
  mufg          : 三菱UFJ銀行
  sbi           : 住信SBIネット銀行
  aeon          : イオンカード
  yucho         : ゆうちょ銀行
  paypay        : PayPay（アプリ明細CSV）
  generic_card  : 汎用クレカ（利用日/店名/金額）
  generic_bank  : 汎用銀行（摘要/出金/入金）
"""
from __future__ import annotations

import io
import re
from typing import Optional

import pandas as pd


# ─────────────────────────────────────────────────────────────────────────────
# 公開名リスト（UI 選択肢）
# ─────────────────────────────────────────────────────────────────────────────

FORMAT_NAMES: dict[str, str] = {
    "moneyforward": "マネーフォワード ME",
    "rakuten": "楽天カード",
    "smbc": "三井住友カード",
    "mufg": "三菱UFJ銀行",
    "sbi": "住信SBIネット銀行",
    "aeon": "イオンカード",
    "yucho": "ゆうちょ銀行",
    "paypay": "PayPay（アプリ）",
    "generic_card": "汎用クレカ（自動）",
    "generic_bank": "汎用銀行（自動）",
    "unknown": "不明・手動マッピング",
}


# ─────────────────────────────────────────────────────────────────────────────
# ファイル種別検出
# ─────────────────────────────────────────────────────────────────────────────

def _detect_file_type(file_bytes: bytes, filename: str = "") -> str:
    """マジックバイト or 拡張子からファイル種別を返す。"""
    # PDF
    if file_bytes[:4] == b"%PDF":
        return "pdf"
    # ZIP 系（xlsx, xlsm, …）
    if file_bytes[:4] == b"PK\x03\x04":
        return "excel"
    # OLE2 系（xls）
    if file_bytes[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        return "excel"
    # 拡張子フォールバック
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if ext == "pdf":
        return "pdf"
    if ext in ("xlsx", "xls", "xlsm", "xlsb"):
        return "excel"
    return "csv"


# ─────────────────────────────────────────────────────────────────────────────
# ファイル読み込み
# ─────────────────────────────────────────────────────────────────────────────

def _read_csv(file_bytes: bytes, skiprows: int = 0) -> pd.DataFrame:
    """複数エンコーディングを試みて DataFrame を返す。"""
    for enc in ("utf-8-sig", "cp932", "utf-8", "shift_jis", "latin-1"):
        try:
            return pd.read_csv(
                io.BytesIO(file_bytes),
                encoding=enc,
                skiprows=skiprows,
                dtype=str,
                on_bad_lines="skip",
            )
        except Exception:
            continue
    raise ValueError("CSV を読み込めませんでした。文字コードを確認してください。")


def _read_excel(file_bytes: bytes) -> pd.DataFrame:
    """
    Excel ファイルを読み込む。
    - 先頭3シートを試し、最も行数の多いシートを採用
    - ヘッダー行（最初の非空行）を自動検出
    """
    best_df: pd.DataFrame = pd.DataFrame()

    for sheet_idx in range(3):
        try:
            # まずヘッダーなしで全体を読む
            raw = pd.read_excel(
                io.BytesIO(file_bytes),
                sheet_name=sheet_idx,
                header=None,
                dtype=str,
            )
            if raw.empty:
                continue

            # ヘッダー行の候補: 非空セルが 3 つ以上ある最初の行
            header_row = 0
            for i, row in raw.iterrows():
                cells = row.dropna()
                cells = cells[cells.astype(str).str.strip() != ""]
                if len(cells) >= 3:
                    header_row = int(i)
                    break

            df = pd.read_excel(
                io.BytesIO(file_bytes),
                sheet_name=sheet_idx,
                header=header_row,
                dtype=str,
            )
            df = df.dropna(how="all")
            df.columns = [str(c).strip() for c in df.columns]

            if len(df) > len(best_df):
                best_df = df

        except Exception:
            continue

    if best_df.empty:
        raise ValueError("Excel ファイルにデータが見つかりませんでした。")
    return best_df


def _read_pdf(file_bytes: bytes) -> pd.DataFrame:
    """
    PDF からテーブルを抽出する（pdfplumber 使用）。
    全ページのテーブルを結合し、最も行数の多いものを返す。
    """
    try:
        import pdfplumber
    except ImportError:
        raise ValueError(
            "PDF の読み込みには pdfplumber が必要です。\n"
            "pip install pdfplumber を実行してください。"
        )

    all_tables: list[pd.DataFrame] = []

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            # テーブル抽出（罫線ベース → テキストベースの順に試行）
            for strategy in (
                {"vertical_strategy": "lines", "horizontal_strategy": "lines"},
                {"vertical_strategy": "text", "horizontal_strategy": "text"},
            ):
                tables = page.extract_tables(strategy)
                if not tables:
                    continue

                for table in tables:
                    if not table or len(table) < 2:
                        continue

                    # 空行を除去して最初の行をヘッダーに
                    rows = [
                        [str(c).strip() if c else "" for c in row]
                        for row in table
                        if any(c for c in row)
                    ]
                    if len(rows) < 2:
                        continue

                    headers = rows[0]
                    # 空ヘッダーに連番を付ける
                    seen: dict[str, int] = {}
                    clean_headers = []
                    for h in headers:
                        h = h or "col"
                        if h in seen:
                            seen[h] += 1
                            h = f"{h}_{seen[h]}"
                        else:
                            seen[h] = 0
                        clean_headers.append(h)

                    try:
                        df = pd.DataFrame(rows[1:], columns=clean_headers)
                        df = df.dropna(how="all")
                        all_tables.append(df)
                    except Exception:
                        continue
                if all_tables:
                    break  # 最初の有効な strategy で OK

    if not all_tables:
        raise ValueError(
            "PDF からテーブルを抽出できませんでした。\n"
            "・テキスト形式（検索可能）の PDF かご確認ください\n"
            "・スキャン画像の PDF は非対応です\n"
            "・CSV または Excel 形式でダウンロードしてください"
        )

    # 最も行数の多いテーブルを採用
    return max(all_tables, key=len)


def _read_file(file_bytes: bytes, filename: str = "") -> pd.DataFrame:
    """ファイル種別を自動判定して DataFrame を返す。"""
    ftype = _detect_file_type(file_bytes, filename)
    if ftype == "pdf":
        return _read_pdf(file_bytes)
    if ftype == "excel":
        return _read_excel(file_bytes)
    return _read_csv(file_bytes)


# ─────────────────────────────────────────────────────────────────────────────
# ユーティリティ
# ─────────────────────────────────────────────────────────────────────────────

def _to_num(val) -> float:
    """カンマ・全角数字・空文字を処理して float に変換する。失敗は 0。"""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return 0.0
    s = str(val).strip().replace(",", "").replace("，", "").replace("　", "")
    s = s.translate(str.maketrans("０１２３４５６７８９．－", "0123456789.-"))
    s = re.sub(r"[^\d.\-]", "", s)
    try:
        return float(s) if s not in ("", "-", ".") else 0.0
    except ValueError:
        return 0.0


def _normalize_cols(df: pd.DataFrame) -> dict[str, str]:
    """列名を正規化した辞書 {正規化名: 元の列名} を返す。"""
    return {
        c.strip().replace("\u3000", "").replace(" ", "").replace("\ufeff", ""): c
        for c in df.columns
    }


# ─────────────────────────────────────────────────────────────────────────────
# フォーマット自動検出
# ─────────────────────────────────────────────────────────────────────────────

def detect_format(df: pd.DataFrame) -> str:
    nc = set(_normalize_cols(df).keys())

    if {"内容", "金額（円）", "保有金融機関"}.issubset(nc):
        return "moneyforward"
    if {"利用日", "利用店名・商品名", "利用金額"}.issubset(nc):
        return "rakuten"
    if {"ご利用日", "ご利用店名", "ご利用金額（円）"}.issubset(nc):
        return "smbc"
    if {"ご利用年月日", "ご利用店名・商品名", "ご利用金額"}.issubset(nc):
        return "aeon"
    if {"摘要", "出金金額", "入金金額"}.issubset(nc) and "日付" in nc:
        return "mufg"
    if {"摘要", "出金金額(円)", "入金金額(円)"}.issubset(nc):
        return "sbi"
    if {"お取り扱い日", "お取り扱い内容等", "お支払い金額", "お預かり金額"}.issubset(nc):
        return "yucho"
    if {"取引日時", "店舗名/相手先", "金額(円)"}.issubset(nc):
        return "paypay"
    if any(k in nc for k in ("利用金額", "金額", "支払金額")):
        if any(k in nc for k in ("利用店名", "利用店名・商品名", "店名", "摘要", "内容")):
            return "generic_card"
    if any("出金" in k for k in nc) and any("入金" in k for k in nc):
        return "generic_bank"

    return "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# フォーマット別パーサー
# ─────────────────────────────────────────────────────────────────────────────

def _parse_moneyforward(df: pd.DataFrame, month: int) -> pd.DataFrame:
    nc = _normalize_cols(df)
    rows = []
    for _, row in df.iterrows():
        transfer = str(row.get(nc.get("振替", ""), "")).strip().upper()
        if transfer in ("TRUE", "1", "はい", "YES"):
            continue
        desc = str(row.get(nc.get("内容", ""), "")).strip()
        amt = _to_num(row.get(nc.get("金額（円）", ""), 0))
        if desc and amt != 0:
            rows.append({"摘要": desc, "金額": amt, "月": month})
    return pd.DataFrame(rows)


def _parse_credit(df: pd.DataFrame, month: int, desc_key: str, amt_key: str) -> pd.DataFrame:
    nc = _normalize_cols(df)
    dc = nc.get(desc_key, "")
    ac = nc.get(amt_key, "")
    rows = []
    for _, row in df.iterrows():
        desc = str(row.get(dc, "")).strip()
        amt = _to_num(row.get(ac, 0))
        if desc and amt > 0:
            rows.append({"摘要": desc, "金額": -amt, "月": month})
    return pd.DataFrame(rows)


def _parse_bank(
    df: pd.DataFrame, month: int, desc_key: str, out_key: str, in_key: str
) -> pd.DataFrame:
    nc = _normalize_cols(df)
    dc  = nc.get(desc_key, "")
    oc  = nc.get(out_key, "")
    ic_ = nc.get(in_key, "")
    rows = []
    for _, row in df.iterrows():
        desc = str(row.get(dc, "")).strip()
        out  = _to_num(row.get(oc, 0))
        inc  = _to_num(row.get(ic_, 0))
        if desc:
            if out > 0:
                rows.append({"摘要": desc, "金額": -out, "月": month})
            if inc > 0:
                rows.append({"摘要": desc, "金額": inc, "月": month})
    return pd.DataFrame(rows)


def _parse_paypay(df: pd.DataFrame, month: int) -> pd.DataFrame:
    nc = _normalize_cols(df)
    rows = []
    for _, row in df.iterrows():
        desc = str(row.get(nc.get("店舗名/相手先", ""), "")).strip()
        amt  = _to_num(row.get(nc.get("金額(円)", ""), 0))
        if desc and amt != 0:
            rows.append({"摘要": desc, "金額": -abs(amt), "月": month})
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# 公開エントリポイント
# ─────────────────────────────────────────────────────────────────────────────

def parse_file(file_bytes: bytes, fmt_key: str, month: int, filename: str = "") -> pd.DataFrame:
    """
    ファイルバイト・フォーマットキー・月番号を受け取り
    標準形式 DataFrame (摘要 / 金額 / 月) を返す。
    CSV / Excel / PDF すべて対応。
    """
    df = _read_file(file_bytes, filename)

    if fmt_key == "moneyforward":
        return _parse_moneyforward(df, month)
    if fmt_key == "rakuten":
        return _parse_credit(df, month, "利用店名・商品名", "利用金額")
    if fmt_key == "smbc":
        return _parse_credit(df, month, "ご利用店名", "ご利用金額（円）")
    if fmt_key == "aeon":
        return _parse_credit(df, month, "ご利用店名・商品名", "ご利用金額")
    if fmt_key == "mufg":
        return _parse_bank(df, month, "摘要", "出金金額", "入金金額")
    if fmt_key == "sbi":
        return _parse_bank(df, month, "摘要", "出金金額(円)", "入金金額(円)")
    if fmt_key == "yucho":
        return _parse_bank(df, month, "お取り扱い内容等", "お支払い金額", "お預かり金額")
    if fmt_key == "paypay":
        return _parse_paypay(df, month)

    nc = _normalize_cols(df)
    nc_set = set(nc.keys())

    if fmt_key == "generic_card":
        desc_k = next((k for k in ("利用店名・商品名", "利用店名", "店名", "摘要", "内容") if k in nc_set), "")
        amt_k  = next((k for k in ("利用金額", "金額", "支払金額") if k in nc_set), "")
        if desc_k and amt_k:
            return _parse_credit(df, month, desc_k, amt_k)

    if fmt_key == "generic_bank":
        desc_k = next((k for k in ("摘要", "内容", "取引内容") if k in nc_set), "")
        out_k  = next((k for k in nc_set if "出金" in k), "")
        in_k   = next((k for k in nc_set if "入金" in k), "")
        if desc_k:
            return _parse_bank(df, month, desc_k, out_k, in_k)

    return pd.DataFrame(columns=["摘要", "金額", "月"])


# 後方互換エイリアス
parse_csv = parse_file


def load_and_detect(file_bytes: bytes, filename: str = "") -> tuple[pd.DataFrame, str]:
    """ファイルを読み込んでフォーマットを自動検出し (生DF, フォーマットキー) を返す。"""
    df  = _read_file(file_bytes, filename)
    fmt = detect_format(df)
    return df, fmt
