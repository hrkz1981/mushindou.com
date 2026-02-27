"""
achieve 範囲用 TSV 出力。

achieve の列構成: group | detail | enemy | average
  ・average = 月平均金額（スクリプト側で収入/不定支出は×12処理される）
"""
import pandas as pd


def generate_achieve_tsv(monthly_averages: dict[str, dict]) -> str:
    """
    Parameters
    ----------
    monthly_averages : {
        "グループ名": {
            "detail": str,
            "enemy":  str,
            "monthly_avg": float,
        }
    }

    Returns
    -------
    str : タブ区切りテキスト（Googleスプレッドシートへ貼り付け用）
    """
    rows = []
    for group, info in monthly_averages.items():
        rows.append({
            "group": group,
            "detail": info["detail"],
            "enemy": info["enemy"],
            "average": int(round(info["monthly_avg"])),
        })

    if not rows:
        return ""

    df = pd.DataFrame(rows, columns=["group", "detail", "enemy", "average"])
    return df.to_csv(sep="\t", index=False, header=False)
