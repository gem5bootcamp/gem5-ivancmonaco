import sys

order = []

def format_line(line):


    ret = line
    ret = ret.split(" ")
    ret = [r for r in ret if r]
    name = ret[0]
    name = name.split(":")[0].split("/")[-1].split(".")[0].split("-")
    cores = name[-1]
    name = " ".join(name[:-2])
    # print(name)
    if "x" in name or "x" in cores:
        return


    value = float(ret[1])
    name = name.capitalize()

    print(f"{name},{cores},{value}")

try:
    args = sys.argv
    prop = args[1]
    print(f"Test,Cores,{prop}")
    while True:
        line = input()
        format_line(line)
except EOFError:
    exit(0)
except Exception as e:
    raise(e)

