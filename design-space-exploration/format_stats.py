import sys

def format_line(line):
    args = sys.argv
    prop = args[1]

    ret = line
    ret = ret.split(" ")
    ret = [r for r in ret if r]
    name = ret[0]
    value = float(ret[1])
    name = " ".join(name.split(":")[0].split("/")[-1].split(".")[0].split("-")).capitalize()
    return f"{name}-{prop}-{value}"

try:
    while True:
        line = input()
        print(format_line(line))
except EOFError:
    exit(0)
except Exception as e:
    raise(e)

