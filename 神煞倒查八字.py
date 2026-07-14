#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字逆向推理引擎 - 最终完整版（共60种）
用法：运行后按提示输入条件，输入 run 求解，输入 exit 退出
"""

# ==================== 基础常量与编码 ====================
STEMS = ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸"]
BRANCHES = ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"]

# 六十甲子纳音五行（0金 1水 2木 3火 4土）
NAYIN_WUXING = [
    0,0,3,3,2,2,4,4,0,0,
    3,3,1,1,4,4,0,0,2,2,
    1,1,4,4,3,3,2,2,1,1,
    0,0,3,3,2,2,4,4,0,0,
    3,3,1,1,4,4,0,0,2,2,
    2,2,1,1,4,4,2,2,1,1
]

def gz_index(stem, branch):
    return (6 * stem - 5 * branch) % 60

def gz_split(index):
    return index % 10, index % 12

MONTH_STEM_BASE = [2,4,6,8,0, 2,4,6,8,0]
def month_stem(year_stem, month_branch):
    return (MONTH_STEM_BASE[year_stem] + (month_branch - 2) % 12) % 10

HOUR_STEM_BASE = [0,2,4,6,8, 0,2,4,6,8]
def hour_stem(day_stem, hour_branch):
    return (HOUR_STEM_BASE[day_stem] + hour_branch) % 10

# ==================== 候选八字与分支工具 ====================
def empty_candidate():
    return {
        "year_stem": None, "year_branch": None,
        "month_stem": None, "month_branch": None,
        "day_stem": None, "day_branch": None,
        "hour_stem": None, "hour_branch": None
    }

def candidate_tuple(cand):
    return (cand["year_stem"], cand["year_branch"],
            cand["month_stem"], cand["month_branch"],
            cand["day_stem"], cand["day_branch"],
            cand["hour_stem"], cand["hour_branch"])

def deduplicate(candidates):
    seen = set()
    result = []
    for c in candidates:
        t = candidate_tuple(c)
        if t not in seen:
            seen.add(t)
            result.append(c)
    return result

def branch_cross_stem_to_branch(cand, src_stem_key, tgt_branch_key, mapping):
    s = cand.get(src_stem_key)
    b = cand.get(tgt_branch_key)
    if s is not None and b is not None:
        target = mapping.get(s)
        if target is None or (isinstance(target, set) and len(target) == 0):
            return []
        if isinstance(target, set):
            return [cand] if b in target else []
        else:
            return [cand] if b == target else []
    if s is not None and b is None:
        target = mapping.get(s)
        if target is None or (isinstance(target, set) and len(target) == 0):
            return []
        if isinstance(target, set):
            return [{**cand, tgt_branch_key: val} for val in target]
        else:
            newc = cand.copy(); newc[tgt_branch_key] = target; return [newc]
    if s is None and b is not None:
        results = []
        for stem, val in mapping.items():
            if isinstance(val, set):
                if b in val:
                    newc = cand.copy(); newc[src_stem_key] = stem; results.append(newc)
            else:
                if b == val:
                    newc = cand.copy(); newc[src_stem_key] = stem; results.append(newc)
        return results
    results = []
    for stem, val in mapping.items():
        if isinstance(val, set) and len(val) == 0:
            continue
        targets = val if isinstance(val, set) else {val}
        for tgt in targets:
            newc = cand.copy(); newc[src_stem_key] = stem; newc[tgt_branch_key] = tgt
            results.append(newc)
    return results

def branch_cross_branch_to_branch(cand, src_branch_key, tgt_branch_key, mapping):
    sb = cand.get(src_branch_key)
    tb = cand.get(tgt_branch_key)
    if callable(mapping):
        mapping_dict = {b: mapping(b) for b in range(12)}
    else:
        mapping_dict = mapping
    if sb is not None and tb is not None:
        target = mapping_dict.get(sb)
        if target is None or (isinstance(target, set) and len(target) == 0):
            return []
        if isinstance(target, set):
            return [cand] if tb in target else []
        else:
            return [cand] if tb == target else []
    if sb is not None and tb is None:
        target = mapping_dict.get(sb)
        if target is None or (isinstance(target, set) and len(target) == 0):
            return []
        if isinstance(target, set):
            return [{**cand, tgt_branch_key: val} for val in target]
        else:
            newc = cand.copy(); newc[tgt_branch_key] = target; return [newc]
    if sb is None and tb is not None:
        results = []
        for src, val in mapping_dict.items():
            if isinstance(val, set):
                if tb in val:
                    newc = cand.copy(); newc[src_branch_key] = src; results.append(newc)
            else:
                if tb == val:
                    newc = cand.copy(); newc[src_branch_key] = src; results.append(newc)
        return results
    results = []
    for src, val in mapping_dict.items():
        targets = val if isinstance(val, set) else {val}
        for tgt in targets:
            newc = cand.copy(); newc[src_branch_key] = src; newc[tgt_branch_key] = tgt
            results.append(newc)
    return results

# ==================== 神煞引擎 ====================
def make_fixed_set_rule(indices, stem_key, branch_key):
    def rule(cand, target_pillar=None):
        s = cand.get(stem_key); b = cand.get(branch_key)
        if s is not None and b is not None:
            return [cand] if gz_index(s, b) in indices else []
        elif s is not None and b is None:
            pairs = [(s, b) for b in range(12) if gz_index(s, b) in indices]
            return [{**cand, branch_key: b} for _, b in pairs]
        elif s is None and b is not None:
            pairs = [(s, b) for s in range(10) if gz_index(s, b) in indices]
            return [{**cand, stem_key: s} for s, _ in pairs]
        else:
            return [{**cand, stem_key: idx%10, branch_key: idx%12} for idx in indices]
    return rule

def make_rule_from_method(method, target_pillar):
    if method.get("source_kind") == "none":
        return make_fixed_set_rule(method["fixed_pillars"],
                                   target_pillar + "_stem",
                                   target_pillar + "_branch")
    source_kind = method["source_kind"]
    target_kind = method["target_kind"]
    tgt_key = method["target_key_template"].format(pillar=target_pillar)
    mapping = method["mapping"]

    if source_kind == "stem" and target_kind == "branch":
        def rule(cand, _tp=None):
            return branch_cross_stem_to_branch(cand, method["source_key"], tgt_key, mapping)
        return rule

    if source_kind == "branch" and target_kind == "branch":
        def rule(cand, _tp=None):
            return branch_cross_branch_to_branch(cand, method["source_key"], tgt_key, mapping)
        return rule

    if source_kind == "stem" and target_kind == "pillar":
        def rule(cand, _tp=None):
            src = cand.get(method["source_key"])
            if src is None:
                return [cand]
            target_idx = mapping.get(src)
            if target_idx is None: return []
            exp_s, exp_b = gz_split(target_idx)
            cur_s = cand.get(target_pillar + "_stem")
            cur_b = cand.get(target_pillar + "_branch")
            if cur_s is not None and cur_b is not None:
                actual_idx = gz_index(cur_s, cur_b)
                return [cand] if actual_idx == target_idx else []
            elif cur_s is not None and cur_b is None:
                if cur_s != exp_s: return []
                newc = cand.copy(); newc[target_pillar + "_branch"] = exp_b; return [newc]
            elif cur_s is None and cur_b is not None:
                if cur_b != exp_b: return []
                newc = cand.copy(); newc[target_pillar + "_stem"] = exp_s; return [newc]
            else:
                newc = cand.copy()
                newc[target_pillar + "_stem"] = exp_s
                newc[target_pillar + "_branch"] = exp_b
                return [newc]
        return rule

    if source_kind == "nayin_wuxing" and target_kind == "branch":
        def rule(cand, _tp=None):
            prefix = method["source_key"]
            s = cand.get(prefix + "_stem"); b = cand.get(prefix + "_branch")
            if s is None or b is None:
                return [cand]
            idx = gz_index(s, b)
            wx = NAYIN_WUXING[idx]
            target = mapping.get(wx)
            if target is None: return []
            cur = cand.get(tgt_key)
            if cur is not None:
                return [cand] if cur == target else []
            else:
                newc = cand.copy(); newc[tgt_key] = target; return [newc]
        return rule

    raise NotImplementedError("不支持的方法类型")

def make_multi_method_rule(methods, target_pillar):
    rules = [make_rule_from_method(m, target_pillar) for m in methods]
    if len(rules) == 1:
        return rules[0]
    def combined(cand, target_pillar=None):
        results = []
        for r in rules:
            results.extend(r(cand, target_pillar))
        return results
    return combined

# ==================== 神煞数据 ====================
HEAVENLY_HE = {0:5, 1:6, 2:7, 3:8, 4:9, 5:0, 6:1, 7:2, 8:3, 9:4}
EARTHLY_HE = {0:1, 1:0, 2:11, 11:2, 3:10, 10:3, 4:9, 9:4, 5:8, 8:5, 6:7, 7:6}
WUXING_LIST = [2, 2, 3, 3, 4, 4, 0, 0, 1, 1]
def stems_ke(s1, s2):
    w1, w2 = WUXING_LIST[s1], WUXING_LIST[s2]
    return (w1==2 and w2==4) or (w1==3 and w2==0) or (w1==4 and w2==1) or (w1==0 and w2==2) or (w1==1 and w2==3)

# 固定集合
KUIGANG_INDICES = {16,46,4,34,28,58}
LIUXIU_INDICES = {42,43,24,54,25,55}
YINCHAYANGCUO_INDICES = {27,28,29,42,43,44,57,58,59,12,13,14}
SHIEDABAI_INDICES = {40,41,8,32,23,16,34,59,17,25}
BAZHUAN_INDICES = {50,51,43,34,55,56,57,49,4,25}
JINSHEN_INDICES = {1,5,9}
SHILING_INDICES = {40,11,52,33,54,46,26,47,38,19}
JIUCHOU_INDICES = {48,18,24,54,45,15,21,51,57,27}
GULUAN_INDICES = {41,53,47,44,50,42,54,48}

# 干->支映射
LU_MAP = {0:2,1:3,2:5,3:6,4:5,5:6,6:8,7:9,8:11,9:0}
JINYU_MAP = {0:4,1:5,2:7,3:8,4:7,5:8,6:10,7:11,8:1,9:2}
WENCHANG_MAP = {0:5,1:6,2:8,3:9,4:8,5:9,6:11,7:0,8:2,9:3}
FUXING_MAP = {0:{2,0},2:{2,0}, 1:{3,1},9:{3,1}, 4:{8},5:{7},3:{11},6:{6},7:{5},8:{4}}
TAIJI_MAP = {0:{0,6},1:{0,6}, 2:{3,9},3:{3,9}, 4:{4,10,1,7},5:{4,10,1,7}, 6:{2,11},7:{2,11}, 8:{5,8},9:{5,8}}
GUOYIN_MAP = {0:10,1:11,2:1,3:2,4:1,5:2,6:4,7:5,8:7,9:8}
HONGYAN_MAP = {0:6,1:8,2:2,3:7,4:4,5:4,6:10,7:9,8:0,9:8}
YANGREN_MAP = {0:3,1:2,2:6,4:6,3:5,5:5,6:9,7:8,8:0,9:11}
LIUXIA_MAP = {0:9,1:10,2:7,3:8,4:5,5:6,6:4,7:3,8:11,9:2}
TIANYI_MAP = {0:{1,7},4:{1,7}, 1:{0,8},5:{0,8}, 2:{11,9},3:{11,9}, 6:{2,6},7:{2,6}, 8:{3,5},9:{3,5}}
TIANCHU_MAP = {0:{5},1:{6},2:{5},3:{6},4:{8}, 5:{9}, 6:{11},7:{0},8:{2},9:{3}}
CIGUAN_MAP = {0:26,1:27,2:41,3:54,4:53,5:6,6:8,7:9,8:59,9:58}

# 支->支映射
PITOU_MAP = {0:4,1:3,2:2,3:1,4:10,5:11,6:10,7:9,8:8,9:7,10:6,11:5}
PIMA_MAP = {0:9,1:10,2:11,3:0,4:3,5:2,6:3,7:4,8:5,9:6,10:7,11:8}
HONGLUAN_MAP = {0:3,1:2,2:1,3:0,4:11,5:10,6:9,7:8,8:7,9:6,10:5,11:4}
TIANXI_MAP = {0:9,1:8,2:7,3:6,4:5,5:4,6:3,7:2,8:1,9:0,10:11,11:10}
XUEREN_MAP = {2:1,3:7,4:2,5:8,6:3,7:9,8:4,9:10,10:5,11:11,0:6,1:0}

def bingfu_map(b): return (b-1)%12
def sangmen_map(b): return (b+2)%12
def diaoke_map(b): return (b-2)%12
def goujiao_set(b): return {(b+3)%12, (b-3)%12}
def yuanchen_set(b): chong = (b+6)%12; return {(chong+1)%12, (chong-1)%12}

def sanhe_mapping(pivot_map):
    mapping = {}
    for triad, result in pivot_map.items():
        for b in triad:
            mapping[b] = result
    return mapping

TAOHUA_MAP = sanhe_mapping({(8,0,4):9, (2,6,10):3, (11,3,7):0, (5,9,1):6})
YIMA_MAP = sanhe_mapping({(8,0,4):2, (2,6,10):8, (5,9,1):11, (11,3,7):5})
HUAGAI_MAP = sanhe_mapping({(2,6,10):10, (8,0,4):4, (5,9,1):1, (11,3,7):7})
JIANGXING_MAP = sanhe_mapping({(2,6,10):6, (8,0,4):0, (5,9,1):9, (11,3,7):3})
WANGSHEN_MAP = sanhe_mapping({(8,0,4):11, (2,6,10):5, (11,3,7):2, (5,9,1):8})
JIESHA_MAP = sanhe_mapping({(8,0,4):5, (2,6,10):11, (11,3,7):8, (5,9,1):2})
ZAISHA_MAP = sanhe_mapping({(8,0,4):6, (2,6,10):0, (11,3,7):9, (5,9,1):3})
LIUE_MAP = sanhe_mapping({(2,6,10):9, (8,0,4):3, (5,9,1):0, (11,3,7):6})
JINGUI_MAP = sanhe_mapping({(8,0,4):0, (11,3,7):3, (2,6,10):6, (5,9,1):9})

GUCHEN_MAP = {2:5,3:5,4:5, 5:8,6:8,7:8, 8:11,9:11,10:11, 11:2,0:2,1:2}
GUASU_MAP = {2:1,3:1,4:1, 5:4,6:4,7:4, 8:7,9:7,10:7, 11:10,0:10,1:10}

SIFEI_MAP = {
    2:{26,27},3:{26,27},4:{26,27}, 5:{48,59},6:{48,59},7:{48,59},
    8:{50,51},9:{50,51},10:{50,51}, 11:{42,53},0:{42,53},1:{42,53}
}

# ==================== 神煞生成器 ====================
def generator_tianshe(pillar):
    if pillar != "day": raise ValueError("天赦仅用于日柱")
    TIAN_SHE = {2:{14},3:{14},4:{14},5:{30},6:{30},7:{30},8:{44},9:{44},10:{44},11:{0},0:{0},1:{0}}
    def rule(cand, target_pillar=None):
        mb = cand["month_branch"]; ds = cand["day_stem"]; db = cand["day_branch"]
        day_idx = None
        if ds is not None and db is not None:
            day_idx = gz_index(ds, db)
        if mb is not None and day_idx is not None:
            return [cand] if mb in TIAN_SHE and day_idx in TIAN_SHE[mb] else []
        if mb is not None and mb in TIAN_SHE:
            results = []
            for idx in TIAN_SHE[mb]:
                s,b = gz_split(idx)
                if (ds is None or ds==s) and (db is None or db==b):
                    newc = cand.copy(); newc["day_stem"]=s; newc["day_branch"]=b
                    results.append(newc)
            return results
        if day_idx is not None and mb is None:
            results = []
            for m, indices in TIAN_SHE.items():
                if day_idx in indices:
                    newc = cand.copy(); newc["month_branch"]=m; results.append(newc)
            return results
        results = []
        for m, indices in TIAN_SHE.items():
            for idx in indices:
                s,b = gz_split(idx)
                if (ds is None or ds==s) and (db is None or db==b):
                    newc = cand.copy(); newc["month_branch"]=m; newc["day_stem"]=s; newc["day_branch"]=b
                    results.append(newc)
        return results
    return rule

def generator_tiande(pillar):
    map_data = {
        2:{"stem":3}, 3:{"branch":8}, 4:{"stem":8}, 5:{"stem":7},
        6:{"branch":11}, 7:{"stem":0}, 8:{"stem":9}, 9:{"branch":2},
        10:{"stem":2}, 11:{"stem":1}, 0:{"branch":5}, 1:{"stem":6}
    }
    def rule(cand, target_pillar=None):
        mb = cand["month_branch"]
        if mb is None: return [cand]
        cond = map_data[mb]
        if "stem" in cond:
            ts = cand.get(f"{pillar}_stem")
            if ts is not None:
                return [cand] if ts == cond["stem"] else []
            else:
                newc = cand.copy(); newc[f"{pillar}_stem"] = cond["stem"]; return [newc]
        else:
            tb = cand.get(f"{pillar}_branch")
            if tb is not None:
                return [cand] if tb == cond["branch"] else []
            else:
                newc = cand.copy(); newc[f"{pillar}_branch"] = cond["branch"]; return [newc]
    return rule

def generator_tiande_he(pillar):
    tiande_map = {
        2:{"stem":3}, 3:{"branch":8}, 4:{"stem":8}, 5:{"stem":7},
        6:{"branch":11}, 7:{"stem":0}, 8:{"stem":9}, 9:{"branch":2},
        10:{"stem":2}, 11:{"stem":1}, 0:{"branch":5}, 1:{"stem":6}
    }
    def rule(cand, target_pillar=None):
        mb = cand["month_branch"]
        if mb is None: return [cand]
        cond = tiande_map[mb]
        if "stem" in cond:
            he_stem = HEAVENLY_HE[cond["stem"]]
            ts = cand.get(f"{pillar}_stem")
            if ts is not None:
                return [cand] if ts == he_stem else []
            else:
                newc = cand.copy(); newc[f"{pillar}_stem"] = he_stem; return [newc]
        else:
            he_branch = EARTHLY_HE[cond["branch"]]
            tb = cand.get(f"{pillar}_branch")
            if tb is not None:
                return [cand] if tb == he_branch else []
            else:
                newc = cand.copy(); newc[f"{pillar}_branch"] = he_branch; return [newc]
    return rule

def generator_yuede(pillar):
    yue_de = {8:8,0:8,4:8, 11:0,3:0,7:0, 2:2,6:2,10:2, 5:6,9:6,1:6}
    def rule(cand, target_pillar=None):
        mb = cand["month_branch"]
        if mb is None: return [cand]
        ts = cand.get(f"{pillar}_stem")
        expected = yue_de[mb]
        if ts is not None:
            return [cand] if ts == expected else []
        else:
            newc = cand.copy(); newc[f"{pillar}_stem"] = expected; return [newc]
    return rule

def generator_yuede_he(pillar):
    yuede_map = {8:8,0:8,4:8, 11:0,3:0,7:0, 2:2,6:2,10:2, 5:6,9:6,1:6}
    def rule(cand, target_pillar=None):
        mb = cand["month_branch"]
        if mb is None: return [cand]
        he_stem = HEAVENLY_HE[yuede_map[mb]]
        ts = cand.get(f"{pillar}_stem")
        if ts is not None:
            return [cand] if ts == he_stem else []
        else:
            newc = cand.copy(); newc[f"{pillar}_stem"] = he_stem; return [newc]
    return rule

def generator_tianluodiwang(pillar):
    if pillar != "day": raise ValueError("天罗地网仅用于日柱")
    def rule(cand, target_pillar=None):
        ys = cand["year_stem"]; yb = cand["year_branch"]; db = cand["day_branch"]
        if ys is None or yb is None: return [cand]
        year_idx = gz_index(ys, yb)
        wx = NAYIN_WUXING[year_idx]
        if wx == 3: valid = {10,11}
        elif wx in (1,4): valid = {4,5}
        else: return [cand]
        if db is not None:
            return [cand] if db in valid else []
        else:
            return [dict(cand, day_branch=b) for b in valid]
    return rule

def generator_liuxia(pillar):
    method = {
        "source_kind": "stem", "source_key": "day_stem",
        "target_kind": "branch", "target_key_template": "{pillar}_branch",
        "mapping": LIUXIA_MAP
    }
    return make_rule_from_method(method, pillar)

def generator_xuetang(pillar):
    chang_sheng = {2:11, 3:2, 4:8, 0:5, 1:8}
    def rule(cand, target_pillar=None):
        ys = cand["year_stem"]; yb = cand["year_branch"]
        if ys is None or yb is None: return [cand]
        year_idx = gz_index(ys, yb)
        wx = NAYIN_WUXING[year_idx]
        expected = chang_sheng[wx]
        tb = cand.get(f"{pillar}_branch")
        if tb is not None:
            return [cand] if tb == expected else []
        else:
            newc = cand.copy(); newc[f"{pillar}_branch"] = expected; return [newc]
    return rule

def generator_tianchu(pillar):
    methods = [
        {"source_kind":"stem","source_key":"day_stem","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":TIANCHU_MAP},
        {"source_kind":"stem","source_key":"year_stem","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":TIANCHU_MAP}
    ]
    return make_multi_method_rule(methods, pillar)

def generator_shiling(pillar):
    if pillar not in ("day", "hour"):
        raise ValueError("十灵仅适用于日柱或时柱")
    return make_fixed_set_rule(SHILING_INDICES, f"{pillar}_stem", f"{pillar}_branch")

def generator_yegui(pillar):
    if pillar != "hour": raise ValueError("夜贵仅适用于时柱")
    YEGUI_DAY_INDICES = {29, 33}
    YEGUI_HOUR_BRANCHES = {9,10,11,0,1,2}
    def rule(cand, target_pillar=None):
        ds = cand["day_stem"]; db = cand["day_branch"]; hb = cand["hour_branch"]
        day_idx = None
        if ds is not None and db is not None:
            day_idx = gz_index(ds, db)
        if day_idx is not None:
            if day_idx not in YEGUI_DAY_INDICES:
                return []
            if hb is not None:
                return [cand] if hb in YEGUI_HOUR_BRANCHES else []
            else:
                return [dict(cand, hour_branch=b) for b in YEGUI_HOUR_BRANCHES]
        results = []
        for idx in YEGUI_DAY_INDICES:
            s, b = gz_split(idx)
            if (ds is None or ds==s) and (db is None or db==b):
                if hb is not None:
                    if hb in YEGUI_HOUR_BRANCHES:
                        newc = cand.copy(); newc["day_stem"]=s; newc["day_branch"]=b; results.append(newc)
                else:
                    for hb_val in YEGUI_HOUR_BRANCHES:
                        newc = cand.copy(); newc["day_stem"]=s; newc["day_branch"]=b; newc["hour_branch"]=hb_val
                        results.append(newc)
        return results
    return rule

def generator_jiuchou(pillar):
    if pillar != "day": raise ValueError("九丑仅适用于日柱")
    return make_fixed_set_rule(JIUCHOU_INDICES, "day_stem", "day_branch")

def generator_fanyin(pillar):
    if pillar == "day": raise ValueError("反吟不能用于日柱自身")
    def rule(cand, target_pillar=None):
        ds = cand["day_stem"]; db = cand["day_branch"]
        ts = cand.get(f"{pillar}_stem"); tb = cand.get(f"{pillar}_branch")
        if ds is None or db is None: return [cand]
        cond1 = (ts is None or ts==ds) and (tb is None or tb==(db+6)%12)
        he_branch = EARTHLY_HE[db]
        cond2 = (tb is None or tb==he_branch) and (ts is None or stems_ke(ts, ds))
        if ts is not None and tb is not None:
            ok1 = (ts==ds and tb==(db+6)%12)
            ok2 = (tb==he_branch and stems_ke(ts, ds))
            return [cand] if (ok1 or ok2) else []
        candidates_pairs = set()
        if ts is None or ts==ds:
            b1 = (db+6)%12
            if tb is None or tb==b1:
                candidates_pairs.add((ds, b1))
        if tb is None or tb==he_branch:
            b2 = he_branch
            for s2 in range(10):
                if stems_ke(s2, ds):
                    if ts is None or ts==s2:
                        candidates_pairs.add((s2, b2))
        results = []
        for s, b in candidates_pairs:
            if (ts is None or ts==s) and (tb is None or tb==b):
                newc = cand.copy()
                newc[f"{pillar}_stem"] = s
                newc[f"{pillar}_branch"] = b
                results.append(newc)
        if not results and (ts is not None or tb is not None):
            return []
        return results if results else [cand]
    return rule

def generator_yuanchen(pillar):
    methods = [
        {"source_kind":"branch","source_key":"day_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":yuanchen_set},
        {"source_kind":"branch","source_key":"year_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":yuanchen_set}
    ]
    return make_multi_method_rule(methods, pillar)

def generator_sanqi(pillar):
    def rule(cand, target_pillar=None):
        ys, ms, ds, hs = cand["year_stem"], cand["month_stem"], cand["day_stem"], cand["hour_stem"]
        if None in (ys, ms, ds, hs): return [cand]
        seq1 = (ys, ms, ds)
        seq2 = (ms, ds, hs)
        def check(seq):
            if set(seq) == {0,4,6}: return True
            if set(seq) == {1,2,3}: return True
            if set(seq) == {7,8,9}: return True
            return False
        return [cand] if check(seq1) or check(seq2) else []
    return rule

def generator_xueren(pillar):
    method = {"source_kind":"branch","source_key":"month_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":XUEREN_MAP}
    return make_rule_from_method(method, pillar)

def generator_guluan(pillar):
    if pillar == "day":
        return make_fixed_set_rule(GULUAN_INDICES, "day_stem", "day_branch")
    elif pillar == "hour":
        def rule(cand, target_pillar=None):
            ds, db = cand["day_stem"], cand["day_branch"]
            hs, hb = cand["hour_stem"], cand["hour_branch"]
            day_idx = gz_index(ds, db) if ds is not None and db is not None else None
            hour_idx = gz_index(hs, hb) if hs is not None and hb is not None else None
            if day_idx is not None and day_idx not in GULUAN_INDICES: return []
            if hour_idx is not None and hour_idx not in GULUAN_INDICES: return []
            possible_days = [idx for idx in GULUAN_INDICES if (ds is None or ds==idx%10) and (db is None or db==idx%12)]
            possible_hours = [idx for idx in GULUAN_INDICES if (hs is None or hs==idx%10) and (hb is None or hb==idx%12)]
            if not possible_days or not possible_hours: return []
            results = []
            for d in possible_days:
                for h in possible_hours:
                    newc = cand.copy()
                    newc["day_stem"], newc["day_branch"] = d%10, d%12
                    newc["hour_stem"], newc["hour_branch"] = h%10, h%12
                    results.append(newc)
            return results
        return rule
    else:
        raise ValueError("孤鸾仅适用于日柱或时柱")

def generator_sifei(pillar):
    if pillar != "day": raise ValueError("四废仅适用于日柱")
    def rule(cand, target_pillar=None):
        mb = cand["month_branch"]; ds = cand["day_stem"]; db = cand["day_branch"]
        if mb is None: return [cand]
        if mb not in SIFEI_MAP: return []
        allowed = SIFEI_MAP[mb]
        if ds is not None and db is not None:
            idx = gz_index(ds, db)
            return [cand] if idx in allowed else []
        results = []
        for idx in allowed:
            s,b = idx%10, idx%12
            if (ds is None or ds==s) and (db is None or db==b):
                newc = cand.copy(); newc["day_stem"]=s; newc["day_branch"]=b
                results.append(newc)
        return results
    return rule

def generator_liujiakongwang(pillar):
    def rule(cand, target_pillar=None):
        ds = cand["day_stem"]
        if ds is None: return [cand]
        yang_count = yin_count = 0
        for p in ["year","month","day","hour"]:
            s = cand[p+"_stem"]; b = cand[p+"_branch"]
            if s is not None and b is not None:
                if s % 2 == 0: yang_count += 1
                else: yin_count += 1
                if b % 2 == 0: yang_count += 1
                else: yin_count += 1
            else:
                return [cand]
        if (ds % 2 == 0 and yang_count > yin_count) or (ds % 2 != 0 and yang_count < yin_count):
            return [cand]
        else:
            return []
    return rule

def generator_xunkong(pillar):
    def rule(cand, target_pillar=None):
        ds = cand["day_stem"]; db = cand["day_branch"]
        if ds is None or db is None: return [cand]
        day_idx = gz_index(ds, db)
        xunshou_idx = day_idx - (day_idx % 10)
        xunshou_branch = xunshou_idx % 12
        kong1 = (xunshou_branch + 10) % 12
        kong2 = (xunshou_branch + 11) % 12
        kong_set = {kong1, kong2}
        tb = cand.get(f"{pillar}_branch")
        if tb is not None:
            return [cand] if tb in kong_set else []
        else:
            return [dict(cand, **{f"{pillar}_branch": b}) for b in kong_set]
    return rule

def generator_feiren(pillar):
    mapping = {stem: (YANGREN_MAP[stem] + 6) % 12 for stem in range(10)}
    method = {
        "source_kind": "stem",
        "source_key": "day_stem",
        "target_kind": "branch",
        "target_key_template": "{pillar}_branch",
        "mapping": mapping
    }
    return make_rule_from_method(method, pillar)

def generator_tianyi_yue(pillar):
    method = {
        "source_kind": "branch",
        "source_key": "month_branch",
        "target_kind": "branch",
        "target_key_template": "{pillar}_branch",
        "mapping": lambda b: (b - 1) % 12
    }
    return make_rule_from_method(method, pillar)

def generator_tongzi(pillar):
    season_branch_map = {
        2: {2, 0}, 3: {2, 0}, 4: {2, 0},
        5: {3, 7, 4}, 6: {3, 7, 4}, 7: {3, 7, 4},
        8: {2, 0}, 9: {2, 0}, 10: {2, 0},
        11: {3, 7, 4}, 0: {3, 7, 4}, 1: {3, 7, 4}
    }
    nayin_branch_map = {
        0: {6, 3}, 2: {6, 3},
        1: {9, 10}, 3: {9, 10},
        4: {4, 5}
    }
    nayin_stem_map = {
        0: {0, 1}, 2: {2, 3}, 1: {4, 5}, 3: {6, 7}, 4: {8, 9}
    }

    def rule_season(cand):
        mb = cand["month_branch"]
        if mb is None: return [cand]
        valid = season_branch_map.get(mb, set())
        if not valid: return []
        tb = cand.get(f"{pillar}_branch")
        if tb is not None:
            return [cand] if tb in valid else []
        else:
            return [{**cand, f"{pillar}_branch": b} for b in valid]

    def rule_nayin_branch(cand):
        ys, yb = cand["year_stem"], cand["year_branch"]
        if ys is None or yb is None: return [cand]
        year_idx = gz_index(ys, yb)
        wx = NAYIN_WUXING[year_idx]
        valid = nayin_branch_map.get(wx, set())
        if not valid: return []
        tb = cand.get(f"{pillar}_branch")
        if tb is not None:
            return [cand] if tb in valid else []
        else:
            return [{**cand, f"{pillar}_branch": b} for b in valid]

    def rule_nayin_stem(cand):
        if pillar != "day": return [cand]
        ys, yb = cand["year_stem"], cand["year_branch"]
        if ys is None or yb is None: return [cand]
        year_idx = gz_index(ys, yb)
        wx = NAYIN_WUXING[year_idx]
        valid = nayin_stem_map.get(wx, set())
        ts = cand.get("day_stem")
        if ts is not None:
            return [cand] if ts in valid else []
        else:
            return [{**cand, "day_stem": s} for s in valid]

    def combined(cand, target_pillar=None):
        results = []
        for r in [rule_season, rule_nayin_branch, rule_nayin_stem]:
            results.extend(r(cand))
        return results
    return combined

def generator_dexiu(pillar):
    def get_dexiu_sets(month_branch):
        if month_branch in (2, 6, 10):   # 寅午戌
            return {2,3}, {4,9}
        elif month_branch in (8, 0, 4):  # 申子辰
            return {8,9,4,5}, {2,7,0,5}
        elif month_branch in (5, 9, 1):  # 巳酉丑
            return {6,7}, {1,6}
        elif month_branch in (11, 3, 7): # 亥卯未
            return {0,1}, {3,8}
        else:
            return set(), set()
    def rule(cand, target_pillar=None):
        mb = cand["month_branch"]
        if mb is None: return [cand]
        de_set, xiu_set = get_dexiu_sets(mb)
        valid = de_set | xiu_set
        ts = cand.get(f"{pillar}_stem")
        if ts is not None:
            return [cand] if ts in valid else []
        else:
            return [{**cand, f"{pillar}_stem": s} for s in valid]
    return rule

# 新增：暗金
def generator_anjin(pillar):
    if pillar != "hour":
        raise ValueError("暗金仅适用于时柱（年支查时支）")
    anjin_map = {
        0: {5}, 6: {5}, 3: {5}, 9: {5},   # 子午卯酉 -> 巳
        2: {9}, 8: {9}, 5: {9}, 11: {9},  # 寅申巳亥 -> 酉
        4: {1}, 10: {1}, 1: {1}, 7: {1}   # 辰戌丑未 -> 丑
    }
    method = {
        "source_kind": "branch",
        "source_key": "year_branch",
        "target_kind": "branch",
        "target_key_template": "{pillar}_branch",
        "mapping": anjin_map
    }
    return make_rule_from_method(method, pillar)

# ==================== 注册与输入解析 ====================
import re

SHENSHA_LIST = [
    ("魁罡", lambda p: make_fixed_set_rule(KUIGANG_INDICES, "day_stem", "day_branch")),
    ("六秀", lambda p: make_fixed_set_rule(LIUXIU_INDICES, "day_stem", "day_branch")),
    ("阴差阳错", lambda p: make_fixed_set_rule(YINCHAYANGCUO_INDICES, "day_stem", "day_branch")),
    ("十恶大败", lambda p: make_fixed_set_rule(SHIEDABAI_INDICES, "day_stem", "day_branch")),
    ("八专", lambda p: make_fixed_set_rule(BAZHUAN_INDICES, "day_stem", "day_branch")),
    ("金神", lambda p: make_fixed_set_rule(JINSHEN_INDICES, "day_stem", "day_branch")),
    ("禄神", [{"source_kind":"stem","source_key":"day_stem","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":LU_MAP}]),
    ("金舆", [
        {"source_kind":"stem","source_key":"day_stem","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":JINYU_MAP},
        {"source_kind":"stem","source_key":"year_stem","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":JINYU_MAP}
    ]),
    ("阳刃", [{"source_kind":"stem","source_key":"day_stem","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":YANGREN_MAP}]),
    ("披头", [{"source_kind":"branch","source_key":"year_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":PITOU_MAP}]),
    ("披麻", [{"source_kind":"branch","source_key":"year_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":PIMA_MAP}]),
    ("红鸾", [{"source_kind":"branch","source_key":"year_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":HONGLUAN_MAP}]),
    ("天喜", [{"source_kind":"branch","source_key":"year_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":TIANXI_MAP}]),
    ("丧门", [{"source_kind":"branch","source_key":"year_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":sangmen_map}]),
    ("吊客", [{"source_kind":"branch","source_key":"year_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":diaoke_map}]),
    ("病符", [{"source_kind":"branch","source_key":"year_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":bingfu_map}]),
    ("钩绞", [{"source_kind":"branch","source_key":"year_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":goujiao_set}]),
    ("桃花", [{"source_kind":"branch","source_key":"year_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":TAOHUA_MAP},
              {"source_kind":"branch","source_key":"day_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":TAOHUA_MAP}]),
    ("驿马", [{"source_kind":"branch","source_key":"year_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":YIMA_MAP},
              {"source_kind":"branch","source_key":"day_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":YIMA_MAP}]),
    ("华盖", [{"source_kind":"branch","source_key":"year_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":HUAGAI_MAP},
              {"source_kind":"branch","source_key":"day_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":HUAGAI_MAP}]),
    ("将星", [{"source_kind":"branch","source_key":"year_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":JIANGXING_MAP},
              {"source_kind":"branch","source_key":"day_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":JIANGXING_MAP}]),
    ("亡神", [{"source_kind":"branch","source_key":"year_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":WANGSHEN_MAP},
              {"source_kind":"branch","source_key":"day_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":WANGSHEN_MAP}]),
    ("劫煞", [{"source_kind":"branch","source_key":"year_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":JIESHA_MAP},
              {"source_kind":"branch","source_key":"day_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":JIESHA_MAP}]),
    ("灾煞", [{"source_kind":"branch","source_key":"year_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":ZAISHA_MAP}]),
    ("六厄", [{"source_kind":"branch","source_key":"year_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":LIUE_MAP}]),
    ("金匮", [{"source_kind":"branch","source_key":"year_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":JINGUI_MAP}]),
    ("文昌", [{"source_kind":"stem","source_key":"day_stem","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":WENCHANG_MAP},
             {"source_kind":"stem","source_key":"year_stem","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":WENCHANG_MAP}]),
    ("福星贵人", [{"source_kind":"stem","source_key":"day_stem","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":FUXING_MAP},
                {"source_kind":"stem","source_key":"year_stem","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":FUXING_MAP}]),
    ("太极贵人", [{"source_kind":"stem","source_key":"day_stem","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":TAIJI_MAP},
                {"source_kind":"stem","source_key":"year_stem","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":TAIJI_MAP}]),
    ("国印贵人", [{"source_kind":"stem","source_key":"day_stem","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":GUOYIN_MAP},
                {"source_kind":"stem","source_key":"year_stem","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":GUOYIN_MAP}]),
    ("天乙贵人", [{"source_kind":"stem","source_key":"day_stem","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":TIANYI_MAP},
                {"source_kind":"stem","source_key":"year_stem","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":TIANYI_MAP}]),
    ("红艳", [{"source_kind":"stem","source_key":"day_stem","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":HONGYAN_MAP},
             {"source_kind":"stem","source_key":"year_stem","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":HONGYAN_MAP}]),
    ("词馆", [
        {"source_kind":"stem","source_key":"day_stem","target_kind":"pillar","target_key_template":"{pillar}","mapping":CIGUAN_MAP},
        {"source_kind":"stem","source_key":"year_stem","target_kind":"pillar","target_key_template":"{pillar}","mapping":CIGUAN_MAP},
        {"source_kind":"nayin_wuxing","source_key":"year","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":{2:2,3:5,4:11,0:8,1:11}}
    ]),
    ("孤辰", [{"source_kind":"branch","source_key":"year_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":GUCHEN_MAP},
              {"source_kind":"branch","source_key":"day_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":GUCHEN_MAP}]),
    ("寡宿", [{"source_kind":"branch","source_key":"year_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":GUASU_MAP},
              {"source_kind":"branch","source_key":"day_branch","target_kind":"branch","target_key_template":"{pillar}_branch","mapping":GUASU_MAP}]),
    ("天赦", generator_tianshe),
    ("天德", generator_tiande),
    ("天德合", generator_tiande_he),
    ("月德", generator_yuede),
    ("月德合", generator_yuede_he),
    ("天罗地网", generator_tianluodiwang),
    ("流霞", generator_liuxia),
    ("学堂", generator_xuetang),
    ("天厨", generator_tianchu),
    ("十灵", generator_shiling),
    ("夜贵", generator_yegui),
    ("九丑", generator_jiuchou),
    ("反吟", generator_fanyin),
    ("元辰", generator_yuanchen),
    ("三奇贵人", generator_sanqi),
    ("血刃", generator_xueren),
    ("孤鸾", generator_guluan),
    ("四废", generator_sifei),
    ("六甲空亡", generator_liujiakongwang),
    ("空亡", generator_xunkong),
    ("飞刃", generator_feiren),
    ("天医", generator_tianyi_yue),
    ("童子", generator_tongzi),
    ("德秀贵人", generator_dexiu),
    ("暗金", generator_anjin),
]

SHENSHA_ALIASES = {
    "天乙": "天乙贵人",
    "天德贵人": "天德",
    "天德贵": "天德",
    "月德贵人": "月德",
    "月德贵": "月德",
    "魁罡日": "魁罡",
    "魁罡贵人": "魁罡",
    "六秀日": "六秀",
    "六秀贵人": "六秀",
    "阴差阳错日": "阴差阳错",
    "十恶大败日": "十恶大败",
    "十恶": "十恶大败",
    "八专日": "八专",
    "八专贵人": "八专",
    "九丑日": "九丑",
    "孤鸾日": "孤鸾",
    "孤鸾煞": "孤鸾",
    "四废日": "四废",
    "十灵日": "十灵",
    "十灵时": "十灵",
    "十灵贵人": "十灵",
    "金神日": "金神",
    "金神时": "金神",
    "禄神贵人": "禄神",
    "金舆贵人": "金舆",
    "羊刃": "阳刃",
    "阳刃贵人": "阳刃",
    "飞刃煞": "飞刃",
    "文昌贵人": "文昌",
    "福星": "福星贵人",
    "太极": "太极贵人",
    "国印": "国印贵人",
    "天厨贵人": "天厨",
    "天厨贵": "天厨",
    "词馆贵人": "词馆",
    "学堂贵人": "学堂",
    "天赦日": "天赦",
    "天德合贵人": "天德合",
    "月德合贵人": "月德合",
    "天罗": "天罗地网",
    "地网": "天罗地网",
    "反吟煞": "反吟",
    "大耗": "元辰",
    "元辰煞": "元辰",
    "旬空": "空亡",
    "旬空亡": "空亡",
    "空亡煞": "空亡",
    "咸池": "桃花",
    "桃花煞": "桃花",
    "驿马星": "驿马",
    "华盖贵人": "华盖",
    "将星贵人": "将星",
    "劫煞贵人": "劫煞",
    "白虎煞": "灾煞",
    "灾煞贵人": "灾煞",
    "亡神煞": "亡神",
    "金匮星": "金匮",
    "金匮贵人": "金匮",
    "血刃煞": "血刃",
    "童子煞": "童子",
    "童子女": "童子",
    "童子贵": "童子",
    "夜贵贵人": "夜贵",
    "孤辰煞": "孤辰",
    "寡宿煞": "寡宿",
    "三奇": "三奇贵人",
    "六甲空亡煞": "六甲空亡",
    "流霞煞": "流霞",
    "红艳煞": "红艳",
    "天医贵人": "天医",
    "天医贵": "天医",
    "披头煞": "披头",
    "披麻煞": "披麻",
    "丧门煞": "丧门",
    "吊客煞": "吊客",
    "病符煞": "病符",
    "钩绞煞": "钩绞",
    "红鸾星": "红鸾",
    "天喜星": "天喜",
    "德秀": "德秀贵人",
    "暗金煞": "暗金",
}

def resolve_shensha_alias(name):
    return SHENSHA_ALIASES.get(name, name)

RULE_GENERATORS = {}

def register(name, generator):
    RULE_GENERATORS[name] = generator

for name, data in SHENSHA_LIST:
    if isinstance(data, list):
        register(name, lambda p, m=data: make_multi_method_rule(m, p))
    else:
        register(name, data)

def parse_condition(cond_str):
    pillar_map = {"年柱":"year","月柱":"month","日柱":"day","时柱":"hour"}
    pattern = r"^(年柱|月柱|日柱|时柱)(.+)$"
    m = re.match(pattern, cond_str.strip())
    if not m:
        raise ValueError("格式错误，应为：柱位+神煞名，如 日柱禄神")
    pillar = pillar_map[m.group(1)]
    rest = m.group(2).strip()
    opt_match = re.match(r"(.+?)\((.+)\)$", rest)
    if opt_match:
        shensha = opt_match.group(1).strip()
        option = opt_match.group(2).strip()
    else:
        shensha = rest
        option = None
    shensha = resolve_shensha_alias(shensha)
    if shensha not in RULE_GENERATORS:
        raise ValueError(f"未知神煞: {shensha}")
    return pillar, shensha, option

# ==================== 约束求解器 ====================
class ConstraintSolver:
    def __init__(self):
        self.rules = []
        self.builtin = [self._validate_pillars, self._validate_month, self._validate_hour]
        self.user_conditions = set()

    def add_rule(self, rule_func, pillar, shensha):
        self.rules.append(rule_func)
        self.user_conditions.add((pillar, shensha))

    def _validate_pillars(self, cand):
        for p in ["year", "month", "day", "hour"]:
            s = cand[p + "_stem"]; b = cand[p + "_branch"]
            if s is not None and b is not None and s % 2 != b % 2:
                return []
        return [cand]

    def _validate_month(self, cand):
        ys = cand["year_stem"]; mb = cand["month_branch"]; ms = cand["month_stem"]
        if ys is not None and mb is not None:
            correct = month_stem(ys, mb)
            if ms is None:
                newc = cand.copy(); newc["month_stem"] = correct; return [newc]
            elif ms != correct:
                return []
        elif ys is not None and ms is not None and mb is None:
            return [{**cand, "month_branch": b} for b in range(12) if month_stem(ys, b) == ms]
        elif ms is not None and mb is not None and ys is None:
            offset = (mb - 2) % 12
            base_first = (ms - offset) % 10
            return [{**cand, "year_stem": y} for y in range(10) if MONTH_STEM_BASE[y] == base_first]
        return [cand]

    def _validate_hour(self, cand):
        ds = cand["day_stem"]; hb = cand["hour_branch"]; hs = cand["hour_stem"]
        if ds is not None and hb is not None:
            correct = hour_stem(ds, hb)
            if hs is None:
                newc = cand.copy(); newc["hour_stem"] = correct; return [newc]
            elif hs != correct:
                return []
        elif ds is not None and hs is not None and hb is None:
            return [{**cand, "hour_branch": b} for b in range(12) if hour_stem(ds, b) == hs]
        elif hs is not None and hb is not None and ds is None:
            base = (hs - hb) % 10
            return [{**cand, "day_stem": d} for d in range(10) if HOUR_STEM_BASE[d] == base]
        return [cand]

    def solve(self, strict=False, max_iter=20):
        candidates = [empty_candidate()]
        for _ in range(max_iter):
            new_candidates = []
            for cand in candidates:
                temp = [cand]
                for rule in self.rules + self.builtin:
                    next_temp = []
                    for c in temp:
                        next_temp.extend(rule(c))
                    temp = next_temp
                    if not temp:
                        break
                new_candidates.extend(temp)
            new_candidates = deduplicate(new_candidates)
            if set(candidate_tuple(c) for c in candidates) == set(candidate_tuple(c) for c in new_candidates):
                break
            candidates = new_candidates
            if not candidates:
                break
        if strict:
            candidates = self._strict_filter(candidates)
        else:
            if 0 < len(candidates) <= 500:
                completed = []
                for c in candidates:
                    completed.extend(self._complete_candidate(c))
                candidates = deduplicate(completed)
        return candidates

    def _complete_candidate(self, cand):
        results = [cand]
        new_results = []
        for c in results:
            ys = c["year_stem"]; mb = c["month_branch"]; ms = c["month_stem"]
            if ys is not None:
                if mb is None and ms is None:
                    for b in range(12):
                        nc = c.copy(); nc["month_branch"] = b; nc["month_stem"] = month_stem(ys, b)
                        new_results.append(nc)
                elif mb is None and ms is not None:
                    for b in range(12):
                        if month_stem(ys, b) == ms:
                            nc = c.copy(); nc["month_branch"] = b; new_results.append(nc)
                elif mb is not None and ms is None:
                    nc = c.copy(); nc["month_stem"] = month_stem(ys, mb); new_results.append(nc)
                else:
                    new_results.append(c)
            else:
                new_results.append(c)
        results = new_results
        new_results = []
        for c in results:
            ds = c["day_stem"]; hb = c["hour_branch"]; hs = c["hour_stem"]
            if ds is not None:
                if hb is None and hs is None:
                    for b in range(12):
                        nc = c.copy(); nc["hour_branch"] = b; nc["hour_stem"] = hour_stem(ds, b)
                        new_results.append(nc)
                elif hb is None and hs is not None:
                    for b in range(12):
                        if hour_stem(ds, b) == hs:
                            nc = c.copy(); nc["hour_branch"] = b; new_results.append(nc)
                elif hb is not None and hs is None:
                    nc = c.copy(); nc["hour_stem"] = hour_stem(ds, hb); new_results.append(nc)
                else:
                    new_results.append(c)
            else:
                new_results.append(c)
        results = new_results
        for p in ["year","day"]:
            new_results = []
            for c in results:
                s = c[p+"_stem"]; b = c[p+"_branch"]
                if s is None and b is None:
                    for i in range(10):
                        for j in range(12):
                            if i%2 == j%2:
                                nc = c.copy(); nc[p+"_stem"]=i; nc[p+"_branch"]=j; new_results.append(nc)
                elif s is not None and b is None:
                    for j in range(12):
                        if s%2 == j%2:
                            nc = c.copy(); nc[p+"_branch"]=j; new_results.append(nc)
                elif s is None and b is not None:
                    for i in range(10):
                        if i%2 == b%2:
                            nc = c.copy(); nc[p+"_stem"]=i; new_results.append(nc)
                else:
                    new_results.append(c)
            results = new_results
        return results

    def _strict_filter(self, candidates):
        final = []
        for c in candidates:
            completed = self._complete_candidate(c)
            for full in completed:
                if not self._has_extra_shensha(full):
                    final.append(full)
        return deduplicate(final)

    def _has_extra_shensha(self, full_cand):
        for shensha_name, gen in RULE_GENERATORS.items():
            for pillar in ["year","month","day","hour"]:
                if (pillar, shensha_name) in self.user_conditions:
                    continue
                try:
                    rule = gen(pillar) if callable(gen) else gen
                    res = rule(full_cand)
                    if res: return True
                except (ValueError, TypeError):
                    pass
        return False

# ==================== 主入口 ====================
def format_candidate(c):
    def fmt(s, b):
        if s is None and b is None: return "??"
        s_str = STEMS[s] if s is not None else "?"
        b_str = BRANCHES[b] if b is not None else "?"
        return s_str + b_str
    return (f"{fmt(c['year_stem'],c['year_branch'])} "
            f"{fmt(c['month_stem'],c['month_branch'])} "
            f"{fmt(c['day_stem'],c['day_branch'])} "
            f"{fmt(c['hour_stem'],c['hour_branch'])}")

if __name__ == "__main__":
    solver = ConstraintSolver()
    print("输入神煞条件（如：日柱魁罡 年柱桃花），可选加 --strict 启用排他模式，输入 'run' 开始求解，输入 'exit' 退出：")
    while True:
        cmd = input(">> ").strip()
        if cmd.lower() == "exit":
            break
        elif cmd.lower() == "run":
            strict = getattr(solver, 'strict', False)
            results = solver.solve(strict=strict)
            print(f"找到 {len(results)} 个候选八字：")
            for c in results:
                print(format_candidate(c))
        else:
            strict = False
            if cmd.endswith(" --strict"):
                strict = True
                cond_str = cmd[:-9].strip()
            else:
                cond_str = cmd
            try:
                pillar, shensha, option = parse_condition(cond_str)
                gen = RULE_GENERATORS[shensha]
                rule = gen(pillar)
                solver.add_rule(rule, pillar, shensha)
                if strict: solver.strict = True
                print(f"已添加条件：{cond_str}" + (" (排他模式将在求解时启用)" if strict else ""))
            except Exception as e:
                print(f"错误：{e}")