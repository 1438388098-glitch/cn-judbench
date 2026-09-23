"""从最高人民法院公报 HTML 抽取法释〔2020〕15号指定条文，逐条写入 lawkb。

verbatim-by-construction：txt 内容直接取自解析出的公报正文，不经手打；
每条附 sha256 text_hash 供事后核。运行前提：.tmp_fetch/gb15.html 存在。
"""
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / ".tmp_fetch" / "gb15.html"
TEXT_DIR = ROOT / "lawkb" / "text"
YAML_PATH = ROOT / "lawkb" / "laws" / "spc_civil_temporal_2020.yaml"
DOC_URL = "gongbao.court.gov.cn/Details/ee50115279a096c479415af97f5a08.html"

TARGET = {
    1: "时间效力一般规则（施行后/施行前/持续性法律事实三款）",
    2: "有利溯及（三个更有利于）",
    3: "新增规定溯及（空白溯及及其限制）",
    4: "原则性规定可依民法典具体规定说理",
    5: "再审不溯及（程序交叉）",
    8: "合同无效认定的新旧法衔接（无效→有效）",
    9: "格式条款提示说明义务溯及适用第四百九十六条",
    20: "跨法合同履行分段适用（衔接适用）",
    25: "解除权行使期限一年衔接规则（期限交叉）",
    27: "保证期间约定不明/未约定的衔接规则（期限交叉）",
}
CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7,
          "八": 8, "九": 9, "十": 10}


def cn2int(cn: str) -> int:
    if cn in CN_NUM:
        return CN_NUM[cn]
    if cn.startswith("十"):
        return 10 + CN_NUM[cn[1:]]
    if cn.endswith("十"):
        return CN_NUM[cn[0]] * 10
    if "十" in cn:
        a, b = cn.split("十")
        return CN_NUM[a] * 10 + CN_NUM[b]
    raise ValueError(cn)


def parse_articles():
    s = HTML.read_text(encoding="utf-8", errors="ignore")
    body = re.search(r'法释〔2020〕15号(.*?)法律声明', s, re.S).group(1)
    body = re.sub(r"<script.*?</script>|<style.*?</style>", "", body, flags=re.S)
    text = re.sub(r"<[^>]+>", "\n", body)
    for ent, ch in [("&nbsp;", " "), ("&ldquo;", "“"), ("&rdquo;", "”"),
                    ("&mdash;", "—"), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">")]:
        text = text.replace(ent, ch)
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    art_re = re.compile(r"^第([一二三四五六七八九十]+)条$")
    sec_re = re.compile(r"^[一二三四五]、")
    arts = {}
    cur = None
    for line in lines:
        m = art_re.match(line)
        if m:
            cur = cn2int(m.group(1))
            arts[cur] = []
            continue
        if sec_re.match(line) or line in ("公　告", "公告") or "最高人民法院" in line:
            cur = None
            continue
        if cur is not None:
            arts[cur].append(line)
    return {n: "".join(ps) for n, ps in arts.items()}


def main():
    arts = parse_articles()
    missing = set(TARGET) - set(arts)
    assert not missing, f"公报文本缺失条文: {missing}"
    for n in TARGET:
        body = arts[n]
        assert body and "<" not in body and len(body) > 30, f"第{n}条抽取异常: {body!r}"
        assert body.endswith("。"), f"第{n}条未以句号结尾: {body[-20:]!r}"
        path = TEXT_DIR / f"spc_civtemp_{n}_2020.txt"
        path.write_bytes(body.encode("utf-8"))

    entries = ["article_version:"]
    for n in sorted(TARGET):
        raw = (TEXT_DIR / f"spc_civtemp_{n}_2020.txt").read_bytes()
        h = hashlib.sha256(raw).hexdigest()
        note = (f"法释〔2020〕15号；第{n}条（{TARGET[n]}）；"
                f"来源：最高人民法院公报 {DOC_URL}")
        entries.append(
            f"- law_id: spc_civil_temporal_2020\n"
            f"  article_no: '{n}'\n"
            f"  version_id: spc_civtemp_{n}_2020\n"
            f"  effective_from: '2021-01-01'\n"
            f"  effective_to: null\n"
            f"  superseded_by: null\n"
            f"  note: {note}\n"
            f"  text_hash: sha256:{h}\n"
            f"  text_ref: text/spc_civtemp_{n}_2020.txt"
        )
    law_block = """law:
  law_id: spc_civil_temporal_2020
  names:
  - 最高人民法院关于适用《中华人民共和国民法典》时间效力的若干规定
  - 民法典时间效力规定
  level: judicial_interpretation
  promulgated_on: '2020-12-14'
  interprets:
  - npc_civil_code
"""
    with open(YAML_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write(law_block + "\n".join(entries) + "\n")
    for n in sorted(TARGET):
        raw = (TEXT_DIR / f"spc_civtemp_{n}_2020.txt").read_bytes()
        print(f"第{n}条 sha256={hashlib.sha256(raw).hexdigest()} bytes={len(raw)}")


if __name__ == "__main__":
    main()
