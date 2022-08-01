def modulo_pow(g, a, n):
    powers = [(0, 1 % n), (1, g % n)]
    while powers[-1][0] < a:
        powers.append((2 * powers[-1][0], (powers[-1][1] * powers[-1][1]) % n))
    result = 1
    while a > 0:
        l, r = 0, len(powers)
        while r - l > 1:
            m = (l + r) // 2
            if powers[m][0] > a:
                r = m
            else:
                l = m
        a -= powers[l][0]
        result = (result * powers[l][1]) % n
    return result

def get_hash(string):
    hash1 = 0
    hash2 = 0
    hash3 = 0

    for el in string:
        hash1 = ord(el) + hash1 * 87
        hash1 %= 107615082980437465713051279749
        hash2 = ord(el) + hash2 * 113
        hash2 %= 137990466427355121354087489403
        hash3 = ord(el) + hash3 * 349
        hash3 %= 116408579582897119488769636867
    string = hex(hash1 * hash2 * hash3)[2:]

    string = hex(modulo_pow(int(string, 16), 44119, 6188877205795806793865168313293451905300166784112828958629652578023924231639087489018776084987599339))
    if len(string) < 66:
        string += '0' * (66 - len(string))
    return string[2:66]

