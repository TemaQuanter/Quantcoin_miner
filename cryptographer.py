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

def get_encrypted_message(message, e, n):
    result = []
    for el in message:
        result.append(str(modulo_pow(ord(el), e, n)))
    return '.'.join(result)

def get_dectypted_message(encrypted_message, d, n):
    result = ''
    for el in map(int, encrypted_message.split('.')):
        result += chr(modulo_pow(el, d, n))
    return result

def get_signature(hash, private_key, public_key):
    return modulo_pow(int(hash, 16), int(private_key, 16), int(public_key, 16))

def get_hash_from_signature(signature, public_key):
    return modulo_pow(int(signature, 16), 65537, int(public_key, 16))