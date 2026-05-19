import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

PATH = r"c:\GitRepo\Study-Materials\Semester-4\English\Monologue_4_Program_Design_and_Computer_Languages.md"

with open(PATH, encoding="utf-8") as f:
    text = f.read()

parts = text.split("## ")
total_sents = 0
total_words = 0
for p in parts[1:]:
    if p.startswith("---"):
        continue
    title, *rest = p.split("\n", 1)
    body = rest[0] if rest else ""
    body = re.sub(r"\*+", "", body)
    body = re.sub(r"^Active Vocabulary.*", "", body, flags=re.MULTILINE)
    body = re.sub(r"^---.*", "", body, flags=re.MULTILINE)
    sub_paras = re.split(r"\n\s*\n", body.strip())
    for sp in sub_paras:
        if not sp.strip():
            continue
        sp_clean = re.sub(r"^\s*\d+\.\d+\.\s*", "", sp)
        sentences = re.findall(r"[^.!?]+[.!?]+", sp_clean)
        sentences = [s for s in sentences if re.search(r"[A-Za-z]", s)]
        words = re.findall(r"\b[A-Za-z]+\b", sp_clean)
        label = title.strip()
        if re.match(r"^\s*\d+\.\d+\.", sp):
            label = label + " / " + re.match(r"^\s*(\d+\.\d+)", sp).group(1)
        print(f"{label:55}  sentences={len(sentences):2}  words={len(words):3}")
        total_sents += len(sentences)
        total_words += len(words)

print(f"{'TOTAL':55}  sentences={total_sents:2}  words={total_words:3}")

vocab = re.findall(r"(?<!\*)\*\*([^*]+?)\*\*(?!\*)", text)
print(f"Vocab items (raw count): {len(vocab)}")
print(f"Unique vocab items: {len(set(vocab))}")

linkers = re.findall(r"\*\*\*([^*]+?)\*\*\*", text)
print(f"Linkers (raw count): {len(linkers)}")
print(f"Unique linkers: {len(set(linkers))}")
