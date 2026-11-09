"""Reference implementation of the DEPD direct / family / total beneficiary rules.
Specification: docs/00_specification.md Section 5.3 to 5.5, docs/kpi_rules.md.
The dashboard must reproduce these results. FAMILY_FACTOR is configuration, not a constant of nature."""
import math

FAMILY_FACTOR = 5                      # config: average family members counted as indirect beneficiaries
NO_W = {'pcrdp', 'assistive_ip', 'regional_dir'}   # no beneficiary summary (Section W hidden)
MISMATCH_TOLERANCE = 0.20             # W vs section figure difference that triggers "review"

def num(v):
    if v is None or v == '' : return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(x) else x

def section_active(r, t):
    """Section-level ACTIVE figure for the facility type: (value, source_label, is_lower_bound)."""
    g = lambda k: num(r.get(k))
    if t in ('rcmhc', 'rcph', 'gov_se', 'gia', 'pcrdp'): return g('c_active'), 'c_active', False
    if t == 'inclusive': return g('n_enrolled'), 'n_enrolled', False
    if t == 'carts':      # sub-programs overlap and parents (v5) are excluded: largest sub-program = lower bound
        v = [g(k) for k in ('v1_active', 'v2_active', 'v3_active', 'v4_active') if g(k) is not None]
        return (max(v) if v else None), 'max(v1..v4_active)', True
    if t == 'nowpdp':
        v = [g(k) for k in ('p2_active', 'p3_active') if g(k) is not None]
        return (max(v) if v else None), 'max(p2_active,p3_active)', True
    return None, None, False

CUM_FIELDS = ('c_cumulative', 'n_integrated', 't_cum', 'u_cum', 'p_cum',
              'Total_Direct_Benefic_since_establishment', 'Cumulative_Disabilit_sued_Since_Inception')
def cumulative(r):
    for k in CUM_FIELDS:
        v = num(r.get(k))
        if v is not None: return v, k
    return None, None

INDIRECT_CATEGORY_FIELDS = ('Parents_Family_Mem_ts_with_disabilities', 'Peer_students_clas_without_disabilities',
                            'Community_members_local_stakeholders', 'Other_school_staff_nistration_personnel')

def reported_indirect(r):
    """Facility-REPORTED indirect reach (outreach / community). Never added to Direct or to the family estimate."""
    for k in ('Total_indirect_reach_since_inception', 'Beneficiary_students_inception_In_Direct',
              'Total_Indirect_Reach_ablishment_Indirect'):
        v = num(r.get(k))
        if v is not None: return v
    return None

def resolve_active(r):
    t = r.get('facility_type'); W = num(r.get('w_total')); S, sf, lower = section_active(r, t); C, _ = cumulative(r)
    if t == 'assistive_ip':   # no W: its direct beneficiaries are the people who received devices in the period
        if str(r.get('r_given', '')).lower() == 'yes':
            ppl = sum(num(r.get(k)) or 0 for k in ('r_male', 'r_female', 'r_trans', 'r_other'))
            return dict(direct=ppl, source='R_recipients', confidence='medium', flags='period_count_not_stock')
        return dict(direct=None, source='not_applicable', confidence='n/a', flags='')
    if t in NO_W: return dict(direct=None, source='not_applicable', confidence='n/a', flags='')
    flags = []
    copied = W is not None and C is not None and S is not None and W == C and S != C   # W copied from cumulative
    if W is not None and W > 0 and not copied:
        d, src, conf = W, 'W', 'high'
        if S is not None and S > 0 and abs(W - S) / max(W, S) > MISMATCH_TOLERANCE:
            flags.append('W_vs_section_mismatch'); conf = 'review'
    elif S is not None and S > 0:
        d, src, conf = S, 'section:' + sf, ('low' if lower else 'medium')
        flags.append('W_copied_from_cumulative' if copied else ('W_zero' if W == 0 else 'W_blank'))
        if lower: flags.append('lower_bound')
    elif W == 0 or S == 0:
        d, src, conf = 0.0, 'zero_report', 'low'; flags.append('all_zero_report')
    else:
        d, src, conf = None, 'no_data', 'n/a'
    return dict(direct=d, source=src, confidence=conf, flags=';'.join(flags))

def resolve_cumulative(r):
    if r.get('facility_type') in NO_W: return dict(direct=None, source='not_collected')
    C, f = cumulative(r)
    return dict(direct=C, source=f or 'not_collected')

def reach(direct, factor=FAMILY_FACTOR):
    """direct (unique people) -> (direct, family_estimate, total_reach). Blank stays blank."""
    if direct is None: return None, None, None
    return direct, direct * factor, direct * (1 + factor)

import pandas as pd

def resolve_dataframe(df: pd.DataFrame, basis: str = "active") -> pd.DataFrame:
    """Apply resolve_active or resolve_cumulative row-by-row and return
    the input df with columns: direct, source, confidence, flags,
    family, total_reach."""
    records = df.to_dict("records")
    if basis == "active":
        results = [resolve_active(r) for r in records]
    elif basis == "cumulative":
        results = [resolve_cumulative(r) for r in records]
    else:
        raise ValueError(f"unknown basis: {basis}")
    res = pd.DataFrame(results)
    # family and total_reach use the module-level FAMILY_FACTOR
    res["family"] = res["direct"].apply(
        lambda x: None if x is None else x * FAMILY_FACTOR
    )
    res["total_reach"] = res["direct"].apply(
        lambda x: None if x is None else x * (1 + FAMILY_FACTOR)
    )
    return pd.concat([df.reset_index(drop=True), res.reset_index(drop=True)], axis=1)

def resolve_reach(direct, factor=None):
    """Wrapper around reach() that uses FAMILY_FACTOR if factor is None."""
    return reach(direct, FAMILY_FACTOR if factor is None else factor)
