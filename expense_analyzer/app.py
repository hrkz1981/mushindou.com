"""
支出管理アナライザー — Streamlit アプリ
5ステップ:
  1. プロフィール設定（価値観も設定）
  2. 明細入力（2ヶ月分）
  3. カテゴリ確認・未分類整理・価値観タグ付け
  4. 分析結果（全国平均比較・価値観マップ）
  5. エクスポート（シンプルCSV / achieve 形式）
"""
import io
import streamlit as st
import pandas as pd

from categorizer import categorize, RULES
from csv_parser import load_and_detect, parse_file, FORMAT_NAMES
from national_averages import (
    get_national_average,
    get_income_reference,
    PREFECTURE_LIST,
    OCCUPATION_LIST,
    FAMILY_TYPE_LIST,
    AGE_LIST,
)
from exporter import generate_achieve_tsv

# ─────────────────────────────────────────────────────────────────────────────
# ページ設定
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="支出管理アナライザー",
    page_icon="💰",
    layout="wide",
)

# ─────────────────────────────────────────────────────────────────────────────
# 定数
# ─────────────────────────────────────────────────────────────────────────────

INCOME_ENEMY = {"収入・予算内", "収入・予算外"}
INVEST_ENEMY = {"投資"}

ALL_ENEMIES = [
    "1 毎月・固定", "2 毎月・変動", "3 不定・固定", "4 不定・変動",
    "投資", "収入・予算内", "収入・予算外",
]

# 支出パターンの表示ラベル（UI用）
ENEMY_LABEL = {
    "1 毎月・固定":  "📌 毎月・固定",
    "2 毎月・変動":  "🔄 毎月・変動",
    "3 不定・固定":  "📅 不定期・固定",
    "4 不定・変動":  "🎲 不定期・変動",
    "投資":          "📈 投資・積立",
    "収入・予算内":  "💴 給与収入",
    "収入・予算外":  "💴 副業・雑収入",
}

# 支出パターンの説明（ヘルプ用）
ENEMY_HELP = {
    "1 毎月・固定": "毎月ほぼ同じ金額が出ていく支出（家賃・サブスク・通信費など）",
    "2 毎月・変動": "毎月使うが金額が変わる支出（食費・光熱費・日用品など）",
    "3 不定・固定": "不定期だが金額はほぼ同じ支出（年会費・車検・保険年払いなど）",
    "4 不定・変動": "不定期で金額も変わる支出（旅行・衣服・娯楽・外食など）",
    "投資":         "将来のための積立・投資（NISA・iDeCo・株式など）",
    "収入・予算内": "メインの収入（給与・賞与など）",
    "収入・予算外": "サブの収入（副業・雑収入・売却益など）",
}

VALUES_LIST = [
    "(未設定)",
    "🏥 健康・美容",
    "👨‍👩‍👧 家族・子育て",
    "📚 自己成長・学習",
    "🎮 娯楽・趣味",
    "✈️ 体験・思い出",
    "💼 仕事・キャリア",
    "🏠 生活・安心",
    "💰 節約・資産形成",
    "🤝 人とのつながり",
]

# ─────────────────────────────────────────────────────────────────────────────
# Session state 初期化
# ─────────────────────────────────────────────────────────────────────────────

DEFAULTS: dict = {
    "step": 1,
    "profile": {},
    "num_months": 2,
    "raw_df": None,
    "cat_df": None,
    "satisfaction": {},
    "value_tags": {},   # {group_name: value_label}
}

for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────────────────────────────────────
# 共通ヘッダー
# ─────────────────────────────────────────────────────────────────────────────

STEP_NAMES = [
    "① プロフィール",
    "② 明細入力",
    "③ カテゴリ確認",
    "④ 分析結果",
    "⑤ エクスポート",
]


def show_header() -> None:
    st.title("💰 支出管理アナライザー")
    st.caption("全国平均 × あなたのプロフィールで、支出の適正度をチェックします")

    cols = st.columns(len(STEP_NAMES))
    for i, (col, name) in enumerate(zip(cols, STEP_NAMES)):
        with col:
            n = i + 1
            current = st.session_state.step
            if n < current:
                st.success(name)
            elif n == current:
                st.info(f"**{name}**")
            else:
                st.markdown(
                    f"<p style='color:gray;text-align:center'>{name}</p>",
                    unsafe_allow_html=True,
                )
    st.divider()


# ─────────────────────────────────────────────────────────────────────────────
# ステップ 1 — プロフィール設定
# ─────────────────────────────────────────────────────────────────────────────

def step1_profile() -> None:
    st.header("プロフィール設定")
    st.markdown("入力内容は全国平均の補正と価値観マップにのみ使用します。")

    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("基本情報")
        occupation = st.selectbox("職種", OCCUPATION_LIST)
        age = st.selectbox("年齢層", AGE_LIST)
        family = st.selectbox("家族構成", FAMILY_TYPE_LIST)
        prefecture = st.selectbox("居住都道府県", PREFECTURE_LIST)

        st.subheader("明細の月数")
        num_months = st.radio(
            "入力する明細は何ヶ月分ですか？",
            options=[1, 2],
            index=1,
            horizontal=True,
            help="2ヶ月の平均を使うと精度が上がります",
        )

    with col_r:
        st.subheader("収入情報")
        ref = get_income_reference(occupation, age)
        st.info(
            f"📊 **参考情報**\n\n"
            f"- 職種平均（手取り概算）: 月 **{ref['occupation_monthly']:,} 円**\n"
            f"- 年齢層平均（手取り概算）: 月 **{ref['age_monthly']:,} 円**\n"
            f"- 総合参考値: 月 **{ref['reference']:,} 円**"
        )

        use_actual = st.checkbox("実際の手取り月収を入力する（より精度が上がります）")
        if use_actual:
            monthly_income = st.number_input(
                "手取り月収（円）",
                min_value=50_000,
                max_value=5_000_000,
                value=ref["reference"],
                step=10_000,
                format="%d",
            )
        else:
            monthly_income = ref["reference"]
            st.caption(f"参考値を使用: {monthly_income:,} 円/月")

        st.divider()

        st.subheader("💫 大切にしていること（任意）")
        st.caption(
            "支出を振り返るとき「自分の価値観に合っているか」を確認できます。\n"
            "後から変更もできます。"
        )
        priority_values = st.multiselect(
            "大切にしていること（複数選択可）",
            options=VALUES_LIST[1:],  # "(未設定)" を除く
            default=st.session_state.profile.get("priority_values", []),
            help="ここで選んだ価値観は④分析結果の「価値観マップ」で ⭐ 表示されます",
        )

    st.divider()
    if st.button("次へ →", type="primary"):
        st.session_state.profile = {
            "occupation": occupation,
            "age": age,
            "family": family,
            "prefecture": prefecture,
            "monthly_income": monthly_income,
            "priority_values": priority_values,
        }
        st.session_state.num_months = num_months
        st.session_state.step = 2
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# ステップ 2 — 明細入力（CSV アップロード or 手動入力）
# ─────────────────────────────────────────────────────────────────────────────

def _proceed_to_step3(combined: pd.DataFrame) -> None:
    """DataFrame を受け取りカテゴリ付与してステップ3へ。"""
    clean = combined[combined["摘要"].astype(str).str.strip() != ""].copy()
    clean["group"]  = clean["摘要"].apply(lambda x: categorize(str(x)).group)
    clean["detail"] = clean["摘要"].apply(lambda x: categorize(str(x)).detail)
    clean["enemy"]  = clean["摘要"].apply(lambda x: categorize(str(x)).enemy)
    st.session_state.raw_df = clean[["摘要", "金額", "月"]].copy()
    st.session_state.cat_df = clean.reset_index(drop=True)
    st.session_state.step = 3
    st.rerun()


def _tab_upload(nm: int) -> None:
    """CSV アップロードタブの中身。"""
    st.markdown(
        f"クレカ・銀行・PayPay など **{nm}ヶ月分** の明細をまとめてアップロードしてください。  \n"
        "複数ファイル・複数金融機関を一度に投げられます。"
    )

    with st.expander("🏦 対応フォーマット"):
        st.markdown("\n".join(f"- {v}" for v in FORMAT_NAMES.values() if v != "不明・手動マッピング"))

    uploaded = st.file_uploader(
        "明細ファイルをドラッグ＆ドロップ（複数可）",
        type=["csv", "tsv", "txt", "xlsx", "xls", "pdf"],
        accept_multiple_files=True,
        key="csv_uploader",
    )

    if not uploaded:
        st.info("ファイルをアップロードすると自動でフォーマットを判定します。")
        return

    all_rows: list[pd.DataFrame] = []
    has_error = False

    for i, uf in enumerate(uploaded):
        st.divider()
        st.subheader(f"📄 {uf.name}")
        file_bytes = uf.read()

        try:
            raw_df, detected_fmt = load_and_detect(file_bytes, uf.name)
        except Exception as e:
            st.error(f"読み込みエラー: {e}")
            has_error = True
            continue

        fmt_keys = [k for k in FORMAT_NAMES if k != "unknown"]
        if detected_fmt != "unknown":
            st.success(f"✓ 自動検出: **{FORMAT_NAMES[detected_fmt]}**")
            default_idx = fmt_keys.index(detected_fmt)
        else:
            st.warning("フォーマットを自動検出できませんでした。手動で選択してください。")
            default_idx = 0

        selected_fmt = st.selectbox(
            "フォーマットを確認・変更",
            options=fmt_keys,
            format_func=lambda k: FORMAT_NAMES[k],
            index=default_idx,
            key=f"fmt_{i}_{uf.name}",
        )

        try:
            parsed = parse_file(file_bytes, selected_fmt, month=i + 1, filename=uf.name)
        except Exception as e:
            st.error(f"パースエラー: {e}")
            with st.expander("生データ（先頭5行）"):
                st.dataframe(raw_df.head(5))
            has_error = True
            continue

        if parsed.empty:
            st.warning("明細データが取得できませんでした。フォーマットを変更してみてください。")
            with st.expander("生データ（先頭5行）"):
                st.dataframe(raw_df.head(5))
            has_error = True
            continue

        st.success(f"{len(parsed):,} 件取得")
        with st.expander(f"プレビュー（先頭 10 件）"):
            st.dataframe(parsed.head(10), use_container_width=True)

        all_rows.append(parsed)

    st.divider()
    c1, c2 = st.columns([1, 5])
    with c1:
        if st.button("← 戻る", key="back_upload"):
            st.session_state.step = 1
            st.rerun()
    with c2:
        total = sum(len(r) for r in all_rows)
        btn_label = f"カテゴリ自動分類 → （{total:,} 件）" if all_rows else "カテゴリ自動分類 →"
        if all_rows and st.button(btn_label, type="primary", key="next_upload"):
            _proceed_to_step3(pd.concat(all_rows, ignore_index=True))


def _tab_manual(nm: int) -> None:
    """手動入力タブの中身。"""
    st.markdown(
        "**金額は支出をマイナス、収入をプラス**で入力します（例: -5000、+280000）。  \n"
        f"「月」列は 1〜{nm} で入力してください。"
    )

    with st.expander("💡 入力例"):
        st.markdown(
            "| 摘要 | 金額 | 月 |\n"
            "|------|------|----|\n"
            "| スーパーXX | -8500 | 1 |\n"
            "| 電気代 | -7200 | 1 |\n"
            "| 給与 | 280000 | 1 |\n"
            "| Netflix | -1490 | 1 |\n"
            "| スーパーXX | -9200 | 2 |\n"
            "| 電気代 | -6800 | 2 |"
        )

    init_df = (
        st.session_state.raw_df.copy()
        if st.session_state.raw_df is not None
        else pd.DataFrame({"摘要": [""] * 15, "金額": [0] * 15, "月": [1] * 15})
    )

    edited = st.data_editor(
        init_df,
        num_rows="dynamic",
        column_config={
            "摘要": st.column_config.TextColumn("摘要（店名・内容）", width="large"),
            "金額": st.column_config.NumberColumn("金額（円）", format="%d"),
            "月": st.column_config.NumberColumn("月", min_value=1, max_value=nm, format="%d"),
        },
        use_container_width=True,
        height=420,
        key="input_editor",
    )

    st.divider()
    c1, c2 = st.columns([1, 5])
    with c1:
        if st.button("← 戻る", key="back_manual"):
            st.session_state.step = 1
            st.rerun()
    with c2:
        if st.button("カテゴリ自動分類 →", type="primary", key="next_manual"):
            clean = edited[
                (edited["摘要"].astype(str).str.strip() != "") &
                (edited["金額"].astype(float) != 0)
            ].copy()
            if len(clean) == 0:
                st.error("明細が1件も入力されていません。")
                return
            _proceed_to_step3(clean)


def step2_input() -> None:
    nm = st.session_state.num_months
    st.header("明細入力")

    tab_upload, tab_manual = st.tabs(["📂 ファイルアップロード", "✏️ 手動入力"])
    with tab_upload:
        _tab_upload(nm)
    with tab_manual:
        _tab_manual(nm)


# ─────────────────────────────────────────────────────────────────────────────
# ステップ 3 — カテゴリ確認・未分類整理・価値観タグ付け
# ─────────────────────────────────────────────────────────────────────────────

def _section_uncategorized_fix(df: pd.DataFrame) -> None:
    """
    未分類アイテムの一括整理UI。
    修正がある場合は session_state.cat_df を更新して rerun する。
    """
    uncats = df[df["group"] == "未分類"]
    if uncats.empty:
        return

    count = len(uncats)
    unique_descs = (
        uncats.groupby("摘要")
        .agg(件数=("金額", "count"), 合計=("金額", "sum"))
        .reset_index()
        .sort_values("件数", ascending=False)
    )

    with st.expander(
        f"⚠️ 未分類が **{count} 件** あります — まとめて整理しましょう（任意）",
        expanded=True,
    ):
        st.markdown(
            "**グループ名**（自由記入）と **支出パターン** を入力して **「一括適用」** を押してください。  \n"
            "入力しない行はスキップされます。"
        )
        with st.expander("支出パターンの選び方"):
            for code, desc in ENEMY_HELP.items():
                if code in ("収入・予算内", "収入・予算外", "投資"):
                    continue
                label = ENEMY_LABEL.get(code, code)
                st.markdown(f"- **{label}** — {desc}")

        grp_inputs = {}
        enemy_inputs = {}

        for _, row in unique_descs.iterrows():
            desc = str(row["摘要"])
            total_amt = int(row["合計"])
            cnt = int(row["件数"])
            safe_key = desc[:40].replace(" ", "_")

            c1, c2, c3 = st.columns([3, 3, 3])
            with c1:
                st.markdown(f"**{desc}**")
                st.caption(f"{cnt}件 / 合計 {total_amt:,}円")
            with c2:
                grp_inputs[desc] = st.text_input(
                    "グループ名",
                    placeholder="例: 食費（外食）",
                    key=f"uc_grp_{safe_key}",
                    label_visibility="collapsed",
                )
            with c3:
                enemy_inputs[desc] = st.selectbox(
                    "種別",
                    options=ALL_ENEMIES,
                    key=f"uc_enemy_{safe_key}",
                    label_visibility="collapsed",
                )

        if st.button("✅ 未分類を一括適用", type="secondary", key="apply_uncat"):
            new_df = st.session_state.cat_df.copy()
            changed = 0
            for desc, grp in grp_inputs.items():
                grp = grp.strip()
                if grp:
                    mask = new_df["摘要"] == desc
                    new_df.loc[mask, "group"] = grp
                    new_df.loc[mask, "detail"] = grp
                    new_df.loc[mask, "enemy"] = enemy_inputs.get(desc, "4 不定・変動")
                    changed += 1
            if changed:
                st.session_state.cat_df = new_df.reset_index(drop=True)
                st.success(f"✅ {changed} 種類の摘要を分類しました")
                st.rerun()
            else:
                st.info("グループ名を入力してください。")


def _section_value_tags(grouped: pd.DataFrame) -> None:
    """
    価値観タグ付けUI。
    各支出グループに「なぜ使っているか」の価値観をひも付ける。
    """
    expense_groups = grouped[~grouped["enemy"].isin(INCOME_ENEMY | INVEST_ENEMY)]
    if expense_groups.empty:
        return

    st.subheader("💫 価値観タグ付け")
    st.markdown(
        "各支出グループに「なぜ使っているか」の価値観をタグ付けします。  \n"
        "④分析結果で **価値観マップ** として確認できます。"
    )

    value_tags = st.session_state.value_tags.copy()

    cols = st.columns(2)
    for idx, (_, row) in enumerate(expense_groups.iterrows()):
        grp = row["group"]
        monthly = row["monthly_avg"]
        current_val = value_tags.get(grp, "(未設定)")
        safe_key = grp[:40].replace(" ", "_")

        with cols[idx % 2]:
            with st.container(border=True):
                c1, c2 = st.columns([2, 3])
                with c1:
                    st.write(f"**{grp}**")
                    st.caption(f"月 {monthly:,.0f}円")
                with c2:
                    val_idx = VALUES_LIST.index(current_val) if current_val in VALUES_LIST else 0
                    value_tags[grp] = st.selectbox(
                        "価値観",
                        options=VALUES_LIST,
                        index=val_idx,
                        key=f"vtag_{safe_key}",
                        label_visibility="collapsed",
                    )

    st.session_state.value_tags = value_tags


def step3_review() -> None:
    st.header("カテゴリ確認・価値観タグ付け")
    df = st.session_state.cat_df.copy()
    nm = st.session_state.num_months

    # ── 未分類の整理 ──────────────────────────────────────────
    _section_uncategorized_fix(df)

    # ── トランザクション編集テーブル ──────────────────────────
    st.subheader("トランザクション一覧（カテゴリを修正できます）")

    with st.expander("💡 「支出パターン」の意味"):
        st.markdown(
            "支出パターンは **予算管理ツールとの連携** に使う分類です。  \n"
            "自動設定されているので、基本は変更不要です。"
        )
        cols = st.columns(2)
        items = list(ENEMY_HELP.items())
        for i, (code, desc) in enumerate(items):
            with cols[i % 2]:
                label = ENEMY_LABEL.get(code, code)
                st.markdown(f"**{label}**  \n{desc}")

    edited = st.data_editor(
        df[["摘要", "金額", "月", "group", "detail", "enemy"]],
        column_config={
            "摘要": st.column_config.TextColumn("摘要", disabled=True, width="medium"),
            "金額": st.column_config.NumberColumn("金額（円）", format="%d", disabled=True),
            "月": st.column_config.NumberColumn("月", disabled=True, width="small"),
            "group": st.column_config.TextColumn("グループ", width="medium"),
            "detail": st.column_config.TextColumn("詳細", width="medium"),
            "enemy": st.column_config.SelectboxColumn(
                "支出パターン",
                options=ALL_ENEMIES,
                width="medium",
                help="📌毎月固定=家賃等 🔄毎月変動=食費等 📅不定固定=年会費等 🎲不定変動=旅行等",
            ),
        },
        use_container_width=True,
        num_rows="fixed",
        height=380,
        key="cat_editor",
    )

    st.divider()

    # ── カテゴリ別サマリー + 満足度チェック ──────────────────
    st.subheader("カテゴリ別サマリー & 満足度設定")
    st.markdown(
        "支出が全国平均を超えていても **「納得している」** にチェックを入れるとOK扱いになります。"
    )

    grouped = (
        edited.groupby("group")
        .agg(total=("金額", "sum"), detail=("detail", "first"), enemy=("enemy", "first"))
        .reset_index()
    )
    grouped["monthly_avg"] = grouped["total"].abs() / nm

    satisfaction = st.session_state.satisfaction.copy()

    for _, row in grouped.iterrows():
        enemy = row["enemy"]
        if enemy in INCOME_ENEMY | INVEST_ENEMY:
            continue

        grp = row["group"]
        avg = row["monthly_avg"]
        safe_key = grp[:40].replace(" ", "_")

        c1, c2, c3 = st.columns([4, 2, 3])
        with c1:
            st.write(f"**{grp}**")
            friendly = ENEMY_LABEL.get(enemy, enemy)
            tip = ENEMY_HELP.get(enemy, "")
            st.caption(f"{friendly}  \n{tip}")
        with c2:
            st.metric("月平均", f"{avg:,.0f} 円")
        with c3:
            satisfied = st.checkbox(
                "この支出は納得している ✅",
                value=satisfaction.get(grp, False),
                key=f"sat_{safe_key}",
            )
            satisfaction[grp] = satisfied

    st.session_state.satisfaction = satisfaction

    st.divider()

    # ── 価値観タグ付け ────────────────────────────────────────
    _section_value_tags(grouped)

    st.divider()
    c1, c2 = st.columns([1, 5])
    with c1:
        if st.button("← 戻る"):
            st.session_state.step = 2
            st.rerun()
    with c2:
        if st.button("分析結果を見る →", type="primary"):
            st.session_state.cat_df = edited.reset_index(drop=True)
            st.session_state.step = 4
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# ステップ 4 — 分析結果
# ─────────────────────────────────────────────────────────────────────────────

def _status(ratio: float) -> tuple:
    """(アイコン, ラベル) を返す。"""
    if ratio <= 0.80:
        return "✅", f"余裕あり（平均の {ratio*100:.0f}%）"
    elif ratio <= 1.10:
        return "🟢", f"適正（平均の {ratio*100:.0f}%）"
    elif ratio <= 1.30:
        return "⚠️", f"やや多め（平均の {ratio*100:.0f}%）"
    else:
        return "🔴", f"超過（平均の {ratio*100:.0f}%）"


def _section_value_map(grouped: pd.DataFrame, nm: int, profile: dict, value_tags: dict) -> None:
    """
    価値観マップ：価値観タグ別に支出を集計し、
    優先価値観との一致度を可視化するセクション。
    """
    priority_values = profile.get("priority_values", [])
    expense_rows = grouped[~grouped["enemy"].isin(INCOME_ENEMY | INVEST_ENEMY)].copy()

    if expense_rows.empty:
        return

    expense_rows["value"] = expense_rows["group"].map(
        lambda g: value_tags.get(g, "(未設定)")
    )

    value_summary = (
        expense_rows.groupby("value")
        .agg(
            月支出合計=("monthly_avg", "sum"),
            グループ数=("group", "count"),
        )
        .reset_index()
        .sort_values("月支出合計", ascending=False)
    )

    total_expense = value_summary["月支出合計"].sum()

    st.subheader("💫 価値観マップ")
    st.markdown(
        "支出を「何のために使っているか」の価値観で集計しています。  \n"
        "⭐ は①プロフィールで選んだ優先価値観です。"
    )

    if not priority_values:
        st.caption("プロフィールで「大切にしていること」を設定すると ⭐ 表示が使えます")

    for _, row in value_summary.iterrows():
        val = row["value"]
        amt = row["月支出合計"]
        grp_count = row["グループ数"]
        pct = amt / total_expense if total_expense > 0 else 0

        is_priority = val in priority_values
        is_unset = val == "(未設定)"
        icon = "⭐" if is_priority else ("❓" if is_unset else "◆")

        with st.container(border=True):
            c1, c2, c3 = st.columns([4, 2, 3])
            with c1:
                label = f"{icon} **{val}**"
                if is_priority:
                    label += " ← 優先"
                st.markdown(label)
                # このvalueに属するグループを表示
                groups_in_val = expense_rows[expense_rows["value"] == val]["group"].tolist()
                st.caption("  ・".join(groups_in_val))
            with c2:
                st.metric("月支出", f"{amt:,.0f}円")
                st.caption(f"{pct*100:.1f}%")
            with c3:
                st.progress(min(pct, 1.0))

    # 優先価値観で未タグのものを警告
    unmatched_priorities = [v for v in priority_values if v not in value_summary["value"].values]
    if unmatched_priorities:
        st.info(
            "💡 以下の優先価値観に対応する支出カテゴリがタグ付けされていません：\n"
            + "、".join(unmatched_priorities)
        )

    # 未設定グループを表示
    unset_groups = expense_rows[expense_rows["value"] == "(未設定)"]["group"].tolist()
    if unset_groups:
        with st.expander(f"❓ 価値観未設定のグループ（{len(unset_groups)}件）"):
            for g in unset_groups:
                st.write(f"- {g}")
            st.caption("③カテゴリ確認 → 価値観タグ付け で設定できます")


def step4_analysis() -> None:
    st.header("分析結果")

    df = st.session_state.cat_df
    profile = st.session_state.profile
    nm = st.session_state.num_months
    satisfaction = st.session_state.satisfaction
    value_tags = st.session_state.value_tags

    grouped = (
        df.groupby("group")
        .agg(total=("金額", "sum"), detail=("detail", "first"), enemy=("enemy", "first"))
        .reset_index()
    )
    grouped["monthly_avg"] = grouped["total"].abs() / nm

    # ── プロフィールサマリー
    with st.expander("📊 使用したプロフィール"):
        p = profile
        st.markdown(
            f"| 項目 | 値 |\n"
            f"|------|----|\n"
            f"| 職種 | {p.get('occupation', '—')} |\n"
            f"| 年齢 | {p.get('age', '—')} |\n"
            f"| 家族構成 | {p.get('family', '—')} |\n"
            f"| 都道府県 | {p.get('prefecture', '—')} |\n"
            f"| 月収（手取り） | {p.get('monthly_income', 0):,} 円 |"
        )

    # ── 収入セクション
    income_rows = grouped[grouped["enemy"].isin(INCOME_ENEMY)]
    if not income_rows.empty:
        st.subheader("💴 収入")
        for _, r in income_rows.iterrows():
            c1, c2 = st.columns([4, 2])
            with c1:
                st.write(f"**{r['group']}** ({r['enemy']})")
            with c2:
                st.metric("月平均", f"{r['monthly_avg']:,.0f} 円")

    # ── 投資セクション
    invest_rows = grouped[grouped["enemy"].isin(INVEST_ENEMY)]
    if not invest_rows.empty:
        st.subheader("📈 投資・積立")
        for _, r in invest_rows.iterrows():
            c1, c2 = st.columns([4, 2])
            with c1:
                st.write(f"**{r['group']}**")
            with c2:
                st.metric("月額", f"{r['monthly_avg']:,.0f} 円")

    st.divider()

    # ── 支出分析（全国平均比較）
    st.subheader("💸 支出分析（全国平均比較）")
    expense_rows = grouped[~grouped["enemy"].isin(INCOME_ENEMY | INVEST_ENEMY)]

    total_user = 0
    total_national = 0
    issue_count = 0
    satisfied_count = 0

    for _, r in expense_rows.iterrows():
        grp = r["group"]
        avg = r["monthly_avg"]
        enemy = r["enemy"]
        satisfied = satisfaction.get(grp, False)

        nat_avg = get_national_average(
            category_name=grp,
            family_type=profile.get("family", ""),
            prefecture=profile.get("prefecture", ""),
            monthly_income=profile.get("monthly_income", 0),
            occupation=profile.get("occupation", ""),
            age=profile.get("age", ""),
        )

        total_user += avg
        if nat_avg:
            total_national += nat_avg

        if nat_avg is None:
            icon, label = "⬜", "比較データなし"
            color = "gray"
        elif satisfied:
            icon, label = "💙", "納得済み（OK）"
            color = "blue"
            satisfied_count += 1
        else:
            ratio = avg / nat_avg if nat_avg > 0 else 1.0
            icon, label = _status(ratio)
            if icon in ("⚠️", "🔴"):
                issue_count += 1
                color = "red" if icon == "🔴" else "orange"
            else:
                color = "green"

        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([3, 2, 2, 3])
            with c1:
                val_tag = value_tags.get(grp, "")
                tag_str = f"  `{val_tag}`" if val_tag and val_tag != "(未設定)" else ""
                st.write(f"{icon} **{grp}**{tag_str}")
                st.caption(ENEMY_LABEL.get(enemy, enemy))
            with c2:
                st.metric("あなた/月", f"{avg:,.0f} 円")
            with c3:
                if nat_avg:
                    st.metric("全国平均/月", f"{nat_avg:,.0f} 円")
                else:
                    st.write("—")
            with c4:
                if color == "red":
                    st.error(label)
                elif color == "orange":
                    st.warning(label)
                elif color == "blue":
                    st.info(label)
                elif nat_avg:
                    st.success(label)
                else:
                    st.caption(label)

    # ── 合計サマリー
    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("支出合計（月平均）", f"{total_user:,.0f} 円")
    with c2:
        if total_national > 0:
            delta = total_user - total_national
            st.metric(
                "全国平均合計（補正後）",
                f"{total_national:,.0f} 円",
                delta=f"{'超過' if delta > 0 else '節約'} {abs(delta):,.0f} 円",
                delta_color="inverse",
            )
    with c3:
        st.metric("注意項目 / 納得済み", f"{issue_count} 件 / {satisfied_count} 件")

    if issue_count == 0:
        st.success("✅ 全国平均を超過している項目はありません！")
    else:
        st.warning(f"⚠️ 全国平均を超過している項目が **{issue_count} 件** あります。")

    st.divider()

    # ── 価値観マップ
    _section_value_map(grouped, nm, profile, value_tags)

    st.divider()
    c1, c2 = st.columns([1, 5])
    with c1:
        if st.button("← 戻る"):
            st.session_state.step = 3
            st.rerun()
    with c2:
        if st.button("エクスポート →", type="primary"):
            st.session_state.step = 5
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# ステップ 5 — エクスポート
# ─────────────────────────────────────────────────────────────────────────────

def step5_export() -> None:
    st.header("エクスポート")

    df = st.session_state.cat_df
    nm = st.session_state.num_months
    value_tags = st.session_state.value_tags

    grouped = (
        df.groupby("group")
        .agg(total=("金額", "sum"), detail=("detail", "first"), enemy=("enemy", "first"))
        .reset_index()
    )
    grouped["monthly_avg"] = grouped["total"].abs() / nm
    grouped["value"] = grouped["group"].map(lambda g: value_tags.get(g, "(未設定)"))

    # ═════════════════════════════════════════
    # A) シンプルCSV（誰でも使える）
    # ═════════════════════════════════════════
    st.subheader("📊 シンプル分析データ（CSV）")
    st.caption("ExcelやGoogleスプレッドシートで開けます。特別な連携ツールは不要です。")

    export_df = grouped.rename(columns={
        "group": "グループ",
        "detail": "詳細",
        "enemy": "種別",
        "monthly_avg": "月平均金額（円）",
        "value": "価値観タグ",
        "total": "合計金額（円）",
    })[["グループ", "詳細", "種別", "月平均金額（円）", "価値観タグ"]].copy()
    export_df["月平均金額（円）"] = export_df["月平均金額（円）"].round(0).astype(int)

    st.dataframe(export_df, use_container_width=True)

    csv_bytes = export_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button(
        label="📥 CSVをダウンロード（Excel/スプレッドシートで開く）",
        data=csv_bytes,
        file_name="expense_summary.csv",
        mime="text/csv",
        type="primary",
    )

    st.divider()

    # ═════════════════════════════════════════
    # B) achieve 形式（Google Sheets 連携用）
    # ═════════════════════════════════════════
    with st.expander("🔧 Google Sheets 予算管理ツールと連携する（achieve 形式）"):
        st.markdown(
            """
**achieve 形式とは？**

このアプリは、Googleスプレッドシートで動作する専用の予算管理ツールと連携できます。
そのツールには `achieve` という名前付きセルがあり、以下の列構成でデータを貼り付けます：

| 列 | 内容 |
|----|------|
| group | カテゴリグループ名 |
| detail | 詳細名 |
| enemy | 種別（毎月固定・変動など） |
| average | 月平均金額 |

**貼り付け手順：**
1. 下のテキストを全選択（Ctrl+A）してコピー（Ctrl+C）
2. Googleスプレッドシートの `achieve` 範囲の **左上セル** をクリック
3. 貼り付け（Ctrl+V）
4. `switch` セルを TRUE にすると予算計画シートへ転記されます
            """
        )

        monthly_averages = {
            r["group"]: {
                "detail": r["detail"],
                "enemy": r["enemy"],
                "monthly_avg": r["monthly_avg"],
            }
            for _, r in grouped.iterrows()
        }

        tsv = generate_achieve_tsv(monthly_averages)

        st.text_area(
            "コピー用テキスト（Ctrl+A → Ctrl+C）",
            value=tsv,
            height=280,
        )

        st.download_button(
            label="📥 achieve.tsv をダウンロード",
            data=tsv.encode("utf-8-sig"),
            file_name="achieve_data.tsv",
            mime="text/tab-separated-values",
        )

    if st.button("← 戻る"):
        st.session_state.step = 4
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# メインルーター
# ─────────────────────────────────────────────────────────────────────────────

show_header()

step = st.session_state.step
if step == 1:
    step1_profile()
elif step == 2:
    step2_input()
elif step == 3:
    step3_review()
elif step == 4:
    step4_analysis()
elif step == 5:
    step5_export()
