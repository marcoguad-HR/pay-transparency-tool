"""
Generate a mock CSV with 150 employees for testing the pay transparency reporting feature.

Data design:
- Departments: Engineering, Finance, Marketing, Sales, HR, Legal, Operations
- Levels: Junior, Mid, Senior, Lead, Director
- Gender: M / F  (~53% M, ~47% F)
- Pay gaps intentionally varied:
    - Engineering Senior/Lead: ~12%  → NON COMPLIANT
    - Finance Senior/Lead:     ~8%   → NON COMPLIANT
    - Legal Senior/Lead:       ~6%   → NON COMPLIANT
    - Operations Mid/Senior:   ~7%   → NON COMPLIANT
    - Sales (all levels):      ~-3%  → COMPLIANT (women paid slightly more due to bonus)
    - HR (all levels):         ~1%   → COMPLIANT
    - Marketing (all levels):  ~4%   → COMPLIANT

Usage:
    python scripts/generate_mock_employees.py
"""

import csv
import random
from pathlib import Path

random.seed(42)

OUTPUT_PATH = Path(__file__).parent.parent / "data" / "mock_employees_150.csv"

# ---------------------------------------------------------------------------
# Configuration: (dept, level) → (male_range, female_range, bonus_range,
#                                  years_range, age_range, contract_weights)
# contract_weights: [full-time, part-time, temporary]
# ---------------------------------------------------------------------------

DEPT_LEVEL_CONFIG = {
    # Engineering — gap ampio a Senior/Lead
    ("Engineering", "Junior"):    ((28000, 36000), (27000, 35000), (3000, 6000),  (0, 3),  (22, 28), [0.75, 0.10, 0.15]),
    ("Engineering", "Mid"):       ((40000, 54000), (38000, 51000), (4000, 8000),  (3, 7),  (26, 34), [0.80, 0.10, 0.10]),
    ("Engineering", "Senior"):    ((58000, 76000), (51000, 66000), (6000, 12000), (6, 12), (30, 40), [0.85, 0.05, 0.10]),
    ("Engineering", "Lead"):      ((72000, 95000), (63000, 83000), (9000, 16000), (10, 18),(34, 46), [0.90, 0.05, 0.05]),
    ("Engineering", "Director"):  ((92000, 128000),(86000, 118000),(14000, 22000),(15, 25),(40, 55), [0.95, 0.05, 0.00]),

    # Finance — gap medio-alto a Senior+
    ("Finance", "Junior"):        ((27000, 36000), (26500, 35000), (2500, 5500),  (0, 3),  (22, 28), [0.70, 0.15, 0.15]),
    ("Finance", "Mid"):           ((39000, 52000), (37000, 50000), (4000, 8000),  (3, 7),  (26, 34), [0.80, 0.10, 0.10]),
    ("Finance", "Senior"):        ((56000, 74000), (51000, 67000), (7000, 13000), (6, 12), (30, 42), [0.85, 0.05, 0.10]),
    ("Finance", "Lead"):          ((70000, 93000), (63000, 84000), (10000, 18000),(10, 18),(35, 48), [0.90, 0.05, 0.05]),
    ("Finance", "Director"):      ((93000, 130000),(87000, 120000),(15000, 24000),(15, 25),(40, 56), [0.95, 0.05, 0.00]),

    # Marketing — gap contenuto (~4%)
    ("Marketing", "Junior"):      ((28000, 37000), (27500, 36000), (3000, 6500),  (0, 3),  (22, 28), [0.65, 0.20, 0.15]),
    ("Marketing", "Mid"):         ((37000, 50000), (36000, 48000), (4000, 8500),  (3, 7),  (26, 34), [0.75, 0.15, 0.10]),
    ("Marketing", "Senior"):      ((50000, 67000), (48000, 64000), (6000, 11000), (6, 12), (30, 40), [0.80, 0.10, 0.10]),
    ("Marketing", "Lead"):        ((64000, 86000), (62000, 82000), (8000, 14000), (10, 18),(34, 46), [0.85, 0.10, 0.05]),

    # Sales — donne leggermente più pagate grazie a bonus
    ("Sales", "Junior"):          ((27000, 36000), (27500, 37000), (4000, 9000),  (0, 3),  (22, 28), [0.70, 0.10, 0.20]),
    ("Sales", "Mid"):             ((36000, 49000), (37000, 50500), (6000, 12000), (3, 7),  (26, 34), [0.75, 0.10, 0.15]),
    ("Sales", "Senior"):          ((48000, 65000), (49500, 66500), (8000, 15000), (6, 12), (30, 40), [0.80, 0.10, 0.10]),

    # HR — quasi parità (~1%)
    ("HR", "Junior"):             ((27000, 35000), (26800, 34800), (2500, 5000),  (0, 3),  (22, 28), [0.65, 0.20, 0.15]),
    ("HR", "Mid"):                ((36000, 48000), (35800, 47500), (3500, 7000),  (3, 7),  (26, 34), [0.70, 0.20, 0.10]),
    ("HR", "Senior"):             ((48000, 63000), (47500, 62500), (5000, 9000),  (6, 12), (30, 40), [0.75, 0.15, 0.10]),

    # Legal — gap moderato a Senior/Lead (~6%)
    ("Legal", "Mid"):             ((42000, 56000), (40000, 53000), (5000, 9000),  (3, 7),  (26, 36), [0.80, 0.10, 0.10]),
    ("Legal", "Senior"):          ((60000, 80000), (55000, 73000), (8000, 14000), (6, 12), (30, 42), [0.85, 0.05, 0.10]),
    ("Legal", "Lead"):            ((76000, 100000),(70000, 91000), (11000, 18000),(10, 18),(35, 48), [0.90, 0.05, 0.05]),

    # Operations — gap medio-alto (~7%)
    ("Operations", "Junior"):     ((27000, 36000), (26000, 34500), (2000, 5000),  (0, 3),  (22, 28), [0.65, 0.15, 0.20]),
    ("Operations", "Mid"):        ((37000, 50000), (34000, 46500), (3500, 7500),  (3, 7),  (26, 34), [0.75, 0.15, 0.10]),
    ("Operations", "Senior"):     ((50000, 67000), (46000, 61000), (5000, 10000), (6, 12), (30, 40), [0.80, 0.10, 0.10]),
    ("Operations", "Lead"):       ((65000, 87000), (60000, 80000), (7000, 13000), (10, 18),(34, 46), [0.85, 0.10, 0.05]),
}

CONTRACT_TYPES = ["full-time", "part-time", "temporary"]

# ---------------------------------------------------------------------------
# Employee slots: (dept, level, n_male, n_female)
# Total = 150  (79M + 71F)
# Each combo has ≥ 2M and ≥ 2F to meet minimum group size for gap analysis
# ---------------------------------------------------------------------------

SLOTS = [
    # Engineering (total 30)
    ("Engineering", "Junior",    3, 2),
    ("Engineering", "Mid",       4, 3),
    ("Engineering", "Senior",    5, 3),
    ("Engineering", "Lead",      4, 2),
    ("Engineering", "Director",  2, 2),
    # Finance (total 24)
    ("Finance", "Junior",        2, 2),
    ("Finance", "Mid",           3, 3),
    ("Finance", "Senior",        4, 3),
    ("Finance", "Lead",          3, 2),
    ("Finance", "Director",      2, 2),
    # Marketing (total 20)
    ("Marketing", "Junior",      3, 3),
    ("Marketing", "Mid",         3, 3),
    ("Marketing", "Senior",      2, 2),
    ("Marketing", "Lead"),       # placeholder — will set below
    # Sales (total 18)
    ("Sales", "Junior",          3, 3),
    ("Sales", "Mid",             3, 3),
    ("Sales", "Senior",          2, 2),
    # HR (total 16)
    ("HR", "Junior",             2, 3),
    ("HR", "Mid",                2, 3),
    ("HR", "Senior",             2, 2),
    # Legal (total 13)
    ("Legal", "Mid",             2, 2),
    ("Legal", "Senior",          3, 2),
    ("Legal", "Lead",            2, 2),
    # Operations (total 18 target)
    ("Operations", "Junior",     3, 2),
    ("Operations", "Mid",        3, 3),
    ("Operations", "Senior",     3, 2),
    ("Operations", "Lead"),       # placeholder
]

# Replace placeholders with proper tuples
SLOTS = [
    # Engineering — 30 tot
    ("Engineering", "Junior",    3, 2),
    ("Engineering", "Mid",       4, 3),
    ("Engineering", "Senior",    5, 3),
    ("Engineering", "Lead",      4, 2),
    ("Engineering", "Director",  2, 2),

    # Finance — 26 tot
    ("Finance", "Junior",        2, 2),
    ("Finance", "Mid",           3, 3),
    ("Finance", "Senior",        4, 3),
    ("Finance", "Lead",          3, 2),
    ("Finance", "Director",      2, 2),

    # Marketing — 23 tot
    ("Marketing", "Junior",      3, 3),
    ("Marketing", "Mid",         4, 3),
    ("Marketing", "Senior",      3, 3),
    ("Marketing", "Lead",        2, 2),

    # Sales — 21 tot
    ("Sales", "Junior",          4, 3),
    ("Sales", "Mid",             4, 4),
    ("Sales", "Senior",          3, 3),

    # HR — 16 tot
    ("HR", "Junior",             3, 3),
    ("HR", "Mid",                3, 3),
    ("HR", "Senior",             2, 2),

    # Legal — 13 tot
    ("Legal", "Mid",             2, 2),
    ("Legal", "Senior",          3, 2),
    ("Legal", "Lead",            2, 2),

    # Operations — 21 tot
    ("Operations", "Junior",     3, 2),
    ("Operations", "Mid",        3, 3),
    ("Operations", "Senior",     3, 2),
    ("Operations", "Lead",       3, 2),
]

# Verify total
total_employees = sum(m + f for _, _, m, f in SLOTS)
assert total_employees == 150, f"Expected 150 employees, got {total_employees}"


def rand_salary(lo: int, hi: int) -> int:
    """Round to nearest 100 EUR for realism."""
    raw = random.randint(lo, hi)
    return round(raw / 100) * 100


def rand_bonus(lo: int, hi: int, has_bonus: bool) -> int:
    if not has_bonus:
        return 0
    raw = random.randint(lo, hi)
    return round(raw / 100) * 100


def generate_employees() -> list[dict]:
    employees = []
    emp_counter = 1

    for dept, level, n_male, n_female in SLOTS:
        cfg = DEPT_LEVEL_CONFIG[(dept, level)]
        male_range, female_range, bonus_range, years_range, age_range, contract_w = cfg

        for gender, count, sal_range in (
            ("M", n_male, male_range),
            ("F", n_female, female_range),
        ):
            for _ in range(count):
                emp_id = f"EMP{emp_counter:04d}"
                emp_counter += 1

                has_bonus = random.random() < 0.65
                base_salary = rand_salary(*sal_range)
                bonus = rand_bonus(*bonus_range, has_bonus)
                total_compensation = base_salary + bonus
                years_exp = random.randint(*years_range)
                age = random.randint(*age_range)
                contract = random.choices(CONTRACT_TYPES, weights=contract_w, k=1)[0]

                employees.append({
                    "employee_id": emp_id,
                    "department": dept,
                    "level": level,
                    "gender": gender,
                    "base_salary": base_salary,
                    "bonus": bonus,
                    "total_compensation": total_compensation,
                    "years_experience": years_exp,
                    "age": age,
                    "contract_type": contract,
                })

    # Shuffle to avoid ordered grouping in CSV
    random.shuffle(employees)

    # Re-assign sequential IDs after shuffle
    for i, emp in enumerate(employees, start=1):
        emp["employee_id"] = f"EMP{i:04d}"

    return employees


def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    employees = generate_employees()

    fieldnames = [
        "employee_id", "department", "level", "gender",
        "base_salary", "bonus", "total_compensation",
        "years_experience", "age", "contract_type",
    ]

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(employees)

    print(f"Generated {len(employees)} employees → {OUTPUT_PATH}")

    # Quick stats
    male_count = sum(1 for e in employees if e["gender"] == "M")
    female_count = sum(1 for e in employees if e["gender"] == "F")
    avg_male = sum(e["base_salary"] for e in employees if e["gender"] == "M") / male_count
    avg_female = sum(e["base_salary"] for e in employees if e["gender"] == "F") / female_count
    overall_gap = (avg_male - avg_female) / avg_male * 100

    print(f"  Male:   {male_count} ({male_count/len(employees)*100:.1f}%)")
    print(f"  Female: {female_count} ({female_count/len(employees)*100:.1f}%)")
    print(f"  Avg salary M: €{avg_male:,.0f}  |  F: €{avg_female:,.0f}")
    print(f"  Overall pay gap: {overall_gap:.1f}%")

    depts = sorted({e["department"] for e in employees})
    print("\n  Per-department avg salary gap (M vs F):")
    for dept in depts:
        dept_emps = [e for e in employees if e["department"] == dept]
        m_salaries = [e["base_salary"] for e in dept_emps if e["gender"] == "M"]
        f_salaries = [e["base_salary"] for e in dept_emps if e["gender"] == "F"]
        if m_salaries and f_salaries:
            m_avg = sum(m_salaries) / len(m_salaries)
            f_avg = sum(f_salaries) / len(f_salaries)
            gap = (m_avg - f_avg) / m_avg * 100
            status = "NON-COMPLIANT" if gap > 5 else "compliant"
            print(f"    {dept:<14} M€{m_avg:>7,.0f}  F€{f_avg:>7,.0f}  gap={gap:+.1f}%  [{status}]")


if __name__ == "__main__":
    main()
