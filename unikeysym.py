codes = [l.split()[:5] for l in open("keysyms.txt") if not l.startswith("#")]
codes = [l for l in codes if l]
keys = {eval(key): {"unicode": unichr(int(uni[1:], 16)),
                    "status": status,
                    "keyname": keyname}
        for key, uni, status, comment, keyname in codes}
