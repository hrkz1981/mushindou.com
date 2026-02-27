"""
各銀行・クレカの CSV を (摘要, 金額, 月) の標準形式に変換する。

対応フォーマット:
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
# ユーティリティ
# ─────────────────────────────────────────────────────────────────────────────

def _to_num(val) -> float:
    """カンマ・全角数字・空文字を処理して float に変換する。失敗は 0。"""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return 0.0
    s = str(val).strip().replace(",", "").replace("，", "").replace("　", "")
    # 全角数字 → 半角
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


def _read_bytes(file_bytes: bytes, skiprows: int = 0) -> pd.DataFrame:
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

    # 三菱UFJ: 日付/摘要/出金金額/入金金額
    if {"摘要", "出金金額", "入金金額"}.issubset(nc) and "日付" in nc:
        return "mufg"

    # 住信SBI
    if {"摘要", "出金金額(円)", "入金金額(円)"}.issubset(nc):
        return "sbi"

    # ゆうちょ
    if {"お取り扱い日", "お取り扱い内容等", "お支払い金額", "お預かり金額"}.issubset(nc):
        return "yucho"

    # PayPay
    if {"取引日時", "店舗名/相手先", "金額(円)"}.issubset(nc):
        return "paypay"

    # 汎用クレカ（出金列だけある）
    if any(k in nc for k in ("利用金額", "金額", "支払金額")):
        if any(k in nc for k in ("利用店名", "利用店名・商品名", "店名", "摘要", "内容")):
            return "generic_card"

    # 汎用銀行（出金/入金が別列）
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
        # 振替（内部移動）はスキップ
        transfer = str(row.get(nc.get("振替", ""), "")).strip().upper()
        if transfer in ("TRUE", "1", "はい", "YES"):
            continue
        desc = str(row.get(nc.get("内容", ""), "")).strip()
        amt = _to_num(row.get(nc.get("金額（円）", ""), 0))
        if desc and amt != 0:
            rows.append({"摘要": desc, "金額": amt, "月": month})
    return pd.DataFrame(rows)


def _parse_credit(df: pd.DataFrame, month: int, desc_key: str, amt_key: str) -> pd.DataFrame:
    """クレカ汎用（支出のみ、金額を負にする）。"""
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


def _parse_bank(df: pd.DataFrame, month: int, desc_key: str, out_key: str, in_key: str) -> pd.DataFrame:
    """銀行汎用（出金/入金が別列）。"""
    nc = _normalize_cols(df)
    dc = nc.get(desc_key, "")
    oc = nc.get(out_key, "")
    ic_ = nc.get(in_key, "")
    rows = []
    for _, row in df.iterrows():
        desc = str(row.get(dc, "")).strip()
        out = _to_num(row.get(oc, 0))
        inc = _to_num(row.get(ic_, 0))
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
        amt = _to_num(row.get(nc.get("金額(円)", ""), 0))
        if desc and amt != 0:
            rows.append({"摘要": desc, "金額": -abs(amt), "月": month})
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# 公開エントリポイント
# ─────────────────────────────────────────────────────────────────────────────

def parse_csv(file_bytes: bytes, fmt_key: str, month: int) -> pd.DataFrame:
    """
    ファイルバイトとフォーマットキーを受け取り、
    標準形式 DataFrame (摘要 / 金額 / 月) を返す。
    """
    df = _read_bytes(file_bytes)

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

    if fmt_key == "generic_card":
        nc = set(_normalize_cols(df).keys())
        desc_k = next((k for k in ("利用店名・商品名", "利用店名", "店名", "摘要", "内容") if k in nc), "")
        amt_k  = next((k for k in ("利用金額", "金額", "支払金額") if k in nc), "")
        if desc_k and amt_k:
            return _parse_credit(df, month, desc_k, amt_k)

    if fmt_key == "generic_bank":
        nc = _normalize_cols(df)
        nc_set = set(nc.keys())
        desc_k = next((k for k in ("摘要", "内容", "取引内容") if k in nc_set), "")
        out_k  = next((k for k in nc_set if "出金" in k), "")
        in_k   = next((k for k in nc_set if "入金" in k), "")
        if desc_k:
            return _parse_bank(df, month, desc_k, out_k, in_k)

    return pd.DataFrame(columns=["摘要", "金額", "月"])


def load_and_detect(file_bytes: bytes) -> tuple[pd.DataFrame, str]:
    """CSV を読み込んでフォーマットを自動検出し (生DF, フォーマットキー) を返す。"""
    df = _read_bytes(file_bytes)
    fmt = detect_format(df)
    return df, fmt
