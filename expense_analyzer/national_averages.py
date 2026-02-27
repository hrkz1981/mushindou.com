"""
全国平均データ（総務省 家計調査 2023年ベース）とプロフィール補正。
"""
from typing import Optional

# ── リスト定義 ──────────────────────────────────────────────────────────

PREFECTURE_LIST = [
    "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
    "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
    "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県",
    "岐阜県", "静岡県", "愛知県", "三重県",
    "滋賀県", "京都府", "大阪府", "兵庫県", "奈良県", "和歌山県",
    "鳥取県", "島根県", "岡山県", "広島県", "山口県",
    "徳島県", "香川県", "愛媛県", "高知県",
    "福岡県", "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県",
]

OCCUPATION_LIST = [
    "医師・歯科医師",
    "弁護士・会計士等の専門職",
    "IT・エンジニア",
    "管理職（部長以上）",
    "管理職（課長クラス）",
    "教師・研究者",
    "公務員（国家・地方）",
    "営業職",
    "事務職・一般職",
    "看護師・医療専門職",
    "販売・接客",
    "製造業・技能職",
    "建設・土木",
    "運輸・物流",
    "飲食・サービス業",
    "パート・アルバイト",
    "フリーランス・自営業",
    "その他・不明",
]

FAMILY_TYPE_LIST = [
    "単身（一人暮らし）",
    "夫婦のみ",
    "夫婦＋子供1人",
    "夫婦＋子供2人",
    "夫婦＋子供3人以上",
    "ひとり親＋子供",
]

AGE_LIST = [
    "20代前半 (20-24歳)",
    "20代後半 (25-29歳)",
    "30代前半 (30-34歳)",
    "30代後半 (35-39歳)",
    "40代前半 (40-44歳)",
    "40代後半 (45-49歳)",
    "50代前半 (50-54歳)",
    "50代後半 (55-59歳)",
    "60代 (60-69歳)",
    "70歳以上",
]

# ── 都道府県別 物価指数（消費者物価指数地域差指数ベース）────────────────

PREFECTURE_COST_INDEX: dict[str, float] = {
    "北海道": 0.97, "青森県": 0.94, "岩手県": 0.94, "宮城県": 0.97,
    "秋田県": 0.94, "山形県": 0.95, "福島県": 0.95,
    "茨城県": 0.98, "栃木県": 0.97, "群馬県": 0.97,
    "埼玉県": 1.01, "千葉県": 1.01, "東京都": 1.07, "神奈川県": 1.04,
    "新潟県": 0.96, "富山県": 0.97, "石川県": 0.98, "福井県": 0.97,
    "山梨県": 0.98, "長野県": 0.97,
    "岐阜県": 0.97, "静岡県": 0.99, "愛知県": 1.01, "三重県": 0.98,
    "滋賀県": 0.99, "京都府": 1.02, "大阪府": 1.03, "兵庫県": 1.01,
    "奈良県": 1.00, "和歌山県": 0.97,
    "鳥取県": 0.95, "島根県": 0.95, "岡山県": 0.97, "広島県": 0.99, "山口県": 0.96,
    "徳島県": 0.97, "香川県": 0.97, "愛媛県": 0.96, "高知県": 0.97,
    "福岡県": 0.98, "佐賀県": 0.95, "長崎県": 0.95, "熊本県": 0.95,
    "大分県": 0.95, "宮崎県": 0.94, "鹿児島県": 0.95, "沖縄県": 0.97,
}

# ── 職種別 年収目安（万円/年）────────────────────────────────────────────

OCCUPATION_ANNUAL_INCOME: dict[str, int] = {
    "医師・歯科医師": 1200,
    "弁護士・会計士等の専門職": 900,
    "IT・エンジニア": 620,
    "管理職（部長以上）": 750,
    "管理職（課長クラス）": 620,
    "教師・研究者": 550,
    "公務員（国家・地方）": 540,
    "営業職": 500,
    "事務職・一般職": 380,
    "看護師・医療専門職": 490,
    "販売・接客": 350,
    "製造業・技能職": 420,
    "建設・土木": 460,
    "運輸・物流": 440,
    "飲食・サービス業": 330,
    "パート・アルバイト": 160,
    "フリーランス・自営業": 450,
    "その他・不明": 460,
}

# ── 年齢別 平均手取り月収目安（万円）────────────────────────────────────

AGE_INCOME_REFERENCE: dict[str, int] = {
    "20代前半 (20-24歳)": 18,
    "20代後半 (25-29歳)": 22,
    "30代前半 (30-34歳)": 27,
    "30代後半 (35-39歳)": 30,
    "40代前半 (40-44歳)": 33,
    "40代後半 (45-49歳)": 35,
    "50代前半 (50-54歳)": 36,
    "50代後半 (55-59歳)": 35,
    "60代 (60-69歳)": 28,
    "70歳以上": 20,
}

# ── 家族構成別 乗数（基準:夫婦のみ=1.0）────────────────────────────────

FAMILY_FACTOR: dict[str, float] = {
    "単身（一人暮らし）": 1.0,   # 単身は別テーブルを使うので乗数は1.0
    "夫婦のみ": 1.0,
    "夫婦＋子供1人": 1.25,
    "夫婦＋子供2人": 1.50,
    "夫婦＋子供3人以上": 1.70,
    "ひとり親＋子供": 0.85,
}

# ── group名 → 大分類キー ─────────────────────────────────────────────────

GROUP_TO_CATEGORY: dict[str, Optional[str]] = {
    "食費（食料品）": "food",
    "食費（コンビニ）": "food",
    "食費（外食）": "food_dining",
    "住居費": "housing",
    "光熱費（電気）": "utilities",
    "光熱費（ガス）": "utilities",
    "光熱費（水道）": "utilities",
    "通信費（携帯）": "communication",
    "通信費（ネット）": "communication",
    "通信費（NHK）": "communication",
    "交通費（車）": "transportation",
    "交通費（公共）": "transportation",
    "日用品費": "household",
    "衣服費": "clothing",
    "医療費": "medical",
    "医療費（薬）": "medical",
    "美容費": "beauty",
    "教育・習い事費": "education",
    "書籍・教材費": "education_books",
    "娯楽費（旅行）": "entertainment",
    "娯楽費（エンタメ）": "entertainment",
    "娯楽費（ゲーム）": "entertainment",
    "保険": "insurance",
    "サブスク": "entertainment",
    "買物（通販）": "other",
    "買物（家電・家具）": "other",
    "交際費": "social",
    "ペット費": "other",
    # 比較対象外
    "ローン返済": None,
    "年間費・税金": None,
    "車両費": None,
    "資産運用": None,
    "給与収入": None,
    "副業・雑収入": None,
    "未分類": None,
}

# ── 全国平均月額（単身世帯）────────────────────────────────────────────
# 総務省 家計調査 2023年 単身勤労者世帯 ベース

BASE_SINGLE: dict[str, int] = {
    "food": 40000,
    "food_dining": 14000,
    "housing": 26000,
    "utilities": 13000,
    "communication": 8500,
    "transportation": 11000,
    "household": 5000,
    "clothing": 5000,
    "medical": 7500,
    "beauty": 5000,
    "education": 1000,
    "education_books": 3000,
    "entertainment": 16000,
    "insurance": 15000,
    "social": 8000,
    "other": 10000,
}

# ── 全国平均月額（2人以上世帯・夫婦ベース）──────────────────────────────
# 総務省 家計調査 2023年 2人以上勤労者世帯 ベース

BASE_COUPLE: dict[str, int] = {
    "food": 68000,
    "food_dining": 18000,
    "housing": 20000,
    "utilities": 24000,
    "communication": 14000,
    "transportation": 25000,
    "household": 12000,
    "clothing": 9500,
    "medical": 16000,
    "beauty": 8000,
    "education": 17000,
    "education_books": 5000,
    "entertainment": 27000,
    "insurance": 25000,
    "social": 12000,
    "other": 20000,
}

# ── 収入感応度（0=収入に関係なし、1=収入に比例）──────────────────────────

INCOME_SENSITIVITY: dict[str, float] = {
    "food": 0.3,
    "food_dining": 0.7,
    "housing": 0.5,
    "utilities": 0.2,
    "communication": 0.3,
    "transportation": 0.5,
    "household": 0.4,
    "clothing": 0.8,
    "medical": 0.3,
    "beauty": 0.8,
    "education": 0.9,
    "education_books": 0.6,
    "entertainment": 0.9,
    "insurance": 0.6,
    "social": 0.8,
    "other": 0.6,
}

# ── 全国平均月収（手取り目安）──────────────────────────────────────────

NATIONAL_AVG_MONTHLY_INCOME = 295_000  # 円


# ── 公開 API ─────────────────────────────────────────────────────────────

def get_national_average(
    category_name: str,
    family_type: str,
    prefecture: str,
    monthly_income: int,
    occupation: str,
    age: str,
) -> Optional[int]:
    """
    カテゴリ名・プロフィールから補正済み全国平均月額を返す。
    比較対象外の場合は None。
    """
    cat = GROUP_TO_CATEGORY.get(category_name)
    if cat is None:
        return None

    # ── ベース金額（家族構成で切り替え）
    if family_type == "単身（一人暮らし）":
        base = BASE_SINGLE.get(cat, 0)
    else:
        base = BASE_COUPLE.get(cat, 0) * FAMILY_FACTOR.get(family_type, 1.0)

    # ── 都道府県物価補正
    pref_factor = PREFECTURE_COST_INDEX.get(prefecture, 1.0)

    # ── 収入補正
    income_factor = min(max(monthly_income / NATIONAL_AVG_MONTHLY_INCOME, 0.4), 3.0)
    sensitivity = INCOME_SENSITIVITY.get(cat, 0.5)
    income_adj = 1.0 + sensitivity * (income_factor - 1.0)

    return max(int(base * pref_factor * income_adj), 0)


def get_income_reference(occupation: str, age: str) -> dict:
    """職種・年齢から収入参考情報を返す。"""
    occ_annual = OCCUPATION_ANNUAL_INCOME.get(occupation, 460)
    age_monthly_man = AGE_INCOME_REFERENCE.get(age, 30)

    occ_monthly = int(occ_annual * 10_000 / 12 * 0.78)  # 概算手取り（78%）
    age_monthly = age_monthly_man * 10_000

    return {
        "occupation_monthly": occ_monthly,
        "age_monthly": age_monthly,
        "reference": int((occ_monthly + age_monthly) / 2),
    }
